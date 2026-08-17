import pandas as pd

from predictive_modeling.alerts import analyze_prediction_errors, generate_alerts


def test_generate_alerts_flags_rows_above_threshold():
    y_proba = pd.Series([0.9, 0.4, 0.5, 0.1])

    alerts = generate_alerts(y_proba, threshold=0.5)

    assert list(alerts) == [1, 0, 1, 0]


def test_analyze_prediction_errors_lists_false_positive_and_negative_dates():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])
    y_true = pd.Series([0, 1, 1, 0])
    alerts = pd.Series([1, 0, 1, 0])

    errors = analyze_prediction_errors(dates, y_true, alerts)

    assert list(errors["false_positives"]) == [pd.Timestamp("2024-01-01")]
    assert list(errors["false_negatives"]) == [pd.Timestamp("2024-01-02")]
