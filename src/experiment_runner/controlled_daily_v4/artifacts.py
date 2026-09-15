"""Esquemas versionados y serialización atómica de artefactos de la Etapa A.

Nunca escribe en las carpetas de evidencia de `controlled_daily_v3`
(`docs/research/`) ni registra nada en MLflow. Requiere un directorio de
salida explícito y rechaza sobreescritura accidental salvo `overwrite=True`.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.config import DECISION_THRESHOLD, depth_role_for_column
from experiment_runner.controlled_daily_v4.metrics import (
    REASON_MONOCLASS,
    REASON_NO_OWN_GRID,
    REASON_UNSPECIFIED,
    metric_envelope,
    metrics_payload,
    summarize_fold_mcc,
)

ARTIFACT_SCHEMA_VERSION = "controlled_daily_v4_stage_a.v4"
"""v2: métricas completas persistidas, diagnóstico por outer fold, provenance
del bootstrap y JSON estrictamente estándar (sin `NaN`/`Infinity`).

v3 (hallazgo H-05, reproducibilidad/trazabilidad): agrega `code_version.json`
(identidad de código -- SHA completo y árbol limpio/modificado, o su
ausencia explícita), `dataset_fingerprint.json` (huella determinista del
conjunto diario elegible de la Etapa A), `inner_fold_boundaries.json` y
`freeze_fold_boundaries.json` (límites de los folds internos y de
congelamiento realmente consumidos, no recalculados aparte), y
`warnings.json` (advertencias de ajuste con contexto). También cambia la
forma de `frozen_config.json`: `single_family`/`soft_voting_bases` ahora son
un resumen explícito (familia, hiperparámetros, MCC) en lugar del volcado
directo del dataclass `FrozenConfig`, que desde v3 incluye los folds de
congelamiento (no serializables como JSON de resultados).

v4 (revisión externa 2026-09-13, cuatro hallazgos sobre el paquete v3):
- `dataset_fingerprint.json` cambia de codificación de floats (de `"%.12g"`,
  con pérdida de precisión que colisionaba valores `float64` distintos, a
  `repr()` de Python, sin pérdida) -- toda huella `v3` queda invalidada, no
  comparable con una `v4`.
- `code_version.json` puede ahora reportar `dirty=False` genuino desde un
  build en contenedor (antes siempre `None` ahí), y distingue metadatos de
  build ausentes de metadatos de build malformados
  (`SOURCE_BUILD_METADATA_INVALID`).
- `environment.json` agrega `constraints_identity` (ruta + SHA-256 del
  `constraints.txt` efectivamente contrastado).
