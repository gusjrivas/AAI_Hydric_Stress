from datetime import date

import pandas as pd

from historical_replay.history_state import classify_history_row
from historical_replay.observations import IMPUTED, MEASURED, MISSING_FROM_SOURCE, UNDETERMINED


def test_a_present_raw_value_is_always_medida_regardless_of_markers():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.31],
            "soil_moisture_imputado": [True],  # deliberately inconsistent/degenerate marker
        }
    )

    state = classify_history_row(
        raw_value=0.30,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == MEASURED
    assert state.causa is None
    assert state.valor_imputado is None


def test_missing_marker_dataframe_is_no_determinado_with_a_causa():
    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 2),
        label_column="soil_moisture",
        imputation_markers_df=None,
    )

    assert state.estado == UNDETERMINED
    assert state.causa is not None
    assert "2024-01-02" in state.causa
    assert state.valor_imputado is None


def test_missing_marker_dataframe_uses_the_caller_supplied_causa_when_given():
    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 2),
        label_column="soil_moisture",
        imputation_markers_df=None,
        undetermined_causa="ImputationSourceDriftError: fuente de imputación cambió.",
    )

    assert state.estado == UNDETERMINED
    assert state.causa == "ImputationSourceDriftError: fuente de imputación cambió."


def test_date_absent_from_markers_is_no_determinado():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.30],
            "soil_moisture_imputado": [False],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 5),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == UNDETERMINED
    assert "2024-01-05" in state.causa


def test_raw_absent_and_marker_says_not_imputed_is_sin_dato_en_fuente():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [None],
            "soil_moisture_imputado": [False],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == MISSING_FROM_SOURCE
    assert state.causa is not None
    assert state.valor_imputado is None


def test_raw_absent_and_marker_says_imputed_is_imputada_with_a_separate_derived_value():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.28],
            "soil_moisture_imputado": [True],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == IMPUTED
    assert state.causa is not None
    assert state.valor_imputado == 0.28
