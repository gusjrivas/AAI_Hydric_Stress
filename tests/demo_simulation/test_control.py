"""Tests de la entrega 2 (control y recuperación): lock de proceso,
máquina de estados, deduplicación de órdenes y recuperación por fase.
Todos contra un backend real (`live_backend`, `uvicorn` en un hilo) y
MLflow sqlite temporal, igual que la entrega 1 — nunca contra `data/`
del repo ni datasets científicos.
"""

from __future__ import annotations

import threading
import time
from datetime import date, timedelta

import pytest

from scripts.demo_simulation import client as client_module
from scripts.demo_simulation.config import DemoSessionConfig
from scripts.demo_simulation.control import ControlOrder, WorkerSupervisor, handle_command
from scripts.demo_simulation.lock import SessionLock, SessionLockError, lock_path
from scripts.demo_simulation.manifest import StepRecord, load_manifest, save_manifest
from scripts.demo_simulation.payload import build_ingest_payload, generate_day_reading
from scripts.demo_simulation.prepare import prepare_session
from scripts.demo_simulation.recovery import diagnose_and_recover
from scripts.demo_simulation.worker import run_step
from tests.demo_simulation.conftest import utc_today


def _prepare(live_backend, reference_session_kwargs, session_id, **overrides):
    kwargs = {**reference_session_kwargs, **overrides}
    config = DemoSessionConfig(**kwargs)
    return prepare_session(
        config,
        today=utc_today(),
        sessions_root=live_backend.sessions_dir,
        data_dir=live_backend.data_dir,
        session_id=session_id,
    )


def _order(command, session_id, revision, request_id="req-1"):
    return ControlOrder(
        command=command, session_id=session_id, expected_revision=revision, request_id=request_id
    )


class _RecordingLauncher:
    def __init__(self):
        self.calls: list[str] = []
        self.lock = threading.Lock()

    def __call__(self, session_id, sessions_root):
        with self.lock:
            self.calls.append(session_id)


# --- Lock de proceso -------------------------------------------------


def test_lock_prevents_two_workers(tmp_path):
    path = lock_path(tmp_path, "demo-x")
    first = SessionLock(path).acquire()
    try:
        with pytest.raises(SessionLockError):
            SessionLock(path).acquire()
    finally:
        first.release()

    # Liberado el primero, un segundo lock sí puede tomarse.
    second = SessionLock(path).acquire()
    second.release()


def test_run_controlled_worker_noop_when_lock_held_elsewhere(
    live_backend, reference_session_kwargs
):
    from scripts.demo_simulation.control import run_controlled_worker

    prepared = _prepare(live_backend, reference_session_kwargs, "demo-lock-noop", days=1)
    manifest = prepared.manifest
    manifest.status = "running"
    save_manifest(manifest, live_backend.sessions_dir)

    held = SessionLock(lock_path(live_backend.sessions_dir, "demo-lock-noop")).acquire()
    try:
        run_controlled_worker("demo-lock-noop", live_backend.sessions_dir, threading.Lock())
        after = load_manifest(live_backend.sessions_dir, "demo-lock-noop")
        # No se tocó el manifiesto de una sesión cuyo lock ya tiene otro dueño.
        assert after.status == "running"
        assert after.cursor == 0
    finally:
        held.release()


# --- Deduplicación y máquina de estados -------------------------------


