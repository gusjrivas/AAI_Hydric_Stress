"""Calibration-plan manifest validation without fitting or assessment.

The manifest is deliberately fail-closed: no methodological value is defaulted.
A draft may be inspected while incomplete, but only a complete ``ready_for_fit``
manifest can pass :func:`require_ready_for_fit` or be frozen for later use.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from predictive_modeling.operational_contract import OPERATIONAL_CONTRACT_VERSION
from predictive_modeling.operational_preparation import DateRange

CALIBRATION_MANIFEST_SCHEMA_VERSION = "producer_calibration_plan_v1"
FROZEN_IDENTITY_SCHEMA_VERSION = "producer_calibration_manifest_identity_v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_MULTIPLICITY_DIMENSIONS = {
    "horizon",
    "seed",
    "stability_window",
    "supported_probability_bin",
}


class CalibrationManifestError(ValueError):
    def __init__(self, issues: tuple[str, ...] | list[str]):
        self.issues = tuple(issues)
        super().__init__("Manifiesto no habilitado para ajuste: " + "; ".join(self.issues))


@dataclass(frozen=True)
class ManifestValidationReport:
    declared_status: str | None
    issues: tuple[str, ...]

    @property
    def ready_for_fit(self) -> bool:
        return self.declared_status == "ready_for_fit" and not self.issues


@dataclass(frozen=True)
class FrozenManifestIdentity:
    manifest_path: Path
    identity_path: Path
    sha256: str
    byte_length: int


def _lookup(root: Mapping[str, Any], path: str) -> Any:
    value: Any = root
    for key in path.split("."):
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _required_text(root: Mapping[str, Any], path: str, issues: list[str]) -> str | None:
    value = _lookup(root, path)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{path} debe ser texto no vacío")
        return None
    return value


def _number_in_range(
    root: Mapping[str, Any],
    path: str,
    issues: list[str],
    *,
    minimum: float,
    maximum: float,
    include_minimum: bool = False,
    include_maximum: bool = False,
) -> float | None:
    value = _lookup(root, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        issues.append(f"{path} debe ser numérico")
        return None
    lower_ok = value >= minimum if include_minimum else value > minimum
    upper_ok = value <= maximum if include_maximum else value < maximum
    if not lower_ok or not upper_ok:
        brackets = ("[" if include_minimum else "(") + ("]" if include_maximum else ")")
        issues.append(f"{path} debe pertenecer a {brackets}{minimum}, {maximum}{brackets}")
        return None
    return float(value)


def _positive_integer(root: Mapping[str, Any], path: str, issues: list[str]) -> int | None:
    value = _lookup(root, path)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        issues.append(f"{path} debe ser un entero positivo")
        return None
    return value


def _strict_date(value: Any, path: str, issues: list[str]) -> date | None:
    if not isinstance(value, str):
        issues.append(f"{path} debe ser fecha ISO YYYY-MM-DD")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        issues.append(f"{path} debe ser fecha ISO YYYY-MM-DD")
        return None
    if parsed.isoformat() != value:
        issues.append(f"{path} debe usar formato ISO YYYY-MM-DD")
        return None
    return parsed


def _strict_utc_timestamp(value: Any, path: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        issues.append(f"{path} debe ser timestamp RFC3339 UTC terminado en Z")
        return
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        issues.append(f"{path} debe ser timestamp RFC3339 UTC terminado en Z")
        return
    if parsed.tzinfo != timezone.utc:
        issues.append(f"{path} debe estar expresado en UTC")


def _range_from_manifest(root: Mapping[str, Any], path: str, issues: list[str]) -> DateRange | None:
    start = _strict_date(_lookup(root, f"{path}.start"), f"{path}.start", issues)
    end = _strict_date(_lookup(root, f"{path}.end"), f"{path}.end", issues)
    if start is None or end is None:
        return None
    try:
        return DateRange(start, end)
    except ValueError as exc:
        issues.append(f"{path}: {exc}")
        return None


def inspect_calibration_manifest(manifest: Mapping[str, Any]) -> ManifestValidationReport:
    """Inspect every pre-fit requirement without supplying missing defaults."""

    if not isinstance(manifest, Mapping):
        return ManifestValidationReport(None, ("La raíz del manifiesto debe ser un objeto",))
    issues: list[str] = []
    status = manifest.get("status")
    if status not in {"draft", "ready_for_fit"}:
        issues.append("status debe ser draft o ready_for_fit")
    if manifest.get("schema_version") != CALIBRATION_MANIFEST_SCHEMA_VERSION:
        issues.append("schema_version no soportada")
    if manifest.get("contract_version") != OPERATIONAL_CONTRACT_VERSION:
        issues.append("contract_version no soportada")
    if manifest.get("calendar_timezone") != "UTC":
        issues.append("calendar_timezone debe ser UTC")
    if manifest.get("horizons") != [1, 2, 3]:
        issues.append("horizons debe declarar exactamente [1, 2, 3]")
    if status == "ready_for_fit":
        _strict_utc_timestamp(manifest.get("frozen_at"), "frozen_at", issues)

    for path in (
        "dataset.dataset_id",
        "dataset.site",
        "dataset.sensor_id",
        "dataset.population",
        "dataset.provenance",
        "dataset.prior_exposure",
        "intended_use",
        "event.variable",
        "event.unit",
        "event.comparison",
        "event.threshold_source",
        "model_plan.family",
        "support.justification",
        "tolerances.justification",
        "uncertainty.method",
        "uncertainty.gap_treatment",
        "multiplicity.method",
    ):
        _required_text(manifest, path, issues)

    dataset_sha = _lookup(manifest, "dataset.sha256")
    if not isinstance(dataset_sha, str) or not _SHA256.fullmatch(dataset_sha):
        issues.append("dataset.sha256 debe ser un SHA-256 hexadecimal minúsculo")
    source_kind = _lookup(manifest, "dataset.source_kind")
    if source_kind not in {"real", "synthetic"}:
        issues.append("dataset.source_kind debe ser real o synthetic")
    if source_kind == "synthetic" and _lookup(manifest, "dataset.synthetic_fixture") is not True:
        issues.append("un dataset synthetic debe declarar synthetic_fixture=true")

    percentile = _number_in_range(manifest, "event.percentile", issues, minimum=0, maximum=100)
    if percentile is None:
        pass
    if _lookup(manifest, "event.comparison") != "lt":
        issues.append("event.comparison debe ser lt")
    if _lookup(manifest, "event.threshold_source") != "training_observations_only":
        issues.append("event.threshold_source debe ser training_observations_only")

    allowed = _range_from_manifest(manifest, "dataset.allowed_dates", issues)
    train = _range_from_manifest(manifest, "partitions.train", issues)
    calibration = _range_from_manifest(manifest, "partitions.calibration", issues)
    evaluation = _range_from_manifest(manifest, "partitions.evaluation", issues)
    if all(value is not None for value in (allowed, train, calibration, evaluation)):
        assert allowed is not None and train is not None
        assert calibration is not None and evaluation is not None
        if not (train.end < calibration.start and calibration.end < evaluation.start):
            issues.append("las particiones deben ser cronológicas y no solaparse")
        if any(
            item.start < allowed.start or item.end > allowed.end
            for item in (train, calibration, evaluation)
        ):
            issues.append("las particiones deben quedar dentro de dataset.allowed_dates")
        reference_start = _strict_date(
            _lookup(manifest, "event.threshold_reference.start"),
            "event.threshold_reference.start",
            issues,
        )
        reference_end = _strict_date(
            _lookup(manifest, "event.threshold_reference.end"),
            "event.threshold_reference.end",
            issues,
        )
        if (reference_start, reference_end) != (train.start, train.end):
            issues.append("event.threshold_reference debe coincidir con partitions.train")

    hyperparameters = _lookup(manifest, "model_plan.hyperparameters")
    if not isinstance(hyperparameters, Mapping) or not hyperparameters:
        issues.append("model_plan.hyperparameters debe fijar parámetros efectivos")
    seeds = manifest.get("training_seeds")
    if seeds != [0, 1, 2, 3, 4]:
        issues.append("training_seeds debe conservar la serie predeclarada [0, 1, 2, 3, 4]")
    deployment_seed = manifest.get("deployment_seed")
    if isinstance(deployment_seed, bool) or not isinstance(deployment_seed, int):
        issues.append("deployment_seed debe ser un entero elegido de antemano")
    elif not isinstance(seeds, list) or deployment_seed not in seeds:
        issues.append("deployment_seed debe pertenecer a training_seeds")

    if _lookup(manifest, "calibration.method") != "sigmoid":
        issues.append("calibration.method debe ser sigmoid")
    if _lookup(manifest, "probability_bins.strategy") != "equal_width":
        issues.append("probability_bins.strategy debe ser equal_width")
    if _lookup(manifest, "probability_bins.count") != 10:
        issues.append("probability_bins.count debe ser 10")
    if _lookup(manifest, "probability_bins.include_one_in_last") is not True:
        issues.append("probability_bins.include_one_in_last debe ser true")

    _positive_integer(manifest, "support.minimum_bin_count", issues)
    _positive_integer(manifest, "support.minimum_class_count", issues)
    _positive_integer(manifest, "support.minimum_temporal_blocks", issues)
    _number_in_range(
        manifest, "coverage.minimum", issues, minimum=0, maximum=1, include_maximum=True
    )
    _number_in_range(manifest, "tolerances.epsilon_ece", issues, minimum=0, maximum=1)
    _number_in_range(manifest, "tolerances.epsilon_bin", issues, minimum=0, maximum=1)
    _number_in_range(manifest, "log_loss.clipping_epsilon", issues, minimum=0, maximum=0.5)

    _positive_integer(manifest, "uncertainty.block_length_days", issues)
    _positive_integer(manifest, "uncertainty.replicates", issues)
    if _lookup(manifest, "uncertainty.nominal_level") != 0.95:
        issues.append("uncertainty.nominal_level debe ser 0.95")
    resampling_seed = _lookup(manifest, "uncertainty.resampling_seed")
    if isinstance(resampling_seed, bool) or not isinstance(resampling_seed, int):
        issues.append("uncertainty.resampling_seed debe ser un entero explícito")

    dimensions = _lookup(manifest, "multiplicity.family_dimensions")
    if not isinstance(dimensions, list) or not _REQUIRED_MULTIPLICITY_DIMENSIONS.issubset(
        set(dimensions)
    ):
        issues.append(
            "multiplicity.family_dimensions debe cubrir horizontes, semillas, ventanas y bins"
        )

    windows = manifest.get("stability_windows")
    parsed_windows: list[DateRange] = []
    if not isinstance(windows, list) or not windows:
        issues.append("stability_windows debe contener ventanas predeclaradas")
    else:
        for index, window in enumerate(windows):
            path = f"stability_windows.{index}"
            if not isinstance(window, Mapping):
                issues.append(f"{path} debe ser un objeto")
                continue
            parsed = _range_from_manifest({"window": window}, "window", issues)
            if parsed is not None:
                parsed_windows.append(parsed)
            if window.get("criteria_reference") != "global":
                issues.append(f"{path}.criteria_reference debe ser global")
    if evaluation is not None and parsed_windows:
        ordered = sorted(parsed_windows, key=lambda item: item.start)
        if any(item.start < evaluation.start or item.end > evaluation.end for item in ordered):
            issues.append("stability_windows debe quedar dentro de evaluation")
        if any(left.end >= right.start for left, right in zip(ordered, ordered[1:])):
            issues.append("stability_windows no debe solaparse")

    return ManifestValidationReport(status if isinstance(status, str) else None, tuple(issues))


def require_ready_for_fit(manifest: Mapping[str, Any]) -> None:
    report = inspect_calibration_manifest(manifest)
    issues = list(report.issues)
    if report.declared_status != "ready_for_fit":
        issues.insert(0, "status no es ready_for_fit")
    if issues:
        raise CalibrationManifestError(issues)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"No se sobrescribe el artefacto existente: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as tmp:
        temp_path = Path(tmp.name)
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
    try:
        if path.exists():
            raise FileExistsError(f"No se sobrescribe el artefacto existente: {path}")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def freeze_calibration_manifest(
    manifest: Mapping[str, Any], manifest_path: str | Path
) -> FrozenManifestIdentity:
    """Write canonical content plus a verification identity; it is not a write lock."""

    require_ready_for_fit(manifest)
    path = Path(manifest_path)
    identity_path = path.with_name(path.name + ".identity.json")
    if path.exists() or identity_path.exists():
        raise FileExistsError("No se sobrescribe un manifiesto o identidad ya congelados.")
    content = _canonical_json_bytes(manifest)
    digest = hashlib.sha256(content).hexdigest()
    identity = {
        "schema_version": FROZEN_IDENTITY_SCHEMA_VERSION,
        "algorithm": "sha256",
        "content_sha256": digest,
        "byte_length": len(content),
        "manifest_schema_version": manifest["schema_version"],
        "contract_version": manifest["contract_version"],
    }
    _write_exclusive(path, content)
    _write_exclusive(identity_path, _canonical_json_bytes(identity))
    return FrozenManifestIdentity(path, identity_path, digest, len(content))


def verify_frozen_calibration_manifest(
    manifest_path: str | Path, identity_path: str | Path | None = None
) -> Mapping[str, Any]:
    """Verify current bytes against the separately recorded content identity."""

    path = Path(manifest_path)
    reference_path = (
        Path(identity_path)
        if identity_path is not None
        else path.with_name(path.name + ".identity.json")
    )
    content = path.read_bytes()
    identity = json.loads(reference_path.read_text(encoding="utf-8"))
    if identity.get("schema_version") != FROZEN_IDENTITY_SCHEMA_VERSION:
        raise CalibrationManifestError(["schema_version de identidad no soportada"])
    actual = hashlib.sha256(content).hexdigest()
    if actual != identity.get("content_sha256") or len(content) != identity.get("byte_length"):
        raise CalibrationManifestError(["el contenido ya no coincide con la identidad congelada"])
    try:
        manifest = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CalibrationManifestError(["el manifiesto congelado no es JSON UTF-8 válido"]) from exc
    require_ready_for_fit(manifest)
    return manifest
