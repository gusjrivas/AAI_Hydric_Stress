from dataclasses import replace
from datetime import date

import pytest

from predictive_modeling.operational_contract import (
    ArtifactIdentity,
    HorizonContract,
    HorizonContractMismatch,
    VariableMetadata,
    validate_horizon_contract_family,
)
from predictive_modeling.operational_preparation import DateRange, TemporalCutPlan


def _cuts():
    return TemporalCutPlan(
        allowed_data=DateRange("2024-01-01", "2024-12-31"),
        train=DateRange("2024-01-01", "2024-06-30"),
        calibration=DateRange("2024-07-01", "2024-09-30"),
        evaluation=DateRange("2024-10-01", "2024-12-30"),
        inference_as_of="2024-12-31",
    )


def _plan(horizon):
    return HorizonContract(
        horizon_days=horizon,
        sensor_id="synthetic-sensor",
        data_snapshot_sha256="f" * 64,
        imputation="forward_fill_inputs_only",
        variables=(
            VariableMetadata("soil_moisture", "m3/m3"),
            VariableMetadata("temperature", "degC"),
        ),
        event_variable="soil_moisture",
        event_threshold=0.25,
        event_unit="m3/m3",
        temporal_cuts=_cuts(),
    )


def test_unfitted_plans_form_a_compatible_three_horizon_family():
    contracts = tuple(_plan(horizon) for horizon in (1, 2, 3))

    validate_horizon_contract_family(contracts)

    assert all(contract.artifact_state == "plan" for contract in contracts)
    assert all(contract.model_identity is None for contract in contracts)


def test_plan_cannot_claim_model_or_calibrator_identity():
    identity = ArtifactIdentity("synthetic-model", "1" * 64, 1)

    with pytest.raises(ValueError, match="plan no ajustado"):
        replace(_plan(1), model_identity=identity)


def test_trained_bundle_requires_real_identity_metadata_but_calibrator_is_optional():
    model_identity = ArtifactIdentity("synthetic-model", "1" * 64, 1)
    bundle = replace(
        _plan(1),
        artifact_state="trained_bundle",
        model_identity=model_identity,
        trained_through=date(2024, 6, 30),
    )

    assert bundle.calibrator_identity is None
    assert bundle.to_dict()["model_identity"]["sha256"] == "1" * 64

    with pytest.raises(ValueError, match="trained_bundle"):
        replace(_plan(1), artifact_state="trained_bundle")


@pytest.mark.parametrize("changed_field", ["event_threshold", "variables"])
def test_incompatible_shared_contract_metadata_is_detected(changed_field):
    contracts = [_plan(horizon) for horizon in (1, 2, 3)]
    change = (
        {"event_threshold": 0.3}
        if changed_field == "event_threshold"
        else {"variables": contracts[1].variables + (VariableMetadata("relative_humidity", "%"),)}
    )
    contracts[1] = replace(contracts[1], **change)

    with pytest.raises(HorizonContractMismatch):
        validate_horizon_contract_family(tuple(contracts))


def test_a_trained_family_requires_a_distinct_model_identity_per_horizon():
    contracts = []
    for horizon in (1, 2, 3):
        contracts.append(
            replace(
                _plan(horizon),
                artifact_state="trained_bundle",
                model_identity=ArtifactIdentity(f"synthetic-model-h{horizon}", "a" * 64, horizon),
                trained_through=date(2024, 6, 30),
            )
        )

    with pytest.raises(HorizonContractMismatch, match="identidad de modelo propia"):
        validate_horizon_contract_family(tuple(contracts))
