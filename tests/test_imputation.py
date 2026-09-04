import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.imputation import interpolate_missing_causal


def _series(values, start="2024-01-01"):
    n = len(values)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.date_range(start, periods=n, freq="D"),
                "temperature": values,
            }
        ),
        provenance="real",
    )


def test_interpolate_missing_causal_fills_gap_with_last_prior_value_not_average():
    df = _series([20.0, None, 24.0])

    imputed = interpolate_missing_causal(df, columns=["temperature"])

    middle_row = imputed[imputed["timestamp"] == "2024-01-02"].iloc[0]
    # forward-fill copia el último valor previo (20.0), nunca un promedio
    # con el valor siguiente (que sería 22.0 con interpolación lineal).
    assert middle_row["temperature"] == 20.0
    assert bool(middle_row["temperature_imputado"]) is True

    first_row = imputed[imputed["timestamp"] == "2024-01-01"].iloc[0]
    assert bool(first_row["temperature_imputado"]) is False


def test_interpolate_missing_causal_leaves_columns_without_gaps_unflagged():
    df = _series([20.0, 21.0])

    imputed = interpolate_missing_causal(df, columns=["temperature"])

    assert not imputed["temperature_imputado"].any()


def test_interpolate_missing_causal_without_warm_start_leaves_leading_nan_as_nan():
    df = _series([None, None, 24.0])

    imputed = interpolate_missing_causal(df, columns=["temperature"])

    assert imputed["temperature"].iloc[0:2].isna().all()
    assert not imputed["temperature_imputado"].iloc[0:2].any()
    assert imputed["temperature"].iloc[2] == 24.0


def test_interpolate_missing_causal_with_warm_start_fills_leading_nan_from_previous_period():
    df = _series([None, None, 24.0])
    warm_start = pd.Series({"temperature": 18.0})

    imputed = interpolate_missing_causal(df, columns=["temperature"], warm_start=warm_start)

    assert imputed["temperature"].iloc[0] == 18.0
    assert imputed["temperature"].iloc[1] == 18.0
    assert bool(imputed["temperature_imputado"].iloc[0]) is True
    assert bool(imputed["temperature_imputado"].iloc[1]) is True
    assert imputed["temperature"].iloc[2] == 24.0


def test_changing_a_future_value_does_not_change_an_earlier_imputed_value():
    baseline = _series([20.0, None, None, 24.0])
    modified = _series([20.0, None, None, 999.0])

    baseline_imputed = interpolate_missing_causal(baseline, columns=["temperature"])
    modified_imputed = interpolate_missing_causal(modified, columns=["temperature"])

    # las dos filas intermedias imputadas (índices 1 y 2) dependen solo del
    # valor previo (índice 0, sin cambios) -> deben ser idénticas en ambas
    # corridas, aunque el valor final (futuro) haya cambiado radicalmente.
    pd.testing.assert_series_equal(
        baseline_imputed["temperature"].iloc[1:3],
        modified_imputed["temperature"].iloc[1:3],
    )


def test_interpolate_missing_causal_never_uses_a_later_value_within_the_same_partition():
    # gap al principio, sin warm_start y sin ningún valor previo dentro del
    # propio df: no debe completarse con el valor posterior (eso sería bfill).
    df = _series([None, 50.0])

    imputed = interpolate_missing_causal(df, columns=["temperature"])

    assert pd.isna(imputed["temperature"].iloc[0])


def test_test_partition_can_bootstrap_from_the_last_value_observed_in_train():
    train_tail_value = 22.5
    warm_start = pd.Series({"temperature": train_tail_value})
    test_df = _series([None, 23.0], start="2024-02-01")

    imputed_test = interpolate_missing_causal(
        test_df, columns=["temperature"], warm_start=warm_start
    )

    assert imputed_test["temperature"].iloc[0] == train_tail_value