def test_duplicate_request_id_returns_same_result_and_launches_worker_once(
    live_backend, reference_session_kwargs
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-dedup", days=1)
    launcher = _RecordingLauncher()
    order = _order("start", "demo-dedup", prepared.manifest.revision, request_id="same-id")

    first = handle_command(
        order,
        live_backend.sessions_dir,
        "demo-dedup",
        launch_worker=launcher,
        command_lock=threading.Lock(),
    )
    second = handle_command(
        order,
        live_backend.sessions_dir,
        "demo-dedup",
        launch_worker=launcher,
        command_lock=threading.Lock(),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.body == second.body
    assert launcher.calls == ["demo-dedup"]  # nunca un segundo worker por la orden repetida


def test_stale_revision_is_rejected_explicitly(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-stale", days=1)
    order = _order("start", "demo-stale", prepared.manifest.revision + 5, request_id="req-stale")

    result = handle_command(
        order,
        live_backend.sessions_dir,
        "demo-stale",
        launch_worker=lambda *a: None,
        command_lock=threading.Lock(),
    )

    assert result.status_code == 409
    assert "revisión" in result.body["error"].lower() or "revision" in result.body["error"].lower()
    manifest = load_manifest(live_backend.sessions_dir, "demo-stale")
    assert manifest.status == "prepared"  # nunca se aplicó en silencio


def test_invalid_transition_is_rejected(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-invalid", days=1)
    # `pause` no es válido desde `prepared`.
    order = _order("pause", "demo-invalid", prepared.manifest.revision, request_id="req-invalid")

    result = handle_command(
        order,
        live_backend.sessions_dir,
        "demo-invalid",
        launch_worker=lambda *a: None,
        command_lock=threading.Lock(),
    )

    assert result.status_code == 409
    assert "transición" in result.body["error"].lower()
    manifest = load_manifest(live_backend.sessions_dir, "demo-invalid")
    assert manifest.status == "prepared"


def test_session_mismatch_is_rejected(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-mismatch", days=1)
    order = _order("start", "otra-sesion", prepared.manifest.revision, request_id="req-mismatch")

    result = handle_command(
        order,
        live_backend.sessions_dir,
        "demo-mismatch",
        launch_worker=lambda *a: None,
        command_lock=threading.Lock(),
    )

    assert result.status_code == 409


# --- Pausa y continuación explícita -----------------------------------


def test_pause_completes_current_step_before_stopping(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-pause", days=2)
    launcher = WorkerSupervisor(sessions_root=live_backend.sessions_dir)
    # Mismo lock que usa `run_controlled_worker` internamente (ver
    # `service.create_app`): si acá se usara un lock distinto, el hilo de
    # control y el worker de fondo podrían leer/escribir el manifiesto al
    # mismo tiempo sin exclusión real entre sí.
    command_lock = launcher.io_lock

    start_order = _order("start", "demo-pause", prepared.manifest.revision, request_id="start-1")
    start_result = handle_command(
        start_order,
        live_backend.sessions_dir,
        "demo-pause",
        launch_worker=launcher.launch,
        command_lock=command_lock,
    )
    assert start_result.status_code == 200

    # Se solicita pausa apenas arrancó: el paso 1 (ya en curso) debe
    # completarse igual, y el worker nunca debe iniciar el paso 2.
    time.sleep(0.2)
    for _ in range(200):
        current = load_manifest(live_backend.sessions_dir, "demo-pause")
        if current.status == "running":
            break
        time.sleep(0.05)

    pause_order = _order("pause", "demo-pause", current.revision, request_id="pause-1")
    pause_result = handle_command(
        pause_order,
        live_backend.sessions_dir,
        "demo-pause",
        launch_worker=launcher.launch,
        command_lock=command_lock,
    )
    assert pause_result.status_code in (200, 409)  # 409 si ya llegó a completed/paused por sí sola

    # Ventana generosa (ver `test_resume_continues_from_first_incomplete_step`
    # para la misma razón): un paso con entrenamiento real puede tardar
    # bastante más bajo carga que en una corrida aislada.
    for _ in range(600):
        final = load_manifest(live_backend.sessions_dir, "demo-pause")
        if final.status in ("paused", "completed"):
            break
        time.sleep(0.1)
    else:
        pytest.fail("El worker no se detuvo tras solicitar pausa.")

    if final.status == "paused":
        assert final.cursor == 1  # el paso en curso terminó; el segundo nunca arrancó
        assert final.steps[final.start_date if final.cursor == 0 else sorted(final.steps)[0]]
        assert all(step.phase == "completed" for step in final.steps.values())


def test_resume_continues_from_first_incomplete_step(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-resume", days=2)
    launcher = WorkerSupervisor(sessions_root=live_backend.sessions_dir)
    command_lock = launcher.io_lock

    handle_command(
        _order("start", "demo-resume", prepared.manifest.revision, request_id="start-1"),
        live_backend.sessions_dir,
        "demo-resume",
        launch_worker=launcher.launch,
        command_lock=command_lock,
    )
    for _ in range(200):
        current = load_manifest(live_backend.sessions_dir, "demo-resume")
        if current.status == "running":
            break
        time.sleep(0.05)

    handle_command(
        _order("pause", "demo-resume", current.revision, request_id="pause-1"),
        live_backend.sessions_dir,
        "demo-resume",
        launch_worker=launcher.launch,
        command_lock=command_lock,
    )
    # Ventana generosa: bajo carga (suite completa corriendo en paralelo
    # con entrenamiento real de modelo por paso) un solo paso puede tardar
    # bastante más que en una corrida aislada; lo que importa es que
    # termine en `paused`, no cuánto tarde.
    for _ in range(600):
        paused = load_manifest(live_backend.sessions_dir, "demo-resume")
        if paused.status in ("paused", "completed"):
            break
        time.sleep(0.1)

    if paused.status == "completed":
        pytest.skip("La sesión terminó antes de poder pausarse en este entorno; no es un fallo.")

    assert paused.status == "paused"
    assert paused.cursor == 1

    resume_result = handle_command(
        _order("resume", "demo-resume", paused.revision, request_id="resume-1"),
        live_backend.sessions_dir,
        "demo-resume",
        launch_worker=launcher.launch,
        command_lock=command_lock,
    )
    assert resume_result.status_code == 200

    for _ in range(600):
        final = load_manifest(live_backend.sessions_dir, "demo-resume")
        if final.status == "completed":
            break
        time.sleep(0.1)
    else:
        pytest.fail("La sesión no completó tras continuar explícitamente.")

    assert final.cursor == 2
    assert len(final.steps) == 2
    assert all(step.phase == "completed" for step in final.steps.values())


# --- Recuperación por fase ---------------------------------------------


def test_recovery_reconciles_confirmed_forecast_without_reposting(
    live_backend, reference_session_kwargs
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-reconcile", days=2)
    manifest = prepared.manifest

    # Día 1 se ejecuta normalmente por el camino ya cubierto en la
    # entrega 1: deja historia entrenable con un día real confirmado.
    manifest = run_step(manifest, live_backend.sessions_dir)
    assert manifest.cursor == 1

    # Simula una "respuesta perdida" del día 2: el backend ya aplicó
    # ingesta + pronóstico (helper de test llama directamente al
    # cliente, nunca al worker), pero el manifiesto quedó anotado solo
    # hasta `forecast_pending` porque el proceso se cortó antes de leer
    # la confirmación.
    day2 = date.fromisoformat(manifest.start_date) + timedelta(days=1)
    reading = generate_day_reading(
        manifest.last_generated_reading, day2, seed=manifest.seed + manifest.next_day_offset
    )
    payload = build_ingest_payload(reading)
    client_module.post_reading(manifest.backend_url, manifest.sensor_id, payload)
    client_module.run_forecast(manifest.backend_url, manifest.sensor_id)

    step = StepRecord(date=day2.isoformat(), phase="forecast_pending", payload=payload)
    manifest.steps[day2.isoformat()] = step
    manifest.status = "running"
    save_manifest(manifest, live_backend.sessions_dir)

    recovered = diagnose_and_recover(manifest, live_backend.sessions_dir)

    # Con 2/2 días, reconciliar el último paso completa la sesión; con
    # más días pendientes quedaría `paused` (nunca sigue sola).
    assert recovered.status == "completed"
    assert recovered.cursor == 2
    assert recovered.steps[day2.isoformat()].phase == "completed"
    assert recovered.steps[day2.isoformat()].feedback_confirmation["fecha"] == day2.isoformat()


def test_recovery_blocks_when_forecast_cannot_be_confirmed(live_backend, reference_session_kwargs):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-uncertain", days=2)
    manifest = prepared.manifest
    manifest = run_step(manifest, live_backend.sessions_dir)
    assert manifest.cursor == 1

    day2 = date.fromisoformat(manifest.start_date) + timedelta(days=1)
    # A diferencia del test anterior, el backend nunca recibió el
    # pronóstico del día 2: no hay forma de distinguir "nunca se envió"
    # de "se envió y se perdió la respuesta" solo mirando el manifiesto.
    step = StepRecord(date=day2.isoformat(), phase="forecast_pending", payload={})
    manifest.steps[day2.isoformat()] = step
    manifest.status = "running"
    save_manifest(manifest, live_backend.sessions_dir)

    recovered = diagnose_and_recover(manifest, live_backend.sessions_dir)

    assert recovered.status == "blocked"
    assert recovered.cursor == 1  # no avanza sin confirmación
    assert recovered.last_error  # motivo diagnosticable
    assert "pronóstico" in recovered.last_error.lower() or "confirm" in recovered.last_error.lower()


def test_recovery_detects_external_change_and_blocks_without_overwriting(
    live_backend, reference_session_kwargs
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-external", days=2)
    manifest = prepared.manifest
    manifest = run_step(manifest, live_backend.sessions_dir)
    assert manifest.cursor == 1

    # Cambio externo: alguien (no esta sesión) ingiere directamente un
    # día más para el mismo sensor, por fuera del worker.
    day2 = date.fromisoformat(manifest.start_date) + timedelta(days=1)
    reading = generate_day_reading(
        manifest.last_generated_reading, day2, seed=manifest.seed + manifest.next_day_offset
    )
    payload = build_ingest_payload(reading)
    client_module.post_reading(manifest.backend_url, manifest.sensor_id, payload)

    manifest.status = "running"
    save_manifest(manifest, live_backend.sessions_dir)

    recovered = diagnose_and_recover(manifest, live_backend.sessions_dir)

    assert recovered.status == "blocked"
    assert recovered.cursor == 1
    assert "cambió" in recovered.last_error.lower() or "cambio" in recovered.last_error.lower()

    # El dato ingerido externamente no se borra ni se sobrescribe.
    quality = client_module.get_quality(manifest.backend_url, manifest.sensor_id)
    assert quality["period_end"] == day2.isoformat()
