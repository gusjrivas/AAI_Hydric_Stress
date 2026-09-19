"""Catalogo operacional de sectores y sensores, separado de las series."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from data_ingestion.sensor_naming import dataset_name_for, validate_sensor_id
from data_ingestion.storage import atomic_write_bytes, interprocess_lock

CATALOG_FORMAT_VERSION = 1
METADATA_DIRECTORY = "ui_metadata"
CATALOG_FILENAME = "catalog.v1.json"
SOURCE_KINDS = {"real", "synthetic", "unknown"}


class CatalogError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: str | None, field: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if value is None:
        raise CatalogError("invalid_catalog_value", f"{field} es obligatorio.", 422)
    cleaned = value.strip()
    if not 1 <= len(cleaned) <= 80:
        raise CatalogError(
            "invalid_catalog_value",
            f"{field} debe contener entre 1 y 80 caracteres luego de trim.",
            422,
            {"field": field},
        )
    return cleaned


def _validated_sensor_id(sensor_id: str) -> str:
    try:
        return validate_sensor_id(sensor_id)
    except ValueError as error:
        raise CatalogError(
            "invalid_sensor_id",
            str(error),
            422,
            {"field": "sensor_id"},
        ) from error


class CatalogRepository:
    """Repositorio JSON versionado con revision optimista y lock entre procesos."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.metadata_dir = self.data_dir / METADATA_DIRECTORY
        self.path = self.metadata_dir / CATALOG_FILENAME
        self.lock_path = self.metadata_dir / ".catalog.lock"

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"format_version": CATALOG_FORMAT_VERSION, "sectors": {}, "sensors": {}}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CatalogError(
                "catalog_storage_unavailable", "No se pudo leer el catalogo.", 503
            ) from error
        if document.get("format_version") != CATALOG_FORMAT_VERSION:
            raise CatalogError(
                "unsupported_catalog_version",
                "La version persistida del catalogo no es compatible.",
                503,
                {"format_version": document.get("format_version")},
            )
        if not isinstance(document.get("sectors"), dict) or not isinstance(
            document.get("sensors"), dict
        ):
            raise CatalogError("invalid_catalog", "El catalogo persistido es invalido.", 503)
        return document

    def _write(self, document: dict[str, Any]) -> None:
        content = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        try:
            atomic_write_bytes(self.path, content)
        except OSError as error:
            raise CatalogError(
                "catalog_storage_unavailable", "No se pudo persistir el catalogo.", 503
            ) from error

    @contextmanager
    def _locked_document(self) -> Iterator[dict[str, Any]]:
        try:
            with interprocess_lock(self.lock_path):
                yield self._read()
        except CatalogError:
            raise
        except OSError as error:
            raise CatalogError(
                "catalog_storage_unavailable",
                "No se pudo bloquear el catalogo.",
                503,
            ) from error

    def snapshot(self) -> dict[str, Any]:
        return self._read()

    def create_sector(self, display_name: str, crop: str | None) -> dict[str, Any]:
        display_name = _clean_text(display_name, "display_name")
        crop = _clean_text(crop, "crop", optional=True)
        with self._locked_document() as document:
            sector_id = f"sec_{uuid4().hex}"
            item = {
                "sector_id": sector_id,
                "display_name": display_name,
                "crop": crop,
                "primary_sensor_id": None,
                "revision": 1,
                "created_at": _now(),
            }
            document["sectors"][sector_id] = item
            self._write(document)
            return item.copy()

    def create_sensor(
        self, sensor_id: str, display_name: str, sector_id: str | None, source_kind: str
    ) -> dict[str, Any]:
        sensor_id = _validated_sensor_id(sensor_id)
        display_name = _clean_text(display_name, "display_name")
        if source_kind not in SOURCE_KINDS:
            raise CatalogError("invalid_catalog_value", "source_kind invalido.", 422)
        with self._locked_document() as document:
            if sensor_id in document["sensors"]:
                raise CatalogError("sensor_already_exists", "El sensor ya esta registrado.", 409)
            if sector_id is not None and sector_id not in document["sectors"]:
                raise CatalogError("sector_not_found", "El sector no existe.", 404)
            item = {
                "sensor_id": sensor_id,
                "display_name": display_name,
                "sector_id": sector_id,
                "source_kind": source_kind,
                "revision": 1,
                "created_at": _now(),
                "registered": True,
            }
            document["sensors"][sensor_id] = item
            self._write(document)
            return item.copy()

    def update_sector(
        self, sector_id: str, expected_revision: int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        with self._locked_document() as document:
            item = document["sectors"].get(sector_id)
            if item is None:
                raise CatalogError("sector_not_found", "El sector no existe.", 404)
            self._check_revision(item, expected_revision)
            if "display_name" in changes:
                item["display_name"] = _clean_text(changes["display_name"], "display_name")
            if "crop" in changes:
                item["crop"] = _clean_text(changes["crop"], "crop", optional=True)
            if "primary_sensor_id" in changes:
                primary = changes["primary_sensor_id"]
                if primary is not None:
                    sensor = document["sensors"].get(primary)
                    if sensor is None:
                        raise CatalogError("sensor_not_found", "El sensor primario no existe.", 404)
                    if sensor["sector_id"] != sector_id:
                        raise CatalogError(
                            "sensor_sector_mismatch",
                            "El sensor primario no pertenece al sector.",
                            409,
                        )
                item["primary_sensor_id"] = primary
            item["revision"] += 1
            self._write(document)
            return item.copy()

    def update_sensor(
        self, sensor_id: str, expected_revision: int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        sensor_id = _validated_sensor_id(sensor_id)
        with self._locked_document() as document:
            item = document["sensors"].get(sensor_id)
            if item is None:
                raise CatalogError("sensor_not_found", "El sensor no esta registrado.", 404)
            self._check_revision(item, expected_revision)
            if "display_name" in changes:
                item["display_name"] = _clean_text(changes["display_name"], "display_name")
            if "source_kind" in changes:
                source_kind = changes["source_kind"]
                if source_kind not in SOURCE_KINDS:
                    raise CatalogError("invalid_catalog_value", "source_kind invalido.", 422)
                item["source_kind"] = source_kind
            if "sector_id" in changes:
                self._change_sensor_sector(document, item, changes["sector_id"])
            item["revision"] += 1
            self._write(document)
            return item.copy()

    def _change_sensor_sector(
        self, document: dict[str, Any], item: dict[str, Any], new_sector_id: str | None
    ) -> None:
        old_sector_id = item["sector_id"]
        if new_sector_id == old_sector_id:
            return
        if new_sector_id is not None and new_sector_id not in document["sectors"]:
            raise CatalogError("sector_not_found", "El sector no existe.", 404)
        if old_sector_id is not None:
            old_sector = document["sectors"][old_sector_id]
            if old_sector["primary_sensor_id"] == item["sensor_id"]:
                raise CatalogError(
                    "primary_sensor_reassignment",
                    "Desasigne el sensor primario antes de moverlo.",
                    409,
                )
        if self._has_operational_history(item["sensor_id"]):
            raise CatalogError(
                "sensor_reassignment_conflict",
                "No se puede reasignar un sensor con lecturas o emisiones.",
                409,
            )
        item["sector_id"] = new_sector_id

    def _has_operational_history(self, sensor_id: str) -> bool:
        for name in (dataset_name_for(sensor_id), f"feedback__{sensor_id}"):
            path = self.data_dir / f"{name}.parquet"
            if not path.exists():
                continue
            try:
                if len(pd.read_parquet(path)) > 0:
                    return True
            except Exception as error:
                raise CatalogError(
                    "catalog_storage_unavailable",
                    "No se pudo verificar el historial del sensor.",
                    503,
                ) from error
        return False

    @staticmethod
    def _check_revision(item: dict[str, Any], expected_revision: int) -> None:
        if item["revision"] != expected_revision:
            raise CatalogError(
                "revision_conflict",
                "La revision esperada no coincide con la revision actual.",
                409,
                {"expected_revision": expected_revision, "actual_revision": item["revision"]},
            )

    def list_sectors(self, created_before: datetime | None = None) -> list[dict[str, Any]]:
        items = (item.copy() for item in self._read()["sectors"].values())
        if created_before is not None:
            cutoff = created_before.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            items = (item for item in items if item["created_at"] <= cutoff)
        return sorted(
            items,
            key=lambda item: (item["created_at"], item["sector_id"]),
        )

    def list_sensors(
        self,
        sector_id: str | None = None,
        created_before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        document = self._read()
        cutoff = None
        if created_before is not None:
            cutoff = created_before.astimezone(timezone.utc)
        registered = {
            key: value.copy()
            for key, value in document["sensors"].items()
            if cutoff is None
            or datetime.fromisoformat(value["created_at"].replace("Z", "+00:00")) <= cutoff
        }
        items = list(registered.values()) + self._discover_legacy(set(registered), cutoff)
        if sector_id is not None:
            items = [item for item in items if item["sector_id"] == sector_id]
        return sorted(items, key=lambda item: (item["sensor_id"], not item["registered"]))

    def _discover_legacy(
        self,
        registered_ids: set[str],
        created_before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        items = []
        try:
            paths = self.data_dir.glob("sensor__*.parquet")
            for path in paths:
                if created_before is not None:
                    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                    if modified_at > created_before:
                        continue
                sensor_id = path.stem.removeprefix("sensor__")
                try:
                    validate_sensor_id(sensor_id)
                except ValueError:
                    continue
                if sensor_id not in registered_ids:
                    items.append(
                        {
                            "sensor_id": sensor_id,
                            "display_name": sensor_id,
                            "sector_id": None,
                            "source_kind": "unknown",
                            "revision": 0,
                            "created_at": None,
                            "registered": False,
                        }
                    )
        except OSError as error:
            raise CatalogError(
                "catalog_storage_unavailable",
                "No se pudieron descubrir las series existentes.",
                503,
            ) from error
        return items

    def is_registered(self, sensor_id: str) -> bool:
        sensor_id = _validated_sensor_id(sensor_id)
        return sensor_id in self._read()["sensors"]

    def sensor_exists(self, sensor_id: str) -> bool:
        sensor_id = _validated_sensor_id(sensor_id)
        if sensor_id in self._read()["sensors"]:
            return True
        return (self.data_dir / f"{dataset_name_for(sensor_id)}.parquet").exists()
