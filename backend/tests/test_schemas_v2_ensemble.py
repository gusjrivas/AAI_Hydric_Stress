from datetime import date

import pytest
from app.schemas_v2 import EnsembleComponentVote, EnsembleDetail, ModelReference
from pydantic import ValidationError


def _component(family, score, alert, trained_through="2026-01-01"):
    return EnsembleComponentVote(
        family=family,
        model_reference=ModelReference(
            model_version=f"{family}-sha",
            horizon_days=1,
            contract_version="producer_daily_h123_v1",
            trained_through=date.fromisoformat(trained_through),
            calibration_version=f"{family}-cal-sha",
            assessment_reference=None,
        ),
        calibrated_through=date(2026, 1, 15),
        score=score,
        decision_threshold=0.5,
        alert=alert,
    )


def test_ensemble_detail_round_trips_with_coherent_fields():
    detail = EnsembleDetail(
        policy_version="ensemble_agreement_v1",
        ensemble_identity_sha256="a" * 64,
        components=[
            _component("logistic_regression", 0.51, True),
            _component("random_forest", 0.51, True),
            _component("hist_gradient_boosting_classifier", 0.01, False),
        ],
        combined_probability=0.34333333333333327,
        combined_alert=False,
        positive_votes=2,
        agreement_category="posible_alerta_acuerdo_parcial",
        calibrated_through=date(2026, 1, 20),
    )
    assert detail.combined_alert is False


def test_ensemble_detail_rejects_positive_votes_inconsistent_with_components():
    with pytest.raises(ValidationError, match="positive_votes"):
        EnsembleDetail(
            policy_version="ensemble_agreement_v1",
            ensemble_identity_sha256="a" * 64,
            components=[
                _component("logistic_regression", 0.51, True),
                _component("random_forest", 0.51, False),
                _component("hist_gradient_boosting_classifier", 0.01, False),
            ],
            combined_probability=0.343333,
            combined_alert=False,
            positive_votes=2,  # only 1 component has alert=True
            agreement_category="posible_alerta_acuerdo_parcial",
            calibrated_through=date(2026, 1, 20),
        )


def test_ensemble_detail_rejects_duplicate_family():
    with pytest.raises(ValidationError, match="3 familias"):
        EnsembleDetail(
            policy_version="ensemble_agreement_v1",
            ensemble_identity_sha256="a" * 64,
            components=[
                _component("logistic_regression", 0.51, True),
                _component("logistic_regression", 0.51, True),
                _component("hist_gradient_boosting_classifier", 0.01, False),
            ],
            combined_probability=0.343333,
            combined_alert=False,
            positive_votes=2,
            agreement_category="posible_alerta_acuerdo_parcial",
            calibrated_through=date(2026, 1, 20),
        )


def test_model_reference_calibrated_through_is_optional_and_backward_compatible():
    ref = ModelReference(
        model_version="m1",
        horizon_days=1,
        contract_version="producer_daily_h123_v1",
        trained_through=date(2026, 1, 1),
        calibration_version="c1",
        assessment_reference=None,
    )
    assert ref.calibrated_through is None
