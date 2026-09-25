"""Operational ensemble of three independently-trained v2 bundles
(logistic_regression, random_forest, hist_gradient_boosting_classifier),
evaluated under an explicit agreement policy (spec
`docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`).

Reuses `load_operational_bundle`/`predict_operational_bundle` unmodified,
once per family. Never renormalizes weights, never falls back to a
single-model bundle when the ensemble is configured but incomplete/invalid,
and never conflates the combined probability with the vote count.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from predictive_modeling.operational_inference import (
    BundleUnavailable,
    OperationalBundle,
    load_operational_bundle,
    predict_operational_bundle,
)

SUPPORTED_FAMILIES: tuple[str, ...] = (
    "logistic_regression",
    "random_forest",
    "hist_gradient_boosting_classifier",
)
SUPPORTED_POLICY_VERSIONS = {"ensemble_agreement_v1"}
_UNIFORM_WEIGHT = 1.0 / 3.0
_WEIGHT_TOLERANCE = 1e-9

_CROSS_CHECK_BUNDLE_FIELDS = (
    "decision_threshold",
    "feature_columns",
    "feature_names",
    "lags",
    "rolling_windows",
)
_CROSS_CHECK_CONTRACT_FIELDS = (
    "sensor_id",
    "horizon_days",
    "contract_version",
    "imputation",
    "variables",
)
_CROSS_CHECK_EVENT_FIELDS = ("variable", "threshold", "unit", "comparison")

AGREEMENT_CATEGORIES: dict[int, str] = {
    3: "alerta_por_unanimidad",
    2: "posible_alerta_acuerdo_parcial",
    1: "sin_alerta_por_mayoria_con_discrepancia",
    0: "sin_alerta_por_unanimidad",
}


class EnsembleManifestMissingError(ValueError):
    """No `ensemble_manifest.json` at the expected path."""


class EnsembleManifestInvalidError(ValueError):
    """`ensemble_manifest.json` exists but fails structural/content validation."""


class EnsembleComponentMissingError(ValueError):
    """A family declared by the manifest has no loadable bundle directory."""


class EnsembleBundleIncompatible(ValueError):
    """Two components disagree on a field that must be identical across the ensemble."""


def _horizon_dir(bundle_root: Path, sensor_id: str, horizon: int) -> Path:
    return Path(bundle_root) / sensor_id / f"horizon_{horizon}"


def is_ensemble_configured(bundle_root: Path, *, sensor_id: str, horizon: int) -> bool:
    """True if there is any evidence of intent to configure an ensemble for
    this sensor/horizon (the `ensemble/` directory or `ensemble_manifest.json`
    exists) — independent of whether that configuration is valid or complete.
    Known limitation: cannot distinguish "never configured" from "both
    signals were removed together"; both look identical (neither present)."""
    horizon_dir = _horizon_dir(bundle_root, sensor_id, horizon)
    return (horizon_dir / "ensemble").exists() or (horizon_dir / "ensemble_manifest.json").exists()


@dataclass(frozen=True)
class EnsembleBundle:
    manifest: dict[str, Any]
    components: dict[str, OperationalBundle]


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _validate_manifest(manifest: Any, *, sensor_id: str, horizon: int) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise EnsembleManifestInvalidError("ensemble_manifest.json debe ser un objeto JSON.")
    if manifest.get("format_version") != 1:
        raise EnsembleManifestInvalidError("format_version debe ser 1.")
    if manifest.get("mode") != "ensemble":
        raise EnsembleManifestInvalidError("mode debe ser 'ensemble'.")
    if manifest.get("sensor_id") != sensor_id or manifest.get("horizon_days") != horizon:
        raise EnsembleManifestInvalidError(
            "sensor_id/horizon_days del manifiesto no coinciden con la ruta solicitada."
        )
    if not isinstance(manifest.get("contract_version"), str) or not manifest["contract_version"]:
        raise EnsembleManifestInvalidError("contract_version debe ser texto no vacío.")
    if manifest.get("policy_version") not in SUPPORTED_POLICY_VERSIONS:
        raise EnsembleManifestInvalidError(
            f"policy_version no soportada: {manifest.get('policy_version')!r}."
        )

    families = manifest.get("families")
    if (
        not isinstance(families, list)
        or len(families) != len(SUPPORTED_FAMILIES)
        or len(set(families)) != len(SUPPORTED_FAMILIES)
        or set(families) != set(SUPPORTED_FAMILIES)
    ):
        raise EnsembleManifestInvalidError(
            f"families debe ser exactamente {SUPPORTED_FAMILIES}, sin duplicados ni extras."
        )

    weights = manifest.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(SUPPORTED_FAMILIES):
        raise EnsembleManifestInvalidError("weights debe declarar exactamente las 3 familias.")
    for family in SUPPORTED_FAMILIES:
        value = weights[family]
        if not _is_finite_number(value) or abs(value - _UNIFORM_WEIGHT) > _WEIGHT_TOLERANCE:
            raise EnsembleManifestInvalidError(
                f"weights[{family!r}] debe ser 1/3 uniforme y finito; obtenido {value!r}."
            )

    return manifest


