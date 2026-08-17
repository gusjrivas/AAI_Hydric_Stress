import numpy as np
import pandas as pd

from predictive_modeling.relevance import feature_relevance


def test_feature_relevance_reports_correlation_with_target():
    rng = np.random.default_rng(0)
    n = 100
    feature_a = rng.normal(0, 1, size=n)
    feature_b = rng.normal(0, 1, size=n)
    target = feature_a * 2 + rng.normal(0, 0.1, size=n)  # muy correlacionada con feature_a

    df = pd.DataFrame({"feature_a": feature_a, "feature_b": feature_b, "target": target})

    report = feature_relevance(
        df, feature_columns=["feature_a", "feature_b"], target_column="target"
    )

    assert abs(report["feature_a"]) > 0.9
    assert abs(report["feature_b"]) < abs(report["feature_a"])
