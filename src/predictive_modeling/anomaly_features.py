"""Fold-local anomaly transformation for temporal model selection."""

from sklearn.base import BaseEstimator, TransformerMixin

from data_quality.anomaly_detection import apply_anomaly_detector, fit_anomaly_detector


class AnomalyFeatures(TransformerMixin, BaseEstimator):
    def __init__(self, raw_columns, model_columns, contamination=0.05, random_state=42):
        self.raw_columns = raw_columns
        self.model_columns = model_columns
        self.contamination = contamination
        self.random_state = random_state

    def fit(self, X, y=None):
        self.detector_ = fit_anomaly_detector(
            X, self.raw_columns, self.contamination, self.random_state
        )
        return self

    def transform(self, X):
        return apply_anomaly_detector(X, self.raw_columns, self.detector_)[
            self.model_columns + ["is_anomaly"]
        ]
