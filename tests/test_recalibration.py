import numpy as np
import pandas as pd

from human_feedback.recalibration import recalibrate_model, select_recalibration_observations
from predictive_modeling.models import build_candidate_models


def test_select_recalibration_observations_excludes_confirmed_and_uncorrected_rejections():
    integrated = pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "estado_validacion": ["confirmada", "rechazada", "rechazada"],
            "etiqueta_corregida": [pd.NA, 1, pd.NA],
        }
    )

    selected = select_recalibration_observations(integrated)

    assert list(selected["fecha"]) == [pd.Timestamp("2024-01-02")]
    assert list(selected["etiqueta_corregida"]) == [1]


def test_recalibrate_model_replaces_labels_and_refits():
    rng = np.random.default_rng(0)
    n = 60
    dates = pd.to_datetime(pd.date_range("2024-01-01", periods=n, freq="D"))
    feature = rng.normal(0, 1, size=n)
    y_train = pd.Series((feature > 0).astype(int), name="stress_label")
    X_train = pd.DataFrame({"feature": feature})

    model = build_candidate_models(random_state=0)["logistic_regression"]

    corrected_fecha = dates[0]
    original_label = int(y_train.iloc[0])
    flipped_label = 1 - original_label
    recalibration_obs = pd.DataFrame(
        {"fecha": [corrected_fecha], "etiqueta_corregida": [flipped_label]}
    )

    fitted, corrected_y_train = recalibrate_model(model, X_train, y_train, dates, recalibration_obs)

    assert corrected_y_train.iloc[0] == flipped_label
    assert hasattr(fitted, "predict")
    assert len(fitted.predict(X_train)) == n
