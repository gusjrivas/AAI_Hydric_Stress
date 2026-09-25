"""Snapshot-to-forecast application service (HU4/HU6); no training by HTTP."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from data_ingestion.history import VARIABLE_UNITS, _origin
from data_ingestion.sensor_naming import dataset_name_for
from data_ingestion.storage import load_dataset_snapshot
from human_feedback.operational_repository import (
    OperationalRepository,
    OperationalRepositoryError,
    SlotSeed,
)
from predictive_modeling.operational_preparation import validate_utc_calendar


def emit_forecasts(
    repository: OperationalRepository,
    *,
    data_dir: Path,
    bundle_root: Path,
    idempotency_key: str,
    now: datetime,
):
    def capture():
        try:
            snapshot = load_dataset_snapshot(
                dataset_name_for(repository.sensor_id), data_dir=data_dir
            )
        except FileNotFoundError:
            return None
        except (OSError, RuntimeError, ValueError) as error:
            raise OperationalRepositoryError(
                "snapshot_unavailable", "No se pudieron capturar las mediciones.", 503
            ) from error
        if snapshot.dataframe.empty:
            return None
        try:
            frame = validate_utc_calendar(snapshot.dataframe)
        except ValueError as error:
            raise OperationalRepositoryError("invalid_calendar", str(error), 409) from error
        as_of = frame.timestamp.max().date()
        if as_of > now.date():
            raise OperationalRepositoryError(
                "future_readings", "Hay mediciones con fecha futura.", 409
            )
        origins = (
            {_origin(value) for value in frame["origen"]} if "origen" in frame else {"unknown"}
        )
        provenance = (
            "unknown"
            if "unknown" in origins
            else (next(iter(origins)) if len(origins) == 1 else "mixed")
        )
        return {
            "frame": frame,
            "batch": {
                "as_of_date": as_of,
                "snapshot_id": snapshot.dataset_sha256,
                "data_age_days": (now.date() - as_of).days,
                "provenance": provenance,
            },
            "artifact": {
                "sha256": snapshot.dataset_sha256,
                "parquet_base64": base64.b64encode(snapshot.content).decode("ascii"),
            },
        }

    def predict(captured, missing):
        # Keep the legacy API importable with its original dependency versions.
        # The stricter operational environment is needed only for explicit v2 inference.
        try:
            from predictive_modeling.ensemble_bundle import (
                EnsembleBundleIncompatible,
                EnsembleComponentMissingError,
                EnsembleManifestInvalidError,
                EnsembleManifestMissingError,
                is_ensemble_configured,
                load_ensemble_bundle,
                predict_ensemble_bundle,
            )
            from predictive_modeling.operational_inference import (
                BundleUnavailable,
                load_operational_bundle,
                predict_operational_bundle,
            )
        except ImportError:
            return [
                SlotSeed(h, "unavailable", reason_code="incompatible_environment")
                for h in (1, 2, 3)
            ]
        ensemble_errors = (
            EnsembleManifestMissingError,
            EnsembleManifestInvalidError,
            EnsembleComponentMissingError,
            EnsembleBundleIncompatible,
        )
        slots = []
        for horizon in (1, 2, 3):
            if horizon not in missing:
                slots.append(SlotSeed(horizon, "unavailable", reason_code="already_available"))
                continue
            horizon_root = bundle_root / repository.sensor_id / f"horizon_{horizon}"
            if is_ensemble_configured(bundle_root, sensor_id=repository.sensor_id, horizon=horizon):
                # Evidence of intent to configure an ensemble (ensemble/ or
                # ensemble_manifest.json exists) — exclusively the ensemble
                # path from here; never retried against the single-model
                # bundle at the same horizon, even if one happens to exist.
                try:
                    ensemble = load_ensemble_bundle(
                        bundle_root, sensor_id=repository.sensor_id, horizon=horizon
                    )
                    captured["artifact"].setdefault("bundles", {})[str(horizon)] = {
                        "mode": "ensemble",
                        "ensemble_manifest": ensemble.manifest,
                        "components": {
                            family: component.metadata
                            for family, component in ensemble.components.items()
                        },
                    }
                    result = predict_ensemble_bundle(
                        ensemble,
                        captured["frame"],
                        sensor_id=repository.sensor_id,
                        units=VARIABLE_UNITS,
                        as_of_date=captured["batch"]["as_of_date"],
                    )
                except ensemble_errors as error:
                    slots.append(
                        SlotSeed(
                            horizon,
                            "unavailable",
                            reason_code=f"{type(error).__name__}:{error}",
                        )
                    )
                    continue
                reference_family = next(iter(sorted(ensemble.components)))
                reference_event = ensemble.components[reference_family].metadata["contract"][
                    "event"
                ]
                slots.append(
                    SlotSeed(
                        horizon_days=result["horizon_days"],
                        status="available",
                        alert=result["combined_alert"],
                        score=result["combined_probability"],
                        score_kind="ensemble_mean_of_calibrated_components",
                        display_probability=None,
                        probability_status="not_qualified",
                        probability_reason_code="incompatible_assessment",
                        decision_threshold=result["decision_threshold"],
                        event_threshold={
                            "variable": reference_event["variable"],
                            "value": reference_event["threshold"],
                            "unit": reference_event["unit"],
                            "comparison": reference_event["comparison"],
                        },
                        model_reference={
                            "model_version": result["ensemble_identity_sha256"],
                            "horizon_days": result["horizon_days"],
                            "contract_version": ensemble.manifest["contract_version"],
                            "trained_through": result["trained_through"],
                            "calibration_version": None,
                            "assessment_reference": None,
                        },
                        ensemble={
                            "policy_version": result["policy_version"],
                            "ensemble_identity_sha256": result["ensemble_identity_sha256"],
                            "components": result["components"],
                            "combined_probability": result["combined_probability"],
                            "combined_alert": result["combined_alert"],
                            "positive_votes": result["positive_votes"],
                            "agreement_category": result["agreement_category"],
                            "calibrated_through": result["calibrated_through"],
                        },
                    )
                )
                continue
            try:
                bundle = load_operational_bundle(
                    horizon_root,
                    sensor_id=repository.sensor_id,
                    horizon=horizon,
                )
                captured["artifact"].setdefault("bundles", {})[str(horizon)] = bundle.metadata
                result = predict_operational_bundle(
                    bundle,
                    captured["frame"],
                    sensor_id=repository.sensor_id,
                    units=VARIABLE_UNITS,
                    as_of_date=captured["batch"]["as_of_date"],
                )
                result.pop("target_date")
                slots.append(SlotSeed(status="available", **result))
            except BundleUnavailable as error:
                slots.append(SlotSeed(horizon, "unavailable", reason_code=error.reason))
        return slots

    return repository.emit_snapshot(
        idempotency_key=idempotency_key, capture=capture, predict=predict, now=now
    )
