import pandas as pd

from data_ingestion.schema import normalize_to_schema
from predictive_modeling.feature_engineering import add_lag_features, add_rolling_features
from predictive_modeling.labeling import add_stress_label, fit_stress_threshold


def _build_dataset(soil_moisture_values):
    n = len(soil_moisture_values)
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=n, freq="D"),
                "soil_moisture": soil_moisture_values,
            }
        ),
        provenance="real",
    )
    df = add_lag_features(df, columns=["soil_moisture"], lags=[1, 2])
    df = add_rolling_features(df, columns=["soil_moisture"], windows=[3])
    threshold = fit_stress_threshold(df, column="soil_moisture", percentile=20)
    df = add_stress_label(df, column="soil_moisture", horizon_days=3, threshold=threshold)
    return df


def test_changing_a_future_value_does_not_change_earlier_feature_rows():
    baseline_values = [0.30, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39]
    modified_values = list(baseline_values)
    modified_values[8] = 0.01  # cambia solo un valor cerca del final

    baseline = _build_dataset(baseline_values)
    modified = _build_dataset(modified_values)

    feature_columns = ["soil_moisture_lag1", "soil_moisture_lag2", "soil_moisture_roll_mean3"]

    # Las filas de índice 0 a 4 no deberían cambiar: ninguna de sus variables
    # (retardos/ventana móvil) depende del valor modificado en el índice 8.
    for column in feature_columns:
        pd.testing.assert_series_equal(
            baseline[column].iloc[0:5],
            modified[column].iloc[0:5],
            check_names=False,
        )
