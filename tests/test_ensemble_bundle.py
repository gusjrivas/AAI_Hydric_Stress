import json
from datetime import date

import numpy as np
import pytest

from predictive_modeling import ensemble_bundle as ensemble_bundle_module
from predictive_modeling.ensemble_bundle import (
    SUPPORTED_FAMILIES,
    EnsembleBundleIncompatible,
    EnsembleComponentMissingError,
    EnsembleManifestInvalidError,
    EnsembleManifestMissingError,
    compute_ensemble_identity,
    is_ensemble_configured,
    load_ensemble_bundle,
    predict_ensemble_bundle,
)
from predictive_modeling.operational_inference import BundleUnavailable
from tests.helpers.synthetic_bundles import (
    StubEstimator,
    write_ensemble_manifest,
    write_single_bundle,
)

# --------------------------------------------------------------------------
# is_ensemble_configured
# --------------------------------------------------------------------------


def test_is_ensemble_configured_false_when_neither_signal_present(tmp_path):
    assert not is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)


def test_is_ensemble_configured_true_when_ensemble_dir_exists(tmp_path):
    (tmp_path / "s1" / "horizon_1" / "ensemble").mkdir(parents=True)
    assert is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)


def test_is_ensemble_configured_true_when_only_manifest_file_exists(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    (d / "ensemble_manifest.json").write_text("{}")
    assert is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)


# --------------------------------------------------------------------------
# load_ensemble_bundle -- manifest-level validation
# --------------------------------------------------------------------------


def _write_full_manifest(path, **overrides):
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": "ensemble_agreement_v1",
        "sensor_id": "s1",
        "horizon_days": 1,
        "contract_version": "producer_daily_h123_v1",
        "families": list(SUPPORTED_FAMILIES),
        "weights": {f: 1 / 3 for f in SUPPORTED_FAMILIES},
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest))
    return manifest


