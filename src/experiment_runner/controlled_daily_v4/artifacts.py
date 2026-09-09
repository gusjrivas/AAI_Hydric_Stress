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

ARTIFACT_SCHEMA_VERSION = "controlled_daily_v4_stage_a.v1"


class OutputDirectoryNotEmptyError(FileExistsError):
    """El directorio de salida ya contiene artefactos; usar `overwrite=True`
    de forma explícita para sobreescribir."""


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    raise TypeError(f"No serializable a JSON: {type(value)}")


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
    content = json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default)
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
        "global_mcc_by_family": selection_result.global_mcc_by_family,
        "pairwise_intervals": {
            f"{a}|{b}": list(interval)
            for (a, b), interval in selection_result.pairwise_intervals.items()
        },
        "equivalence_set": selection_result.equivalence_set,
        "stable_winner": selection_result.stable_winner,
        "selected_family": selection_result.selected_family,
        "selection_reason": selection_result.selection_reason,
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

    written["input_hashes"] = output_dir / "input_hashes.json"
    _write_json(written["input_hashes"], input_hashes)

    written["outer_fold_boundaries"] = output_dir / "outer_fold_boundaries.json"
    _write_json(written["outer_fold_boundaries"], outer_fold_boundaries)

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
                "inner_median_mcc": r.inner_median_mcc,
                "inner_fold_mcc": r.inner_fold_mcc,
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

    written["selection_decision"] = output_dir / "selection_decision.json"
    _write_json(written["selection_decision"], _selection_result_to_json(selection_result))

    frozen_payload: dict[str, Any] = {}
    if frozen_single_family is not None:
        frozen_payload["single_family"] = frozen_single_family
    if frozen_soft_voting_bases is not None:
        frozen_payload["soft_voting_bases"] = frozen_soft_voting_bases
    frozen_payload["final_p20_train"] = final_p20_train
    written["frozen_config"] = output_dir / "frozen_config.json"
    _write_json(written["frozen_config"], frozen_payload)

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
