"""Build a self-contained, verifiable historical-replay package for one
already-executed v3 run (spec `historical-replay`, design.md §7).

Reads only already-persisted MLflow artifacts (child + parent run) and a
local raw dataset file already verified by hash; never retrains, infers, or
recalculates any scientific metric. Builds into a private temporary
directory and only publishes it after it round-trips through
`historical_replay.package_loader.load_package` without error — an
inconsistent package is never left at the destination path. The resulting
package loads with `load_package`, offline, without MLflow.

Usage:
    python scripts/build_replay_package.py \
        --run-id-child 1157696b7bb941e394c5af530c762b07 \
        --experiment-id 4 \
        --dataset-path /path/to/melchor_romero_2024_consolidado.parquet \
        --output-dir /path/to/replay_packages/base-seed4-1157696b7b-v2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import pandas as pd

from historical_replay.admission_policy import verify_admitted
from historical_replay.imputation_markers import reconstruct_imputation_markers
from historical_replay.package_loader import load_package

PACKAGE_SCHEMA_VERSION = "historical_replay_package_v2"
_REQUIRED_STATUS = "FINISHED"

KNOWN_LIMITATIONS = [
    "Calibracion no acreditada para este run. El unico motor de evaluacion de "
    "calibracion presente en el repositorio "
    "(predictive_modeling/calibration_assessment.py) no se aplico a este run: "
    "fue introducido en una fecha posterior al commit de ejecucion y "
    "pertenece a otra capacidad (multi-horizon daily predictors).",
    "El marcador de imputacion (derived/imputation_markers.parquet) es un "
    "derivado post-hoc: recomputado deterministicamente a partir de la copia "
    "del dataset ya verificada por hash, no persistido por la corrida original.",
    "target_observed=false no esta ejercitado por ningun ejemplo real de este "
    "run (todas las filas de predictions.json tienen target_observed=true).",
    "El supuesto de disponibilidad diaria de insumos crudos es un supuesto "
    "documentado del protocolo v3, no verificado por fila.",
]


class ProvenanceMissingError(ValueError):
    """The run does not declare the historical dataset hash this build
    requires — never substituted by a hash computed today."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_metadata_section(run) -> dict:
    return {
        "run_id": run.info.run_id,
        "experiment_id": run.info.experiment_id,
        "status": run.info.status,
        "run_name": run.info.run_name,
        "tags": dict(run.data.tags),
        "params": dict(run.data.params),
        "metrics": dict(run.data.metrics),
    }


