"""Pure, stateless projection of a `HistoricalPredictionRecord` onto a
simulated clock date (spec `historical-replay`, requirements RH-02, RH-03,
RH-04, RH-05).

`project(record, simulated_clock)` never mutates `record`. Absent fields
mean "not yet revealed" — they are never present as `null`/`None` in the
returned dict, per RH-02 ("el campo está ausente de la proyección, no
enmascarado").
"""

from __future__ import annotations

from datetime import date, datetime


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def project(record, simulated_clock: date) -> dict | None:
    origin = _as_date(record.identity.timestamp_origen)
    if simulated_clock < origin:
        return None

    view = {
        "timestamp_origen": record.identity.timestamp_origen.isoformat(),
        "target_timestamp": record.target_timestamp.isoformat(),
        "y_proba": record.y_proba,
        "y_pred": record.y_pred,
        "experiment_id": record.identity.experiment_id,
        "run_id": record.identity.run_id,
        "config_name": record.identity.config_name,
        "seed": record.identity.seed,
    }

    target = _as_date(record.target_timestamp)
    if simulated_clock < target:
        return view

    view["target_observed"] = record.target_observed
    if record.target_observed:
        view["y_true"] = record.y_true
        view["baselines"] = dict(record.baselines)
    return view