def load_ensemble_bundle(bundle_root: Path, *, sensor_id: str, horizon: int) -> EnsembleBundle:
    """Only call when `is_ensemble_configured` already returned True. Never
    returns a partial `EnsembleBundle`: either every check passes, or a typed
    exception is raised naming the exact family/field at fault."""
    horizon_dir = _horizon_dir(bundle_root, sensor_id, horizon)
    manifest_path = horizon_dir / "ensemble_manifest.json"
    if not manifest_path.exists():
        raise EnsembleManifestMissingError(
            f"ensemble_manifest.json ausente en {manifest_path} (ensemble/ existe pero sin manifiesto)."
        )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EnsembleManifestInvalidError(f"ensemble_manifest.json ilegible: {error}") from error

    manifest = _validate_manifest(raw, sensor_id=sensor_id, horizon=horizon)

    components: dict[str, OperationalBundle] = {}
    for family in sorted(SUPPORTED_FAMILIES):
        family_dir = horizon_dir / "ensemble" / family
        if not family_dir.exists():
            raise EnsembleComponentMissingError(
                f"ensemble_component_missing:{family}: no existe {family_dir}."
            )
        try:
            components[family] = load_operational_bundle(
                family_dir, sensor_id=sensor_id, horizon=horizon
            )
        except BundleUnavailable as error:
            raise EnsembleComponentMissingError(
                f"ensemble_component_unavailable:{family}:{error.reason}"
            ) from error

    _cross_check_components(components)
    return EnsembleBundle(manifest=manifest, components=components)


def _cross_check_components(components: dict[str, OperationalBundle]) -> None:
    families = sorted(components)
    reference_family = families[0]
    reference = components[reference_family].metadata
    for family in families[1:]:
        candidate = components[family].metadata
        for field in _CROSS_CHECK_BUNDLE_FIELDS:
            if candidate.get(field) != reference.get(field):
                raise EnsembleBundleIncompatible(
                    f"{field}: {reference.get(field)!r} ({reference_family}) != "
                    f"{candidate.get(field)!r} ({family})"
                )
        ref_contract, cand_contract = reference["contract"], candidate["contract"]
        for field in _CROSS_CHECK_CONTRACT_FIELDS:
            if ref_contract.get(field) != cand_contract.get(field):
                raise EnsembleBundleIncompatible(
                    f"contract.{field}: {ref_contract.get(field)!r} ({reference_family}) != "
                    f"{cand_contract.get(field)!r} ({family})"
                )
        ref_event, cand_event = ref_contract["event"], cand_contract["event"]
        for field in _CROSS_CHECK_EVENT_FIELDS:
            if ref_event.get(field) != cand_event.get(field):
                raise EnsembleBundleIncompatible(
                    f"event.{field}: {ref_event.get(field)!r} ({reference_family}) != "
                    f"{cand_event.get(field)!r} ({family})"
                )
        # Same model_identity/calibrator_identity sha256 across two distinct
        # families would mean they are not actually independent artifacts.
        if (
            ref_contract["model_identity"]["sha256"] == cand_contract["model_identity"]["sha256"]
            or ref_contract["calibrator_identity"]["sha256"]
            == cand_contract["calibrator_identity"]["sha256"]
        ):
            raise EnsembleBundleIncompatible(
                f"model_identity/calibrator_identity: {reference_family} y {family} "
                "comparten el mismo hash de artefacto — no son componentes independientes."
            )


