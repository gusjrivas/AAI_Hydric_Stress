"""Dependencia compartida de FastAPI para validar `sensor_id` en los
cuatro routers de `alerting-ui` (ADR-0008): un único punto de
validación, reusando `data_ingestion.sensor_naming.validate_sensor_id`.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, HTTPException

from data_ingestion.catalog import CatalogRepository
from data_ingestion.sensor_naming import validate_sensor_id
from human_feedback.operational_repository import OperationalRepository

from .config import get_dataset_data_dir, is_producer_v2_enabled


def get_valid_sensor_id(sensor_id: str) -> str:
    try:
        return validate_sensor_id(sensor_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def get_catalog_repository(
    data_dir: Path = Depends(get_dataset_data_dir),
) -> CatalogRepository:
    """Repositorio operacional aislable mediante dependency_overrides."""
    return CatalogRepository(data_dir)


def get_operational_repository(
    sensor_id: str,
    data_dir: Path = Depends(get_dataset_data_dir),
) -> OperationalRepository:
    """Repositorio v2 de emisiones/revisiones del sensor de la ruta,
    aislable mediante dependency_overrides igual que el resto de v2.
    """
    return OperationalRepository(data_dir, sensor_id)


def require_producer_v2_enabled(
    enabled: bool = Depends(is_producer_v2_enabled),
) -> None:
    if not enabled:
        raise HTTPException(status_code=404, detail="Not Found")


def get_producer_bundle_root(data_dir: Path = Depends(get_dataset_data_dir)) -> Path:
    """Administrator-controlled deployment directory; never a client-supplied path."""
    return Path(os.environ.get("PRODUCER_BUNDLE_ROOT", str(data_dir / "operational_bundles")))