def test_load_ensemble_bundle_raises_when_manifest_missing(tmp_path):
    (tmp_path / "s1" / "horizon_1" / "ensemble").mkdir(parents=True)
    with pytest.raises(EnsembleManifestMissingError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_malformed_json(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    (d / "ensemble_manifest.json").write_text("{not valid json")
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_unsupported_policy_version(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_full_manifest(d / "ensemble_manifest.json", policy_version="future_v99")
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_non_uniform_weights(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_full_manifest(
        d / "ensemble_manifest.json",
        weights={
            "logistic_regression": 0.5,
            "random_forest": 0.25,
            "hist_gradient_boosting_classifier": 0.25,
        },
    )
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_wrong_family_set(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_full_manifest(
        d / "ensemble_manifest.json", families=["logistic_regression", "random_forest"]
    )
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_nan_weight(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": "ensemble_agreement_v1",
        "sensor_id": "s1",
        "horizon_days": 1,
        "contract_version": "producer_daily_h123_v1",
        "families": list(SUPPORTED_FAMILIES),
        "weights": {
            "logistic_regression": float("nan"),
            "random_forest": 1 / 3,
            "hist_gradient_boosting_classifier": 1 / 3,
        },
    }
    (d / "ensemble_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_typed_error_on_unhashable_policy_version(tmp_path):
    """policy_version=[] is unhashable -- `... not in SUPPORTED_POLICY_VERSIONS`
    must not raise a bare TypeError; it must be a typed manifest error."""
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_full_manifest(d / "ensemble_manifest.json", policy_version=[])
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_typed_error_on_a_non_string_family(tmp_path):
    """A `families` entry that is an object (unhashable) must not raise a
    bare TypeError from `set(families)`; it must be a typed manifest error."""
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_full_manifest(
        d / "ensemble_manifest.json",
        families=["logistic_regression", {"not": "a string"}, "hist_gradient_boosting_classifier"],
    )
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


# --------------------------------------------------------------------------
# load_ensemble_bundle -- component loading + cross-checks (real fixtures)
# --------------------------------------------------------------------------


def _write_three_components(
    tmp_path,
    *,
    sensor_id="s1",
    horizon=1,
    event=None,
    decision_threshold=0.5,
    bundle_contract_version="producer_daily_h123_v1",
    manifest_contract_version=None,
    duplicate_probabilities: dict[str, float] | None = None,
    lags=None,
    rolling_windows=None,
):
    horizon_dir = tmp_path / sensor_id / f"horizon_{horizon}"
    probabilities = duplicate_probabilities or {}
    for index, family in enumerate(SUPPORTED_FAMILIES):
        # Distinct dummy probability per family so the serialized bytes (and
        # therefore each artifact's sha256 identity) are genuinely distinct —
        # load_ensemble_bundle rejects components that share an artifact hash
        # (never "three renamed copies of the same model"). The actual value
        # is irrelevant for aggregation-math tests, which monkeypatch
        # predict_operational_bundle entirely. `duplicate_probabilities` lets
        # a specific test override this to deliberately create a collision.
        probability = probabilities.get(family, 0.1 * (index + 1))
        model = StubEstimator(
            positive_probability=probability,
            feature_names_in_=np.array(["temperature", "relative_humidity"], dtype=object),
        )
        calibrator = StubEstimator(
            positive_probability=probability,
            feature_names_in_=np.array(["temperature", "relative_humidity"], dtype=object),
        )
        write_single_bundle(
            horizon_dir / "ensemble" / family,
            sensor_id=sensor_id,
            horizon=horizon,
            model=model,
            calibrator=calibrator,
            model_identity_label=f"{family}_model",
            calibrator_identity_label=f"{family}_calibrator",
            event=event,
            decision_threshold=decision_threshold,
            contract_version=bundle_contract_version,
            lags=lags,
            rolling_windows=rolling_windows,
        )
    write_ensemble_manifest(
        horizon_dir,
        sensor_id=sensor_id,
        horizon=horizon,
        contract_version=manifest_contract_version or bundle_contract_version,
    )
    return horizon_dir


def test_load_ensemble_bundle_succeeds_with_three_valid_components(tmp_path):
    _write_three_components(tmp_path)
    ensemble = load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
    assert set(ensemble.components) == set(SUPPORTED_FAMILIES)


def test_load_ensemble_bundle_raises_when_decision_threshold_is_not_half(tmp_path):
    """decision_threshold=0.5 is a requirement of ensemble_agreement_v1
    itself, frozen and never tuned -- not merely a cross-component
    agreement. All 3 components agreeing on 0.6 must still be rejected."""
    _write_three_components(tmp_path, decision_threshold=0.6)
    with pytest.raises(EnsembleBundleIncompatible, match="decision_threshold"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_when_a_component_contract_version_disagrees_with_the_manifest(
    tmp_path,
):
    """The 3 components can agree with *each other* on contract_version
    while all 3 disagree with what ensemble_manifest.json itself declares —
    that must still be rejected, not only pairwise component disagreement."""
    _write_three_components(
        tmp_path,
        bundle_contract_version="producer_daily_h123_v1",
        manifest_contract_version="producer_daily_h123_v2",
    )
    with pytest.raises(EnsembleBundleIncompatible, match="contract_version"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


# --------------------------------------------------------------------------
# compute_ensemble_identity -- covers the effective preparation too, and is
# insensitive to dict/JSON key insertion order
# --------------------------------------------------------------------------


def _load_identity(tmp_path, **kwargs):
    _write_three_components(tmp_path, **kwargs)
    ensemble = load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
    return compute_ensemble_identity(ensemble.manifest, ensemble.components)


def test_ensemble_identity_changes_when_lags_change(tmp_path):
    identity_a = _load_identity(tmp_path / "a", lags=[1])
    identity_b = _load_identity(tmp_path / "b", lags=[1, 2, 3])
    assert identity_a != identity_b


def test_ensemble_identity_changes_when_rolling_windows_change(tmp_path):
    identity_a = _load_identity(tmp_path / "a", rolling_windows=[3])
    identity_b = _load_identity(tmp_path / "b", rolling_windows=[3, 7])
    assert identity_a != identity_b


def test_ensemble_identity_changes_when_decision_threshold_changes(tmp_path):
    # decision_threshold=0.5 is required by ensemble_agreement_v1 (see the
    # cross-check test above), so this exercises identity sensitivity via a
    # direct call to compute_ensemble_identity on a bundle that never goes
    # through the 0.5-enforcing cross-check itself.
    _write_three_components(tmp_path / "a", decision_threshold=0.5)
    _write_three_components(tmp_path / "b", decision_threshold=0.5)
    ensemble_a = load_ensemble_bundle(tmp_path / "a", sensor_id="s1", horizon=1)
    ensemble_b = load_ensemble_bundle(tmp_path / "b", sensor_id="s1", horizon=1)
    identity_a = compute_ensemble_identity(ensemble_a.manifest, ensemble_a.components)
    # Tamper with the loaded (in-memory only) metadata to simulate a
    # different effective decision_threshold without re-triggering the
    # cross-check that would otherwise reject it.
    for bundle in ensemble_b.components.values():
        bundle.metadata["decision_threshold"] = 0.6
    identity_b = compute_ensemble_identity(ensemble_b.manifest, ensemble_b.components)
    assert identity_a != identity_b


def test_ensemble_identity_changes_when_a_component_artifact_changes(tmp_path):
    identity_a = _load_identity(tmp_path / "a")
    identity_b = _load_identity(
        tmp_path / "b", duplicate_probabilities={"logistic_regression": 0.777}
    )
    assert identity_a != identity_b


def test_ensemble_identity_is_unaffected_by_weights_dict_key_insertion_order(tmp_path):
    _write_three_components(tmp_path)
    ensemble = load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
    identity_sorted_keys = compute_ensemble_identity(ensemble.manifest, ensemble.components)

    reordered_manifest = dict(ensemble.manifest)
    reordered_manifest["weights"] = {
        family: ensemble.manifest["weights"][family]
        for family in reversed(sorted(ensemble.manifest["weights"]))
    }
    identity_reordered = compute_ensemble_identity(reordered_manifest, ensemble.components)

    reordered_components = dict(reversed(list(ensemble.components.items())))
    identity_components_reordered = compute_ensemble_identity(
        ensemble.manifest, reordered_components
    )

    assert identity_sorted_keys == identity_reordered == identity_components_reordered


def test_load_ensemble_bundle_raises_on_duplicate_hash_between_second_and_third_family(tmp_path):
    """A byte-identical duplicate between the second and third family
    (alphabetically: logistic_regression, random_forest), while the first
    (hist_gradient_boosting_classifier) is distinct from both, must still be
    caught — checking every candidate only against a fixed reference would
    miss this, since neither duplicate would compare unequal to the
    reference alone."""
    _write_three_components(
        tmp_path,
        duplicate_probabilities={
            "hist_gradient_boosting_classifier": 0.1,
            "logistic_regression": 0.5,
            "random_forest": 0.5,
        },
    )
    with pytest.raises(EnsembleBundleIncompatible, match="logistic_regression y random_forest"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_when_a_family_directory_is_missing(tmp_path):
    horizon_dir = _write_three_components(tmp_path)
    import shutil

    shutil.rmtree(horizon_dir / "ensemble" / "random_forest")
    with pytest.raises(EnsembleComponentMissingError, match="random_forest"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_when_a_component_bundle_is_unavailable(tmp_path):
    horizon_dir = _write_three_components(tmp_path)
    # Corrupt one family's model.joblib so load_operational_bundle itself
    # raises BundleUnavailable -- confirms family+cause propagate.
    (horizon_dir / "ensemble" / "hist_gradient_boosting_classifier" / "model.joblib").write_bytes(
        b"not a real joblib file"
    )
    with pytest.raises(EnsembleComponentMissingError, match="hist_gradient_boosting_classifier"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_event_mismatch_between_components(tmp_path):
    horizon_dir = tmp_path / "s1" / "horizon_1"
    for family, threshold in zip(SUPPORTED_FAMILIES, [0.3, 0.3, 0.28]):
        model = StubEstimator(
            positive_probability=0.6,
            feature_names_in_=np.array(["temperature", "relative_humidity"], dtype=object),
        )
        calibrator = StubEstimator(
            positive_probability=0.6,
            feature_names_in_=np.array(["temperature", "relative_humidity"], dtype=object),
        )
        write_single_bundle(
            horizon_dir / "ensemble" / family,
            sensor_id="s1",
            horizon=1,
            model=model,
            calibrator=calibrator,
            model_identity_label=f"{family}_model",
            calibrator_identity_label=f"{family}_calibrator",
            event={
                "variable": "soil_moisture",
                "threshold": threshold,
                "unit": "m3/m3",
                "comparison": "lt",
            },
        )
    write_ensemble_manifest(horizon_dir, sensor_id="s1", horizon=1)
    with pytest.raises(EnsembleBundleIncompatible, match="event.threshold"):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


# --------------------------------------------------------------------------
# predict_ensemble_bundle -- aggregation math, via a controlled double
# (per spec: doubles are reserved for exact-probability cases)
# --------------------------------------------------------------------------


def _fake_predict_operational_bundle_factory(
    probabilities: dict[str, float], decision_threshold=0.5
):
    def _fake(bundle, dataframe, *, sensor_id, units, as_of_date):
        family = bundle.metadata["_family"]
        p = probabilities[family]
        return {
            "horizon_days": 1,
            "target_date": "2026-06-02",
            "alert": p >= decision_threshold,
            "score": p,
            "score_kind": "calibrated_probability",
            "display_probability": None,
            "probability_status": "not_qualified",
            "probability_reason_code": "incompatible_assessment",
            "decision_threshold": decision_threshold,
            "model_reference": {
                "model_version": f"{family}-model-sha",
                "horizon_days": 1,
                "contract_version": "producer_daily_h123_v1",
                "trained_through": {
                    "logistic_regression": "2024-03-01",
                    "random_forest": "2024-03-15",
                    "hist_gradient_boosting_classifier": "2024-03-31",
                }[family],
                "calibration_version": f"{family}-calibrator-sha",
                "assessment_reference": None,
            },
        }

    return _fake


def _build_ensemble_with_probabilities(tmp_path, probabilities: dict[str, float]):
    _write_three_components(tmp_path)
    ensemble = load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
    # Tag each component's metadata (in-memory only) so the fake predictor
    # knows which family it's "predicting" for.
    for family, bundle in ensemble.components.items():
        bundle.metadata["_family"] = family
    return ensemble


def test_discrepancy_case_majority_says_possible_alert_but_average_says_no(tmp_path, monkeypatch):
    probabilities = {
        "logistic_regression": 0.51,
        "random_forest": 0.51,
        "hist_gradient_boosting_classifier": 0.01,
    }
    ensemble = _build_ensemble_with_probabilities(tmp_path, probabilities)
    monkeypatch.setattr(
        ensemble_bundle_module,
        "predict_operational_bundle",
        _fake_predict_operational_bundle_factory(probabilities),
    )

    result = predict_ensemble_bundle(
        ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1)
    )

    assert result["positive_votes"] == 2
    assert result["agreement_category"] == "posible_alerta_acuerdo_parcial"
    assert abs(result["combined_probability"] - 0.34333333333333327) < 1e-9
    assert result["combined_alert"] is False


def test_discrepancy_case_minority_says_alert_but_average_agrees(tmp_path, monkeypatch):
    probabilities = {
        "logistic_regression": 0.99,
        "random_forest": 0.49,
        "hist_gradient_boosting_classifier": 0.49,
    }
    ensemble = _build_ensemble_with_probabilities(tmp_path, probabilities)
    monkeypatch.setattr(
        ensemble_bundle_module,
        "predict_operational_bundle",
        _fake_predict_operational_bundle_factory(probabilities),
    )

    result = predict_ensemble_bundle(
        ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1)
    )

    assert result["positive_votes"] == 1
    assert result["agreement_category"] == "sin_alerta_por_mayoria_con_discrepancia"
    assert abs(result["combined_probability"] - 0.6566666666666667) < 1e-9
    assert result["combined_alert"] is True
    # trained_through aggregate must be the MAXIMUM, not the minimum
    assert result["trained_through"] == "2024-03-31"


@pytest.mark.parametrize(
    "probabilities,expected_votes,expected_category",
    [
        (
            {
                "logistic_regression": 0.9,
                "random_forest": 0.9,
                "hist_gradient_boosting_classifier": 0.9,
            },
            3,
            "alerta_por_unanimidad",
        ),
        (
            {
                "logistic_regression": 0.9,
                "random_forest": 0.9,
                "hist_gradient_boosting_classifier": 0.1,
            },
            2,
            "posible_alerta_acuerdo_parcial",
        ),
        (
            {
                "logistic_regression": 0.9,
                "random_forest": 0.1,
                "hist_gradient_boosting_classifier": 0.1,
            },
            1,
            "sin_alerta_por_mayoria_con_discrepancia",
        ),
        (
            {
                "logistic_regression": 0.1,
                "random_forest": 0.1,
                "hist_gradient_boosting_classifier": 0.1,
            },
            0,
            "sin_alerta_por_unanimidad",
        ),
    ],
)
def test_four_vote_combinations(
    tmp_path, monkeypatch, probabilities, expected_votes, expected_category
):
    ensemble = _build_ensemble_with_probabilities(tmp_path, probabilities)
    monkeypatch.setattr(
        ensemble_bundle_module,
        "predict_operational_bundle",
        _fake_predict_operational_bundle_factory(probabilities),
    )

    result = predict_ensemble_bundle(
        ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1)
    )

    assert result["positive_votes"] == expected_votes
    assert result["agreement_category"] == expected_category


def test_boundary_at_exactly_the_threshold_for_one_component_and_the_average(tmp_path, monkeypatch):
    probabilities = {
        "logistic_regression": 0.5,
        "random_forest": 0.5,
        "hist_gradient_boosting_classifier": 0.5,
    }
    ensemble = _build_ensemble_with_probabilities(tmp_path, probabilities)
    monkeypatch.setattr(
        ensemble_bundle_module,
        "predict_operational_bundle",
        _fake_predict_operational_bundle_factory(probabilities),
    )

    result = predict_ensemble_bundle(
        ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1)
    )

    assert result["positive_votes"] == 3  # >= comparator: 0.5 >= 0.5 is True
    assert result["combined_probability"] == 0.5
    assert result["combined_alert"] is True


def test_component_bundle_unavailable_at_predict_time_preserves_family_and_cause(
    tmp_path, monkeypatch
):
    ensemble = _build_ensemble_with_probabilities(
        tmp_path,
        {
            "logistic_regression": 0.6,
            "random_forest": 0.6,
            "hist_gradient_boosting_classifier": 0.6,
        },
    )

    def _raising_fake(bundle, dataframe, *, sensor_id, units, as_of_date):
        if bundle.metadata["_family"] == "random_forest":
            raise BundleUnavailable("model_not_available_at_date")
        return _fake_predict_operational_bundle_factory(
            {
                "logistic_regression": 0.6,
                "random_forest": 0.6,
                "hist_gradient_boosting_classifier": 0.6,
            }
        )(bundle, dataframe, sensor_id=sensor_id, units=units, as_of_date=as_of_date)

    monkeypatch.setattr(ensemble_bundle_module, "predict_operational_bundle", _raising_fake)

    with pytest.raises(
        EnsembleComponentMissingError, match="random_forest.*model_not_available_at_date"
    ):
        predict_ensemble_bundle(
            ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1)
        )
