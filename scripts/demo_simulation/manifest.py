"""Manifiesto persistido de una sesión de demostración (diseño, sección
4). Se guarda por reemplazo atómico (`os.replace`, atómico dentro del
mismo sistema de archivos) para que un corte de proceso a mitad de
escritura nunca deje un manifiesto truncado o mezclado con el anterior.

Los estados de sesión de esta entrega incluyen `pausing`/`paused`
(diseño, sección 4): el worker de ejecución directa por CLI
(`scripts.demo_simulation.worker.run_session`) nunca los produce por sí
mismo, pero sí debe reconocerlos (una sesión pausada por el adaptador
HTTP no reinicia sola desde la CLI). `command_log` registra, por
`request_id`, el resultado ya emitido de cada orden de control HTTP
aceptada o rechazada (deduplicación, diseño sección 6); el worker de
ejecución directa no lo usa.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

SessionStatus = Literal["prepared", "running", "pausing", "paused", "blocked", "completed"]
StepPhase = Literal["pending", "ingest_pending", "ingested", "forecast_pending", "completed"]

GENERATOR_VERSION = "demo_simulation.mock_sensor_chain@v1"


@dataclass
class StepRecord:
    date: str  # ISO, día calendario reproducido (no timestamp subdiario)
    phase: StepPhase = "pending"
    payload: dict[str, Any] | None = None
    payload_hash: str | None = None
    ingest_response: dict[str, Any] | None = None
    dataset_check: dict[str, Any] | None = None
    forecast_verdict: dict[str, Any] | None = None
    feedback_confirmation: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class DemoManifest:
    session_id: str
    sensor_id: str
    backend_url: str
    seed: int
    interval_seconds: int
    history_start: str
    history_end: str
    start_date: str
    days: int
    end_date: str
    history_rows: int
    contract: dict[str, Any]
    generator_version: str = GENERATOR_VERSION
    status: SessionStatus = "prepared"
    cursor: int = 0
    last_generated_reading: dict[str, Any] | None = None
    next_day_offset: int = 0
    steps: dict[str, StepRecord] = field(default_factory=dict)
    last_error: str | None = None
    revision: int = 0
    command_log: dict[str, dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["steps"] = {k: asdict(v) for k, v in self.steps.items()}
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DemoManifest:
        data = dict(data)
        steps_raw = data.pop("steps", {})
        manifest = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        manifest.steps = {k: StepRecord(**v) for k, v in steps_raw.items()}
        return manifest


def session_dir(sessions_root: Path, session_id: str) -> Path:
    return sessions_root / session_id


def manifest_path(sessions_root: Path, session_id: str) -> Path:
    return session_dir(sessions_root, session_id) / "manifest.json"


def save_manifest(manifest: DemoManifest, sessions_root: Path) -> Path:
    """Persiste `manifest` por reemplazo atómico. Incrementa `revision`
    y `updated_at` en cada guardado, para que dos lecturas del archivo
    puedan detectar si cambió entre medio (control futuro, entrega 2).
    """
    manifest.revision += 1
    manifest.updated_at = datetime.now(timezone.utc).isoformat()
    path = manifest_path(sessions_root, manifest.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # El sufijo incluye PID, hilo y un token único: en la entrega 2 el
    # worker de fondo y el hilo que atiende una orden HTTP pueden
    # guardar manifiestos de la misma sesión desde el mismo proceso, y
    # un nombre temporal compartido colisiona (falla `os.replace` o,
    # en Windows, incluso la escritura previa por archivo en uso).
    tmp_path = path.with_name(
        path.name + f".tmp-{os.getpid()}-{threading.get_ident()}-{uuid.uuid4().hex}"
    )
    tmp_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    # En Windows, `os.replace` puede fallar transitoriamente con
    # `PermissionError` si otro hilo tiene el destino abierto para lectura
    # en ese instante exacto (ver `load_manifest`); se reintenta unas
    # pocas veces antes de propagar cualquier otro error.
    last_error: PermissionError | None = None
    for attempt in range(10):
        try:
            os.replace(tmp_path, path)
            return path
        except PermissionError as error:
            last_error = error
            time.sleep(0.01 * (attempt + 1))
    raise last_error  # pragma: no cover - solo si la colisión persiste 10 intentos


def load_manifest(sessions_root: Path, session_id: str) -> DemoManifest:
    """Lee el manifiesto persistido. En la entrega 2, un hilo de control
    (orden HTTP) y el worker de fondo pueden leer y reemplazar el mismo
    archivo casi al mismo tiempo; en Windows, `os.replace` puede colisionar
    transitoriamente con una lectura concurrente y levantar
    `PermissionError` aunque el archivo exista y el contenido sea válido
    (nunca ocurre por un manifiesto realmente ausente o corrupto). Se
    reintenta la lectura unas pocas veces antes de propagar cualquier otro
    error.
    """
    path = manifest_path(sessions_root, session_id)
    if not path.exists():
        raise FileNotFoundError(f"No existe una sesión de demo '{session_id}' en {sessions_root}")
    last_error: PermissionError | None = None
    for attempt in range(10):
        try:
            return DemoManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except PermissionError as error:
            last_error = error
            time.sleep(0.01 * (attempt + 1))
    raise last_error  # pragma: no cover - solo si la colisión persiste 10 intentos


def session_exists(sessions_root: Path, session_id: str) -> bool:
    return manifest_path(sessions_root, session_id).exists()


def parse_date(value: str) -> date:
    return date.fromisoformat(value)
