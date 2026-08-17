import pandas as pd

from data_ingestion.schema import normalize_to_schema
from predictive_modeling.feature_engineering import add_lag_features, add_rolling_features


def _climate_df():
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=6, freq="D"),
                "temperature": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        ),
        provenance="real",
    )


def test_add_lag_features_uses_only_past_values():
    df = _climate_df()

    result = add_lag_features(df, columns=["temperature"], lags=[1, 2])

    # el día en índice 3 (valor 40.0) con lag 1 debe ver el valor del día anterior (30.0)
    assert result["temperature_lag1"].iloc[3] == 30.0
    # con lag 2 debe ver el valor de 2 días antes (20.0)
    assert result["temperature_lag2"].iloc[3] == 20.0
    # el primer día no tiene pasado -> NaN
    assert pd.isna(result["temperature_lag1"].iloc[0])


def test_add_rolling_features_uses_only_past_and_current_values():
    df = _climate_df()

    result = add_rolling_features(df, columns=["temperature"], windows=[3])

    # media móvil de 3 días hasta el índice 2 (10, 20, 30) = 20.0
    assert result["temperature_roll_mean3"].iloc[2] == 20.0
    # no debe incluir el valor del día 3 (40.0) en la ventana del día 2
    assert result["temperature_roll_mean3"].iloc[2] != round((20.0 + 30.0 + 40.0) / 3, 6)
