from __future__ import annotations

import pandas as pd

from experiment_runner.controlled_daily_v4.config import (
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_SOFT_VOTING,
    PRIMARY_DEPTH_COLUMN,
    HistGradientBoostingGridSpec,
    LogisticRegressionGridSpec,
    ProtocolConfig,
    RandomForestGridSpec,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    aggregate_era5_daily,
    build_daily_joined_series,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
    replace_missing_sentinel,
)
from experiment_runner.controlled_daily_v4.selection import (
    OUTCOME_NO_STABLE_WINNER,
    OUTCOME_NO_VALID_SELECTION,
    OUTCOME_STABLE_WINNER,
)
from experiment_runner.controlled_daily_v4.stage_a_runner import build_eligible_frame, run_stage_a
from tests.controlled_daily_v4_fixtures import write_synthetic_pergamino_csv_pair

FAST_CONFIG = ProtocolConfig(
    bootstrap_replicas=30,
    logistic_regression_grid=LogisticRegressionGridSpec(C=(0.1, 1.0)),
    random_forest_grid=RandomForestGridSpec(
        n_estimators=(50,), max_depth=(4,), min_samples_leaf=(5,)
    ),
    hist_gradient_boosting_grid=HistGradientBoostingGridSpec(
        learning_rate=(0.1,), max_iter=(50,), max_leaf_nodes=(15,), l2_regularization=(0.0,)
    ),
)


def _synthetic_daily_series(tmp_path, n_days=350, seed=11):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=n_days, seed=seed)
    _era5_meta, era5_df = load_era5_hourly_raw(era5)
    era5_daily = aggregate_era5_daily(era5_df)
    _nasa_meta, nasa_df = load_nasa_power_daily_raw(nasa)
    nasa_df = replace_missing_sentinel(nasa_df)
    return build_daily_joined_series(era5_daily, nasa_df)


def test_run_stage_a_end_to_end_on_synthetic_series(tmp_path):
    daily_series = _synthetic_daily_series(tmp_path)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)

    assert results.selection.outcome in (
        OUTCOME_STABLE_WINNER,
        OUTCOME_NO_STABLE_WINNER,
        OUTCOME_NO_VALID_SELECTION,
    )

    if results.selection.outcome != OUTCOME_NO_VALID_SELECTION:
        assert results.selection.selected_family in (
            FAMILY_LOGISTIC_REGRESSION,
            FAMILY_RANDOM_FOREST,
            FAMILY_HIST_GRADIENT_BOOSTING,
            FAMILY_SOFT_VOTING,
        )
        assert results.final_estimator is not None
        assert results.final_p20_train is not None


def test_stage_a_oof_predictions_have_no_duplicate_timestamps_and_are_ordered(tmp_path):
    daily_series = _synthetic_daily_series(tmp_path)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)

    for family, oof in results.oof_by_family.items():
        timestamps = pd.to_datetime(oof.frame_with_segment_id["feature_timestamp"])
        assert not timestamps.duplicated().any(), family
        assert timestamps.is_monotonic_increasing, family


def test_stage_a_oof_excludes_gap_rows_between_outer_folds(tmp_path):
    """En cada outer fold quedan exactamente `gap` emisiones entre el final del
    train y el comienzo de la validación, y esas filas no pertenecen ni al
    train ni a la validación de ese fold.

    La exclusión es por fold, no global: con `TimeSeriesSplit` las filas del
    gap de un fold son las últimas del `outer_val` del fold anterior, de modo
    que sí aparecen en el OOF a través de ese otro segmento — predichas por un
    modelo cuyo train terminaba antes todavía. Lo que el gap garantiza es que
    ningún fold evalúe una emisión adyacente al final de su propio train.
    """
    daily_series = _synthetic_daily_series(tmp_path)
    results = run_stage_a(daily_series, PRIMARY_DEPTH_COLUMN, FAST_CONFIG)

    oof = results.oof_by_family[FAMILY_LOGISTIC_REGRESSION]
    eligible = pd.to_datetime(
        build_eligible_frame(daily_series, PRIMARY_DEPTH_COLUMN)["feature_timestamp"]
    )

    # El OOF es exactamente la unión de las validaciones.
    assert len(oof.y_true) == sum(len(f.validation) for f in results.outer_folds)

    for fold in results.outer_folds:
        train_timestamps = set(pd.to_datetime(fold.train["feature_timestamp"]))
        validation_timestamps = set(pd.to_datetime(fold.validation["feature_timestamp"]))
        train_end = max(train_timestamps)
        validation_start = min(validation_timestamps)

        gap_rows = set(eligible[(eligible > train_end) & (eligible < validation_start)])
        assert len(gap_rows) == FAST_CONFIG.gap, f"outer fold {fold.index}"
        assert not (gap_rows & train_timestamps), f"outer fold {fold.index}"
        assert not (gap_rows & validation_timestamps), f"outer fold {fold.index}"


def test_three_outer_folds_are_generated():
    # Config normativa (no FAST_CONFIG) solo para verificar n_splits, sin
    # ejecutar el runner completo con la grilla real (demasiado lento para
    # un test unitario).
    from experiment_runner.controlled_daily_v4.config import ProtocolConfig as PC

    assert PC().outer_n_splits == 3
    assert PC().inner_n_splits == 3
