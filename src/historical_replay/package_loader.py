"""Load a reproducible historical-replay package from disk, with no network
or MLflow dependency (spec `historical-replay`, requirements RH-06, RH-11;
design.md §7).

Every check fails explicitly (typed exception) rather than degrading to a
warning: a package that does not pass every validation is not loaded at all.
This loader never trusts the manifest's own summary at face value — it
cross-checks it against `run_metadata.json` (the captured parent/child run
facts) and against the other packaged documents (`effective_configuration.json`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from historical_replay.admission_policy import verify_admitted
from historical_replay.records import HistoricalPredictionRecord, build_records

SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {"historical_replay_package_v2"}
_REQUIRED_STATUS = "FINISHED"


class UnsupportedManifestVersionError(ValueError):
    """The manifest declares a `schema_version` this loader does not support."""


class IntegrityError(ValueError):
    """A file's custody hash does not match the manifest, or a required
    file is absent from disk."""


class InventoryError(ValueError):
    """A file the loader needs to read is not listed in the manifest's
    inventory, or its declared path resolves outside the package directory."""


class ProvenanceError(ValueError):
    """The dataset's historical hash (captured at execution time) is
    missing, or inconsistent between the manifest, the packaged copy's
    custody hash, or the metadata originally captured in `run_metadata.json`."""


class ParentChildInconsistencyError(ValueError):
    """The manifest's declared candidate does not match the parent/child
    run facts captured in `run_metadata.json` (ids, experiment, status,
    `mlflow.parentRunId`, config/seed, commit)."""


class TrainingDatesError(ValueError):
    """`training_dates` is absent, empty, or contains a malformed date."""


class TrainingMaturityError(ValueError):
    """A training date's target has not matured before the declared cutoff."""


class PredictionBeforeCutoffError(ValueError):
    """A prediction's origin date is earlier than the authorized cutoff
    (`split_date`) — this run's test predictions must never predate it."""


class TemporalConcordanceError(ValueError):
    """`horizon_days`/`split_date` disagree between the documents that
    declare them (manifest, `effective_configuration.json`, `run_metadata.json`)."""


@dataclass(frozen=True)
class LoadedReplayPackage:
    manifest: dict
    run_metadata: dict
    records: list[HistoricalPredictionRecord]
    dataset: pd.DataFrame
    effective_configuration: dict


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_join(package_dir: Path, relative_path: str) -> Path:
    package_root = package_dir.resolve()
    candidate = (package_dir / relative_path).resolve()
    if candidate != package_root and package_root not in candidate.parents:
        raise InventoryError(f"Ruta fuera del directorio del paquete: {relative_path!r}")
    return candidate


def _require_inventoried(manifest: dict, relative_path: str) -> None:
    if relative_path not in manifest.get("files", {}):
        raise InventoryError(
            f"Archivo consumido por el lector no figura en el inventario del "
            f"manifiesto: {relative_path!r}"
        )


