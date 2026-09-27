from __future__ import annotations

import ast
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiment_runner import ensemble_retrospective_evaluation as evaluation
from predictive_modeling.contract import feature_names
from predictive_modeling.ensemble_bundle import load_ensemble_bundle, predict_ensemble_bundle
from predictive_modeling.operational_preparation import DateRange, TemporalCutPlan
from tests.helpers.synthetic_bundles import (
    StubEstimator,
    write_ensemble_manifest,
    write_single_bundle,
)

ERA5_HEADER = [
    "latitude,longitude,elevation,utc_offset_seconds,timezone,timezone_abbreviation",
    "-33.899998,-60.6,70.0,-10800,America/Argentina/Buenos_Aires,GMT-3",
    "",
    "time,soil_moisture_0_to_7cm (m³/m³),soil_moisture_7_to_28cm (m³/m³),"
    "soil_moisture_28_to_100cm (m³/m³),soil_moisture_100_to_255cm (m³/m³)",
]


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _write_era5(
    path: Path,
    values: dict[date, float],
    *,
    missing_hour: tuple[date, int] | None = None,
    duplicate_hour: tuple[date, int] | None = None,
) -> None:
    lines = list(ERA5_HEADER)
    for day, value in sorted(values.items()):
        for hour in range(24):
            if missing_hour == (day, hour):
                continue
            cell = "" if math.isnan(value) else str(value)
            lines.append(f"{day.isoformat()}T{hour:02d}:00,{cell},{cell},{cell},{cell}")
        if duplicate_hour and duplicate_hour[0] == day:
            hour = duplicate_hour[1]
            lines.append(f"{day.isoformat()}T{hour:02d}:00,{value},{value},{value},{value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_nasa(path: Path, values: dict[date, tuple[float, float]]) -> None:
    lines = [
        "-BEGIN HEADER-",
        "synthetic fixture",
        "-END HEADER-",
        "YEAR,DOY,RH2M,ALLSKY_SFC_SW_DWN,T2M,PRECTOTCORR",
    ]
    for day, (rh, solar) in sorted(values.items()):
        lines.append(f"{day.year},{day.timetuple().tm_yday},{rh},{solar},20,0")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_mixed_pair(root: Path, future_value: float = 0.9) -> tuple[Path, Path]:
    days = _days(date(2022, 12, 25), date(2024, 1, 2))
    soil = {day: (0.2 if day.year <= 2023 else future_value) for day in days}
    weather = {day: (60.0 if day.year <= 2023 else future_value, 20.0) for day in days}
    era5 = root / "era5.csv"
    nasa = root / "nasa.csv"
    _write_era5(era5, soil)
    _write_nasa(nasa, weather)
    return era5, nasa


def _cuts() -> TemporalCutPlan:
    return TemporalCutPlan(
        allowed_data=DateRange("2020-01-01", "2023-12-31"),
        train=DateRange("2020-01-01", "2021-12-31"),
        calibration=DateRange("2022-01-01", "2022-12-31"),
        evaluation=DateRange("2023-01-01", "2023-12-31"),
        inference_as_of="2023-12-31",
    )


def _write_test_ensemble(root: Path, horizon: int) -> None:
    sensor = evaluation.SENSOR_ID
    horizon_root = root / sensor / f"horizon_{horizon}"
    write_ensemble_manifest(horizon_root, sensor_id=sensor, horizon=horizon)
    columns = ["soil_moisture", "relative_humidity", "solar_radiation"]
    names = feature_names(columns, [1, 2, 3], [3, 7], include_current=True)
    probabilities = {
        "hist_gradient_boosting_classifier": 0.39,
        "logistic_regression": 0.9,
        "random_forest": 0.41,
    }
    variables = [
        {"name": "soil_moisture", "unit": "m3/m3"},
        {"name": "relative_humidity", "unit": "%"},
        {"name": "solar_radiation", "unit": "MJ/m2/day"},
    ]
    for family, probability in probabilities.items():
        model = StubEstimator(probability, feature_names_in_=np.asarray(names, dtype=object))
        calibrator = StubEstimator(probability, feature_names_in_=np.asarray(names, dtype=object))
        write_single_bundle(
            horizon_root / "ensemble" / family,
            sensor_id=sensor,
            horizon=horizon,
            model=model,
            calibrator=calibrator,
            feature_columns=columns,
            feature_names=names,
            lags=[1, 2, 3],
            rolling_windows=[3, 7],
            event={
                "variable": "soil_moisture",
                "threshold": 0.3,
                "unit": "m3/m3",
                "comparison": "lt",
            },
            variables=variables,
            temporal_cuts=_cuts(),
            trained_through="2021-12-31",
            calibrated_through="2022-12-31",
            model_identity_label=f"{family}-model",
            calibrator_identity_label=f"{family}-calibrator",
        )


def _inference_frame() -> pd.DataFrame:
    days = pd.date_range("2022-12-26", "2023-01-10", freq="D")
    return pd.DataFrame(
        {
            "timestamp": days,
            "soil_moisture": np.linspace(0.4, 0.2, len(days)),
            "relative_humidity": np.linspace(60, 70, len(days)),
            "solar_radiation": np.linspace(20, 25, len(days)),
        }
    )


def test_stream_filter_happens_before_numeric_ingestion_and_future_values_have_no_influence(
    tmp_path,
):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    era5_a, nasa_a = _write_mixed_pair(first, future_value=999.0)
    era5_b, nasa_b = _write_mixed_pair(second, future_value=-999.0)
    filtered = []
    for index, (era5, nasa) in enumerate(((era5_a, nasa_a), (era5_b, nasa_b))):
        out_era5 = tmp_path / f"era5-{index}.csv"
        out_nasa = tmp_path / f"nasa-{index}.csv"
        era_record = evaluation.stream_filter_era5(era5, out_era5)
        nasa_record = evaluation.stream_filter_nasa(nasa, out_nasa)
        assert era_record["rows_excluded_after_2023"] == 48
        assert nasa_record["rows_excluded_after_2023"] == 2
        assert era_record["future_bytes_traversed_values_not_parsed_or_aggregated"] is True
        filtered.append((out_era5.read_bytes(), out_nasa.read_bytes()))
    assert filtered[0] == filtered[1]


def test_restricted_ingestion_preserves_missing_sentinel_and_hourly_coverage_controls(tmp_path):
    days = _days(date(2022, 12, 26), date(2023, 1, 3))
    soil = {day: 0.3 for day in days}
    weather = {day: (60.0, 20.0) for day in days}
    weather[date(2023, 1, 1)] = (-999.0, 20.0)
    era5 = tmp_path / "era5.csv"
    nasa = tmp_path / "nasa.csv"
    # 24 rows but only 23 unique hours: hour 12 is absent and hour 11 duplicated.
    _write_era5(
        era5,
        soil,
        missing_hour=(date(2023, 1, 2), 12),
        duplicate_hour=(date(2023, 1, 2), 11),
    )
    _write_nasa(nasa, weather)
    frame, details = evaluation.build_restricted_daily_frame(era5, nasa)
    assert details["duplicate_timestamps"] == 0
    jan1 = frame.loc[frame["timestamp"] == pd.Timestamp("2023-01-01")].iloc[0]
    jan2 = frame.loc[frame["timestamp"] == pd.Timestamp("2023-01-02")].iloc[0]
    assert pd.isna(jan1["relative_humidity"])
    assert pd.isna(jan2["soil_moisture"])
    assert details["missing_by_column"]["soil_moisture"] == 1


@pytest.mark.parametrize("horizon", [1, 2, 3])
def test_production_inference_is_causal_aligned_and_average_differs_from_majority(
    tmp_path, horizon
):
    root = tmp_path / "bundles"
    _write_test_ensemble(root, horizon)
    before = evaluation.tree_hashes(root)
    ensemble = load_ensemble_bundle(root, sensor_id=evaluation.SENSOR_ID, horizon=horizon)
    frame = _inference_frame()
    units = {"soil_moisture": "m3/m3", "relative_humidity": "%", "solar_radiation": "MJ/m2/day"}
    as_of = date(2023, 1, 3)
    original = predict_ensemble_bundle(
        ensemble, frame, sensor_id=evaluation.SENSOR_ID, units=units, as_of_date=as_of
    )
    changed = frame.copy()
    changed.loc[
        changed["timestamp"] > pd.Timestamp(as_of),
        ["soil_moisture", "relative_humidity", "solar_radiation"],
    ] = 999.0
    repeated = predict_ensemble_bundle(
        ensemble, changed, sensor_id=evaluation.SENSOR_ID, units=units, as_of_date=as_of
    )
    assert original == repeated
    assert original["target_date"] == (as_of + timedelta(days=horizon)).isoformat()
    assert original["combined_probability"] == pytest.approx((0.39 + 0.9 + 0.41) / 3)
    assert original["combined_alert"] is True
    assert original["positive_votes"] == 1
    assert evaluation.tree_hashes(root) == before


def test_metrics_report_undefined_instead_of_zero_and_reliability_support():
    undefined = evaluation.method_metrics([0, 0], [0, 0])
    assert undefined["precision"] == {
        "status": "undefined",
        "value": None,
        "reason": "no_predicted_positives",
    }
    assert undefined["recall"]["status"] == "undefined"
    assert undefined["mcc"]["status"] == "undefined"
    defined = evaluation.method_metrics([0, 1, 1, 0], [0, 1, 0, 0], [0.1, 0.8, 0.4, 0.2])
    assert defined["confusion_matrix"] == {"tn": 2, "fp": 0, "fn": 1, "tp": 1}
    assert defined["average_precision"]["status"] == "defined"
    assert sum(item["n"] for item in defined["reliability_bins"]) == 4
    assert sum(item["positives"] for item in defined["reliability_bins"]) == 2


def test_episode_gaps_break_continuity_and_censor_onsets():
    days = pd.date_range("2023-01-01", "2023-01-10", freq="D")
    values = [0.4, 0.2, 0.2, np.nan, 0.2, 0.2, 0.4, 0.2, 0.4, 0.4]
    frame = pd.DataFrame({"timestamp": days, "soil_moisture": values})
    episodes = evaluation.observed_episodes(frame, 0.3)
    assert [(item["start"], item["end"]) for item in episodes] == [
        ("2023-01-02", "2023-01-03"),
        ("2023-01-05", "2023-01-06"),
        ("2023-01-08", "2023-01-08"),
    ]
    assert episodes[0]["start_determinable"] is True
    assert episodes[1]["left_censored"] is True
    assert episodes[2]["start_determinable"] is True


def test_target_bounds_persistence_common_cases_and_fixed_p20(tmp_path, monkeypatch):
    class Component:
        def __init__(self):
            self.metadata = {
                "decision_threshold": 0.5,
                "contract": {
                    "event": {"threshold": 0.3},
                    "variables": [
                        {"name": "soil_moisture", "unit": "m3/m3"},
                        {"name": "relative_humidity", "unit": "%"},
                        {"name": "solar_radiation", "unit": "MJ/m2/day"},
                    ],
                },
            }

    class Ensemble:
        components = {family: Component() for family in evaluation.FAMILIES}

    def fake_component(component, dataframe, *, sensor_id, units, as_of_date):
        del component, dataframe, sensor_id, units
        return {
            "score": 0.6,
            "alert": True,
            "decision_threshold": 0.5,
            "target_date": as_of_date.isoformat(),
        }

    def fake_ensemble(ensemble, dataframe, *, sensor_id, units, as_of_date):
        del ensemble, dataframe, sensor_id, units, as_of_date
        return {"combined_probability": 0.6, "combined_alert": True}

    monkeypatch.setattr(evaluation, "predict_operational_bundle", fake_component)
    monkeypatch.setattr(evaluation, "predict_ensemble_bundle", fake_ensemble)
    days = pd.date_range("2022-12-26", "2023-12-31", freq="D")
    moisture = np.full(len(days), 0.4)
    moisture[(days == pd.Timestamp("2023-06-02"))] = 0.2
    moisture[(days == pd.Timestamp("2023-07-01"))] = np.nan
    frame = pd.DataFrame(
        {
            "timestamp": days,
            "soil_moisture": moisture,
            "relative_humidity": 60.0,
            "solar_radiation": 20.0,
        }
    )
    rows, summary = evaluation.evaluate_horizon(frame, Ensemble(), 3)
    assert rows[-1]["target_date"] == "2023-12-31"
    assert all(date.fromisoformat(row["target_date"]).year == 2023 for row in rows)
    june = next(row for row in rows if row["emission_date"] == "2023-06-01")
    assert june["target"] == 0
    assert june["persistence_alert"] == 0
    assert summary["physical_threshold_p20"] == 0.3
    assert summary["exclusions"]["invalid_target_observation"] == 1
    assert summary["common_cases"] == summary["candidate_emissions"] - 2


def test_bootstrap_uses_paired_non_circular_blocks_and_counts_undefined():
    rows = []
    for index, day in enumerate(pd.date_range("2023-01-01", periods=90, freq="D")):
        target = index % 3 == 0
        rows.append(
            {
                "emission_date": day.date().isoformat(),
                "target": int(target),
                "average_alert": int(index % 4 == 0),
                "persistence_alert": int(index % 5 == 0),
            }
        )
    result = evaluation.paired_block_bootstrap(
        rows, {"average_minus_persistence": ("average", "persistence")}
    )
    assert result["block_length_days"] == 30
    assert result["seed"] == 20250109
    assert result["replicates_requested"] == 5000
    assert result["candidate_blocks"] == 61
    assert result["resampled_rows_per_segment"] == [90]
    assert result["comparisons"]["average_minus_persistence"]["replicates_defined"] >= 4000
    assert result["comparisons"]["average_minus_persistence"]["status"] == "defined"


def _bootstrap_rows(days: list[date], *, constant_target: int | None = None):
    rows = []
    for index, day in enumerate(days):
        target = constant_target if constant_target is not None else int(index % 3 == 0)
        rows.append(
            {
                "emission_date": day.isoformat(),
                "target": target,
                "average_alert": int(index % 4 == 0),
                "persistence_alert": int(index % 5 == 0),
            }
        )
    return rows


def test_bootstrap_preserves_each_continuous_segment_without_crossing_gap():
    first = _days(date(2023, 1, 1), date(2023, 2, 9))  # 40 cases
    second = _days(date(2023, 3, 1), date(2023, 4, 4))  # 35 cases
    segments = evaluation._continuous_segments(first + second)
    indices = evaluation._draw_segmented_block_indices(np.random.default_rng(7), segments)
    assert len(indices) == 75
    assert set(indices[:40]).issubset(set(range(40)))
    assert set(indices[40:]).issubset(set(range(40, 75)))

    result = evaluation.paired_block_bootstrap(
        _bootstrap_rows(first + second),
        {"average_minus_persistence": ("average", "persistence")},
    )
    assert result["segment_lengths"] == [40, 35]
    assert result["resampled_rows_per_segment"] == [40, 35]
    assert result["candidate_blocks_by_segment"] == [11, 6]


def test_bootstrap_is_undefined_when_any_segment_is_shorter_than_block():
    first = _days(date(2023, 1, 1), date(2023, 2, 4))  # 35 cases
    second = _days(date(2023, 3, 1), date(2023, 3, 10))  # 10 cases
    result = evaluation.paired_block_bootstrap(
        _bootstrap_rows(first + second),
        {"average_minus_persistence": ("average", "persistence")},
    )
    comparison = result["comparisons"]["average_minus_persistence"]
    assert result["status"] == "undefined"
    assert result["reason"] == "segment_shorter_than_block_length"
    assert result["short_segment_lengths"] == [10]
    assert comparison["delta_mcc_ci95"] is None


def test_bootstrap_requires_four_thousand_valid_replicates_for_interval():
    days = _days(date(2023, 1, 1), date(2023, 3, 1))
    result = evaluation.paired_block_bootstrap(
        _bootstrap_rows(days, constant_target=0),
        {"average_minus_persistence": ("average", "persistence")},
    )
    comparison = result["comparisons"]["average_minus_persistence"]
    assert result["status"] == "undefined"
    assert result["reason"] == "insufficient_valid_replicates"
    assert comparison["replicates_defined"] == 0
    assert comparison["replicates_discarded_undefined"] == 5000
    assert comparison["delta_mcc_ci95"] is None


def test_evaluator_source_contains_no_fit_or_recalibration_calls():
    source_path = Path(evaluation.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id if isinstance(function, ast.Name) else ""
            )
            if name in {
                "fit",
                "fit_estimator",
                "recalibrate",
                "run_demo",
                "run_stage_a",
                "run_stage_b",
                "run_stage_c",
            }:
                forbidden.append((name, node.lineno))
    assert forbidden == []


def test_json_writer_rejects_nan_by_serializing_null(tmp_path):
    path = tmp_path / "strict.json"
    evaluation.write_json(path, {"undefined": float("nan")})
    assert json.loads(path.read_text(encoding="utf-8")) == {"undefined": None}
    assert "NaN" not in path.read_text(encoding="utf-8")
