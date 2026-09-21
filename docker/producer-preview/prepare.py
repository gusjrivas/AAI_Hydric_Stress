"""Seed only the isolated producer preview volume with synthetic fixtures.

This is a local usability environment, not a real calibration/evaluation run.
Never reads the project's historical dataset or frozen operational manifest.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from architecture_integration.producer_emission import emit_forecasts
from data_ingestion.catalog import CatalogRepository
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import atomic_write_bytes, load_dataset_snapshot, save_dataset
from human_feedback.operational_repository import OperationalRepository
from predictive_modeling.calibration_manifest import freeze_calibration_manifest
from predictive_modeling.operational_run import run_operational_manifest
from predictive_modeling.operational_run_artifacts import persist_operational_run
from tests.test_operational_run import _synthetic_frame, _synthetic_ready_manifest

DATA = Path("/workspace/data")
MARKER = DATA / "producer-preview-ready.json"
BUNDLES = DATA / "operational_bundles"


def shift_range(value: dict, offset: timedelta) -> None:
    for key in ("start", "end"):
        value[key] = (date.fromisoformat(value[key]) + offset).isoformat()


def prepare() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if MARKER.exists():
        print("La prueba ya está preparada. Se conservan mediciones y opiniones.", flush=True)
        return
    # Never silently overwrite a partial run or an unrelated populated volume.
    if any(DATA.iterdir()):
        raise RuntimeError(
            "Volumen no vacío sin marcador. Revisar la preparación; no se sobrescribe."
        )
    now = datetime.now(timezone.utc)
    today = now.date()
    offset = today - date(2024, 8, 27)
    catalog = CatalogRepository(DATA)
    for number, (sensor, name, crop) in enumerate(
        [
            ("prueba-norte", "Huerta norte", "Tomate"),
            ("prueba-sur", "Huerta sur", "Lechuga"),
        ]
    ):
        print(f"Preparando {name}: mediciones y modelos sintéticos…", flush=True)
        sector = catalog.create_sector(name, crop)
        catalog.create_sensor(
            sensor, "Punto de medición simulado", sector["sector_id"], "synthetic"
        )
        catalog.update_sector(sector["sector_id"], 1, {"primary_sensor_id": sensor})
        frame = _synthetic_frame()
        frame["timestamp"] += pd.Timedelta(days=offset.days)
        frame["temperature"] += number * 2
        frame["origen"] = "sintetico"
        # Visible, explicit historical missing measurement; current inference stays usable.
        frame.loc[frame.index[-15], "temperature"] = float("nan")
        dataset = dataset_name_for(sensor)
        save_dataset(dataset, frame, data_dir=DATA)
        snapshot = load_dataset_snapshot(dataset, data_dir=DATA)
        manifest = _synthetic_ready_manifest(snapshot.dataset_sha256)
        manifest["dataset"].update(sensor_id=sensor, dataset_id=dataset)
        shift_range(manifest["dataset"]["allowed_dates"], offset)
        shift_range(manifest["event"]["threshold_reference"], offset)
        for period in manifest["partitions"].values():
            shift_range(period, offset)
        for period in manifest["stability_windows"]:
            shift_range(period, offset)
        manifest["frozen_at"] = now.isoformat().replace("+00:00", "Z")
        manifest_dir = DATA / "preview_manifests"
        manifest_dir.mkdir(exist_ok=True)
        manifest_path = manifest_dir / f"{sensor}.json"
        identity = freeze_calibration_manifest(manifest, manifest_path)
        result = run_operational_manifest(
            manifest, snapshot.dataframe, dataset_sha256=snapshot.dataset_sha256
        )
        persist_operational_run(
            result,
            output_dir=BUNDLES / sensor,
            run_id=f"preview-{sensor}-{today}",
            manifest_path=manifest_path,
            manifest_identity_sha256=identity.sha256,
            dataset_id=dataset,
            repo_root=Path("/workspace"),
        )
        repository = OperationalRepository(DATA, sensor)
        # Generate past-dated results with an earlier input snapshot, without fitting again.
        # Their target dates are already reviewable; opinions remain pending for the user.
        past = frame.loc[frame.timestamp.dt.date <= today - timedelta(days=3)]
        save_dataset(dataset, past, data_dir=DATA)
        emit_forecasts(
            repository, data_dir=DATA, bundle_root=BUNDLES, idempotency_key="preview-past", now=now
        )
        save_dataset(dataset, frame, data_dir=DATA)
        _, current = emit_forecasts(
            repository,
            data_dir=DATA,
            bundle_root=BUNDLES,
            idempotency_key="preview-current",
            now=now,
        )
        if not all(slot["status"] == "available" for slot in current["slots"]):
            raise RuntimeError(
                f"El entorno no pudo preparar los tres horizontes de {sensor}: {current}"
            )
    catalog.create_sensor(
        "prueba-sin-datos", "Punto todavía sin mediciones", sector["sector_id"], "synthetic"
    )
    atomic_write_bytes(
        MARKER,
        json.dumps(
            {
                "format_version": 1,
                "created_at": now.isoformat(),
                "source_kind": "synthetic",
                "purpose": "local UI preview; no calibration claim",
            },
            indent=2,
        ).encode(),
    )
    print(
        "Prueba lista: dos sectores, tres días futuros y pendientes.",
        flush=True,
    )


if __name__ == "__main__":
    prepare()
