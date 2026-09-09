"""Métricas realmente calculadas y persistidas, y JSON estrictamente estándar.

Cubre el §12 del protocolo (todas las secundarias y operativas se reportan
siempre, con convención explícita ante casos degenerados), el §8.4 (diagnóstico
por outer fold con mediana e IQR) y la exigencia de evidencia interoperable:
ningún artefacto puede contener `NaN`, `Infinity` ni `-Infinity`.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    build_metrics_payload,
    normalize_for_json,
    write_stage_a_artifacts,
)
from experiment_runner.controlled_daily_v4.environment import capture_environment
from experiment_runner.controlled_daily_v4.metrics import (
    METRIC_STATUS_DEFINED,
    METRIC_STATUS_UNDEFINED,
    calibration_curve_10_bins,
    metric_envelope,
    metrics_payload,
    summarize_fold_mcc,
)

STRICT_TOKENS = ("NaN", "Infinity", "-Infinity")


def _assert_strict_json(text: str) -> object:
    """Rechaza tokens no estándar tanto textualmente como al re-parsear."""
    for token in STRICT_TOKENS:
        assert token not in text, f"token no estándar '{token}' presente en el artefacto"

    def reject(constant):
        raise AssertionError(f"constante JSON no estándar: {constant}")

    return json.loads(text, parse_constant=reject)


# --------------------------------------------------------------------------
# Envelope de métricas
# --------------------------------------------------------------------------


def test_defined_metric_envelope_carries_the_value_and_a_defined_status():
    assert metric_envelope(0.42, "monoclass_y_true") == {
        "value": pytest.approx(0.42),
        "status": METRIC_STATUS_DEFINED,
    }


def test_undefined_metric_envelope_uses_null_and_an_explicit_reason():
    assert metric_envelope(float("nan"), "monoclass_y_true") == {
        "value": None,
        "status": METRIC_STATUS_UNDEFINED,
        "undefined_reason": "monoclass_y_true",
    }


def test_infinite_metric_is_also_treated_as_undefined():
    assert metric_envelope(float("inf"), "diverged")["status"] == METRIC_STATUS_UNDEFINED


# --------------------------------------------------------------------------
# Payload completo de métricas
# --------------------------------------------------------------------------


def _balanced_case(n=120, seed=0):
    rng = np.random.default_rng(seed)
    y_true = (rng.random(n) < 0.35).astype(int)
    y_score = np.where(y_true == 1, rng.uniform(0.5, 1.0, n), rng.uniform(0.0, 0.5, n))
    y_pred = (y_score >= 0.5).astype(int)
    return y_true, y_pred, y_score


def test_metrics_payload_reports_every_metric_required_by_the_protocol():
    y_true, y_pred, y_score = _balanced_case()
    payload = metrics_payload(y_true, y_pred, y_score)
    for name in (
        "mcc",
        "average_precision",
        "balanced_accuracy",
        "f1",
        "precision",
        "recall",
        "roc_auc",
        "brier_score",
        "log_loss",
    ):
        assert payload[name]["status"] == METRIC_STATUS_DEFINED, name
    assert payload["confusion_matrix"] == [
        [int(((y_true == 0) & (y_pred == 0)).sum()), int(((y_true == 0) & (y_pred == 1)).sum())],
        [int(((y_true == 1) & (y_pred == 0)).sum()), int(((y_true == 1) & (y_pred == 1)).sum())],
    ]
    for name in (
        "alert_rate",
        "false_positives_per_30_days",
        "false_negatives_per_30_days",
        "episode_recall",
        "alert_precision",
    ):
        assert name in payload["operational"], name
    assert len(payload["calibration"]) == 10


@pytest.mark.filterwarnings("ignore:A single label was found:UserWarning")
def test_monoclass_payload_marks_mcc_and_roc_auc_undefined_with_their_reason():
    y_true = np.ones(20, dtype=int)
    y_score = np.linspace(0.6, 0.9, 20)
    y_pred = (y_score >= 0.5).astype(int)
    payload = metrics_payload(y_true, y_pred, y_score)

    assert payload["mcc"]["undefined_reason"] == "monoclass_y_true"
    assert payload["roc_auc"]["undefined_reason"] == "monoclass_y_true"
    # Brier y log loss se calculan siempre (protocolo, sección 12).
    assert payload["brier_score"]["status"] == METRIC_STATUS_DEFINED
    assert payload["log_loss"]["status"] == METRIC_STATUS_DEFINED
    # La matriz sigue siendo 2x2 aunque una fila quede en cero.
    assert len(payload["confusion_matrix"]) == 2
    assert all(len(row) == 2 for row in payload["confusion_matrix"])


@pytest.mark.filterwarnings("ignore:A single label was found:UserWarning")
def test_payload_without_positive_labels_marks_average_precision_undefined():
    y_true = np.zeros(20, dtype=int)
    y_score = np.linspace(0.1, 0.4, 20)
    payload = metrics_payload(y_true, (y_score >= 0.5).astype(int), y_score)
    assert payload["average_precision"]["undefined_reason"] == "no_positive_labels_in_y_true"
    assert payload["operational"]["episode_recall"]["undefined_reason"] == (
        "no_stress_episodes_in_y_true"
    )


@pytest.mark.filterwarnings("ignore:A single label was found:UserWarning")
def test_no_metric_is_silently_turned_into_zero():
    y_true = np.ones(20, dtype=int)
    y_score = np.full(20, 0.8)
    payload = metrics_payload(y_true, np.ones(20, dtype=int), y_score)
    assert payload["mcc"]["value"] is None
    assert payload["mcc"]["value"] != 0


def test_calibration_bins_report_counts_and_leave_empty_bins_undefined():
    y_true = np.array([0, 1, 1, 0])
    y_score = np.array([0.05, 0.95, 0.92, 0.02])
    bins = calibration_curve_10_bins(y_true, y_score)
    assert len(bins) == 10
    assert sum(b["count"] for b in bins) == 4
    empty = [b for b in bins if b["count"] == 0]
    assert empty, "el caso de prueba deja bins vacíos"
    for b in empty:
        assert b["observed_frequency"]["status"] == METRIC_STATUS_UNDEFINED


# --------------------------------------------------------------------------
# Diagnóstico por outer fold (protocolo, sección 8.4)
# --------------------------------------------------------------------------


def test_fold_mcc_summary_reports_median_quartiles_and_iqr():
    summary = summarize_fold_mcc([0.1, 0.3, 0.5])
    assert summary["median"]["value"] == pytest.approx(0.3)
    assert summary["q1"]["value"] == pytest.approx(0.2)
    assert summary["q3"]["value"] == pytest.approx(0.4)
    assert summary["iqr"]["value"] == pytest.approx(0.2)
    assert summary["n_folds_defined"] == 3
    assert summary["n_folds_undefined"] == 0
    assert summary["percentile_method"] == "linear"


def test_fold_mcc_summary_counts_undefined_folds_without_dropping_them_silently():
    summary = summarize_fold_mcc([0.2, float("nan"), 0.4])
    assert summary["n_folds_defined"] == 2
    assert summary["n_folds_undefined"] == 1
    assert summary["median"]["value"] == pytest.approx(0.3)
    assert summary["per_fold"][1]["status"] == METRIC_STATUS_UNDEFINED


def test_fold_mcc_summary_is_fully_undefined_when_every_fold_is_undefined():
    summary = summarize_fold_mcc([float("nan"), float("nan")])
    assert summary["n_folds_defined"] == 0
    assert summary["median"]["status"] == METRIC_STATUS_UNDEFINED
    assert summary["iqr"]["status"] == METRIC_STATUS_UNDEFINED


# --------------------------------------------------------------------------
# Normalización recursiva para JSON estricto
# --------------------------------------------------------------------------


def test_normalization_replaces_every_non_finite_scalar():
    payload = {
        "a": float("nan"),
        "b": [float("inf"), -float("inf"), 1.0],
        "c": {"d": np.float64("nan")},
    }
    normalized = normalize_for_json(payload)
    text = json.dumps(normalized, allow_nan=False)
    _assert_strict_json(text)
    assert normalized["a"]["status"] == METRIC_STATUS_UNDEFINED
    assert normalized["b"][0]["status"] == METRIC_STATUS_UNDEFINED
    assert normalized["b"][2] == pytest.approx(1.0)
    assert normalized["c"]["d"]["status"] == METRIC_STATUS_UNDEFINED


def test_normalization_converts_numpy_and_timestamp_types():
    payload = {
        "int": np.int64(3),
        "float": np.float64(1.5),
        "array": np.array([1.0, 2.0]),
        "timestamp": pd.Timestamp("2022-12-31"),
        "bool": np.bool_(True),
    }
    normalized = normalize_for_json(payload)
    text = json.dumps(normalized, allow_nan=False)
    _assert_strict_json(text)
    assert normalized["int"] == 3
    assert normalized["float"] == pytest.approx(1.5)
    assert normalized["array"] == [1.0, 2.0]
    assert normalized["timestamp"].startswith("2022-12-31")
    assert normalized["bool"] is True


# --------------------------------------------------------------------------
# Captura real del entorno
# --------------------------------------------------------------------------


def test_environment_capture_records_real_versions_not_placeholders():
    import numpy as real_numpy
    import sklearn

    env = capture_environment()
    assert env["python_version"].startswith("3.")
    assert env["packages"]["numpy"] == real_numpy.__version__
    assert env["packages"]["scikit-learn"] == sklearn.__version__
    for package in ("pandas", "scipy", "pyarrow", "joblib", "threadpoolctl"):
        assert env["packages"][package], package
    assert "platform" in env
    assert "PENDING" not in json.dumps(env)


def test_environment_capture_is_json_strict():
    _assert_strict_json(json.dumps(normalize_for_json(capture_environment()), allow_nan=False))


# --------------------------------------------------------------------------
# metrics.json integrado y artefactos estrictos
# --------------------------------------------------------------------------


class _FakeFoldResult:
    def __init__(self, index, y_true, y_pred, y_score):
        self.outer_fold_index = index
        self.y_true = y_true
        self.y_pred = y_pred
        self.y_score = y_score
        self.p20_train = 0.3
        self.inner_median_mcc = float("nan") if index == 3 else 0.4
        self.inner_fold_mcc = [0.3, float("nan"), 0.5]

        class _Config:
            config_id = "fake[c=1]"
            params = {"weighting": "none"}

        self.inner_best_config = _Config()


class _FakeOOF:
    def __init__(self, y_true, y_pred, y_score, per_fold_mcc):
        self.y_true = y_true
        self.y_pred = y_pred
        self.y_score = y_score
        self.per_fold_mcc = per_fold_mcc
        self.frame_with_segment_id = pd.DataFrame(
            {
                "feature_timestamp": pd.date_range("2015-01-07", periods=len(y_true)),
                "segment_id": ["outer_fold_1"] * len(y_true),
            }
        )


def _fake_inputs():
    y_true, y_pred, y_score = _balanced_case(n=90)
    per_family_results = {
        "logistic_regression": [
            _FakeFoldResult(
                i + 1,
                y_true[i * 30 : (i + 1) * 30],
                y_pred[i * 30 : (i + 1) * 30],
                y_score[i * 30 : (i + 1) * 30],
            )
            for i in range(3)
        ]
    }
    oof = {"logistic_regression": _FakeOOF(y_true, y_pred, y_score, [0.3, float("nan"), 0.5])}
    return per_family_results, oof


def test_metrics_payload_artifact_has_global_and_per_fold_blocks():
    per_family_results, oof = _fake_inputs()
    payload = build_metrics_payload(per_family_results, oof)

    assert payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    family = payload["by_family"]["logistic_regression"]
    assert family["global"]["mcc"]["status"] in (
        METRIC_STATUS_DEFINED,
        METRIC_STATUS_UNDEFINED,
    )
    assert len(family["per_outer_fold"]) == 3
    assert [f["outer_fold_index"] for f in family["per_outer_fold"]] == [1, 2, 3]
    assert "mcc" in family["per_outer_fold"][0]
    assert "operational" in family["per_outer_fold"][0]
    assert family["fold_mcc_summary"]["n_folds_defined"] >= 1


def test_per_fold_mcc_is_never_empty_in_the_metrics_artifact():
    per_family_results, oof = _fake_inputs()
    payload = build_metrics_payload(per_family_results, oof)
    summary = payload["by_family"]["logistic_regression"]["fold_mcc_summary"]
    assert summary["per_fold"], "per_fold_mcc no puede quedar vacío"
    assert len(summary["per_fold"]) == 3


def test_global_mcc_is_recomputed_from_oof_and_is_not_the_mean_of_folds():
    per_family_results, oof = _fake_inputs()
    payload = build_metrics_payload(per_family_results, oof)
    family = payload["by_family"]["logistic_regression"]
    fold_values = [
        f["mcc"]["value"] for f in family["per_outer_fold"] if f["mcc"]["value"] is not None
    ]
    mean_of_folds = sum(fold_values) / len(fold_values)
    from experiment_runner.controlled_daily_v4.metrics import mcc_strict

    expected = mcc_strict(oof["logistic_regression"].y_true, oof["logistic_regression"].y_pred)
    assert family["global"]["mcc"]["value"] == pytest.approx(expected)
    if not math.isclose(mean_of_folds, expected, abs_tol=1e-12):
        assert family["global"]["mcc"]["value"] != pytest.approx(mean_of_folds)


def test_written_artifacts_are_all_strict_json_even_with_undefined_metrics(tmp_path):
    per_family_results, oof = _fake_inputs()

    class _Selection:
        outcome = "NO_VALID_SELECTION"
        global_mcc_by_family = {"logistic_regression": float("nan")}
        pairwise_intervals = {("logistic_regression", "random_forest"): (float("nan"),) * 2}
        equivalence_set: list[str] = []
        stable_winner = None
        selected_family = None
        selection_reason = "oof_concatenado_monoclase_o_mcc_indefinido"
        bootstrap_diagnostics: dict = {}

    written = write_stage_a_artifacts(
        tmp_path / "out",
        depth_column="soil_moisture_0_to_7cm",
        resolved_config={"stage": "A"},
        provenance_report={"era5_sha256": "abc"},
        environment_info=capture_environment(),
        input_hashes={"era5_sha256": "abc"},
        outer_fold_boundaries=[{"outer_fold_index": 1}],
        per_family_outer_results=per_family_results,
        oof_by_family=oof,
        selection_result=_Selection(),
        frozen_single_family=None,
        frozen_soft_voting_bases=None,
        final_p20_train=float("nan"),
    )

    assert "metrics" in written
    for name, path in written.items():
        if path.suffix == ".json":
            _assert_strict_json(path.read_text(encoding="utf-8"))
