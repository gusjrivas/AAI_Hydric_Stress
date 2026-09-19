"""Fachada v2 para catálogo operativo e históricos del productor."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from data_ingestion.catalog import CatalogError, CatalogRepository
from data_ingestion.history import query_readings

from ..dependencies import get_catalog_repository, require_producer_v2_enabled
from ..schemas_v2 import (
    ErrorResponse,
    ReadingsResponse,
    SectorCreate,
    SectorListResponse,
    SectorPatch,
    SectorResponse,
    SensorCreate,
    SensorListResponse,
    SensorPatch,
    SensorResponse,
)

router = APIRouter(
    prefix="/api/v2",
    tags=["producer-v2"],
    dependencies=[Depends(require_producer_v2_enabled)],
)

ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Recurso desconocido"},
    409: {"model": ErrorResponse, "description": "Conflicto de estado o revisión"},
    422: {"model": ErrorResponse, "description": "Solicitud inválida"},
    503: {"model": ErrorResponse, "description": "Almacenamiento no disponible"},
}


def _invalid_cursor() -> CatalogError:
    return CatalogError(
        "invalid_cursor",
        "El cursor no es válido para esta consulta.",
        422,
    )


def _encode_cursor(
    resource: str,
    filters: dict[str, Any],
    cutoff: datetime,
    after: list[str],
) -> str:
    payload = {
        "version": 1,
        "resource": resource,
        "filters": filters,
        "cutoff": cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "after": after,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(serialized).decode().rstrip("=")


def _decode_cursor(
    cursor: str,
    resource: str,
    filters: dict[str, Any],
) -> tuple[datetime, list[str]]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if (
            payload.get("version") != 1
            or payload.get("resource") != resource
            or payload.get("filters") != filters
            or not isinstance(payload.get("after"), list)
            or not all(isinstance(item, str) for item in payload["after"])
            or not isinstance(payload.get("cutoff"), str)
        ):
            raise _invalid_cursor()
        cutoff = datetime.fromisoformat(payload["cutoff"].replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise _invalid_cursor()
        return cutoff.astimezone(timezone.utc), payload["after"]
    except CatalogError:
        raise
    except (
        AttributeError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
        binascii.Error,
    ) as error:
        raise _invalid_cursor() from error


@router.get(
    "/sectors",
    response_model=SectorListResponse,
    responses=ERROR_RESPONSES,
)
def list_sectors(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SectorListResponse:
    filters: dict[str, Any] = {}
    if cursor is None:
        cutoff = datetime.now(timezone.utc)
        after: list[str] = []
    else:
        cutoff, after = _decode_cursor(cursor, "sectors", filters)
        if len(after) != 2:
            raise _invalid_cursor()

    items = repository.list_sectors(created_before=cutoff)
    if after:
        items = [
            item for item in items if (item["created_at"], item["sector_id"]) > (after[0], after[1])
        ]
    page = items[: limit + 1]
    has_more = len(page) > limit
    page = page[:limit]
    next_cursor = None
    if has_more:
        last = page[-1]
        next_cursor = _encode_cursor(
            "sectors",
            filters,
            cutoff,
            [last["created_at"], last["sector_id"]],
        )
    return SectorListResponse(items=page, next_cursor=next_cursor)


@router.post(
    "/sectors",
    response_model=SectorResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_sector(
    payload: SectorCreate,
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SectorResponse:
    return SectorResponse(**repository.create_sector(payload.display_name, payload.crop))


@router.patch(
    "/sectors/{sector_id}",
    response_model=SectorResponse,
    responses=ERROR_RESPONSES,
)
def update_sector(
    sector_id: str,
    payload: SectorPatch,
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SectorResponse:
    changes = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    return SectorResponse(**repository.update_sector(sector_id, payload.expected_revision, changes))


@router.get(
    "/sensors",
    response_model=SensorListResponse,
    responses=ERROR_RESPONSES,
)
def list_sensors(
    sector_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SensorListResponse:
    filters = {"sector_id": sector_id}
    if cursor is None:
        cutoff = datetime.now(timezone.utc)
        after: list[str] = []
    else:
        cutoff, after = _decode_cursor(cursor, "sensors", filters)
        if len(after) != 1:
            raise _invalid_cursor()

    items = repository.list_sensors(sector_id=sector_id, created_before=cutoff)
    if after:
        items = [item for item in items if item["sensor_id"] > after[0]]
    page = items[: limit + 1]
    has_more = len(page) > limit
    page = page[:limit]
    next_cursor = None
    if has_more:
        next_cursor = _encode_cursor(
            "sensors",
            filters,
            cutoff,
            [page[-1]["sensor_id"]],
        )
    return SensorListResponse(items=page, next_cursor=next_cursor)


@router.post(
    "/sensors",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_sensor(
    payload: SensorCreate,
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SensorResponse:
    return SensorResponse(
        **repository.create_sensor(
            payload.sensor_id,
            payload.display_name,
            payload.sector_id,
            payload.source_kind,
        )
    )


@router.patch(
    "/sensors/{sensor_id}",
    response_model=SensorResponse,
    responses=ERROR_RESPONSES,
)
def update_sensor(
    sensor_id: str,
    payload: SensorPatch,
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> SensorResponse:
    changes = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    return SensorResponse(**repository.update_sensor(sensor_id, payload.expected_revision, changes))


@router.get(
    "/sensors/{sensor_id}/readings",
    response_model=ReadingsResponse,
    responses=ERROR_RESPONSES,
)
def get_readings(
    sensor_id: str,
    days: int = Query(default=30, ge=1, le=365),
    end: date | None = Query(default=None),
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> ReadingsResponse:
    result = query_readings(
        sensor_id,
        repository.data_dir,
        registered=repository.is_registered(sensor_id),
        days=days,
        end=end,
    )
    return ReadingsResponse(**result)
