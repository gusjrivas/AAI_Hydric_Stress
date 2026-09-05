from datetime import date

import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.splitting import purge_target_horizon, temporal_train_test_split


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


def _train_with_dates(dates):
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(dates),
                "temperature": list(range(len(dates))),
            }
        ),
        provenance="real",
    )


def test_purge_target_horizon_removes_the_last_horizon_days_rows():
    train = _train_with_dates(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])

    purged = purge_target_horizon(train, horizon_days=2)

    assert list(purged["timestamp"]) == list(pd.to_datetime(["2024-01-01", "2024-01-02"]))


def test_purge_target_horizon_with_zero_horizon_returns_train_unchanged():
    train = _train_with_dates(["2024-01-01", "2024-01-02", "2024-01-03"])

    purged = purge_target_horizon(train, horizon_days=0)

    assert list(purged["timestamp"]) == list(train["timestamp"])


def test_purge_target_horizon_returns_empty_when_horizon_covers_all_rows():
    train = _train_with_dates(["2024-01-01", "2024-01-02"])

    purged = purge_target_horizon(train, horizon_days=3)

    assert len(purged) == 0
