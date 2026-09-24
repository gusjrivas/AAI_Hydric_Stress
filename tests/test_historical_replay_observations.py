from datetime import date

import pandas as pd
import pytest

from historical_replay.observations import (
    CrossSeriesObservationError,
    ObservationConsistencyError,
    link_observation,
)
from historical_replay.records import build_records


def _record(target_observed=True, y_true=1.0):
    row = {
        "experiment_id": "4",
        "run_id": "1157696b7bb941e394c5af530c762b07",
        "config_name": "base",
        "seed": 4,
        "timestamp": "2024-10-19T00:00:00.000",
        "target_timestamp": "2024-10-22T00:00:00.000",
        "target_observed": target_observed,
        "y_true": y_true,
        "y_proba": 0.44,
        "y_pred": 0,
    }
    return build_records([row], horizon_days=3)[0]


def _dataset(values):
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-10-19", periods=len(values), freq="D"),
            "soil_moisture": values,
        }
    )


def test_links_a_real_measurement_at_the_target_date():
    record = _record()
    dataset_df = _dataset([0.30, 0.31, 0.32, 0.20])  # 2024-10-22 -> 0.20

    observation = link_observation(
        record=record,
        dataset_name="melchor_romero_2024_consolidado",
        expected_dataset_name="melchor_romero_2024_consolidado",
        dataset_df=dataset_df,
        label_column="soil_moisture",
        imputation_markers_df=None,
    )

    assert observation.target_date == date(2024, 10, 22)
    assert observation.raw_value == 0.20
    assert observation.state == "medida"


def test_rejects_a_dataset_name_that_does_not_match_the_declared_series():
    record = _record()
    dataset_df = _dataset([0.30, 0.31, 0.32, 0.20])

    with pytest.raises(CrossSeriesObservationError):
        link_observation(
            record=record,
            dataset_name="otro_sensor_2025",
            expected_dataset_name="melchor_romero_2024_consolidado",
            dataset_df=dataset_df,
            label_column="soil_moisture",
            imputation_markers_df=None,
        )


def test_rejects_when_target_date_is_absent_from_the_series():
    record = _record()
    dataset_df = _dataset([0.30, 0.31])  # solo hasta 2024-10-20, sin el objetivo

    with pytest.raises(CrossSeriesObservationError):
        link_observation(
            record=record,
            dataset_name="melchor_romero_2024_consolidado",
            expected_dataset_name="melchor_romero_2024_consolidado",
            dataset_df=dataset_df,
            label_column="soil_moisture",
            imputation_markers_df=None,
        )


def test_rejects_ambiguous_duplicate_dates_in_the_series():
    dataset_df = _dataset([0.30, 0.31, 0.32, 0.20])
    duplicated = pd.concat([dataset_df, dataset_df.iloc[[-1]]], ignore_index=True)
    record = _record()

    with pytest.raises(CrossSeriesObservationError):
        link_observation(
            record=record,
            dataset_name="melchor_romero_2024_consolidado",
            expected_dataset_name="melchor_romero_2024_consolidado",
            dataset_df=duplicated,
            label_column="soil_moisture",
            imputation_markers_df=None,
        )


def test_flags_imputed_state_from_the_markers():
    record = _record()
    dataset_df = _dataset([0.30, 0.31, 0.32, 0.20])
    markers_df = dataset_df.copy()
    markers_df["soil_moisture_imputado"] = [False, False, False, True]

    observation = link_observation(
        record=record,
        dataset_name="melchor_romero_2024_consolidado",
        expected_dataset_name="melchor_romero_2024_consolidado",
        dataset_df=dataset_df,
        label_column="soil_moisture",
        imputation_markers_df=markers_df,
    )

    assert observation.state == "imputada"


def test_target_observed_true_but_raw_value_missing_is_a_consistency_error():
    record = _record(target_observed=True, y_true=1.0)
    dataset_df = _dataset([0.30, 0.31, 0.32, None])  # objetivo nulo en el dataset

    with pytest.raises(ObservationConsistencyError):
        link_observation(
            record=record,
            dataset_name="melchor_romero_2024_consolidado",
            expected_dataset_name="melchor_romero_2024_consolidado",
            dataset_df=dataset_df,
            label_column="soil_moisture",
            imputation_markers_df=None,
        )
