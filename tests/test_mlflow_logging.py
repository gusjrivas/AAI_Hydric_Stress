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
