"""Fixtures de `scripts.demo_simulation` (tarea 0.2 del change
`add-accelerated-sensor-demo`): entorno temporal aislado (dataset,
feedback y registro MLflow propios de cada test, nunca `data/` real del
proyecto ni datasets científicos) y una configuración de sesión de
demostración reproducible, fija de antemano y no elegida por las
alertas que produce.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import mlflow
import pytest
import requests
import uvicorn

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_dataset_data_dir, get_feedback_data_dir  # noqa: E402
from app.main import app  # noqa: E402

# Sesión de referencia fija para los tests de este change: un período
# lejano en el pasado, suficientemente largo para entrenar (verificado
# contra el pipeline real en test_prepare.py / test_worker.py), nunca
# ajustado según las alertas que resulten de la semilla.
REFERENCE_SEED = 42
REFERENCE_HISTORY_DAYS = 120
REFERENCE_START_DATE = date(2026, 1, 1)
REFERENCE_DAYS = 5


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _ServerThread(threading.Thread):
    def __init__(self, config: uvicorn.Config):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(config)

    def run(self) -> None:
        self.server.run()

    def stop(self) -> None:
        self.server.should_exit = True


@pytest.fixture
def live_backend(tmp_path):
    """Backend real (`app.main.app`) servido por un `uvicorn` en un hilo
    de fondo, sobre un puerto libre en loopback — HTTP real de punta a
    punta, nunca `TestClient` ni un doble del router. El dataset, el
    feedback y el registro MLflow quedan en `tmp_path`, nunca en
    `data/` del repo ni en datasets científicos.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sessions_dir = tmp_path / "demo_sessions"

    mlflow.set_tracking_uri(f"sqlite:///{tmp_path.as_posix()}/mlflow.db")
    mlflow.set_experiment("test-demo-simulation")

    app.dependency_overrides[get_dataset_data_dir] = lambda: data_dir
    app.dependency_overrides[get_feedback_data_dir] = lambda: data_dir

    import app.pipeline as pipeline_module

    pipeline_module._selection_cache = {}

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    thread = _ServerThread(config)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            requests.get(f"{base_url}/openapi.json", timeout=0.5)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.05)
    else:
        thread.stop()
        raise RuntimeError("El backend de prueba (uvicorn) no arrancó a tiempo.")

    yield SimpleNamespace(base_url=base_url, data_dir=data_dir, sessions_dir=sessions_dir)

    thread.stop()
    thread.join(timeout=5)
    app.dependency_overrides.clear()
    pipeline_module._selection_cache = {}


@pytest.fixture
def reference_session_kwargs(live_backend):
    """Parámetros fijos de la sesión de referencia de este change (ver
    constantes del módulo), listos para pasar a
    `scripts.demo_simulation.config.DemoSessionConfig`.
    """
    return {
        "start_date": REFERENCE_START_DATE,
        "days": REFERENCE_DAYS,
        "history_days": REFERENCE_HISTORY_DAYS,
        "seed": REFERENCE_SEED,
        "backend_url": live_backend.base_url,
        "interval_seconds": 1,
    }