def _read_json(package_dir: Path, manifest: dict, relative_path: str) -> dict:
    _require_inventoried(manifest, relative_path)
    path = _safe_join(package_dir, relative_path)
    if not path.exists():
        raise IntegrityError(f"Archivo del manifiesto ausente: {relative_path!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_file_integrity(package_dir: Path, manifest: dict) -> None:
    for relative_path, entry in manifest["files"].items():
        file_path = _safe_join(package_dir, relative_path)
        if not file_path.exists():
            raise IntegrityError(f"Archivo del manifiesto ausente: {relative_path!r}")
        actual = _sha256_of(file_path)
        expected = entry["custody_sha256"]
        if actual != expected:
            raise IntegrityError(
                f"Hash de custodia no coincide para {relative_path!r}: "
                f"esperado {expected}, obtenido {actual}."
            )


def _verify_admission_policy(run_metadata: dict) -> None:
    """Gate against the fixed policy in `historical_replay.admission_policy`,
    sourced from `run_metadata.json` (the facts actually captured from
    MLflow at build time) — never from `manifest["candidate"]` or
    `manifest["admission_contract"]`, which are the package's own summary
    of itself and a self-declared candidate could always satisfy trivially
    by including itself in its own list. `_verify_parent_child_metadata`
    separately confirms the manifest's summary matches these same facts."""
    child = run_metadata.get("child", {})
    parent = run_metadata.get("parent", {})
    verify_admitted(
        experiment_id=child.get("experiment_id"),
        run_id_child=child.get("run_id"),
        run_id_parent=parent.get("run_id"),
        config_name=child.get("params", {}).get("config_name"),
        seed=_safe_int(child.get("params", {}).get("seed")),
        commit_sha=parent.get("params", {}).get("commit_sha"),
        dataset_sha256=parent.get("params", {}).get("dataset_sha256"),
    )


def _verify_parent_child_metadata(manifest: dict, run_metadata: dict) -> None:
    candidate = manifest["candidate"]
    child = run_metadata.get("child", {})
    parent = run_metadata.get("parent", {})
    checks = [
        (
            child.get("run_id") == candidate["run_id_child"],
            "child.run_id vs candidate.run_id_child",
        ),
        (
            child.get("experiment_id") == candidate["experiment_id"],
            "child.experiment_id vs candidate.experiment_id",
        ),
        (
            parent.get("experiment_id") == candidate["experiment_id"],
            "parent.experiment_id vs candidate.experiment_id",
        ),
        (
            parent.get("run_id") == candidate["run_id_parent"],
            "parent.run_id vs candidate.run_id_parent",
        ),
        (
            child.get("tags", {}).get("mlflow.parentRunId") == candidate["run_id_parent"],
            "child.tags['mlflow.parentRunId'] vs candidate.run_id_parent",
        ),
        (child.get("status") == _REQUIRED_STATUS, f"child.status == {_REQUIRED_STATUS!r}"),
        (parent.get("status") == _REQUIRED_STATUS, f"parent.status == {_REQUIRED_STATUS!r}"),
        (
            str(child.get("params", {}).get("config_name")) == str(candidate["config_name"]),
            "child.params.config_name vs candidate.config_name",
        ),
        (
            _safe_int(child.get("params", {}).get("seed")) == int(candidate["seed"]),
            "child.params.seed vs candidate.seed",
        ),
        (
            parent.get("params", {}).get("commit_sha")
            == manifest.get("execution_identity", {}).get("commit_sha"),
            "parent.params.commit_sha vs manifest.execution_identity.commit_sha",
        ),
    ]
    for ok, label in checks:
        if not ok:
            raise ParentChildInconsistencyError(
                f"Metadatos inconsistentes entre manifest.json y run_metadata.json: {label}"
            )


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _verify_dataset_provenance(package_dir: Path, manifest: dict, run_metadata: dict) -> None:
    dataset_info = manifest["dataset"]
    relative_path = dataset_info["package_relative_path"]
    _require_inventoried(manifest, relative_path)
    custody = manifest["files"][relative_path]["custody_sha256"]
    historical = dataset_info.get("historical_sha256")
    if not historical:
        raise ProvenanceError(
            "manifest.dataset.historical_sha256 ausente: para este candidato el hash "
            "histórico debe existir en la evidencia archivada; nunca se sustituye por "
            "un hash calculado hoy."
        )
    if custody != historical:
        raise ProvenanceError(
            "El hash de custodia del dataset empaquetado no coincide con el "
            f"hash histórico declarado en el manifiesto: custodia={custody}, "
            f"histórico={historical}."
        )
    run_metadata_hash = run_metadata.get("parent", {}).get("params", {}).get("dataset_sha256")
    if run_metadata_hash != historical:
        raise ProvenanceError(
            "El hash histórico del manifiesto no coincide con el declarado en "
            f"run_metadata.json (metadatos originales empaquetados): "
            f"manifiesto={historical}, run_metadata={run_metadata_hash!r}."
        )


def _parse_date(value):
    return datetime.fromisoformat(value).date()


def _verify_training_dates_and_concordance(
    manifest: dict, effective_configuration: dict, run_metadata: dict
) -> None:
    training_dates = effective_configuration.get("training_dates")
    if not training_dates or not isinstance(training_dates, list):
        raise TrainingDatesError(
            "training_dates ausente o vacío en effective_configuration.json; no se "
            "acepta este candidato sin esa evidencia."
        )

    horizon_days = manifest["temporal_semantics"]["horizon_days"]
    try:
        cutoff = _parse_date(manifest["temporal_semantics"]["split_date"])
    except (ValueError, TypeError) as exc:
        raise TrainingDatesError(
            f"split_date del manifiesto inválido: "
            f"{manifest['temporal_semantics'].get('split_date')!r}"
        ) from exc

    for raw_date in training_dates:
        try:
            training_date = _parse_date(raw_date)
        except (ValueError, TypeError) as exc:
            raise TrainingDatesError(f"Fecha de entrenamiento mal formada: {raw_date!r}") from exc
        target = training_date + timedelta(days=horizon_days)
        if not target < cutoff:
            raise TrainingMaturityError(
                f"Fecha de entrenamiento {raw_date!r} no madura antes del corte "
                f"{cutoff.isoformat()!r}: su objetivo ({target.isoformat()}) no es anterior."
            )

    contract_horizon = effective_configuration.get("contract", {}).get("horizon_days")
    if contract_horizon is not None and int(contract_horizon) != int(horizon_days):
        raise TemporalConcordanceError(
            "horizon_days de manifest.temporal_semantics "
            f"({horizon_days!r}) no concuerda con "
            f"effective_configuration.json::contract.horizon_days ({contract_horizon!r})."
        )

    parent_params = run_metadata.get("parent", {}).get("params", {})
    rm_horizon = parent_params.get("horizon_days")
    if rm_horizon is not None and int(rm_horizon) != int(horizon_days):
        raise TemporalConcordanceError(
            f"horizon_days del manifiesto ({horizon_days!r}) no concuerda con "
            f"run_metadata.json::parent.params.horizon_days ({rm_horizon!r})."
        )
    rm_split = parent_params.get("split_date")
    if rm_split is not None and _parse_date(rm_split) != cutoff:
        raise TemporalConcordanceError(
            f"split_date del manifiesto ({cutoff.isoformat()!r}) no concuerda con "
            f"run_metadata.json::parent.params.split_date ({rm_split!r})."
        )


def _verify_predictions_after_cutoff(records, cutoff) -> None:
    for record in records:
        if record.identity.timestamp_origen < cutoff:
            raise PredictionBeforeCutoffError(
                f"Predicción con origen {record.identity.timestamp_origen.isoformat()} "
                f"anterior al corte autorizado {cutoff.isoformat()}."
            )


def load_package(package_dir: Path | str) -> LoadedReplayPackage:
    package_dir = Path(package_dir)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))

    if manifest["schema_version"] not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        raise UnsupportedManifestVersionError(
            f"schema_version no soportada: {manifest['schema_version']!r}"
        )

    _verify_file_integrity(package_dir, manifest)

    run_metadata = _read_json(package_dir, manifest, "run_metadata.json")
    _verify_admission_policy(run_metadata)
    _verify_parent_child_metadata(manifest, run_metadata)
    _verify_dataset_provenance(package_dir, manifest, run_metadata)

    predictions = _read_json(package_dir, manifest, "predictions.json")
    effective_configuration = _read_json(package_dir, manifest, "effective_configuration.json")

    _verify_training_dates_and_concordance(manifest, effective_configuration, run_metadata)

    candidate = manifest["candidate"]
    records = build_records(
        predictions["rows"],
        experiment_id=candidate["experiment_id"],
        run_id=candidate["run_id_child"],
        config_name=candidate["config_name"],
        seed=candidate["seed"],
        horizon_days=manifest["temporal_semantics"]["horizon_days"],
    )

    cutoff = _parse_date(manifest["temporal_semantics"]["split_date"])
    _verify_predictions_after_cutoff(records, cutoff)

    dataset_rel = manifest["dataset"]["package_relative_path"]
    _require_inventoried(manifest, dataset_rel)
    dataset_path = _safe_join(package_dir, dataset_rel)
    dataset = pd.read_parquet(dataset_path)

    return LoadedReplayPackage(
        manifest=manifest,
        run_metadata=run_metadata,
        records=records,
        dataset=dataset,
        effective_configuration=effective_configuration,
    )