- `resolved_config.json` agrega `effective_protocol_config` (el
  `ProtocolConfig` completo efectivamente consumido: fronteras temporales,
  horizonte, gap, folds, lags, ventanas móviles, umbral, margen práctico,
  parámetros de bootstrap y las tres grillas de hiperparámetros)."""

TRANSFER_CONTRACT_SCHEMA_VERSION = "controlled_daily_v4_transfer_contract.v1"
"""Versión propia del contrato de transferencia A→B serializado en
`frozen_config.json` (`openspec/changes/implement-controlled-daily-v4-stage-b-c/`).
Deliberadamente distinta de `ARTIFACT_SCHEMA_VERSION` (que versiona el paquete
completo de artefactos de una corrida) y de `DATASET_FINGERPRINT_FORMAT_VERSION`
(que versiona únicamente la huella del conjunto elegible): el contrato puede
evolucionar de forma independiente de ambas. Un lector del contrato
(`transfer_contract.load_frozen_config_contract`) rechaza cualquier
`schema_version` que no reconozca explícitamente, en lugar de asumir una forma
no verificada."""


STAGE_B_ARTIFACT_SCHEMA_VERSION = "controlled_daily_v4_stage_b.v1"
"""Esquema propio de los artefactos de la Etapa B (`write_stage_b_artifacts`),
deliberadamente distinto de `ARTIFACT_SCHEMA_VERSION` (Etapa A) y de
`TRANSFER_CONTRACT_SCHEMA_VERSION` (el contrato de transferencia A→B que B
consume, no produce): B no reescribe ni sobreescribe ningún artefacto de A,
persiste su propio directorio de salida con su propia versión de esquema."""

STAGE_C_ARTIFACT_SCHEMA_VERSION = "controlled_daily_v4_stage_c.v1"
"""Esquema propio de los artefactos de la Etapa C (`write_stage_c_artifacts`),
distinto de los anteriores por la misma razón que B: C nunca reescribe
artefactos de A ni de B, persiste su propio directorio de salida exclusivo."""


class OutputDirectoryNotEmptyError(FileExistsError):
    """El directorio de salida ya contiene artefactos; usar `overwrite=True`
    de forma explícita para sobreescribir."""


class StageBOutputDirectoryConflictsWithProducerError(ValueError):
    """`--output-dir` de la Etapa B coincide con, está contenido dentro de, o
    contiene al `producer_dir` (el directorio de evidencia de A que B
    consume) -- ya sea de forma literal, por rutas relativas distintas que
    normalizan al mismo destino real, o por un enlace simbólico.

    Revisión externa (2026-09-14), hallazgo sobre protección de los
    artefactos de A: `--overwrite` nunca autoriza modificar la evidencia de
    A, sin excepción. Esta verificación se aplica incondicionalmente, tanto
    en la CLI (antes de entrenar nada) como en `write_stage_b_artifacts`
    (antes de escribir cualquier archivo) -- ninguna de las dos confía en que
    la otra ya la haya hecho."""


def validate_stage_b_output_directory(output_dir: str | Path, producer_dir: str | Path) -> None:
    """Rechaza toda coincidencia efectiva entre `output_dir` (destino de B) y
    `producer_dir` (evidencia de A), tras normalizar ambas rutas (incluidos
    enlaces simbólicos) con `Path.resolve()`: nunca compara las cadenas
    crudas recibidas, que pueden diferir (relativa vs. absoluta, `..`,
    mayúsculas de unidad en Windows) y aun así resolver al mismo destino."""
    output_resolved = Path(output_dir).resolve()
    producer_resolved = Path(producer_dir).resolve()

    if output_resolved == producer_resolved:
        raise StageBOutputDirectoryConflictsWithProducerError(
            f"--output-dir ('{output_dir}') coincide con --producer-dir ('{producer_dir}') "
            "una vez normalizadas ambas rutas (enlaces simbólicos incluidos): la Etapa B "
            "nunca escribe en el directorio productor de A, ni siquiera con --overwrite."
        )
    if output_resolved.is_relative_to(producer_resolved):
        raise StageBOutputDirectoryConflictsWithProducerError(
            f"--output-dir ('{output_dir}') está contenido dentro de --producer-dir "
            f"('{producer_dir}'): la Etapa B nunca escribe dentro del directorio productor "
            "de A, ni siquiera con --overwrite."
        )
    if producer_resolved.is_relative_to(output_resolved):
        raise StageBOutputDirectoryConflictsWithProducerError(
            f"--producer-dir ('{producer_dir}') está contenido dentro de --output-dir "
            f"('{output_dir}'): la Etapa B nunca escribe en un directorio que contenga la "
            "evidencia de A, ni siquiera con --overwrite."
        )


class StageCOutputDirectoryConflictError(ValueError):
    """`--output-dir` de la Etapa C coincide con, está contenido dentro de, o
    contiene a alguno de los directorios protegidos (evidencia de A, de B, o
    el archivo del ledger del holdout) -- de forma literal, por rutas
    relativas distintas que normalizan al mismo destino, o por un enlace
    simbólico. `--overwrite` no existe para la Etapa C (Decisión 3 del
    documento de decisiones, adoptada para este encargo: prohibición
    incondicional), por lo que esta verificación es, en la práctica, siempre
    incondicional."""


def _reject_path_overlap(output_dir: Path, protected_path: Path, protected_label: str) -> None:
    output_resolved = output_dir.resolve()
    protected_resolved = protected_path.resolve()
    if output_resolved == protected_resolved:
        raise StageCOutputDirectoryConflictError(
            f"--output-dir ('{output_dir}') coincide con {protected_label} "
            f"('{protected_path}') una vez normalizadas ambas rutas (enlaces simbólicos "
            "incluidos): la Etapa C nunca escribe en un directorio/archivo protegido."
        )
    if output_resolved.is_relative_to(protected_resolved):
        raise StageCOutputDirectoryConflictError(
            f"--output-dir ('{output_dir}') está contenido dentro de {protected_label} "
            f"('{protected_path}'): la Etapa C nunca escribe dentro de un directorio protegido."
        )
    if protected_resolved.is_relative_to(output_resolved):
        raise StageCOutputDirectoryConflictError(
            f"{protected_label} ('{protected_path}') está contenido dentro de --output-dir "
            f"('{output_dir}'): la Etapa C nunca escribe en un directorio que contenga "
            "evidencia protegida."
        )


def validate_stage_c_output_directory(
    output_dir: str | Path,
    *,
    producer_dir: str | Path,
    stage_b_dir: str | Path,
    ledger_path: str | Path,
) -> None:
    """Rechaza toda coincidencia efectiva (literal, por anidamiento, o por
    enlace simbólico) entre `output_dir` (destino de C) y CUALQUIERA de:
    `producer_dir` (evidencia de A), `stage_b_dir` (evidencia de B), o
    `ledger_path` (el archivo del ledger del holdout) -- protección explícita
    pedida para C, análoga a `validate_stage_b_output_directory` pero
    extendida a tres rutas protegidas en vez de una."""
    output_dir = Path(output_dir)
    _reject_path_overlap(output_dir, Path(producer_dir), "--producer-dir (evidencia de A)")
    _reject_path_overlap(output_dir, Path(stage_b_dir), "--stage-b-dir (evidencia de B)")
    _reject_path_overlap(output_dir, Path(ledger_path), "--holdout-ledger-path (ledger)")


def normalize_for_json(value: Any) -> Any:
    """Normaliza recursivamente un payload a tipos JSON estrictamente estándar.

    Todo escalar no finito (`NaN`, `Infinity`, `-Infinity`) se convierte en la
    envoltura explícita de métrica indefinida, de modo que el artefacto nunca
    contenga tokens fuera de la especificación JSON. También resuelve escalares
    y arrays de NumPy, fechas, timestamps, dataclasses, mapas y secuencias."""
    if value is None or isinstance(value, (str, bool, np.bool_)):
        return bool(value) if isinstance(value, np.bool_) else value
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (int,)):
        return value
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not np.isfinite(numeric):
            return metric_envelope(numeric, REASON_UNSPECIFIED)
        return numeric
    if isinstance(value, np.ndarray):
        return [normalize_for_json(v) for v in value.tolist()]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, pd.Series):
        return [normalize_for_json(v) for v in value.tolist()]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return normalize_for_json(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {_normalize_key(k): normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_for_json(v) for v in value]
    if hasattr(value, "__dict__"):
        return normalize_for_json(vars(value))
    raise TypeError(f"No serializable a JSON: {type(value)}")


def _normalize_key(key: Any) -> str:
    """Las claves JSON deben ser cadenas: una clave de par `(a, b)` se
    serializa como `"a|b"`, consistente con `_selection_result_to_json`."""
    if isinstance(key, tuple):
        return "|".join(str(k) for k in key)
    return str(key)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _write_json(path: Path, payload: Any) -> None:
    """Serializa con `allow_nan=False`: cualquier token no estándar que
    sobreviviera a la normalización aborta la escritura en lugar de producir
    evidencia no interoperable."""
    content = json.dumps(
        normalize_for_json(payload), indent=2, ensure_ascii=False, allow_nan=False, sort_keys=False
    )
    _atomic_write_text(path, content)


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _selection_result_to_json(selection_result: Any) -> dict[str, Any]:
    return {
        "outcome": selection_result.outcome,
        "global_mcc_by_family": {
            family: metric_envelope(value, REASON_MONOCLASS)
            for family, value in selection_result.global_mcc_by_family.items()
        },
        "pairwise_intervals": {
            f"{a}|{b}": {
                "lower": metric_envelope(interval[0], REASON_MONOCLASS),
                "upper": metric_envelope(interval[1], REASON_MONOCLASS),
            }
            for (a, b), interval in selection_result.pairwise_intervals.items()
        },
        "bootstrap_diagnostics": {
            f"{a}|{b}": diagnostics
            for (a, b), diagnostics in getattr(
                selection_result, "bootstrap_diagnostics", {}
            ).items()
        },
        "equivalence_set": selection_result.equivalence_set,
        "stable_winner": selection_result.stable_winner,
        "selected_family": selection_result.selected_family,
        "selection_reason": selection_result.selection_reason,
    }


def build_metrics_payload(
    per_family_outer_results: dict[str, list[Any]],
    oof_by_family: dict[str, Any],
) -> dict[str, Any]:
    """Artefacto de métricas versionado (protocolo, sección 12 y 8.4).

    Por candidato: métricas globales recalculadas desde el OOF concatenado
    completo (nunca como promedio de folds), métricas por outer fold, y el
    diagnóstico de mediana/cuartiles/IQR del MCC por fold."""
    by_family: dict[str, Any] = {}
    for family, oof in oof_by_family.items():
        results = per_family_outer_results.get(family, [])
        per_outer_fold = []
        fold_mcc: list[float] = []
        for result in results:
            payload = metrics_payload(result.y_true, result.y_pred, result.y_score)
            payload["outer_fold_index"] = result.outer_fold_index
            payload["p20_train"] = float(result.p20_train)
            per_outer_fold.append(payload)
            value = payload["mcc"]["value"]
            fold_mcc.append(float("nan") if value is None else float(value))

        recorded = list(getattr(oof, "per_fold_mcc", []) or [])
        summary_source = recorded if recorded else fold_mcc
        by_family[family] = {
            "global": metrics_payload(oof.y_true, oof.y_pred, oof.y_score),
            "per_outer_fold": per_outer_fold,
            "fold_mcc_summary": summarize_fold_mcc(summary_source),
        }

    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "global_mcc_source": "recomputed_from_concatenated_oof",
        "decision_threshold": DECISION_THRESHOLD,
        "by_family": by_family,
    }


def ensure_output_directory(output_dir: str | Path, overwrite: bool = False) -> Path:
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise OutputDirectoryNotEmptyError(
            f"'{output_dir}' ya contiene archivos. Pasar overwrite=True para sobreescribir "
            "explícitamente."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def oof_to_dataframe(oof) -> pd.DataFrame:
    frame = oof.frame_with_segment_id.copy()
    frame["y_true"] = oof.y_true
    frame["y_pred"] = oof.y_pred
    frame["y_score"] = oof.y_score
    return frame


def _frozen_config_to_json(frozen: Any) -> dict[str, Any]:
    """Payload JSON de un `FrozenConfig`, excluyendo explícitamente `folds`
    (contiene los DataFrames de train/validation): esos límites se persisten
    aparte, como boundaries, nunca como datos (hallazgo H-05; ver
    `freeze_fold_boundaries`)."""
    return {
        "family": frozen.family,
        "config": {"family": frozen.config.family, "params": frozen.config.params},
        "median_mcc": metric_envelope(frozen.median_mcc, REASON_NO_OWN_GRID),
        "fold_mcc": [metric_envelope(v, REASON_MONOCLASS) for v in frozen.fold_mcc],
    }


def _producer_identity_reference(
    code_version: dict[str, Any] | None, dataset_fingerprint: dict[str, Any] | None
) -> dict[str, Any]:
    """Referencia inequívoca, embebida en `frozen_config.json`, a la evidencia
    ya persistida por el productor (`code_version.json`, `dataset_fingerprint.json`)
    -- derivada de los mismos objetos efectivos que esta corrida ya calculó y
    escribió aparte, nunca recalculada ni inferida de un nombre de archivo."""
    dataset_fingerprint = dataset_fingerprint or {}
    return {
        "code_identity": code_version or {},
        "dataset_fingerprint_ref": {
            "schema_version": dataset_fingerprint.get("schema_version"),
            "sha256": dataset_fingerprint.get("sha256"),
            "n_rows": dataset_fingerprint.get("n_rows"),
            "scope": dataset_fingerprint.get("scope"),
        },
    }


def _fold_boundaries(folds: list[Any]) -> list[dict[str, Any]]:
    """Límites/cantidades de una lista de folds ya generados (nunca
    recalculados): mismo formato que `outer_fold_boundaries` (hallazgo H-05)."""
    return [
        {
            "fold_index": fold.index,
            "segment_id": fold.segment_id,
            "n_train": len(fold.train),
            "n_validation": len(fold.validation),
            "train_feature_start": str(fold.train["feature_timestamp"].min()),
            "train_feature_end": str(fold.train["feature_timestamp"].max()),
            "validation_feature_start": str(fold.validation["feature_timestamp"].min()),
            "validation_feature_end": str(fold.validation["feature_timestamp"].max()),
        }
        for fold in folds
    ]


def write_stage_a_artifacts(
    output_dir: str | Path,
    *,
    depth_column: str,
    input_mode: str,
    scientific_run: bool,
    resolved_config: dict[str, Any],
    provenance_report: Any,
    environment_info: dict[str, Any],
    input_hashes: dict[str, str],
    outer_fold_boundaries: list[dict[str, Any]],
    per_family_outer_results: dict[str, list[Any]],
    oof_by_family: dict[str, Any],
    selection_result: Any,
    frozen_single_family: Any | None,
    frozen_soft_voting_bases: dict[str, Any] | None,
    final_p20_train: float | None,
    code_version: dict[str, Any] | None = None,
    dataset_fingerprint: dict[str, Any] | None = None,
    inner_fold_boundaries_by_outer: dict[int, list[Any]] | None = None,
    final_estimator_details: dict[str, Any] | None = None,
    soft_voting_combination_weights: dict[str, float] | None = None,
    warnings_log: list[dict[str, Any]] | None = None,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Serializa todos los artefactos de una corrida de Etapa A. Nunca
    escribe en `docs/research/` ni registra nada en MLflow."""
    output_dir = ensure_output_directory(output_dir, overwrite=overwrite)
    written: dict[str, Path] = {}

    written["schema_version"] = output_dir / "schema_version.json"
    _write_json(written["schema_version"], {"schema_version": ARTIFACT_SCHEMA_VERSION})

    written["resolved_config"] = output_dir / "resolved_config.json"
    _write_json(written["resolved_config"], {"depth_column": depth_column, **resolved_config})

    written["provenance"] = output_dir / "provenance.json"
    _write_json(written["provenance"], provenance_report)

    written["environment"] = output_dir / "environment.json"
    _write_json(written["environment"], environment_info)

    written["code_version"] = output_dir / "code_version.json"
    _write_json(written["code_version"], code_version or {})

    written["input_hashes"] = output_dir / "input_hashes.json"
    _write_json(written["input_hashes"], input_hashes)

    written["dataset_fingerprint"] = output_dir / "dataset_fingerprint.json"
    _write_json(written["dataset_fingerprint"], dataset_fingerprint or {})

    written["outer_fold_boundaries"] = output_dir / "outer_fold_boundaries.json"
    _write_json(written["outer_fold_boundaries"], outer_fold_boundaries)

    written["inner_fold_boundaries"] = output_dir / "inner_fold_boundaries.json"
    _write_json(
        written["inner_fold_boundaries"],
        {
            str(outer_index): _fold_boundaries(folds)
            for outer_index, folds in (inner_fold_boundaries_by_outer or {}).items()
        },
    )

    written["warnings"] = output_dir / "warnings.json"
    _write_json(written["warnings"], warnings_log or [])

    p20_by_fold = {
        family: [
            {"outer_fold_index": r.outer_fold_index, "p20_train": r.p20_train} for r in results
        ]
        for family, results in per_family_outer_results.items()
    }
    written["p20_by_fold"] = output_dir / "p20_by_fold.json"
    _write_json(written["p20_by_fold"], p20_by_fold)

    hyperparameters_inner_selected = {
        family: [
            {
                "outer_fold_index": r.outer_fold_index,
                "config_id": r.inner_best_config.config_id,
                "params": r.inner_best_config.params,
                "inner_median_mcc": metric_envelope(r.inner_median_mcc, REASON_NO_OWN_GRID),
                "inner_fold_mcc": [metric_envelope(v, REASON_MONOCLASS) for v in r.inner_fold_mcc],
                "soft_voting_base_config_ids": getattr(r, "soft_voting_base_config_ids", {}),
                "soft_voting_base_weighting_modes": getattr(
                    r, "soft_voting_base_weighting_modes", {}
                ),
            }
            for r in results
        ]
        for family, results in per_family_outer_results.items()
    }
    written["hyperparameters_inner_selected"] = output_dir / "hyperparameters_inner_selected.json"
    _write_json(written["hyperparameters_inner_selected"], hyperparameters_inner_selected)

    for family, oof in oof_by_family.items():
        path = output_dir / f"oof_predictions_{family}.csv"
        _write_csv(path, oof_to_dataframe(oof))
        written[f"oof_predictions_{family}"] = path

    written["metrics"] = output_dir / "metrics.json"
    _write_json(written["metrics"], build_metrics_payload(per_family_outer_results, oof_by_family))

    written["selection_decision"] = output_dir / "selection_decision.json"
    _write_json(written["selection_decision"], _selection_result_to_json(selection_result))

    candidate_produced = frozen_single_family is not None or frozen_soft_voting_bases is not None
    frozen_payload: dict[str, Any] = {
        "schema_version": TRANSFER_CONTRACT_SCHEMA_VERSION,
        "input_mode": input_mode,
        "scientific_run": scientific_run,
        "depth_column": depth_column,
        "depth_role": depth_role_for_column(depth_column),
        # Ausencia explícita (contrato de transferencia A→B): si la Etapa A no
        # produjo candidato (`selection.selected_family is None`), este campo
        # queda `false` y ningún `single_family`/`soft_voting_bases` se
        # serializa -- nunca se fabrica una configuración congelada.
        "candidate_produced": candidate_produced,
        "selected_family": selection_result.selected_family,
        # Referencias inequívocas a la evidencia ya persistida del productor
        # (código + huella del conjunto derivado de A), para que la
        # admisibilidad de un futuro consumidor de B pueda contrastarlas sin
        # inferir identidades a partir de nombres de archivo.
        "producer": _producer_identity_reference(code_version, dataset_fingerprint),
    }
    freeze_folds: list[Any] | None = None
    if frozen_single_family is not None:
        frozen_payload["single_family"] = _frozen_config_to_json(frozen_single_family)
        freeze_folds = frozen_single_family.folds
    if frozen_soft_voting_bases is not None:
        frozen_payload["soft_voting_bases"] = {
            family: _frozen_config_to_json(fc) for family, fc in frozen_soft_voting_bases.items()
        }
        # Las tres bases se congelan sobre el mismo `eligible_frame`/n_splits/gap,
        # por lo que comparten exactamente los mismos folds (hallazgo H-05):
        # se registran una única vez, no por base.
        freeze_folds = next(iter(frozen_soft_voting_bases.values())).folds
        # Pesos de COMBINACIÓN del ensamble (protocolo, sección 7.5) --
        # concepto distinto de `weighting` (balanceo de clases por familia,
        # ya dentro de cada `config.params`). Se persiste el diccionario
        # EFECTIVAMENTE usado por el estimador ya ajustado
        # (`SoftVotingClassifier.combination_weights()`), nunca un default
        # inventado en la lectura -- si no se recibe, el campo queda `null`
        # y la lectura estructural lo rechaza como incoherente.
        frozen_payload["soft_voting_combination_weights"] = soft_voting_combination_weights
    frozen_payload["final_p20_train"] = final_p20_train
    # Regularización efectiva verificada por API del estimador congelado
    # (protocolo, sección 7.2): L2 real, no la declarada en la grilla.
    # El estimador ajustado en memoria (`results.final_estimator`) nunca se
    # serializa aquí: este artefacto persiste únicamente la configuración
    # congelada (familia + hiperparámetros + detalle de la API del estimador
    # ya ajustado), suficiente para reconstruir el mismo estimador reentrenando
    # con `freezing.fit_final_estimator` sobre el mismo `eligible_frame`
    # (identificado por `dataset_fingerprint.json`) — no es un modelo
    # serializado (hallazgo H-05, punto f).
    frozen_payload["final_estimator_details"] = final_estimator_details or {}
    written["frozen_config"] = output_dir / "frozen_config.json"
    _write_json(written["frozen_config"], frozen_payload)

    written["freeze_fold_boundaries"] = output_dir / "freeze_fold_boundaries.json"
    _write_json(
        written["freeze_fold_boundaries"], _fold_boundaries(freeze_folds) if freeze_folds else []
    )

    written["holdout_status"] = output_dir / "holdout_status.json"
    _write_json(
        written["holdout_status"],
        {
            "stage_b_executed": False,
            "stage_c_executed": False,
            "holdout_2024_2025_open": False,
            "note": "Ejecución de Stage A únicamente. B y C no implementadas en este runner.",
        },
    )

    return written


def _bootstrap_diagnostics_to_json(diagnostics: Any | None) -> dict[str, Any]:
    if diagnostics is None:
        return {}
    return dataclasses.asdict(diagnostics)


def _stage_b_predictions_frame(result: Any) -> pd.DataFrame:
    """`predictions_2023.csv` (protocolo, sección 10/13).

    Revisión externa (2026-09-14), hallazgo sobre persistencia del resultado
    monoclase: cuando `result.predictions_available` es `False` (entrenamiento
    o evaluación monoclase; ver `stage_b_runner.run_stage_b`), los vectores de
    predicción del candidato y de los tres baselines están genuinamente
    AUSENTES -- de longitud distinta a `y_true`/`feature_timestamps`, nunca
    reconciliable en un único DataFrame de columnas iguales. En ese caso se
    persisten únicamente los timestamps y (si están disponibles) las
    etiquetas verdaderas: nunca se fabrica una predicción, ni se reemplaza la
    ausencia por ceros o por `NaN` disfrazado de predicción real. El motivo
    de la ausencia queda en `decision.json` (`reasons`), no aquí."""
    if result.predictions_available:
        return pd.DataFrame(
            {
                "feature_timestamp": result.feature_timestamps,
                "y_true": result.y_true,
                "y_pred_candidate": result.y_pred_candidate,
                "y_score_candidate": result.y_score_candidate,
                "y_pred_persistence": result.y_pred_persistence,
                "y_pred_majority_class": result.y_pred_majority_class,
                "y_pred_constant_stress": result.y_pred_constant_stress,
            }
        )
    data: dict[str, Any] = {"feature_timestamp": result.feature_timestamps}
    if len(result.y_true) == len(result.feature_timestamps):
        data["y_true"] = result.y_true
    return pd.DataFrame(data)