def compute_ensemble_identity(manifest: dict[str, Any], components: dict[str, OperationalBundle]) -> str:
    """Deterministic identity: policy + weights + the manifest's own
    relevant fields (contract_version) + each component's model/calibrator/
    contract hashes (which already encode event/preparation, since
    `bundle.json["files"]["contract.json"]` covers the full contract,
    including event and feature preparation). The policy version alone
    never identifies the concrete artifacts used."""
    payload = {
        "policy_version": manifest["policy_version"],
        "contract_version": manifest["contract_version"],
        "weights": {family: manifest["weights"][family] for family in sorted(manifest["weights"])},
        "components": {
            family: {
                "model_sha256": bundle.metadata["files"]["model.joblib"],
                "calibrator_sha256": bundle.metadata["files"]["calibrator.joblib"],
                "contract_sha256": bundle.metadata["files"]["contract.json"],
            }
            for family, bundle in sorted(components.items())
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def predict_ensemble_bundle(
    ensemble: EnsembleBundle,
    dataframe,
    *,
    sensor_id: str,
    units: dict[str, str],
    as_of_date: date,
) -> dict[str, Any]:
    """Predicts each of the 3 components via the real, unmodified
    `predict_operational_bundle` (same causal cutoff and temporal-admissibility
    check as the single-model path), then aggregates. Any `BundleUnavailable`
    from a component propagates with the family preserved in the message —
    the caller (producer_emission.py) is responsible for turning that into a
    per-horizon `unavailable` SlotSeed, never a fallback."""
    per_family: dict[str, dict[str, Any]] = {}
    for family, bundle in sorted(ensemble.components.items()):
        try:
            per_family[family] = predict_operational_bundle(
                bundle, dataframe, sensor_id=sensor_id, units=units, as_of_date=as_of_date
            )
        except BundleUnavailable as error:
            raise EnsembleComponentMissingError(
                f"ensemble_component_unavailable:{family}:{error.reason}"
            ) from error

    decision_thresholds = {r["decision_threshold"] for r in per_family.values()}
    if len(decision_thresholds) != 1:
        raise EnsembleBundleIncompatible(
            f"decision_threshold difiere entre componentes al predecir: {decision_thresholds!r}"
        )
    decision_threshold = decision_thresholds.pop()

    probabilities = [r["score"] for r in per_family.values()]
    if not all(_is_finite_number(p) and 0.0 <= p <= 1.0 for p in probabilities):
        raise EnsembleBundleIncompatible(
            f"una probabilidad de componente no es finita en [0,1]: {probabilities!r}"
        )
    combined_probability = sum(probabilities) / len(probabilities)
    combined_alert = combined_probability >= decision_threshold
    positive_votes = sum(1 for r in per_family.values() if r["alert"])
    agreement_category = AGREEMENT_CATEGORIES[positive_votes]

    trained_through = max(r["model_reference"]["trained_through"] for r in per_family.values())
    calibrated_through = max(
        ensemble.components[family].metadata["contract"]["calibrated_through"]
        for family in per_family
    )
    horizon_days = next(iter(per_family.values()))["horizon_days"]
    target_date = next(iter(per_family.values()))["target_date"]

    components_detail = [
        {
            "family": family,
            "score": result["score"],
            "alert": result["alert"],
            "decision_threshold": result["decision_threshold"],
            "calibrated_through": ensemble.components[family].metadata["contract"][
                "calibrated_through"
            ],
            "model_reference": result["model_reference"],
        }
        for family, result in sorted(per_family.items())
    ]

    return {
        "horizon_days": horizon_days,
        "target_date": target_date,
        "combined_probability": combined_probability,
        "combined_alert": combined_alert,
        "positive_votes": positive_votes,
        "agreement_category": agreement_category,
        "decision_threshold": decision_threshold,
        "trained_through": trained_through,
        "calibrated_through": calibrated_through,
        "ensemble_identity_sha256": compute_ensemble_identity(ensemble.manifest, ensemble.components),
        "policy_version": ensemble.manifest["policy_version"],
        "components": components_detail,
    }
