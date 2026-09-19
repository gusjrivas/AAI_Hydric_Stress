"""Esquemas OpenAPI de catalogo e historial operacional v2."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CatalogText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]
SensorId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,64}$"),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SectorCreate(StrictModel):
    display_name: CatalogText
    crop: CatalogText | None = None


class SectorPatch(StrictModel):
    expected_revision: int = Field(ge=1)
    display_name: CatalogText | None = None
    crop: CatalogText | None = None
    primary_sensor_id: SensorId | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        changed = self.model_fields_set - {"expected_revision"}
        if not changed:
            raise ValueError("Debe indicar al menos un campo para actualizar.")
        if "display_name" in changed and self.display_name is None:
            raise ValueError("display_name no admite null.")
        return self


class SectorResponse(StrictModel):
    sector_id: str
    display_name: str
    crop: str | None
    primary_sensor_id: str | None
    revision: int
    created_at: datetime


class SectorListResponse(StrictModel):
    items: list[SectorResponse]
    next_cursor: str | None


class SensorCreate(StrictModel):
    sensor_id: SensorId
    display_name: CatalogText
    sector_id: str | None = None
    source_kind: Literal["real", "synthetic", "unknown"]


class SensorPatch(StrictModel):
    expected_revision: int = Field(ge=1)
    display_name: CatalogText | None = None
    sector_id: str | None = None
    source_kind: Literal["real", "synthetic", "unknown"] | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        changed = self.model_fields_set - {"expected_revision"}
        if not changed:
            raise ValueError("Debe indicar al menos un campo para actualizar.")
        if "display_name" in changed and self.display_name is None:
            raise ValueError("display_name no admite null.")
        if "source_kind" in changed and self.source_kind is None:
            raise ValueError("source_kind no admite null.")
        return self


class SensorResponse(StrictModel):
    sensor_id: str
    display_name: str
    sector_id: str | None
    source_kind: Literal["real", "synthetic", "unknown"]
    revision: int
    created_at: datetime | None
    registered: bool


class SensorListResponse(StrictModel):
    items: list[SensorResponse]
    next_cursor: str | None


class ReadingWindow(StrictModel):
    start_date: date
    end_date: date
    expected_days: int


class ReadingRow(StrictModel):
    date: date
    soil_moisture: float | None
    relative_humidity: float | None
    solar_radiation: float | None
    temperature: float | None
    precipitation: float | None
    wind_speed: float | None
    et0: float | None
    origin: Literal["real", "synthetic", "unknown"]
    quality_flags: list[str]


class VariableCoverage(StrictModel):
    variable: str
    observed_days: int
    missing_days: int


class InputRole(StrictModel):
    variable: str
    role: Literal["model_input", "context_only", "unknown"]
    basis: Literal["issued", "configured", "unknown"]
    model_reference: str | None


class ReadingsResponse(StrictModel):
    sensor_id: str
    calendar_timezone: Literal["UTC"]
    server_today: date
    snapshot_id: str | None
    window: ReadingWindow
    status: Literal["ready", "no_readings"]
    rows: list[ReadingRow]
    missing_dates: list[date]
    variable_coverage: list[VariableCoverage]
    units: dict[str, str]
    input_roles: list[InputRole]
    last_reading_date: date | None
    data_age_days: int | None
    provenance: Literal["real", "synthetic", "mixed", "unknown"]


class ErrorBody(StrictModel):
    code: str
    message: str
    details: dict
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorBody
