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

from experiment_runner.controlled_daily_v4.config import DECISION_THRESHOLD
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


class OutputDirectoryNotEmptyError(FileExistsError):
    """El directorio de salida ya contiene artefactos; usar `overwrite=True`
    de forma explícita para sobreescribir."""


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

    frozen_payload: dict[str, Any] = {}
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
