import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.scaling import apply_standardization, standardize


def test_apply_standardization_uses_given_params_not_own_stats():
    train = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "temperature": [20.0, 22.0, 24.0],
            }
        ),
        provenance="real",
    )
    test = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-04"]),
                "temperature": [30.0],
            }
        ),
        provenance="real",
    )

    _, params = standardize(train, columns=["temperature"])
    scaled_test = apply_standardization(test, params)

    mean, std = params["temperature"]
    expected = (30.0 - mean) / std
    assert round(scaled_test["temperature"].iloc[0], 6) == round(expected, 6)
