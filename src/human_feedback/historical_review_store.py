"""Feedback aislado del recorrido historico (HU7/HU8, UI de productor).

Una revision registrada mientras se navega una emision historica es una
prueba tecnica del mecanismo de revision bajo el reloj simulado -- nunca
una opinion operativa real. Debe quedar aislada de
`human_feedback.operational_repository.OperationalRepository`: separar
componentes de React no basta (ver `HistoricalWalkthrough.tsx`); la
garantia real esta en que ninguna escritura de este modulo toca jamas
`ui_metadata/operational_v2__<sensor_id>.json`, ni ninguna lectura de ese
archivo consulta jamas este directorio. Una actualizacion operativa sobre
el mismo `forecast_id` (revision real via `/forecasts/{id}/reviews`)
nunca puede modificar lo que este modulo devuelve, y viceversa.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from data_ingestion.sensor_naming import validate_sensor_id
from data_ingestion.storage import StorageLockTimeout, atomic_write_bytes, interprocess_lock
from human_feedback.operational_repository import (
    OperationalRepositoryError,
    REVIEW_ACTIONS,
    _isoformat_z,
    _request_hash,
)

FORMAT_VERSION = 1
HISTORICAL_FEEDBACK_DIRECTORY = "historical_feedback"

PENDING_REVIEW_STATE = {"status": "pending", "revision": 0, "latest_review": None}


class HistoricalReviewStore:
    """Documento JSON propio por sensor, en su propio subdirectorio --
    nunca `ui_metadata/`. `data_dir` es el mismo directorio del catalogo
    (lecturas/emisiones ya preparadas), pero el archivo que este modulo
    lee y escribe no se superpone con ninguno de
    `OperationalRepository`."""

    def __init__(self, data_dir: Path, sensor_id: str):
        self.sensor_id = validate_sensor_id(sensor_id)
        self.directory = Path(data_dir) / HISTORICAL_FEEDBACK_DIRECTORY
        self.path = self.directory / f"{self.sensor_id}.json"
        self.lock_path = self.directory / f".{self.sensor_id}.lock"

    def _empty(self) -> dict[str, Any]:
        return {
            "format_version": FORMAT_VERSION,
            "sensor_id": self.sensor_id,
            "reviews": {},
            "idempotency": {},
        }

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise OperationalRepositoryError(
                "historical_feedback_storage_unavailable",
                "No se pudo leer el feedback historico.",
                503,
            ) from error
        if document.get("format_version") != FORMAT_VERSION:
            raise OperationalRepositoryError(
                "unsupported_historical_feedback_version",
                "La version persistida del feedback historico no es compatible.",
                503,
                {"format_version": document.get("format_version")},
            )
        return document

    def _write(self, document: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        try:
            atomic_write_bytes(self.path, content)
        except OSError as error:
            raise OperationalRepositoryError(
                "historical_feedback_storage_unavailable",
                "No se pudo persistir el feedback historico.",
                503,
            ) from error

    @contextmanager
    def _locked_document(self, *, timeout: float = 10.0) -> Iterator[dict[str, Any]]:
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            with interprocess_lock(self.lock_path, timeout=timeout):
                yield self._read()
        except StorageLockTimeout as error:
            raise OperationalRepositoryError(
                "historical_feedback_storage_unavailable",
                "No se pudo bloquear el feedback historico.",
                503,
            ) from error
        except OperationalRepositoryError:
            raise
        except OSError as error:
            raise OperationalRepositoryError(
                "historical_feedback_storage_unavailable",
                "No se pudo bloquear el feedback historico.",
                503,
            ) from error

    def get_review_state(self, forecast_id: str) -> dict[str, Any]:
        """Nunca consulta `OperationalRepository`: si no hay una revision
        historica registrada para este `forecast_id`, es `pending` --
        independientemente de si existe una revision operativa real sobre
        la misma emision."""
        document = self._read()
        return document["reviews"].get(forecast_id, dict(PENDING_REVIEW_STATE))

    def submit_review(
        self,
        *,
        forecast_id: str,
        request_id: str,
        expected_revision: int,
        action: str,
        comment: str | None,
        forecast_alert: bool,
        review_open_at: datetime,
        now: datetime,
    ) -> tuple[int, dict[str, Any]]:
        if action not in REVIEW_ACTIONS:
            raise OperationalRepositoryError(
                "invalid_action", "action debe ser confirm o reject.", 422
            )
        if not request_id:
            raise OperationalRepositoryError(
                "invalid_request_id", "request_id es obligatorio.", 422
            )
        with self._locked_document() as document:
            request_payload = {
                "expected_revision": expected_revision,
                "action": action,
                "comment": comment,
            }
            request_hash = _request_hash(request_payload)
            idem_key = f"{forecast_id}:{request_id}"
            idem_store = document["idempotency"]
            existing_idem = idem_store.get(idem_key)
            if existing_idem is not None:
                if existing_idem["request_hash"] != request_hash:
                    raise OperationalRepositoryError(
                        "idempotency_conflict",
                        "El request_id ya se uso con otro contenido.",
                        409,
                    )
                return existing_idem["status_code"], existing_idem["review_snapshot"]

            if now < review_open_at:
                raise OperationalRepositoryError(
                    "review_not_open",
                    "La revision todavia no esta abierta.",
                    409,
                    {"review_open_at": _isoformat_z(review_open_at)},
                )

            state = document["reviews"].get(forecast_id, dict(PENDING_REVIEW_STATE))
            if expected_revision != state["revision"]:
                raise OperationalRepositoryError(
                    "revision_conflict",
                    "La revision esperada no coincide con la revision actual.",
                    409,
                    {
                        "expected_revision": expected_revision,
                        "actual_revision": state["revision"],
                    },
                )

            observed_label = forecast_alert if action == "confirm" else not forecast_alert
            new_revision = state["revision"] + 1
            review_event = {
                "review_id": "histrev_" + uuid4().hex,
                "request_id": request_id,
                "revision": new_revision,
                "forecast_id": forecast_id,
                "action": action,
                "observed_label": observed_label,
                "comment": comment,
                "reviewed_at": _isoformat_z(now),
            }
            new_state = {
                "status": "confirmed" if action == "confirm" else "rejected",
                "revision": new_revision,
                "latest_review": review_event,
            }
            document["reviews"][forecast_id] = new_state
            idem_store[idem_key] = {
                "request_hash": request_hash,
                "status_code": 201,
                "review_snapshot": new_state,
            }
            self._write(document)
            return 201, new_state


__all__ = ["HistoricalReviewStore", "PENDING_REVIEW_STATE"]
