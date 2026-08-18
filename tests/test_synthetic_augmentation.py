import numpy as np
import pandas as pd

from experiment_runner.synthetic_augmentation import add_synthetic_rows


def _feature_engineered_train_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    feature_a = rng.normal(0.35, 0.03, size=n)
    feature_b = rng.normal(20, 3, size=n)
    stress_label = rng.integers(0, 2, size=n)
    return pd.DataFrame(
        {
            "feature_a_lag1": feature_a,
            "feature_b_roll_mean3": feature_b,
            "stress_label": stress_label,
            "origen": "real",
        }
    )


def test_add_synthetic_rows_marks_provenance_and_keeps_binary_label():
    train_df = _feature_engineered_train_df()

    augmented = add_synthetic_rows(
        train_df,
        feature_columns=["feature_a_lag1", "feature_b_roll_mean3"],
        target_column="stress_label",
        n_samples=20,
        random_state=42,
    )

    assert len(augmented) == len(train_df) + 20
    synthetic_rows = augmented[augmented["origen"] == "sintetico"]
    assert len(synthetic_rows) == 20
    assert set(synthetic_rows["stress_label"].unique()) <= {0, 1}
    assert not synthetic_rows[["feature_a_lag1", "feature_b_roll_mean3"]].isna().any().any()
