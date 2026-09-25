"""Feedback de demostración (spec `historical-replay`, requirement RH-07):
persistido en un almacenamiento exclusivo, separado del paquete científico,
del `feedback_log` operativo (`src/human_feedback/schema.py`) y de la
recalibración — nunca alcanza `select_recalibration_observations`,
`recalibrate_predictor` ni `recalibrate_model`. Reutiliza únicamente los
nombres de estado de `human_feedback` (`confirmada`/`rechazada`), no su
módulo ni su archivo.

El feedback solo puede registrarse después de que la observación haya sido
revelada (`target_observed=true` y `simulated_date >= target_timestamp`,
espejo del contrato de `historical_replay.projection.project`) — nunca
antes. `registered_at` (fecha real) y `simulated_at` (fecha simulada al
registrar) se guardan siempre por separado; el registro nunca se atribuye a
un experto ni a una fecha histórica que no ocurrió.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from data_ingestion.storage import interprocess_lock

ADMITTED_VALIDATION_STATES = ("confirmada", "rechazada")
ADMITTED_ETIQUETAS = (0, 1)


class UnknownPredictionError(ValueError):
    """The referenced `timestamp_origen` does not match any prediction in
    the loaded package — feedback is never linked to a fabricated identity."""


class FeedbackNotYetRevealedError(ValueError):
    """The prediction's observation has not been revealed yet at
    `simulated_date` — feedback cannot reference a result the replay
    itself would not show at that clock."""


class InvalidFeedbackContentError(ValueError):
    """`estado_validacion`/`etiqueta_corregida` outside the admitted values."""


@dataclass(frozen=True)
class ReplayFeedbackRecord:
    timestamp_origen: str
    experiment_id: str
    run_id: str
    estado_validacion: str
    etiqueta_corregida: int | None
    observacion: str | None
    registered_at: str
    simulated_at: str


class ReplayFeedbackStore:
    """Append-only JSON-lines store, one file per `package_id`, isolated
    under its own directory — never `data/feedback__<sensor_id>.parquet`,
    never inside `replay_packages/`. Writes are serialized across
    processes via `interprocess_lock` on a dedicated `.lock` file next to
    the `.jsonl` (never the `.jsonl` itself as lock target), because
    append-mode writes are not guaranteed atomic between processes on
    this platform (F-08)."""

    def __init__(self, storage_dir: Path, *, package_id: str):
        self._path = Path(storage_dir) / f"{package_id}.jsonl"
        self._lock_path = Path(storage_dir) / f"{package_id}.jsonl.lock"

    def append(self, record: ReplayFeedbackRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with interprocess_lock(self._lock_path):
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def list_for(self, timestamp_origen: str) -> list[ReplayFeedbackRecord]:
        if not self._path.exists():
            return []
        records = []
        with self._path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if payload["timestamp_origen"] == timestamp_origen:
                    records.append(ReplayFeedbackRecord(**payload))
        return records


def _find_record(records, timestamp_origen: date):
    for record in records:
        if record.identity.timestamp_origen == timestamp_origen:
            return record
    return None


def register_feedback(
    records,
    store: ReplayFeedbackStore,
    *,
    timestamp_origen: date,
    simulated_date: date,
    estado_validacion: str,
    etiqueta_corregida: int | None = None,
    observacion: str | None = None,
) -> ReplayFeedbackRecord:
    record = _find_record(records, timestamp_origen)
    if record is None:
        raise UnknownPredictionError(
            f"No hay ninguna predicción con origen {timestamp_origen.isoformat()}; "
            "no se registra feedback sobre una identidad inexistente."
        )

    if estado_validacion not in ADMITTED_VALIDATION_STATES:
        raise InvalidFeedbackContentError(
            f"estado_validacion debe ser uno de {ADMITTED_VALIDATION_STATES}: "
            f"{estado_validacion!r}"
        )
    if etiqueta_corregida is not None and etiqueta_corregida not in ADMITTED_ETIQUETAS:
        raise InvalidFeedbackContentError(
            f"etiqueta_corregida debe ser una de {ADMITTED_ETIQUETAS}: {etiqueta_corregida!r}"
        )

    revealed = record.target_observed and simulated_date >= record.target_timestamp
    if not revealed:
        raise FeedbackNotYetRevealedError(
            f"La observación de {timestamp_origen.isoformat()} todavía no fue revelada "
            f"en la fecha simulada {simulated_date.isoformat()}; no se registra feedback "
            "sobre un resultado que el propio recorrido no muestra todavía."
        )

    feedback = ReplayFeedbackRecord(
        timestamp_origen=timestamp_origen.isoformat(),
        experiment_id=record.identity.experiment_id,
        run_id=record.identity.run_id,
        estado_validacion=estado_validacion,
        etiqueta_corregida=etiqueta_corregida,
        observacion=observacion,
        registered_at=datetime.now(timezone.utc).isoformat(),
        simulated_at=simulated_date.isoformat(),
    )
    store.append(feedback)
    return feedback


def visible_feedback_for(
    records, store: ReplayFeedbackStore, *, timestamp_origen: date, simulated_date: date
) -> list[ReplayFeedbackRecord]:
    """Proyección de lectura del feedback ya persistido: retrocede el reloj
    y el feedback vuelve a ocultarse, sin borrar el registro (mismo
    principio que `historical_replay.projection.project`)."""
    record = _find_record(records, timestamp_origen)
    if record is None:
        return []
    revealed = record.target_observed and simulated_date >= record.target_timestamp
    if not revealed:
        return []
    return store.list_for(timestamp_origen.isoformat())
