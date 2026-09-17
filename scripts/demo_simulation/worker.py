"""Secuencia causal de un paso diario y su ejecución sobre N pasos
(diseño, sección 3). `run_step` es el núcleo reutilizado tanto por la
ejecución directa de la CLI (`run_session`) como por el worker de fondo
del adaptador HTTP local (`scripts.demo_simulation.control`, entrega 2).
`run_session` sostiene el lock de proceso de `scripts.demo_simulation.lock`
mientras corre, para que no compita con el worker de control sobre la
misma sesión; no ofrece pausa/continuación HTTP (eso vive en `control`).

Orden fijo por paso: generar y persistir intención (`ingest_pending`) →
`POST /sensors/{sensor_id}/readings` → persistir `ingested` → verificar
por `GET /quality/{sensor_id}` que no hay días posteriores a `d` →
persistir `forecast_pending` → `POST /forecast/{sensor_id}/run` →
confirmar por `GET /feedback/{sensor_id}` → persistir `completed` y
avanzar cursor. Cualquier fallo o resultado que no pueda confirmarse
bloquea la sesión (`status="blocked"`) y detiene el avance: esta entrega
no reintenta ni reconcilia automáticamente (eso es la entrega 2).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from .client import (
    DemoBackendError,
    DemoBackendUncertain,
    get_feedback,
    get_quality,
    post_reading,
    run_forecast,
)
from .lock import SessionLock, lock_path
from .manifest import DemoManifest, StepRecord, load_manifest, parse_date, save_manifest
from .payload import build_ingest_payload, generate_day_reading, payload_hash, reading_to_json


class DemoStepError(RuntimeError):
    """Un paso no pudo completarse ni confirmarse. La sesión queda
    `blocked`, con el manifiesto ya persistido, antes de que esta
    excepción se propague.
    """


def next_pending_day(manifest: DemoManifest) -> date:
    """Fecha calendario del próximo paso pendiente según `manifest.cursor`."""
    start = parse_date(manifest.start_date)
    return start + timedelta(days=manifest.cursor)


_next_day = next_pending_day  # alias interno, ver `run_step`


def _block(manifest: DemoManifest, sessions_root: Path, reason: str) -> None:
    manifest.status = "blocked"
    manifest.last_error = reason
    save_manifest(manifest, sessions_root)


def run_step(manifest: DemoManifest, sessions_root: Path) -> DemoManifest:
    """Ejecuta el día pendiente según `manifest.cursor`. Devuelve el
    manifiesto actualizado (ya persistido en cada fase). Levanta
    `DemoStepError` si el paso no puede confirmarse; en ese caso la
    sesión ya quedó `blocked` y persistida antes de propagar el error.
    """
    if manifest.status == "completed":
        raise DemoStepError("La sesión ya está completa; no admite rebobinar ni más pasos.")
    if manifest.cursor >= manifest.days:
        manifest.status = "completed"
        save_manifest(manifest, sessions_root)
        return manifest

    day = _next_day(manifest)
    day_key = day.isoformat()
    step = manifest.steps.get(day_key) or StepRecord(date=day_key)
    manifest.status = "running"

    try:
        if step.phase == "pending":
            reading = generate_day_reading(
                manifest.last_generated_reading, day, seed=manifest.seed + manifest.next_day_offset
            )
            payload = build_ingest_payload(reading)
            step.payload = payload
            step.payload_hash = payload_hash(payload)
            step.phase = "ingest_pending"
            manifest.steps[day_key] = step
            manifest.last_generated_reading = reading_to_json(reading)
            save_manifest(manifest, sessions_root)

        if step.phase == "ingest_pending":
            try:
                ingest_response = post_reading(
                    manifest.backend_url, manifest.sensor_id, step.payload
                )
            except DemoBackendUncertain as error:
                raise DemoStepError(
                    f"No se pudo confirmar la ingesta del {day_key}: {error}. Esta entrega no "
                    "reintenta ni reconcilia automáticamente (entrega 2)."
                ) from error
            except DemoBackendError as error:
                raise DemoStepError(f"La ingesta del {day_key} fue rechazada: {error}") from error

            if not ingest_response.get("timestamp", "").startswith(day_key):
                raise DemoStepError(
                    f"La ingesta del {day_key} devolvió una fecha distinta: "
                    f"{ingest_response.get('timestamp')!r}."
                )
            step.ingest_response = ingest_response
            step.phase = "ingested"
            manifest.steps[day_key] = step
            save_manifest(manifest, sessions_root)

        if step.phase == "ingested":
            expected_total = manifest.history_rows + manifest.cursor + 1
            quality = get_quality(manifest.backend_url, manifest.sensor_id)
            if quality is None:
                raise DemoStepError(
                    f"No se pudo verificar el dataset tras ingerir el {day_key}: sensor sin "
                    "datos según /quality."
                )
            if quality["period_end"] != day_key:
                raise DemoStepError(
                    f"El dataset reporta período hasta {quality['period_end']!r} tras ingerir "
                    f"{day_key}: se detiene el avance para no publicar días futuros."
                )
            if quality["total_rows"] != expected_total:
                raise DemoStepError(
                    f"El dataset tiene {quality['total_rows']} filas tras ingerir {day_key}; se "
                    f"esperaban {expected_total}."
                )
            step.dataset_check = {
                "period_end": quality["period_end"],
                "total_rows": quality["total_rows"],
            }
            step.phase = "forecast_pending"
            manifest.steps[day_key] = step
            save_manifest(manifest, sessions_root)

        if step.phase == "forecast_pending":
            try:
                forecast = run_forecast(manifest.backend_url, manifest.sensor_id)
            except DemoBackendUncertain as error:
                raise DemoStepError(
                    f"No se pudo confirmar el pronóstico del {day_key}: {error}. El dato ya "
                    "ingerido se conserva; esta entrega no reintenta automáticamente."
                ) from error
            except DemoBackendError as error:
                raise DemoStepError(
                    f"El pronóstico del {day_key} no se confirmó ({error}); el dato ya ingerido "
                    "se conserva."
                ) from error

            verdicts = forecast.get("verdicts", [])
            matching = [v for v in verdicts if v["fecha"] == day_key]
            if len(matching) != 1:
                raise DemoStepError(
                    f"El pronóstico no devolvió exactamente un veredicto para {day_key} "
                    f"(recibidos: {[v['fecha'] for v in verdicts]})."
                )
            verdict = matching[0]

            feedback = get_feedback(manifest.backend_url, manifest.sensor_id)
            feedback_rows = (feedback or {}).get("rows", [])
            confirmed = [row for row in feedback_rows if row["fecha"] == day_key]
            if len(confirmed) != 1:
                raise DemoStepError(
                    f"No se encontró un registro de feedback confirmado para {day_key}."
                )
            confirmation = confirmed[0]
            if (
                confirmation["fecha_objetivo"] != verdict["fecha_objetivo"]
                or confirmation["y_proba"] != verdict["probabilidad"]
            ):
                raise DemoStepError(
                    f"El registro de feedback para {day_key} no coincide con el veredicto "
                    "recién emitido; se detiene sin avanzar."
                )

            step.forecast_verdict = verdict
            step.feedback_confirmation = confirmation
            step.phase = "completed"
            manifest.steps[day_key] = step
            manifest.cursor += 1
            manifest.next_day_offset += 1
            manifest.last_error = None
            manifest.status = "completed" if manifest.cursor >= manifest.days else "running"
            save_manifest(manifest, sessions_root)

        return manifest

    except DemoStepError as error:
        step.error = str(error)
        manifest.steps[day_key] = step
        _block(manifest, sessions_root, str(error))
        raise


def run_session(
    session_id: str,
    sessions_root: Path,
    *,
    steps: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> DemoManifest:
    """Carga la sesión `session_id` y ejecuta `steps` pasos (o hasta
    completarla si `steps` es `None`), esperando `interval_seconds`
    entre pasos exitosos. Se detiene en el primer paso que no pueda
    confirmarse, dejando la sesión `blocked` y propagando la excepción.

    Sostiene `SessionLock` mientras corre: si otro proceso (por ejemplo
    el worker de fondo del adaptador HTTP, `scripts.demo_simulation.control`)
    ya la tiene, levanta `SessionLockError` sin tocar el manifiesto de la
    sesión ajena.
    """
    manifest = load_manifest(sessions_root, session_id)
    if manifest.status == "blocked":
        raise DemoStepError(
            f"La sesión '{session_id}' está bloqueada ({manifest.last_error!r}); esta entrega "
            "no reintenta automáticamente (entrega 2)."
        )
    if manifest.status in ("paused", "pausing"):
        raise DemoStepError(
            f"La sesión '{session_id}' está {manifest.status!r} por el adaptador de control; "
            "continuar requiere una orden explícita de `resume`, nunca la reanuda esta CLI sola."
        )

    with SessionLock(lock_path(sessions_root, session_id)):
        executed = 0
        while manifest.status != "completed" and (steps is None or executed < steps):
            manifest = run_step(manifest, sessions_root)
            executed += 1
            if manifest.status != "completed" and (steps is None or executed < steps):
                sleep_fn(manifest.interval_seconds)
        return manifest
