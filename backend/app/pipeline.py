"""Per-sensor orchestration, with fitted state reused atomically as a bundle."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pandas as pd

from architecture_integration.pipeline import predict_available, run_end_to_end_pipeline
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, get_dataset_fingerprint, load_dataset
from human_feedback.model_registry import load_latest_recalibrated_model, load_predictor_by_id
from predictive_modeling.contract import make_contract
from predictive_modeling.models import build_candidate_models

from .config import FEATURE_COLUMNS, HORIZON_DAYS, LABEL_COLUMN, RANDOM_STATE

_selection_cache_lock = threading.Lock()
_selection_cache: dict[str, dict[str, Any]] = {}


def configured_contract():
    return make_contract(FEATURE_COLUMNS, LABEL_COLUMN, HORIZON_DAYS)


def load_dataset_or_raise(sensor_id: str, data_dir: Path = DEFAULT_DATA_DIR):
    name = dataset_name_for(sensor_id)
    before = get_dataset_fingerprint(name, data_dir)
    df = load_dataset(name, data_dir=data_dir)
    after = get_dataset_fingerprint(name, data_dir)
    if before != after:
        raise ValueError("El dataset cambió durante la lectura; repetir la solicitud.")
    return df, after


def execute_configured_pipeline(
    df, sensor_id, fingerprint=None, data_dir=DEFAULT_DATA_DIR, predictor_model_id=None
):
    contract = configured_contract()
    predictor = (
        load_predictor_by_id(sensor_id, predictor_model_id, contract)
        if predictor_model_id
        else load_latest_recalibrated_model(sensor_id, expected_contract=contract)
    )
    fingerprint = fingerprint or get_dataset_fingerprint(dataset_name_for(sensor_id), data_dir)
    with _selection_cache_lock:
        cached = _selection_cache.get(sensor_id)
    if predictor is None and cached is not None and cached["fingerprint"] == fingerprint:
        cached["predictor"].validate(contract)
        predictor = cached["predictor"]
    if df.empty:
        raise ValueError("Dataset vacío.")
    split_date = pd.to_datetime(df.timestamp).sort_values().iloc[int(len(df) * 0.8)].date()
    result = run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        # The UI uses the fixed Random Forest contract; automatic CV selection
        # remains available in the experimental core and fails explicitly when
        # its folds are not eligible.
        model=predictor or build_candidate_models(RANDOM_STATE)["random_forest"],
        skip_fit=predictor is not None,
        include_anomaly_detection=False,
        horizon_days=HORIZON_DAYS,
        random_state=RANDOM_STATE,
    )
    if result["model_name"] is None:
        result["model_name"] = "random_forest"
    if predictor is None:
        with _selection_cache_lock:
            _selection_cache[sensor_id] = {
                "predictor": result["predictor"],
                "fingerprint": fingerprint,
            }
    # Latest observable day; no future label is needed to issue its alert.
    available = predict_available(df, result["predictor"])
    latest = pd.to_datetime(df.timestamp).max()
    result["forecast"] = available[available.timestamp == latest].reset_index(drop=True)
    return result