def write_stage_b_artifacts(
    output_dir: str | Path,
    *,
    input_mode: str,
    scientific_run: bool,
    resolved_config: dict[str, Any],
    producer_dir: str | Path,
    producer_contract_raw: dict[str, Any],
    consumer_code_identity: dict[str, Any],
    consumer_environment_info: dict[str, Any],
    consumer_environment_issues: list[str],
    result: Any,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Serializa todos los artefactos de una corrida de la Etapa B. Nunca
    escribe dentro de `producer_dir` (el directorio de artefactos de A que
    consume): siempre un directorio de salida separado, explícito, con la
    misma política de sobreescritura de `ensure_output_directory` que A.

    Revisión externa (2026-09-14), hallazgo sobre protección de los
    artefactos de A: `validate_stage_b_output_directory` se verifica aquí,
    ANTES de `ensure_output_directory` y de cualquier escritura -- ante un
    rechazo, ningún archivo del productor (ni del propio `output_dir`) se
    toca. Esta verificación es incondicional: `overwrite=True` nunca la
    omite, y la CLI la repite por su cuenta antes de entrenar (no confía en
    que el escritor sea quien la aplique)."""
    validate_stage_b_output_directory(output_dir, producer_dir)
    output_dir = ensure_output_directory(output_dir, overwrite=overwrite)
    written: dict[str, Path] = {}

    written["schema_version"] = output_dir / "schema_version.json"
    _write_json(written["schema_version"], {"schema_version": STAGE_B_ARTIFACT_SCHEMA_VERSION})

    written["resolved_config"] = output_dir / "resolved_config.json"
    _write_json(
        written["resolved_config"],
        {"input_mode": input_mode, "scientific_run": scientific_run, **resolved_config},
    )

    written["producer_reference"] = output_dir / "producer_reference.json"
    _write_json(
        written["producer_reference"],
        {
            "producer_dir": str(producer_dir),
            "producer_frozen_config": producer_contract_raw,
        },
    )

    written["code_version"] = output_dir / "code_version.json"
    _write_json(written["code_version"], consumer_code_identity)

    written["environment"] = output_dir / "environment.json"
    _write_json(
        written["environment"],
        {
            **consumer_environment_info,
            "validation_issues": consumer_environment_issues,
            "validated_before_training": True,
        },
    )

    written["warnings"] = output_dir / "warnings.json"
    _write_json(written["warnings"], getattr(result, "warnings_log", None) or [])

    written["training_dataset_fingerprint"] = output_dir / "training_dataset_fingerprint.json"
    _write_json(written["training_dataset_fingerprint"], result.training_dataset_fingerprint)

    written["temporal_boundaries"] = output_dir / "temporal_boundaries.json"
    _write_json(
        written["temporal_boundaries"],
        {
            "training_frame_n_rows": result.training_frame_n_rows,
            "training_target_timestamp_cutoff": "2022-12-31",
            "evaluation_frame_n_rows": result.evaluation_frame_n_rows,
            "evaluation_target_timestamp_min": result.evaluation_target_timestamp_min,
            "evaluation_target_timestamp_max": result.evaluation_target_timestamp_max,
        },
    )

    written["p20_train"] = output_dir / "p20_train.json"
    _write_json(written["p20_train"], {"p20_train": result.p20_train})

    written["predictions"] = output_dir / "predictions_2023.csv"
    _write_csv(written["predictions"], _stage_b_predictions_frame(result))

    written["metrics"] = output_dir / "metrics.json"
    _write_json(
        written["metrics"],
        {
            "schema_version": STAGE_B_ARTIFACT_SCHEMA_VERSION,
            "candidate": result.metrics_candidate,
            "baseline_persistence": result.metrics_persistence,
            "baseline_majority_class": result.metrics_majority_class,
            "baseline_constant_stress": result.metrics_constant_stress,
            "mcc_candidate": metric_envelope(result.mcc_candidate, REASON_MONOCLASS),
            "mcc_persistence": metric_envelope(result.mcc_persistence, REASON_MONOCLASS),
            "delta_mcc_point_estimate": metric_envelope(
                result.delta_mcc_point_estimate, REASON_MONOCLASS
            ),
        },
    )

    written["bootstrap"] = output_dir / "bootstrap.json"
    interval = (
        result.bootstrap_result.interval if result.bootstrap_result is not None else (None, None)
    )
    _write_json(
        written["bootstrap"],
        {
            # Distingue "bootstrap no ejecutado" (entrenamiento/evaluación
            # monoclase: `False`) de "bootstrap ejecutado sin réplicas
            # válidas" (`True`, con `diagnostics` igual poblado pero
            # `interval_lower`/`interval_upper` en `null`) -- hallazgo H-05,
            # evidencia de reproducibilidad de B: nunca se reejecuta el
            # bootstrap solo para reconstruir estos diagnósticos.
            "bootstrap_executed": getattr(
                result, "bootstrap_executed", result.bootstrap_result is not None
            ),
            "interval_lower": interval[0],
            "interval_upper": interval[1],
            "diagnostics": _bootstrap_diagnostics_to_json(result.bootstrap_diagnostics),
        },
    )

    written["decision"] = output_dir / "decision.json"
    _write_json(
        written["decision"],
        {
            "verdict": result.verdict,
            "reasons": result.verdict_reasons,
            # Ausencia explícita de predicciones (hallazgo H-05, persistencia
            # del resultado monoclase): `false` cuando el entrenamiento o la
            # evaluación resultaron monoclase (ver
            # `stage_b_runner.StageBResult.predictions_available`) -- nunca
            # se infiere de la longitud de `predictions_2023.csv`.
            "predictions_available": getattr(result, "predictions_available", True),
            "rule": {
                "mcc_candidate_must_be_positive": True,
                "delta_mcc_lower_bound_minimum": -0.05,
            },
        },
    )

    written["holdout_status"] = output_dir / "holdout_status.json"
    _write_json(
        written["holdout_status"],
        {
            "stage_b_executed": True,
            "stage_b_verdict": result.verdict,
            "stage_c_executed": False,
            "holdout_2024_2025_open": False,
            "note": (
                "Ejecución de Stage B. C no implementada en este runner; el veredicto de B "
                "queda persistido aquí, pero ningún mecanismo de este paquete lo consume "
                "todavía para habilitar C (Decisión 2, ledger del holdout, pendiente)."
            ),
        },
    )

    return written


def _stage_c_predictions_frame(result: Any) -> pd.DataFrame:
    """`predictions_2024_2025.csv` (protocolo, sección 11/13). Mismo criterio
    que `_stage_b_predictions_frame`: ante entrenamiento/evaluación monoclase
    (`predictions_available=False`), nunca se fabrica una predicción ni se
    reemplaza la ausencia por ceros -- solo se persisten los timestamps y (si
    están disponibles) las etiquetas verdaderas."""
    if result.predictions_available:
        return pd.DataFrame(
            {
                "feature_timestamp": result.feature_timestamps,
                "y_true": result.y_true,
                "y_pred_candidate": result.y_pred_candidate,
                "y_score_candidate": result.y_score_candidate,
                "y_pred_persistence": result.y_pred_persistence,
                "y_pred_majority_class": result.y_pred_majority_class,
                "y_pred_constant_stress": result.y_pred_constant_stress,
            }
        )
    data: dict[str, Any] = {"feature_timestamp": result.feature_timestamps}
    if len(result.y_true) == len(result.feature_timestamps):
        data["y_true"] = result.y_true
    return pd.DataFrame(data)


def write_stage_c_artifacts(
    output_dir: str | Path,
    *,
    input_mode: str,
    scientific_run: bool,
    resolved_config: dict[str, Any],
    producer_dir: str | Path,
    producer_contract_raw: dict[str, Any],
    stage_b_dir: str | Path,
    stage_b_decision_raw: dict[str, Any],
    ledger_path: str | Path,
    holdout_identity_key: str,
    attempt_id: str,
    authorized_by: str,
    consumer_code_identity: dict[str, Any],
    consumer_environment_info: dict[str, Any],
    consumer_environment_issues: list[str],
    result: Any,
) -> dict[str, Path]:
    """Serializa todos los artefactos de una corrida de la Etapa C. Nunca
    escribe dentro de `producer_dir` (A), `stage_b_dir` (B) ni en el archivo
    de `ledger_path` -- `validate_stage_c_output_directory` se verifica aquí,
    ANTES de `ensure_output_directory` y de cualquier escritura, exactamente
    igual que en B. La Etapa C nunca acepta `overwrite`: cada apertura del
    holdout es un evento único, por lo que esta función no expone ese
    parámetro (a diferencia de A y B) -- `ensure_output_directory` se invoca
    siempre con `overwrite=False`."""
    validate_stage_c_output_directory(
        output_dir, producer_dir=producer_dir, stage_b_dir=stage_b_dir, ledger_path=ledger_path
    )
    output_dir = ensure_output_directory(output_dir, overwrite=False)
    written: dict[str, Path] = {}

    written["schema_version"] = output_dir / "schema_version.json"
    _write_json(written["schema_version"], {"schema_version": STAGE_C_ARTIFACT_SCHEMA_VERSION})

    written["resolved_config"] = output_dir / "resolved_config.json"
    _write_json(
        written["resolved_config"],
        {"input_mode": input_mode, "scientific_run": scientific_run, **resolved_config},
    )

    written["producer_reference"] = output_dir / "producer_reference.json"
    _write_json(
        written["producer_reference"],
        {
            "producer_dir": str(producer_dir),
            "producer_frozen_config": producer_contract_raw,
            "stage_b_dir": str(stage_b_dir),
            "stage_b_decision": stage_b_decision_raw,
        },
    )

    written["holdout_ledger_reference"] = output_dir / "holdout_ledger_reference.json"
    _write_json(
        written["holdout_ledger_reference"],
        {
            "ledger_path": str(ledger_path),
            "holdout_identity_key": holdout_identity_key,
            "attempt_id": attempt_id,
            "authorized_by": authorized_by,
        },
    )

    written["code_version"] = output_dir / "code_version.json"
    _write_json(written["code_version"], consumer_code_identity)

    written["environment"] = output_dir / "environment.json"
    _write_json(
        written["environment"],
        {
            **consumer_environment_info,
            "validation_issues": consumer_environment_issues,
            "validated_before_training": True,
        },
    )

    written["warnings"] = output_dir / "warnings.json"
    _write_json(written["warnings"], getattr(result, "warnings_log", None) or [])

    written["training_dataset_fingerprint"] = output_dir / "training_dataset_fingerprint.json"
    _write_json(written["training_dataset_fingerprint"], result.training_dataset_fingerprint)

    written["temporal_boundaries"] = output_dir / "temporal_boundaries.json"
    _write_json(
        written["temporal_boundaries"],
        {
            "training_frame_n_rows": result.training_frame_n_rows,
            "training_target_timestamp_cutoff": "2023-12-31",
            "evaluation_frame_n_rows": result.evaluation_frame_n_rows,
            "evaluation_target_timestamp_min": result.evaluation_target_timestamp_min,
            "evaluation_target_timestamp_max": result.evaluation_target_timestamp_max,
        },
    )

    written["p20_train"] = output_dir / "p20_train.json"
    _write_json(written["p20_train"], {"p20_train": result.p20_train})

    written["predictions"] = output_dir / "predictions_2024_2025.csv"
    _write_csv(written["predictions"], _stage_c_predictions_frame(result))

    written["metrics"] = output_dir / "metrics.json"
    _write_json(
        written["metrics"],
        {
            "schema_version": STAGE_C_ARTIFACT_SCHEMA_VERSION,
            "candidate": result.metrics_candidate,
            "baseline_persistence": result.metrics_persistence,
            "baseline_majority_class": result.metrics_majority_class,
            "baseline_constant_stress": result.metrics_constant_stress,
            "mcc_candidate": metric_envelope(result.mcc_candidate, REASON_MONOCLASS),
            "mcc_persistence": metric_envelope(result.mcc_persistence, REASON_MONOCLASS),
            "delta_mcc_point_estimate": metric_envelope(
                result.delta_mcc_point_estimate, REASON_MONOCLASS
            ),
        },
    )

    written["bootstrap"] = output_dir / "bootstrap.json"
    interval = (
        result.bootstrap_result.interval if result.bootstrap_result is not None else (None, None)
    )
    _write_json(
        written["bootstrap"],
        {
            # Exclusivamente DIAGNÓSTICO en C (ver stage_c_runner.py):
            # ningún umbral de aprobación se deriva de este intervalo -- la
            # Etapa C no tiene compuerta de aceptación/rechazo.
            "bootstrap_executed": getattr(
                result, "bootstrap_executed", result.bootstrap_result is not None
            ),
            "interval_lower": interval[0],
            "interval_upper": interval[1],
            "diagnostics": _bootstrap_diagnostics_to_json(result.bootstrap_diagnostics),
        },
    )

    written["outcome"] = output_dir / "outcome.json"
    _write_json(
        written["outcome"],
        {
            # Deliberadamente SIN campo 'verdict': la Etapa C no produce un
            # veredicto de aprobación/rechazo (esa compuerta es exclusiva de
            # B, protocolo sección 10) -- un resultado desfavorable de C
            # nunca autoriza repetir la evaluación (protocolo, sección 11).
            "predictions_available": getattr(result, "predictions_available", True),
            "reasons": getattr(result, "outcome_reasons", []),
            "classification": {
                "stage": "C",
                "permits": "Validación temporal final de un único modelo ya congelado",
                "does_not_permit": "Selección, recalibración, nueva comparación de familias",
            },
        },
    )

    written["holdout_status"] = output_dir / "holdout_status.json"
    _write_json(
        written["holdout_status"],
        {
            "stage_b_executed": True,
            "stage_c_executed": True,
            "holdout_2024_2025_open": True,
            "note": (
                "Ejecución de Stage C: el holdout 2024-2025 fue abierto de forma durable y "
                "permanente por esta corrida (ver holdout_ledger_reference.json). Este campo "
                "describe la evidencia de ESTA corrida -- el estado autoritativo de exclusión "
                "vive en el ledger (holdout_ledger.py), no en este archivo."
            ),
        },
    )

    return written
