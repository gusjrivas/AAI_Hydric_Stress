import pandas as pd

from data_ingestion.schema import normalize_to_schema
from predictive_modeling.labeling import add_stress_label


def _soil_moisture_series(values):
    n = len(values)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=n, freq="D"),
                "soil_moisture": values,
            }
        ),
        provenance="real",
    )


def test_add_stress_label_flags_future_value_below_threshold():
    # 10 valores altos, el día 5 (índice 4) tiene un valor futuro bajo en t+3
    values = [0.40] * 10
    values[7] = 0.10  # muy por debajo del percentil 20 de esta serie
    df = _soil_moisture_series(values)

    labeled = add_stress_label(df, column="soil_moisture", horizon_days=3, percentile=20)

    # el día en índice 4 (2024-01-05) mira 3 días adelante -> índice 7 (valor bajo)
    row = labeled[labeled["timestamp"] == "2024-01-05"].iloc[0]
    assert row["stress_label"] == 1


def test_add_stress_label_leaves_unlabelable_tail_as_na():
    values = [0.40] * 10
    df = _soil_moisture_series(values)

    labeled = add_stress_label(df, column="soil_moisture", horizon_days=3, percentile=20)

    # los últimos 3 días no tienen horizonte futuro completo
    tail = labeled.iloc[-3:]
    assert tail["stress_label"].isna().all()

    # el resto sí tiene etiqueta (0, ya que todos los valores son iguales al umbral)
    head = labeled.iloc[:-3]
    assert head["stress_label"].notna().all()
