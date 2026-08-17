import pandas as pd

from data_ingestion.storage import load_dataset
from human_feedback.registry import (
    integrate_feedback_with_predictions,
    save_feedback_log,
    upsert_feedback_log,
)
from human_feedback.schema import init_feedback_log, update_feedback


def test_save_feedback_log_roundtrips_through_storage_contract(tmp_path):
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    log = update_feedback(log, fecha=pd.Timestamp("2024-01-01"), estado_validacion="confirmada")

    save_feedback_log("feedback_test", log, data_dir=tmp_path)
    loaded = load_dataset("feedback_test", data_dir=tmp_path)

    pd.testing.assert_frame_equal(loaded, log)


def test_upsert_feedback_log_preserves_existing_validation_and_adds_new_dates():
    existing = init_feedback_log(pd.to_datetime(["2024-01-01", "2024-01-02"]), pd.Series([1, 0]))
    existing = update_feedback(
        existing, fecha=pd.Timestamp("2024-01-01"), estado_validacion="confirmada"
    )

    new_dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    new_alerts = pd.Series([0, 0, 1])

    merged = upsert_feedback_log(existing, new_dates, new_alerts)

    row_jan1 = merged.loc[merged["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    row_jan3 = merged.loc[merged["fecha"] == pd.Timestamp("2024-01-03")].iloc[0]

    assert row_jan1["estado_validacion"] == "confirmada"
    assert row_jan3["estado_validacion"] == "pendiente"
    assert len(merged) == 3


def test_integrate_feedback_with_predictions_joins_by_date():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)

    predictions = pd.DataFrame(
        {
            "fecha": dates,
            "y_proba": [0.8, 0.3],
            "stress_label": [1, 0],
        }
    )

    integrated = integrate_feedback_with_predictions(log, predictions)

    row = integrated.loc[integrated["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert row["y_proba"] == 0.8
    assert row["stress_label"] == 1
    assert row["estado_validacion"] == "pendiente"
