"""Tests del adaptador HTTP local (`scripts.demo_simulation.service`),
entrega 2. Sirve la app FastAPI con `uvicorn` en un hilo sobre un puerto
libre de loopback y habla con ella por HTTP real (`requests`), igual que
`tests/demo_simulation/conftest.py::live_backend` para el backend de la
entrega 1 — nunca `fastapi.testclient.TestClient` (evita además una
dependencia de `starlette.testclient` que no está garantizada en el
entorno de `python-quality`, donde solo se instala el extra `dev`, no
`backend`).
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass

import pytest
import requests
import uvicorn

from scripts.demo_simulation.config import DemoSessionConfig
from scripts.demo_simulation.manifest import load_manifest
from scripts.demo_simulation.prepare import prepare_session
from scripts.demo_simulation.service import create_app
from tests.demo_simulation.conftest import utc_today

ALLOWED_ORIGIN = "http://localhost:5173"


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


@dataclass
class _HttpClient:
    """Envoltorio delgado sobre `requests` con la misma forma mínima que
    usan los tests (`.get`/`.post` devolviendo algo con `.status_code` y
    `.json()`), para no acoplar los tests al transporte real.
    """

    base_url: str

    def get(self, path: str, headers: dict | None = None) -> requests.Response:
        return requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)

    def post(self, path: str, json: dict, headers: dict | None = None) -> requests.Response:
        return requests.post(f"{self.base_url}{path}", json=json, headers=headers, timeout=10)


@pytest.fixture
def _client(live_backend, request):
    """Levanta el adaptador de control (`create_app`) en un `uvicorn`
    real sobre un puerto de loopback libre, y lo apaga al terminar el
    test. Requiere el `session_id` como parámetro indirecto.
    """
    threads: list[_ServerThread] = []

    def _start(session_id: str) -> _HttpClient:
        app = create_app(session_id, live_backend.sessions_dir, allowed_origins=[ALLOWED_ORIGIN])
        port = _free_port()
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        thread = _ServerThread(config)
        thread.start()
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(200):
            try:
                requests.get(f"{base_url}/demo/session", timeout=0.5)
                break
            except requests.exceptions.ConnectionError:
                time.sleep(0.05)
        else:
            thread.stop()
            raise RuntimeError("El adaptador de control no arrancó a tiempo.")
        threads.append(thread)
        return _HttpClient(base_url=base_url)

    yield _start

    for thread in threads:
        thread.stop()
        thread.join(timeout=5)


def test_service_refuses_to_start_without_a_prepared_session(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_app("demo-inexistente", tmp_path)


def test_get_session_is_read_only(live_backend, reference_session_kwargs, _client):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-get", days=1)
    client = _client("demo-http-get")

    for _ in range(3):
        response = client.get("/demo/session")
        assert response.status_code == 200
        assert response.json()["status"] == "prepared"

    after = load_manifest(live_backend.sessions_dir, "demo-http-get")
    # GET repetido no crea recursos, no inicia el worker y no cambia la
    # revisión del manifiesto.
    assert after.revision == prepared.manifest.revision
    assert after.status == "prepared"


def test_get_session_missing_returns_404_without_creating_anything(
    live_backend, reference_session_kwargs, _client
):
    # Sesión preparada y luego desaparecida (ej. borrada a mano): GET no
    # la recrea ni sustituye la lectura por un valor inventado.
    session_id = "demo-http-vanish"
    _prepare(live_backend, reference_session_kwargs, session_id, days=1)
    client = _client(session_id)
    manifest_path = live_backend.sessions_dir / session_id / "manifest.json"
    manifest_path.unlink()

    response = client.get("/demo/session")
    assert response.status_code == 404
    assert not manifest_path.exists()


def test_duplicate_start_request_is_idempotent_over_http(
    live_backend, reference_session_kwargs, _client
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-dedup", days=1)
    client = _client("demo-http-dedup")
    order = {
        "session_id": "demo-http-dedup",
        "expected_revision": prepared.manifest.revision,
        "request_id": "same-request",
    }

    first = client.post("/demo/session/start", json=order, headers={"origin": ALLOWED_ORIGIN})
    second = client.post("/demo/session/start", json=order, headers={"origin": ALLOWED_ORIGIN})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    for _ in range(200):
        if load_manifest(live_backend.sessions_dir, "demo-http-dedup").status == "completed":
            break
        time.sleep(0.1)


def test_stale_revision_rejected_over_http(live_backend, reference_session_kwargs, _client):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-stale", days=1)
    client = _client("demo-http-stale")
    order = {
        "session_id": "demo-http-stale",
        "expected_revision": prepared.manifest.revision + 10,
        "request_id": "req-1",
    }

    response = client.post("/demo/session/start", json=order, headers={"origin": ALLOWED_ORIGIN})

    assert response.status_code == 409


def test_unauthorized_origin_is_rejected_on_mutating_request(
    live_backend, reference_session_kwargs, _client
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-origin", days=1)
    client = _client("demo-http-origin")
    order = {
        "session_id": "demo-http-origin",
        "expected_revision": prepared.manifest.revision,
        "request_id": "req-1",
    }

    response = client.post(
        "/demo/session/start", json=order, headers={"origin": "http://evil.example"}
    )

    assert response.status_code == 403
    manifest = load_manifest(live_backend.sessions_dir, "demo-http-origin")
    assert manifest.status == "prepared"  # la orden nunca se procesó


def test_get_is_not_blocked_by_origin_validation(live_backend, reference_session_kwargs, _client):
    _prepare(live_backend, reference_session_kwargs, "demo-http-get-origin", days=1)
    client = _client("demo-http-get-origin")

    response = client.get("/demo/session", headers={"origin": "http://evil.example"})

    # GET nunca muta nada: no aplica la misma restricción de Origin que
    # las mutaciones (diseño, sección 6/ADR-0012 hablan de "mutaciones
    # de control"); igual se valida CORS a nivel de cabeceras de
    # respuesta si un navegador la consume, pero la lectura no se rechaza.
    assert response.status_code == 200


def test_backend_url_cannot_be_overridden_from_the_request(
    live_backend, reference_session_kwargs, _client
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-fixed-backend", days=1)
    client = _client("demo-http-fixed-backend")
    order = {
        "session_id": "demo-http-fixed-backend",
        "expected_revision": prepared.manifest.revision,
        "request_id": "req-1",
        "backend_url": "http://attacker.example:9999",  # campo ajeno al contrato
    }

    response = client.post("/demo/session/start", json=order, headers={"origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    manifest = load_manifest(live_backend.sessions_dir, "demo-http-fixed-backend")
    assert manifest.backend_url == reference_session_kwargs["backend_url"]  # sin cambios

    # Se espera a que el worker termine (día único) antes de que el
    # fixture cierre el backend, para no dejar un hilo de fondo corriendo
    # contra un servidor ya apagado.
    for _ in range(200):
        current = load_manifest(live_backend.sessions_dir, "demo-http-fixed-backend")
        if current.status == "completed":
            break
        time.sleep(0.1)


def test_start_launches_worker_and_get_reflects_progress(
    live_backend, reference_session_kwargs, _client
):
    prepared = _prepare(live_backend, reference_session_kwargs, "demo-http-progress", days=1)
    client = _client("demo-http-progress")
    order = {
        "session_id": "demo-http-progress",
        "expected_revision": prepared.manifest.revision,
        "request_id": "req-1",
    }

    response = client.post("/demo/session/start", json=order, headers={"origin": ALLOWED_ORIGIN})
    assert response.status_code == 200
    assert response.json()["status"] in ("running", "completed")

    for _ in range(200):
        current = client.get("/demo/session").json()
        if current["status"] == "completed":
            break
        time.sleep(0.1)
    else:
        pytest.fail("La sesión no completó tras `start` vía HTTP.")

    assert current["cursor"] == 1
    manifest = load_manifest(live_backend.sessions_dir, "demo-http-progress")
    assert manifest.status == "completed"
