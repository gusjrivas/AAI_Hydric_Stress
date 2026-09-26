import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from predictive_modeling.bundle_packaging import (
    EstimatorNotFittedError,
    FeatureNameCountMismatchError,
    IncompatibleFeatureNamesError,
    attach_feature_names,
)


def _fitted_model():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    y = np.array([0, 1, 0, 1])
    return RandomForestClassifier(n_estimators=2, random_state=0).fit(X, y), X, y


def test_attach_feature_names_sets_attribute_matching_fit_order():
    model, _, _ = _fitted_model()
    assert not hasattr(model, "feature_names_in_")

    attach_feature_names(model, ["temperature", "humidity"])

    assert list(model.feature_names_in_) == ["temperature", "humidity"]


def test_attach_feature_names_rejects_an_unfitted_estimator():
    model = RandomForestClassifier(n_estimators=2, random_state=0)
    with pytest.raises(EstimatorNotFittedError):
        attach_feature_names(model, ["temperature", "humidity"])


def test_attach_feature_names_rejects_wrong_column_count():
    model, _, _ = _fitted_model()
    with pytest.raises(FeatureNameCountMismatchError):
        attach_feature_names(model, ["only_one"])


def test_attach_feature_names_refuses_to_overwrite_incompatible_names():
    import pandas as pd

    X = pd.DataFrame({"a": [1.0, 3.0, 5.0, 7.0], "b": [2.0, 4.0, 6.0, 8.0]})
    y = np.array([0, 1, 0, 1])
    model = RandomForestClassifier(n_estimators=2, random_state=0).fit(X, y)
    assert list(model.feature_names_in_) == ["a", "b"]

    with pytest.raises(IncompatibleFeatureNamesError):
        attach_feature_names(model, ["temperature", "humidity"])


def test_attach_feature_names_is_a_noop_when_names_already_match():
    import pandas as pd

    X = pd.DataFrame({"a": [1.0, 3.0, 5.0, 7.0], "b": [2.0, 4.0, 6.0, 8.0]})
    y = np.array([0, 1, 0, 1])
    model = RandomForestClassifier(n_estimators=2, random_state=0).fit(X, y)

    attach_feature_names(model, ["a", "b"])  # should not raise
    assert list(model.feature_names_in_) == ["a", "b"]


def test_attach_feature_names_does_not_change_predicted_probabilities():
    model, X, _ = _fitted_model()
    before = model.predict_proba(X)
    attach_feature_names(model, ["temperature", "humidity"])
    after = model.predict_proba(X)
    assert np.array_equal(before, after)
