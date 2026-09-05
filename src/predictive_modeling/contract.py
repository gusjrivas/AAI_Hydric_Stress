"""Versioned fitted predictor and the complete semantics of its inputs/target."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

PIPELINE_VERSION = "controlled_daily_v3"


class ModelContractMismatch(ValueError):
    """The saved predictor cannot be used with the requested experiment."""


def feature_names(columns, lags, windows, include_current=False):
    names = list(columns) if include_current else []
    names += [f"{c}_lag{lag}" for c in columns for lag in lags]
    names += [f"{c}_roll_mean{window}" for c in columns for window in windows]
    if not names or len(names) != len(set(names)):
        raise ValueError("Las variables predictoras deben ser únicas y no vacías.")
    return names


def make_contract(
    columns,
    label_column="soil_moisture",
    horizon_days=3,
    lags=None,
    rolling_windows=None,
    include_current=False,
    include_anomaly_detection=False,
    contamination=0.05,
    alert_threshold=0.5,
    percentile=20.0,
):
    lags = [1, 2, 3] if lags is None else list(lags)
    windows = [3, 7] if rolling_windows is None else list(rolling_windows)
    if not isinstance(horizon_days, int) or horizon_days < 1:
        raise ValueError("horizon_days debe ser un entero positivo.")
    if any(not isinstance(x, int) or x < 1 for x in lags + windows):
        raise ValueError("Retardos y ventanas deben ser enteros positivos.")
    if not 0 < percentile < 100 or not 0 <= alert_threshold <= 1:
        raise ValueError("Percentil o umbral de alerta inválido.")
    names = feature_names(columns, lags, windows, include_current)
    if include_anomaly_detection:
        names += ["is_anomaly"]
    units = {
        "soil_moisture": "m3/m3",
        "solar_radiation": "MJ/m2/day",
        "relative_humidity": "%",
        "temperature": "degC",
        "precipitation": "mm/day",
        "wind_speed": "m/s",
        "et0": "mm/day",
    }
    return {
        "contract_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "raw_input_features": list(columns),
        "model_features": names,
        "input_dtype": "float64",
        "model_dtypes": ["bool" if c == "is_anomaly" else "float64" for c in names],
        "units": {c: units.get(c, "declared_by_dataset") for c in columns},
        "frequency": "D",
        "day_convention": "UTC_naive_midnight",
        "issuance": "after_daily_observations_available",
        "imputation": "causal_ffill",
        "lags": lags,
        "rolling_windows": windows,
        "rolling_includes_current": True,
        "include_current": include_current,
        "include_anomaly_detection": include_anomaly_detection,
        "contamination": contamination if include_anomaly_detection else None,
        "label_column": label_column,
        "horizon_days": horizon_days,
        "target_rule": "observed_value_at_t_plus_h_less_than_frozen_threshold",
        "percentile": percentile,
        "positive_class": 1,
        "alert_threshold": alert_threshold,
    }


def positive_probability(model, X):
    if X.empty:
        return pd.Series(dtype=float)
    classes = list(model.classes_)
    if 1 not in classes:
        return pd.Series(np.zeros(len(X)))
    return pd.Series(model.predict_proba(X)[:, classes.index(1)], dtype=float)


@dataclass
class FittedPredictor:
    model: Any
    contract: dict
    threshold: float
    trained_through: str
    detector: Any = None
    model_name: str | None = None
    calibration_end: str | None = None
    applied_feedback: dict | None = None
    model_id: str = field(default_factory=lambda: uuid4().hex)
    selection_warning: str | None = None
    fold_diagnostics: list = field(default_factory=list)
    training_rows: int = 0

    def validate(self, expected):
        if self.contract != expected:
            changed = sorted(
                k
                for k in set(self.contract) | set(expected)
                if self.contract.get(k) != expected.get(k)
            )
            raise ModelContractMismatch(f"Contrato incompatible: {changed}")
        actual = list(getattr(self.model, "feature_names_in_", []))
        if actual != self.contract["model_features"]:
            raise ModelContractMismatch("Metadata distinta de las columnas reales del estimador.")
        if not np.isfinite(self.threshold):
            raise ModelContractMismatch("Umbral de estrés no finito.")
        if self.contract["include_anomaly_detection"] != (self.detector is not None):
            raise ModelContractMismatch("Falta o sobra el detector ajustado.")
