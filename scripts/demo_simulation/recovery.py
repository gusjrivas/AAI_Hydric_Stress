"""Recuperación conservadora por fase (diseño, sección 5). Se invoca al
arrancar el adaptador HTTP (`scripts.demo_simulation.service`) sobre una
sesión que quedó `running`/`pausing` tras un reinicio del controlador, y
dentro de la orden explícita `resume` cuando la sesión está `blocked`
(diseño, sección 6: "`blocked` exige reconciliación satisfactoria, nunca
salta comprobaciones").

Nunca reintenta un POST no confirmado ni reanuda sola: solo decide, a
partir de lecturas (`GET`), si el paso pendiente puede considerarse
seguro de continuar (`paused`) o si la incertidumbre exige mantener el
bloqueo (`blocked`) hasta que un operador lo revise.
"""

from __future__ import annotations

from pathlib import Path

from .client import DemoBackendError, DemoBackendUncertain, get_feedback, get_quality
from .manifest import DemoManifest, StepRecord, save_manifest
from .worker import next_pending_day


def _last_completed_step(manifest: DemoManifest) -> StepRecord | None:
    completed = [s for s in manifest.steps.values() if s.phase == "completed"]
    if not completed:
        return None
    return max(completed, key=lambda s: s.date)


def _detect_external_change(manifest: DemoManifest) -> str | None:
    """Compara el estado actual del backend contra los únicos dos
    estados que esta sesión reconoce como propios: el último punto
    confirmado (`dataset_check` del último paso completado, o el fin de
    la historia inicial si ningún paso terminó todavía) y, si el paso
    pendiente ya dejó una intención de payload persistida, el resultado
    esperado de que ese payload se haya aplicado (la reconciliación de
    "respuesta perdida" que maneja `diagnose_and_recover` a continuación).

    Cualquier otro estado del dataset —una fila de más, un período
    distinto, menos filas— no lo explica ningún paso propio de esta
    sesión: se reporta para bloquear, sin sobrescribir ni intentar
    "reparar" nada.
    """
    try:
        quality = get_quality(manifest.backend_url, manifest.sensor_id)
    except DemoBackendUncertain as error:
        return (
            f"No se pudo verificar el dataset del sensor '{manifest.sensor_id}' tras el "
            f"reinicio: {error}"
        )
    except DemoBackendError as error:
        return f"El backend rechazó la verificación del dataset tras el reinicio: {error}"

    last_step = _last_completed_step(manifest)
    if last_step is not None and last_step.dataset_check is not None:
        baseline_end = last_step.dataset_check.get("period_end")
        baseline_rows = last_step.dataset_check.get("total_rows")
    else:
        baseline_end = manifest.history_end
        baseline_rows = manifest.history_rows

    if quality is None:
        if baseline_rows:
            return (
                f"El sensor '{manifest.sensor_id}' ya no tiene dataset según /quality; se "
                "detecta un cambio externo ajeno a esta sesión."
            )
        return None

    if quality.get("period_end") == baseline_end and quality.get("total_rows") == baseline_rows:
        return None  # nada avanzó desde el último punto confirmado por esta sesión.

    day_key = next_pending_day(manifest).isoformat()
    pending_step = manifest.steps.get(day_key)
    if pending_step is not None and pending_step.payload is not None:
        expected_rows = manifest.history_rows + manifest.cursor + 1
        if quality.get("period_end") == day_key and quality.get("total_rows") == expected_rows:
            return None  # coincide con el payload que esta sesión ya había persistido.

    return (
        f"El dataset del sensor '{manifest.sensor_id}' cambió por fuera de lo que esta sesión "
        f"reconoce: se esperaba período hasta {baseline_end!r} con {baseline_rows} filas (o, si ya "
        f"había un paso propio pendiente para {day_key}, hasta esa fecha), el backend reporta "
        f"{quality.get('period_end')!r} con {quality.get('total_rows')} filas. No se sobrescribe "
        "ni se borra nada; se bloquea para revisión manual."
    )


def diagnose_and_recover(manifest: DemoManifest, sessions_root: Path) -> DemoManifest:
    """Diagnostica el estado de la sesión y la deja `paused`, `blocked`
    o `completed` (nunca `running`): reanudar la ejecución siempre exige
    una orden explícita posterior (`start`/`resume`), incluso cuando la
    reconciliación resulta satisfactoria.
    """
    if manifest.status not in ("running", "pausing", "blocked"):
        return manifest

    if manifest.cursor >= manifest.days:
        manifest.status = "completed"
        manifest.last_error = None
        save_manifest(manifest, sessions_root)
        return manifest

    external_change = _detect_external_change(manifest)
    if external_change:
        manifest.status = "blocked"
        manifest.last_error = external_change
        save_manifest(manifest, sessions_root)
        return manifest

    day = next_pending_day(manifest)
    day_key = day.isoformat()
    step = manifest.steps.get(day_key)

    if step is None or step.phase in ("pending", "ingest_pending", "ingested"):
        # La ingesta reemplaza la fila del mismo día (idempotente por
        # fecha, ver proposal.md): reintentar el POST de ingesta desde
        # aquí no duplica nada. La consulta de calidad tras ingerir es
        # una lectura. Es seguro dejar la sesión pausada a la espera de
        # una orden explícita de continuación.
        manifest.status = "paused"
        manifest.last_error = None
        save_manifest(manifest, sessions_root)
        return manifest

    if step.phase == "forecast_pending":
        # El POST de pronóstico no es idempotente: no se reintenta sin
        # antes comprobar, por lectura, si ya se aplicó.
        try:
            feedback = get_feedback(manifest.backend_url, manifest.sensor_id)
        except DemoBackendUncertain as error:
            manifest.status = "blocked"
            manifest.last_error = (
                f"No se pudo verificar si el pronóstico del {day_key} se ejecutó tras el "
                f"reinicio: {error}. No se reintenta automáticamente."
            )
            save_manifest(manifest, sessions_root)
            return manifest
        except DemoBackendError as error:
            manifest.status = "blocked"
            manifest.last_error = (
                f"El backend rechazó la verificación del pronóstico del {day_key} tras el "
                f"reinicio: {error}."
            )
            save_manifest(manifest, sessions_root)
            return manifest

        rows = (feedback or {}).get("rows", [])
        confirmed = [row for row in rows if row["fecha"] == day_key]
        if len(confirmed) == 1:
            confirmation = confirmed[0]
            step.forecast_verdict = {
                "fecha": confirmation["fecha"],
                "fecha_objetivo": confirmation["fecha_objetivo"],
                "probabilidad": confirmation.get("y_proba"),
            }
            step.feedback_confirmation = confirmation
            step.phase = "completed"
            step.error = None
            manifest.steps[day_key] = step
            manifest.cursor += 1
            manifest.next_day_offset += 1
            manifest.last_error = None
            manifest.status = "completed" if manifest.cursor >= manifest.days else "paused"
            save_manifest(manifest, sessions_root)
            return manifest

        manifest.status = "blocked"
        manifest.last_error = (
            f"No se pudo confirmar si el pronóstico del {day_key} llegó a ejecutarse tras el "
            "reinicio del controlador (ni evidencia de éxito ni garantía de que no vaya a "
            "completarse todavía). Se bloquea la sesión; requiere revisión manual antes de "
            "continuar."
        )
        save_manifest(manifest, sessions_root)
        return manifest

    # step.phase == "completed": el cursor debería haber avanzado ya;
    # es seguro continuar en el próximo día.
    manifest.status = "paused"
    manifest.last_error = None
    save_manifest(manifest, sessions_root)
    return manifest
