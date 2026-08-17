import pandas as pd

from human_feedback.schema import init_feedback_log, update_feedback


def test_init_feedback_log_marks_every_alert_as_pending():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])

    log = init_feedback_log(dates, alerts)

    assert list(log["estado_validacion"]) == ["pendiente", "pendiente"]
    assert log["etiqueta_corregida"].isna().all()
    assert log["observacion"].isna().all()


def test_update_feedback_confirms_a_pending_alert():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)

    updated = update_feedback(log, fecha=pd.Timestamp("2024-01-01"), estado_validacion="confirmada")

    row = updated.loc[updated["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert row["estado_validacion"] == "confirmada"


def test_update_feedback_rejects_with_correction_and_observation():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)

    updated = update_feedback(
        log,
        fecha=pd.Timestamp("2024-01-01"),
        estado_validacion="rechazada",
        etiqueta_corregida=0,
        observacion="no habia estres real ese dia",
    )

    row = updated.loc[updated["fecha"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert row["estado_validacion"] == "rechazada"
    assert row["etiqueta_corregida"] == 0
    assert row["observacion"] == "no habia estres real ese dia"
