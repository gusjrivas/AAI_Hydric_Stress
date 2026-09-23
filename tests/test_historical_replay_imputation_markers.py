import pandas as pd
import pytest

from data_ingestion.schema import normalize_to_schema
from historical_replay import imputation_markers
from historical_replay.imputation_markers import (
    ImputationSourceDriftError,
    reconstruct_imputation_markers,
    verify_imputation_source_matches_verified_commit,
)


def _series(soil_moisture_values, start="2024-01-01"):
    n = len(soil_moisture_values)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": pd.date_range(start, periods=n, freq="D"),
                "soil_moisture": soil_moisture_values,
            }
        ),
        provenance="real",
    )


def test_reconstructs_imputed_flag_for_a_forward_filled_gap():
    df = _series([0.30, None, 0.28])

    result = reconstruct_imputation_markers(df, columns=["soil_moisture"])

    middle = result[result["timestamp"] == "2024-01-02"].iloc[0]
    assert middle["soil_moisture"] == 0.30
    assert bool(middle["soil_moisture_imputado"]) is True


def test_measured_values_are_not_flagged_as_imputed():
    df = _series([0.30, 0.29])

    result = reconstruct_imputation_markers(df, columns=["soil_moisture"])

    assert not result["soil_moisture_imputado"].any()


def test_gap_with_no_prior_value_stays_null_and_unflagged():
    df = _series([None, 0.28])

    result = reconstruct_imputation_markers(df, columns=["soil_moisture"])

    first = result[result["timestamp"] == "2024-01-01"].iloc[0]
    assert pd.isna(first["soil_moisture"])
    assert bool(first["soil_moisture_imputado"]) is False


def test_source_equivalence_with_the_historical_commit_currently_holds():
    # No debe lanzar: data_quality.imputation/temporal coinciden hoy con lo
    # verificado contra el commit que produjo el candidato (2026-09-23).
    verify_imputation_source_matches_verified_commit()


def test_source_drift_is_detected_and_blocks_reconstruction(monkeypatch):
    monkeypatch.setitem(
        imputation_markers._VERIFIED_SOURCE_SHA256,
        "data_quality.imputation",
        "0" * 64,
    )

    with pytest.raises(ImputationSourceDriftError):
        verify_imputation_source_matches_verified_commit()

    df = _series([0.30, 0.29])
    with pytest.raises(ImputationSourceDriftError):
        reconstruct_imputation_markers(df, columns=["soil_moisture"])
