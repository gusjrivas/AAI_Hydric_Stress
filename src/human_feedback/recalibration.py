"""Selección de observaciones y recalibración supervisada de un modelo
candidato (spec human-feedback, requirements "Selección de
observaciones para recalibración" y "Recalibración supervisada de un
modelo candidato").
"""

from __future__ import annotations

import pandas as pd
from sklearn.base import clone


def select_recalibration_observations(integrated_log: pd.DataFrame) -> pd.DataFrame:
    """Selecciona, de un registro integrado con predicciones, solo las
    observaciones `rechazada` con `etiqueta_corregida` no nula: las
    únicas que aportan una corrección real y verificable.
    """
    mask = (integrated_log["estado_validacion"] == "rechazada") & (
        integrated_log["etiqueta_corregida"].notna()
    )
    return integrated_log.loc[mask, ["fecha", "etiqueta_corregida"]].reset_index(drop=True)


def recalibrate_model(
    model: object,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    dates_train: pd.Series,
    recalibration_obs: pd.DataFrame,
) -> tuple[object, pd.Series]:
    """Reemplaza, en `y_train`, la etiqueta de cada fecha presente en
    `recalibration_obs` por su `etiqueta_corregida`, y reentrena una
    copia de `model` sobre el conjunto de entrenamiento corregido.
    Devuelve el modelo recalibrado y las etiquetas corregidas usadas.
    """
    dates_train = pd.Series(dates_train).reset_index(drop=True)
    corrected_y_train = y_train.reset_index(drop=True).copy()

    correction_by_date = dict(
        zip(recalibration_obs["fecha"], recalibration_obs["etiqueta_corregida"])
    )
    for fecha, etiqueta_corregida in correction_by_date.items():
        corrected_y_train.loc[dates_train == fecha] = etiqueta_corregida

    fitted = clone(model)
    fitted.fit(X_train, corrected_y_train)

    return fitted, corrected_y_train


def recalibrate_predictor(predictor, df, feedback_log):
    """Refit on matured observed targets, replaying all prior human corrections.

    Former evaluation rows can become training data; trained_through then moves
    forward so they cannot be evaluated out of sample again.
    """
    from dataclasses import replace
    from uuid import uuid4

    from architecture_integration.pipeline import predict_available
    from predictive_modeling.labeling import add_stress_label

    required = {"fecha", "target_timestamp", "validated_at", "model_version", "target_threshold"}
    if not required.issubset(feedback_log):
        raise ValueError("Feedback histórico sin procedencia temporal suficiente.")
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    horizon = predictor.contract["horizon_days"]
    valid = feedback_log[
        (feedback_log.estado_validacion == "rechazada")
        & feedback_log.etiqueta_corregida.notna()
        & feedback_log.validated_at.notna()
        & (feedback_log.validated_at <= now)
        & (feedback_log.validated_at >= feedback_log.target_timestamp + pd.Timedelta(days=1))
        & (feedback_log.target_timestamp < now.normalize())
        & feedback_log.model_version.notna()
    ].copy()
    if not valid.target_threshold.eq(predictor.threshold).all():
        raise ValueError("Las correcciones corresponden a otro umbral de referencia.")
    if not valid.target_timestamp.eq(valid.fecha + pd.Timedelta(days=horizon)).all():
        raise ValueError("Horizonte de feedback incompatible con el modelo.")
    previous = dict(predictor.applied_feedback or {})
    corrections = dict(previous)
    for row in valid.itertuples():
        if row.etiqueta_corregida not in (0, 1):
            raise ValueError("Etiqueta corregida inválida.")
        corrections[str(pd.Timestamp(row.fecha))] = int(row.etiqueta_corregida)
    pending = {k: v for k, v in corrections.items() if previous.get(k) != v}
    if not pending:
        raise ValueError("No hay correcciones nuevas y maduras pendientes de aplicar.")
    featured = predict_available(df, predictor)
    labels = add_stress_label(df, predictor.contract["label_column"], horizon, predictor.threshold)
    featured = featured.merge(labels[["timestamp", "stress_label"]], on="timestamp", how="left")
    for fecha, corrected in corrections.items():
        featured.loc[featured.timestamp == pd.Timestamp(fecha), "stress_label"] = corrected
    eligible = featured.dropna(subset=["stress_label"])
    eligible = eligible[eligible.target_timestamp < now.normalize()].reset_index(drop=True)
    pending_dates = pd.to_datetime(list(pending))
    if not pd.Series(pending_dates).isin(eligible.timestamp).all():
        raise ValueError(
            "Falta historial de features para aplicar todas las correcciones pendientes."
        )
    if eligible.stress_label.nunique() < 2:
        raise ValueError("La recalibración requiere ambas clases.")
    names = predictor.contract["model_features"]
    fitted = clone(predictor.model).fit(eligible[names], eligible.stress_label.astype(int))
    updated = replace(
        predictor,
        model=fitted,
        model_id=uuid4().hex,
        trained_through=str(eligible.target_timestamp.max()),
        applied_feedback=corrections,
        training_rows=len(eligible),
    )
    updated.validate(updated.contract)
    return updated, list(pending_dates), len(eligible)
