"""Máquina de estados, deduplicación de órdenes y worker de fondo del
adaptador HTTP local (diseño, secciones 4 y 6). Este módulo no depende
de FastAPI: `scripts.demo_simulation.service` lo envuelve en endpoints
HTTP, lo que permite probar la máquina de estados y la exclusión sin
levantar un servidor.

Invariantes de esta entrega:

- Una orden repetida (mismo `request_id`) siempre devuelve el resultado
  ya registrado, nunca se vuelve a evaluar ni dispara un segundo worker.
- Una revisión (`expected_revision`) desactualizada se rechaza con 409
  explícito, nunca se aplica ni se ignora en silencio.
- Una transición no contemplada desde el estado vigente se rechaza con
  409, nunca se fuerza.
- La aceptación de la orden se persiste antes de despertar el worker.
- Pausar nunca cancela un POST en vuelo: solo se aplica entre pasos
  (ver `run_controlled_worker`).
- Continuar tras un reinicio nunca es automático: siempre requiere una
  orden explícita de `start`/`resume` procesada por este módulo.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .lock import SessionLock, SessionLockError, lock_path
from .manifest import DemoManifest, SessionStatus, load_manifest, save_manifest
from .recovery import diagnose_and_recover
from .worker import DemoStepError, next_pending_day, run_step

# Transiciones válidas por orden: {estado_actual: estado_resultante}.
_TRANSITIONS: dict[str, dict[SessionStatus, SessionStatus]] = {
    "start": {"prepared": "running"},
    "pause": {"running": "pausing"},
    "resume": {"paused": "running", "blocked": "running"},
}


@dataclass(frozen=True)
class ControlOrder:
    command: str  # "start" | "pause" | "resume"
    session_id: str
    expected_revision: int
    request_id: str


@dataclass(frozen=True)
class ControlResult:
    status_code: int
    body: dict[str, Any]


def public_view(manifest: DemoManifest) -> dict[str, Any]:
    """Vista pública de una sesión (diseño, sección 6): sin rutas
    locales ni detalles internos del manifiesto, solo lo necesario para
    que la UI/el operador entiendan el progreso y un error legible.
    """
    current_step = None
    if manifest.cursor < manifest.days:
        current_step = manifest.steps.get(next_pending_day(manifest).isoformat())

    completed_dates = sorted(s.date for s in manifest.steps.values() if s.phase == "completed")
    if current_step is not None:
        phase = current_step.phase
    elif manifest.status == "completed":
        phase = "completed"
    else:
        phase = "pending"
    return {
        "session_id": manifest.session_id,
        "sensor_id": manifest.sensor_id,
        "status": manifest.status,
        "phase": phase,
        "cursor": manifest.cursor,
        "days": manifest.days,
        "simulated_date": current_step.date if current_step else None,
        "last_ingested_date": completed_dates[-1] if completed_dates else None,
        "last_forecast_date": completed_dates[-1] if completed_dates else None,
        "interval_seconds": manifest.interval_seconds,
        "revision": manifest.revision,
        "error": manifest.last_error,
    }


def _reject(
    manifest: DemoManifest,
    sessions_root: Path,
    order: ControlOrder,
    status_code: int,
    reason: str,
) -> ControlResult:
    body = {"error": reason, "status": manifest.status, "revision": manifest.revision}
    manifest.command_log[order.request_id] = {"status_code": status_code, "body": body}
    save_manifest(manifest, sessions_root)
    return ControlResult(status_code, body)


def handle_command(
    order: ControlOrder,
    sessions_root: Path,
    controlled_session_id: str,
    *,
    launch_worker: Callable[[str, Path], None],
    command_lock: threading.Lock,
) -> ControlResult:
    """Aplica `order` a la sesión controlada, bajo `command_lock` (un
    único lock de proceso serializa las órdenes de control HTTP de este
    servicio: dos clientes concurrentes nunca evalúan la orden en
    paralelo contra el mismo manifiesto).
    """
    with command_lock:
        if order.session_id != controlled_session_id:
            return ControlResult(
                409,
                {
                    "error": (
                        f"Este servicio controla la sesión '{controlled_session_id}'; "
                        f"la orden nombra '{order.session_id}'."
                    )
                },
            )

        manifest = load_manifest(sessions_root, controlled_session_id)

        if order.request_id in manifest.command_log:
            record = manifest.command_log[order.request_id]
            return ControlResult(record["status_code"], record["body"])

        if order.expected_revision != manifest.revision:
            return _reject(
                manifest,
                sessions_root,
                order,
                409,
                f"Revisión obsoleta: la orden trae revisión {order.expected_revision}, la "
                f"vigente es {manifest.revision}. Volvé a consultar el estado antes de reintentar.",
            )

        transitions = _TRANSITIONS.get(order.command)
        if transitions is None:
            return _reject(
                manifest,
                sessions_root,
                order,
                409,
                f"Orden de control desconocida: '{order.command}'.",
            )

        if order.command == "resume" and manifest.status == "blocked":
            manifest = diagnose_and_recover(manifest, sessions_root)
            if manifest.status == "blocked":
                return _reject(
                    manifest,
                    sessions_root,
                    order,
                    409,
                    f"La reconciliación no pudo despejar el bloqueo: {manifest.last_error}",
                )
            if manifest.status != "paused":
                # La reconciliación ya completó la sesión o la dejó en
                # un estado terminal: no hay transición de `resume` que
                # aplicar además de la reconciliación misma.
                body = public_view(manifest)
                manifest.command_log[order.request_id] = {"status_code": 200, "body": body}
                save_manifest(manifest, sessions_root)
                return ControlResult(200, body)
            # Reconciliación satisfactoria: la sesión quedó `paused`,
            # ahora sí es válido aplicar la transición normal de `resume`.

        if manifest.status not in transitions:
            return _reject(
                manifest,
                sessions_root,
                order,
                409,
                f"Transición inválida: '{order.command}' no es válida desde el estado "
                f"'{manifest.status}'.",
            )

        manifest.status = transitions[manifest.status]
        if manifest.status != "blocked":
            manifest.last_error = None
        body = public_view(manifest)
        manifest.command_log[order.request_id] = {"status_code": 200, "body": body}
        # Persistir aceptación antes de despertar el worker (diseño, sección 6).
        save_manifest(manifest, sessions_root)

        if order.command in ("start", "resume") and manifest.status == "running":
            launch_worker(controlled_session_id, sessions_root)

        return ControlResult(200, body)


def run_controlled_worker(session_id: str, sessions_root: Path, io_lock: threading.Lock) -> None:
    """Worker de fondo de una sesión controlada por HTTP. Corre pasos
    mientras el estado sea `running`, y se detiene sin iniciar el
    siguiente paso apenas detecta `pausing` (nunca cancela un POST en
    vuelo: el chequeo ocurre entre pasos, nunca en medio de `run_step`).

    `io_lock` es el mismo lock de proceso que serializa las órdenes de
    control HTTP (`handle_command`): sin él, una orden de pausa podría
    guardar el manifiesto al mismo tiempo que este worker, y la última
    escritura ganadora podría revertir en silencio la pausa solicitada
    o el progreso del worker (evitado aquí, no solo por disciplina de
    revisión sino por exclusión real de escritura).

    Si no puede tomar el lock de sistema operativo de la sesión (otro
    worker ya la tiene, por ejemplo la CLI de ejecución directa), se
    retira sin tocar el manifiesto: la sesión ajena sigue su curso.
    """
    try:
        lock = SessionLock(lock_path(sessions_root, session_id)).acquire()
    except SessionLockError:
        return

    try:
        while True:
            with io_lock:
                manifest = load_manifest(sessions_root, session_id)
                # Una pausa solicitada durante el intervalo entre pasos (o
                # antes de que este worker llegara a correr el primero)
                # debe resolverse acá mismo, nunca dejarse "pausing" a
                # medias: por eso este chequeo, igual que el de abajo tras
                # cada paso, siempre completa la transición a `paused`
                # antes de retirarse.
                if manifest.status == "pausing":
                    manifest.status = "paused"
                    manifest.last_error = None
                    save_manifest(manifest, sessions_root)
                    return
                if manifest.status != "running":
                    return
                if manifest.cursor >= manifest.days:
                    manifest.status = "completed"
                    manifest.last_error = None
                    save_manifest(manifest, sessions_root)
                    return

            try:
                with io_lock:
                    manifest = run_step(manifest, sessions_root)
            except DemoStepError:
                return  # `run_step` ya dejó la sesión `blocked` y persistida.

            with io_lock:
                manifest = load_manifest(sessions_root, session_id)
                if manifest.status == "pausing":
                    manifest.status = "paused"
                    manifest.last_error = None
                    save_manifest(manifest, sessions_root)
                    return
                if manifest.status != "running":
                    return
                interval = manifest.interval_seconds
            if manifest.cursor < manifest.days:
                time.sleep(interval)
    finally:
        lock.release()


@dataclass
class WorkerSupervisor:
    """Lanza como máximo un hilo de worker por sesión dentro de este
    proceso (dedup en memoria, complementaria al lock de sistema
    operativo entre procesos), compartiendo `io_lock` con
    `handle_command` para que ambos caminos nunca escriban el
    manifiesto al mismo tiempo. Pensado para uso desde
    `scripts.demo_simulation.service`.
    """

    sessions_root: Path
    io_lock: threading.Lock = field(default_factory=threading.Lock)
    _threads: dict[str, threading.Thread] = field(default_factory=dict)
    _guard: threading.Lock = field(default_factory=threading.Lock)

    def launch(self, session_id: str, sessions_root: Path) -> None:
        with self._guard:
            existing = self._threads.get(session_id)
            if existing is not None and existing.is_alive():
                return
            thread = threading.Thread(
                target=run_controlled_worker,
                args=(session_id, sessions_root, self.io_lock),
                name=f"demo-worker-{session_id}",
                daemon=True,
            )
            self._threads[session_id] = thread
            thread.start()
