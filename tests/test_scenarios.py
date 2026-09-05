import numpy as np
import pandas as pd

from experiment_runner.scenarios import inject_gaussian_noise, subsample_training_period


def _dataset(n=100, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(pd.date_range("2024-01-01", periods=n, freq="D"))
    return pd.DataFrame(
        {
            "timestamp": dates,
            "soil_moisture": rng.normal(0.35, 0.03, size=n),
        }
    )


def test_subsample_training_period_keeps_most_recent_fraction_and_all_test_rows():
    df = _dataset(n=100)
    split_date = df["timestamp"].iloc[80].date()

    reduced = subsample_training_period(df, split_date=split_date, train_fraction=0.5)

    cutoff = pd.Timestamp(split_date)
    train_rows = reduced[reduced["timestamp"] < cutoff]
    test_rows = reduced[reduced["timestamp"] >= cutoff]

    assert len(train_rows) == 40
    assert len(test_rows) == 20
    assert train_rows["timestamp"].max() == df[df["timestamp"] < cutoff]["timestamp"].max()


def test_subsample_training_period_no_reduction_when_fraction_is_one():
    df = _dataset(n=50)
    split_date = df["timestamp"].iloc[40].date()

    reduced = subsample_training_period(df, split_date=split_date, train_fraction=1.0)

    pd.testing.assert_frame_equal(
        reduced.sort_values("timestamp").reset_index(drop=True),
        df.sort_values("timestamp").reset_index(drop=True),
    )


def test_inject_gaussian_noise_changes_values_but_preserves_shape():
    df = _dataset(n=30)

    noisy = inject_gaussian_noise(
        df,
        columns=["soil_moisture"],
        noise_std_ratio=0.5,
        random_state=42,
        scales={"soil_moisture": df.iloc[:20].soil_moisture.std()},
    )

    assert noisy.shape == df.shape
    assert not noisy["soil_moisture"].equals(df["soil_moisture"])


def test_inject_gaussian_noise_zero_ratio_leaves_values_unchanged():
    df = _dataset(n=30)

    noisy = inject_gaussian_noise(
        df, columns=["soil_moisture"], noise_std_ratio=0.0, random_state=42
    )

    pd.testing.assert_series_equal(noisy["soil_moisture"], df["soil_moisture"])
