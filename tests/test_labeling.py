import pandas as pd

from data_ingestion.schema import normalize_to_schema
from predictive_modeling.labeling import add_stress_label, fit_stress_threshold


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


def test_fit_stress_threshold_computes_the_percentile_of_the_given_dataframe():
    values = [0.10, 0.20, 0.30, 0.40, 0.50]
    df = _soil_moisture_series(values)

    threshold = fit_stress_threshold(df, column="soil_moisture", percentile=20)

    assert threshold == df["soil_moisture"].quantile(0.20)


def test_add_stress_label_flags_future_value_below_threshold():
    # 10 valores altos, el día 5 (índice 4) tiene un valor futuro bajo en t+3
    values = [0.40] * 10
    values[7] = 0.10  # muy por debajo del percentil 20 de esta serie
    df = _soil_moisture_series(values)
    threshold = fit_stress_threshold(df, column="soil_moisture", percentile=20)

    labeled = add_stress_label(df, column="soil_moisture", horizon_days=3, threshold=threshold)

    # el día en índice 4 (2024-01-05) mira 3 días adelante -> índice 7 (valor bajo)
    row = labeled[labeled["timestamp"] == "2024-01-05"].iloc[0]
    assert row["stress_label"] == 1


def test_add_stress_label_leaves_unlabelable_tail_as_na():
    values = [0.40] * 10
    df = _soil_moisture_series(values)
    threshold = fit_stress_threshold(df, column="soil_moisture", percentile=20)

    labeled = add_stress_label(df, column="soil_moisture", horizon_days=3, threshold=threshold)

    # los últimos 3 días no tienen horizonte futuro completo
    tail = labeled.iloc[-3:]
    assert tail["stress_label"].isna().all()

    # el resto sí tiene etiqueta (0, ya que todos los valores son iguales al umbral)
    head = labeled.iloc[:-3]
    assert head["stress_label"].notna().all()


def test_add_stress_label_reuses_a_frozen_threshold_instead_of_recomputing_it():
    # El umbral se calcula sobre una serie (simula "train") y se aplica,
    # congelado, a una serie distinta (simula "test") — nunca se recalcula
    # el percentil sobre la segunda serie, aunque su distribución sea
    # radicalmente distinta.
    train_like = _soil_moisture_series([0.40] * 10)
    threshold = fit_stress_threshold(train_like, column="soil_moisture", percentile=20)

    test_like = _soil_moisture_series([0.01] * 10)  # todo muy por debajo del umbral de train
    labeled = add_stress_label(
        test_like, column="soil_moisture", horizon_days=3, threshold=threshold
    )

    # con el umbral de train (0.40), todos los valores de test (0.01) quedan
    # por debajo -> stress_label=1 en todas las filas con horizonte completo.
    head = labeled.iloc[:-3]
    assert (head["stress_label"] == 1).all()
