"""Adaptador HTTP local del controlador de demostración (diseño,
sección 6). Controla una única sesión ya preparada por la CLI de la
entrega 1 (`scripts.demo_simulation.prepare`); no expone una operación
de preparación genérica (ADR-0007, ADR-0012).

Reglas de esta entrega, no negociables:

- `GET /demo/session` nunca crea recursos, nunca inicia el worker,
  nunca avanza la sesión: es puramente de lectura.
- El backend de destino (`backend_url`, ya fijado en el manifiesto por
  `prepare`) no se puede reconfigurar desde una request HTTP.
- El servicio es local: se enlaza a loopback por defecto y valida
  `Origin` contra una única lista configurada por variable de entorno
  del proceso, nunca por parámetro de la request.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .control import ControlOrder, WorkerSupervisor, handle_command, public_view
from .manifest import load_manifest, session_exists
from .recovery import diagnose_and_recover

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8010
DEFAULT_ALLOWED_ORIGIN = "http://localhost:5173"


class ControlOrderBody(BaseModel):
    session_id: str
    expected_revision: int
    request_id: str


def _env_allowed_origins() -> list[str]:
    raw = os.environ.get("DEMO_CONTROL_ALLOWED_ORIGIN", DEFAULT_ALLOWED_ORIGIN)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(
    session_id: str, sessions_root: Path, *, allowed_origins: list[str] | None = None
) -> FastAPI:
    """Construye la app FastAPI del controlador para `session_id`. La
    sesión debe existir ya (preparada por la CLI); este servicio no la
    crea. Al construirse, diagnostica y recupera conservadoramente una
    sesión que haya quedado `running`/`pausing` de un reinicio anterior
    del controlador (diseño, sección 4: "ninguna sesión continúa
    automáticamente").
    """
    if not session_exists(sessions_root, session_id):
        raise FileNotFoundError(
            f"No existe una sesión de demo '{session_id}' preparada en {sessions_root}. "
            "Este servicio no prepara sesiones nuevas: usá "
            "`python -m scripts.demo_simulation prepare` primero."
        )

    manifest = load_manifest(sessions_root, session_id)
    if manifest.status in ("running", "pausing"):
        diagnose_and_recover(manifest, sessions_root)

    origins = allowed_origins if allowed_origins is not None else _env_allowed_origins()
    supervisor = WorkerSupervisor(sessions_root=sessions_root)
    command_lock = supervisor.io_lock  # mismo lock: ver `control.run_controlled_worker`.

    app = FastAPI(title="Controlador local de demostración acelerada (HU6)")
    app.state.session_id = session_id
    app.state.sessions_root = sessions_root
    app.state.allowed_origins = origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.middleware("http")
    async def _validate_origin(request: Request, call_next):
        """Valida `Origin` explícitamente además del CORS estándar
        (diseño, sección 6 y ADR-0012): una request mutante con un
        `Origin` presente y no listado se rechaza, incluso si llega
        fuera del ciclo de preflight que ya cubre `CORSMiddleware`.
        """
        origin = request.headers.get("origin")
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and origin is not None:
            if origin not in origins:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": f"Origin '{origin}' no autorizado para este controlador local."
                    },
                )
        return await call_next(request)

    @app.get("/demo/session")
    def get_session() -> JSONResponse:
        """Puramente de lectura: no crea, no inicia, no avanza nada."""
        try:
            current = load_manifest(sessions_root, session_id)
        except FileNotFoundError:
            return JSONResponse(status_code=404, content={"error": "No hay sesión preparada."})
        return JSONResponse(status_code=200, content=public_view(current))

    def _dispatch(command: str, order_body: ControlOrderBody) -> JSONResponse:
        order = ControlOrder(
            command=command,
            session_id=order_body.session_id,
            expected_revision=order_body.expected_revision,
            request_id=order_body.request_id,
        )
        result = handle_command(
            order,
            sessions_root,
            session_id,
            launch_worker=supervisor.launch,
            command_lock=command_lock,
        )
        return JSONResponse(status_code=result.status_code, content=result.body)

    @app.post("/demo/session/start")
    def start_session(order: ControlOrderBody) -> JSONResponse:
        return _dispatch("start", order)

    @app.post("/demo/session/pause")
    def pause_session(order: ControlOrderBody) -> JSONResponse:
        return _dispatch("pause", order)

    @app.post("/demo/session/resume")
    def resume_session(order: ControlOrderBody) -> JSONResponse:
        return _dispatch("resume", order)

    return app


def serve(
    session_id: str,
    sessions_root: Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    allowed_origins: list[str] | None = None,
) -> None:
    """Arranca el servicio de control (bloqueante). Pensado para
    `python -m scripts.demo_simulation serve`, nunca para el arranque
    normal de la aplicación (perfil Docker `demo`, opt-in explícito).
    """
    import uvicorn

    app = create_app(session_id, sessions_root, allowed_origins=allowed_origins)
    uvicorn.run(app, host=host, port=port, log_level="info")
