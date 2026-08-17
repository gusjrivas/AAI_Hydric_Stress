from datetime import date

import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.splitting import temporal_train_test_split


def test_temporal_split_does_not_mix_dates_across_sets():
    df = normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
                ),
                "temperature": [20.0, 21.0, 22.0, 23.0],
            }
        ),
        provenance="real",
    )

    train, test = temporal_train_test_split(df, split_date=date(2024, 1, 3))

    assert train["timestamp"].max() < test["timestamp"].min()
    assert list(train["timestamp"]) == list(pd.to_datetime(["2024-01-01", "2024-01-02"]))
    assert list(test["timestamp"]) == list(pd.to_datetime(["2024-01-03", "2024-01-04"]))
