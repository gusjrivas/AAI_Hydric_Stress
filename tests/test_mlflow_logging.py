import mlflow
import pandas as pd

from experiment_runner.mlflow_logging import log_configuration_results


def test_log_configuration_results_creates_parent_and_nested_child_runs(tmp_path):
    tracking_uri = f"file:///{tmp_path.as_posix()}/mlruns"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("test-experiment")

    results = pd.DataFrame(
        {
            "seed": [1, 2],
            "precision": [0.6, 0.7],
            "recall": [0.5, 0.6],
            "f1": [0.55, 0.65],
            "roc_auc": [0.6, 0.65],
        }
    )
    config_params = {"include_anomaly_detection": True, "include_synthetic": False}

    parent_run_id = log_configuration_results(
        config_name="base", config_params=config_params, results=results
    )

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    parent_run = client.get_run(parent_run_id)

    assert parent_run.data.params["config_name"] == "base"
    assert parent_run.data.params["include_anomaly_detection"] == "True"
    assert parent_run.data.metrics["f1_mean"] == results["f1"].mean()

    child_runs = client.search_runs(
        experiment_ids=[parent_run.info.experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
    )
    assert len(child_runs) == 2
    child_seeds = sorted(int(run.data.params["seed"]) for run in child_runs)
    assert child_seeds == [1, 2]


def test_log_configuration_results_logs_any_metric_column_present_not_a_fixed_list(tmp_path):
    tracking_uri = f"file:///{tmp_path.as_posix()}/mlruns"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("test-experiment-extra-metrics")

    results = pd.DataFrame(
        {
            "seed": [1, 2],
            "f1": [0.55, 0.65],
            "mcc": [0.10, 0.20],
            "always_stress_f1": [0.30, 0.30],
        }
    )

    parent_run_id = log_configuration_results(config_name="base", config_params={}, results=results)

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    parent_run = client.get_run(parent_run_id)

    assert parent_run.data.metrics["mcc_mean"] == results["mcc"].mean()
    assert parent_run.data.metrics["always_stress_f1_mean"] == results["always_stress_f1"].mean()


def test_logged_predictions_reproduce_metrics(tmp_path):
    import json
    from pathlib import Path

    from predictive_modeling.evaluation import evaluate_classifier

    mlflow.set_tracking_uri(f"file:///{tmp_path.as_posix()}/mlruns")
    mlflow.set_experiment("predictions-roundtrip")
    predictions = pd.DataFrame(
        {"y_true": [0, 1, 1], "y_pred": [0, 1, 0], "y_proba": [0.1, 0.8, 0.4]}
    )
    metrics = evaluate_classifier(predictions.y_true, predictions.y_pred, predictions.y_proba)
    results = pd.DataFrame([{"seed": 7, **metrics}])
    results.attrs["artifacts"] = [
        {"seed": 7, "contract": {"model_features": ["x"]}, "predictions": predictions}
    ]
    parent = log_configuration_results("base", {"pipeline_version": "controlled_daily_v3"}, results)
    client = mlflow.MlflowClient()
    run = client.get_run(parent)
    child = client.search_runs([run.info.experiment_id], f"tags.mlflow.parentRunId = '{parent}'")[0]
    path = client.download_artifacts(child.info.run_id, "predictions.json")
    restored = pd.DataFrame(json.loads(Path(path).read_text())["rows"])
    recalculated = evaluate_classifier(restored.y_true, restored.y_pred, restored.y_proba)
    for name, value in recalculated.items():
        assert value == child.data.metrics[name]