def build_package(
    *,
    experiment_id: str,
    run_id_child: str,
    dataset_path: Path,
    output_dir: Path,
    tracking_uri: str | None = None,
    exported_at: str | None = None,
) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"El paquete ya existe, no se sobrescribe: {output_dir}")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    client = mlflow.MlflowClient()
    child = client.get_run(run_id_child)
    if child.info.experiment_id != experiment_id:
        raise ValueError(
            f"El run {run_id_child!r} pertenece al experimento "
            f"{child.info.experiment_id!r}, no a {experiment_id!r}. "
            "Se detiene la construccion; no se sustituye el candidato."
        )
    if child.info.status != _REQUIRED_STATUS:
        raise ValueError(
            f"El run {run_id_child!r} tiene estado {child.info.status!r}, se "
            f"requiere {_REQUIRED_STATUS!r}."
        )
    parent_run_id = child.data.tags.get("mlflow.parentRunId")
    if not parent_run_id:
        raise ValueError(
            f"El run {run_id_child!r} no declara mlflow.parentRunId; no se puede "
            "resolver su procedencia completa (dataset_sha256, commit_sha)."
        )
    parent = client.get_run(parent_run_id)
    if parent.info.status != _REQUIRED_STATUS:
        raise ValueError(
            f"El run padre {parent_run_id!r} tiene estado {parent.info.status!r}, "
            f"se requiere {_REQUIRED_STATUS!r}."
        )

    parent_params = dict(parent.data.params)
    parent_metrics = dict(parent.data.metrics)

    historical_dataset_sha256 = parent_params.get("dataset_sha256")
    if not historical_dataset_sha256:
        raise ProvenanceMissingError(
            f"El run padre {parent_run_id!r} no declara dataset_sha256: para este "
            "candidato el hash historico debe existir en la evidencia archivada. "
            "Se rechaza la construccion; nunca se sustituye por un hash calculado hoy."
        )

    actual_dataset_sha256 = _sha256(dataset_path)
    if actual_dataset_sha256 != historical_dataset_sha256:
        raise ValueError(
            "El dataset provisto no coincide con el hash historico del run: "
            f"esperado {historical_dataset_sha256}, obtenido {actual_dataset_sha256}. "
            "Se detiene la construccion; no se arma el paquete con datos inconsistentes."
        )

    # Restriccion aplicada tambien en el constructor, no solo en el lector
    # (defecto corregido en el Paso 3): la acreditacion se decide contra la
    # politica externa (historical_replay.admission_policy), nunca
    # generandola para el run recibido como argumento sin mas. Si algo no
    # coincide, se informa la discrepancia exacta y se detiene la
    # construccion -- no se corrige por inferencia.
    admitted = verify_admitted(
        experiment_id=experiment_id,
        run_id_child=run_id_child,
        run_id_parent=parent_run_id,
        config_name=child.data.params.get("config_name"),
        seed=int(child.data.params["seed"]),
        commit_sha=parent_params.get("commit_sha"),
        dataset_sha256=historical_dataset_sha256,
    )

    staging_parent = output_dir.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-staging-", dir=staging_parent))
    try:
        (staging_dir / "dataset").mkdir()
        (staging_dir / "derived").mkdir()

        predictions_local = Path(client.download_artifacts(run_id_child, "predictions.json"))
        effective_config_local = Path(
            client.download_artifacts(run_id_child, "effective_configuration.json")
        )
        (staging_dir / "predictions.json").write_bytes(predictions_local.read_bytes())
        (staging_dir / "effective_configuration.json").write_bytes(
            effective_config_local.read_bytes()
        )

        run_metadata = {
            "child": _run_metadata_section(child),
            "parent": _run_metadata_section(parent),
        }
        (staging_dir / "run_metadata.json").write_text(
            json.dumps(run_metadata, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

        dataset_dest = staging_dir / "dataset" / dataset_path.name
        dataset_dest.write_bytes(dataset_path.read_bytes())

        contract = json.loads((staging_dir / "effective_configuration.json").read_text())[
            "contract"
        ]
        raw_input_features = contract["raw_input_features"]
        raw = pd.read_parquet(dataset_dest)
        markers = reconstruct_imputation_markers(raw, raw_input_features)
        marker_columns = ["timestamp"] + [f"{c}_imputado" for c in raw_input_features]
        markers[marker_columns].to_parquet(staging_dir / "derived" / "imputation_markers.parquet")

        dataset_rel = f"dataset/{dataset_path.name}"
        experiment_name = client.get_experiment(experiment_id).name

        manifest = {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "package_id": output_dir.name,
            "exported_at": exported_at or datetime.now(timezone.utc).isoformat(),
            # Puramente descriptivo: derivado de la politica externa ya
            # verificada arriba (`admitted`), nunca autorizado por si mismo.
            # El lector (`package_loader.py`) no lee este bloque para
            # decidir admision -- vuelve a verificar contra la misma
            # politica, sourced desde run_metadata.json.
            "admission_contract": {
                "scope": "single_manually_verified_candidate",
                "verified_candidates": [
                    {
                        "experiment_id": admitted.experiment_id,
                        "run_id_child": admitted.run_id_child,
                        "model_identity_verified_by": admitted.model_identity_verified_by,
                        "note": admitted.note,
                    }
                ],
            },
            "candidate": {
                "experiment_id": experiment_id,
                "experiment_name": experiment_name,
                "run_id_child": run_id_child,
                "run_name_child": child.info.run_name,
                "run_id_parent": parent_run_id,
                "run_name_parent": parent.info.run_name,
                "config_name": child.data.params.get("config_name"),
                "seed": int(child.data.params["seed"]),
            },
            "execution_identity": {
                "commit_sha": parent_params.get("commit_sha", "unknown"),
                "working_tree_status": parent_params.get("working_tree_status", "unknown"),
                "run_date": parent_params.get("run_date", "unknown"),
                "pipeline_version": parent_params.get("pipeline_version", "unknown"),
            },
            "dataset": {
                "name": parent_params.get("dataset", dataset_path.stem),
                "historical_sha256": historical_dataset_sha256,
                "package_relative_path": dataset_rel,
            },
            "temporal_semantics": {
                "frequency": "D",
                "day_convention": "UTC_naive_midnight",
                "issuance": "after_daily_observations_available",
                "horizon_days": int(parent_params.get("horizon_days", contract["horizon_days"])),
                "split_date": parent_params.get("split_date", "unknown"),
            },
            "label_rule": {
                "label_column": parent_params.get("label_column", contract.get("label_column")),
                "unit": contract.get("units", {}).get(
                    parent_params.get("label_column", contract.get("label_column"))
                ),
                "rule": contract.get("target_rule", "unknown"),
                "percentile": float(parent_params.get("percentile", contract.get("percentile"))),
                "frozen_threshold": parent_metrics.get(
                    "threshold_mean", parent_metrics.get("threshold")
                ),
            },
            "decision_rule": {
                "classifier_output": "y_proba",
                "alert_threshold": float(
                    parent_params.get("alert_threshold", contract.get("alert_threshold"))
                ),
                "calibration_status": "no acreditada para este run",
            },
            "known_limitations": KNOWN_LIMITATIONS,
        }

        files = {}
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(staging_dir).as_posix()
                files[rel] = {"custody_sha256": _sha256(path)}
        manifest["files"] = files

        (staging_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Validar antes de publicar: el paquete solo se traslada a su
        # ubicacion final si supera integramente `load_package`.
        load_package(staging_dir)

        staging_dir.replace(output_dir)
    except BaseException:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id-child", required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracking-uri")
    parser.add_argument("--exported-at")
    args = parser.parse_args()
    manifest = build_package(
        experiment_id=args.experiment_id,
        run_id_child=args.run_id_child,
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        tracking_uri=args.tracking_uri,
        exported_at=args.exported_at,
    )
    print(f"package_id={manifest['package_id']} written to {args.output_dir}")


if __name__ == "__main__":
    main()
