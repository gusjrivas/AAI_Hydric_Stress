"""Preparación explícita por CLI de una sesión de demostración (diseño,
sección 2). Escribe directamente el prefijo histórico sintético al
almacenamiento del backend (acceso de escritura explícito de `prepare`,
igual que `scripts/seed_mock_sensor_dataset.py`, ADR-0007) — la
diferencia con el worker (`scripts.demo_simulation.worker`) es que este
último solo escribe vía HTTP.

No sobrescribe recursos existentes: si el dataset, el feedback log o el
directorio de sesión del `sensor_id`/`session_id` resuelto ya existen,
se rechaza sin tocarlos.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from data_ingestion.mock_sensor import generate_next_reading
from data_ingestion.schema import normalize_to_schema
from data_ingestion.sensor_naming import dataset_name_for, feedback_log_name_for
from data_ingestion.storage import DEFAULT_DATA_DIR, save_dataset

from .client import get_active_contract
from .config import DEMO_SENSOR_PREFIX, DemoConfigError, DemoSessionConfig, validate_config
from .manifest import DemoManifest, save_manifest, session_exists
from .payload import reading_to_json

DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parents[2] / "demo_sessions"


class DemoCollisionError(DemoConfigError):
    """El sensor o la sesión resueltos ya tienen recursos existentes."""


@dataclass(frozen=True)
class PrepareResult:
    manifest: DemoManifest
    manifest_path: Path
    history_rows: int


def generate_session_id() -> str:
    """`demo-<id>` con un sufijo aleatorio corto (diseño, sección 2). No
    elegido por quien prepara la demo: garantiza sensor exclusivo por
    construcción, no por convención del usuario.
    """
    return f"{DEMO_SENSOR_PREFIX}{secrets.token_hex(5)}"


def _check_no_collision(session_id: str, sessions_root: Path, data_dir: Path) -> None:
    if session_exists(sessions_root, session_id):
        raise DemoCollisionError(f"Ya existe una sesión de demo '{session_id}'.")
    dataset_path = data_dir / f"{dataset_name_for(session_id)}.parquet"
    if dataset_path.exists():
        raise DemoCollisionError(
            f"Ya existe un dataset para el sensor '{session_id}' ({dataset_path}); "
            "prepare no sobrescribe recursos existentes."
        )
    feedback_path = data_dir / f"{feedback_log_name_for(session_id)}.parquet"
    if feedback_path.exists():
        raise DemoCollisionError(
            f"Ya existe un registro de feedback para el sensor '{session_id}' "
            f"({feedback_path}); prepare no sobrescribe recursos existentes."
        )


def _generate_history(start: date, end: date, seed: int) -> tuple[pd.DataFrame, dict]:
    """Encadena `generate_next_reading` día a día en `[start, end]`
    (ambos incluidos), reusando exactamente la lógica de
    `data_ingestion.mock_sensor.seed_mock_dataset`. Devuelve el
    DataFrame ya normalizado y la última lectura generada (para que el
    worker continúe el random walk sin releerla del dataset).
    """
    dates = pd.date_range(start, end, freq="D")
    rows: list[dict] = []
    previous: pd.Series | None = None
    last_reading: dict = {}
    for offset, timestamp in enumerate(dates):
        reading = generate_next_reading(previous, timestamp, random_state=seed + offset)
        rows.append(reading)
        previous = pd.Series(reading)
        last_reading = reading

    generated = normalize_to_schema(pd.DataFrame(rows), provenance="sintetico")
    return generated, last_reading


def prepare_session(
    config: DemoSessionConfig,
    *,
    today: date,
    sessions_root: Path = DEFAULT_SESSIONS_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    session_id: str | None = None,
) -> PrepareResult:
    """Ejecuta la preparación completa: valida, chequea colisión,
    consulta el contrato operativo, genera el prefijo histórico y
    persiste el manifiesto. Si cualquier paso falla, no queda ningún
    recurso a medio escribir: el dataset se guarda recién al final, y el
    manifiesto se guarda por reemplazo atómico una única vez.
    """
    resolved_id = session_id or generate_session_id()
    config = DemoSessionConfig(
        sensor_id=resolved_id,
        start_date=config.start_date,
        days=config.days,
        history_days=config.history_days,
        seed=config.seed,
        backend_url=config.backend_url,
        interval_seconds=config.interval_seconds,
    )

    _check_no_collision(resolved_id, sessions_root, data_dir)

    contract = get_active_contract(config.backend_url, resolved_id)
    horizon_days = contract["horizon_days"]
    validate_config(config, today=today, horizon_days=horizon_days)

    history_df, last_reading = _generate_history(
        config.history_start, config.history_end, config.seed
    )
    if history_df.empty:
        raise DemoConfigError("El historial generado quedó vacío; revisar --history-days.")

    manifest = DemoManifest(
        session_id=resolved_id,
        sensor_id=resolved_id,
        backend_url=config.backend_url,
        seed=config.seed,
        interval_seconds=config.interval_seconds,
        history_start=config.history_start.isoformat(),
        history_end=config.history_end.isoformat(),
        start_date=config.start_date.isoformat(),
        days=config.days,
        end_date=config.end_date.isoformat(),
        history_rows=len(history_df),
        contract={
            "horizon_days": contract["horizon_days"],
            "contract_version": contract["contract_version"],
            "pipeline_version": contract["pipeline_version"],
        },
        status="prepared",
        cursor=0,
        last_generated_reading=reading_to_json(last_reading),
        next_day_offset=config.history_days,
    )

    # Escritura de datos primero: si falla, el manifiesto (que marca la
    # sesión como preparada) nunca llega a persistirse.
    save_dataset(dataset_name_for(resolved_id), history_df, data_dir=data_dir)
    path = save_manifest(manifest, sessions_root)

    return PrepareResult(manifest=manifest, manifest_path=path, history_rows=len(history_df))
