"""Export a named MLflow HU7 experiment to deterministic JSON and Markdown.

This script only reads MLflow; it never runs an experiment or overwrites an
existing artifact unless ``--overwrite`` is explicitly supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import mlflow


def _unknown_or(params: dict, *names: str):
    for name in names:
        if name in params:
            return params[name]
    return "unknown"


def _read_artifact(client, run_id: str, name: str):
    try:
        path = client.download_artifacts(run_id, name)
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, mlflow.exceptions.MlflowException):
        return "unknown"


def _git_state() -> tuple[str, str]:
    def run(*args):
        try:
            return subprocess.check_output(
                ["git", *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"

    return run("rev-parse", "HEAD"), run("status", "--porcelain", "--untracked-files=no")


def _dataset_sha(dataset_name: str) -> str:
    candidates = [Path("data") / f"{dataset_name}.parquet"]
    for path in candidates:
        if path.exists():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    return "unknown"


def export_experiment(
    experiment_name: str,
    *,
    tracking_uri: str | None = None,
    exported_at: str | None = None,
):
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"MLflow experiment not found: {experiment_name}")
    runs = client.search_runs(
        [experiment.experiment_id], order_by=["attribute.start_time ASC"], max_results=10000
    )
    parents = [run for run in runs if not run.data.tags.get("mlflow.parentRunId")]
    exported_runs = []
    for parent in sorted(parents, key=lambda run: (run.info.run_id, run.info.start_time or 0)):
        params = dict(parent.data.params)
        children = [
            run
            for run in runs
            if run.data.tags.get("mlflow.parentRunId") == parent.info.run_id
        ]
        children.sort(key=lambda run: (run.data.params.get("seed", "unknown"), run.info.run_id))
        exported_children = []
        for child in children:
            child_params = dict(child.data.params)
            exported_children.append(
                {
                    "run_id": child.info.run_id,
                    "name": child.info.run_name,
                    "params": child_params,
                    "metrics": dict(child.data.metrics),
                    "effective_configuration": _read_artifact(
                        client, child.info.run_id, "effective_configuration.json"
                    ),
                    "predictions": _read_artifact(client, child.info.run_id, "predictions.json"),
                }
            )
        exported_runs.append(
            {
                "run_id": parent.info.run_id,
                "name": parent.info.run_name,
                "params": params,
                "metrics": dict(parent.data.metrics),
                "configuration": _read_artifact(client, parent.info.run_id, "configuration.json"),
                "children": exported_children,
            }
        )
    first_params = exported_runs[0]["params"] if exported_runs else {}
    training_commit = _unknown_or(first_params, "commit_sha", "training_commit_sha")
    working_tree = _unknown_or(first_params, "working_tree_status")
    dataset_name = _unknown_or(first_params, "dataset")
    payload = {
        "schema_version": 1,
        "experiment_name": experiment_name,
        "pipeline_version": _unknown_or(first_params, "pipeline_version"),
        "dataset_name": dataset_name,
        "dataset_sha256": _unknown_or(first_params, "dataset_sha256")
        if first_params.get("dataset_sha256")
        else _dataset_sha(dataset_name) if dataset_name != "unknown" else "unknown",
        "training_commit_sha": training_commit,
        "working_tree_status": working_tree,
        "exported_at": exported_at or datetime.now(timezone.utc).isoformat(),
        "runs": exported_runs,
    }
    return payload


def render_table(payload: dict) -> str:
    rows = []
    for run in payload["runs"]:
        metrics = run["metrics"]
        rows.append(
            "| {name} | {f1:.4f} | {std:.4f} | {mcc:.4f} | {ap:.4f} | {id} |".format(
                name=run["name"],
                f1=metrics.get("f1_mean", float("nan")),
                std=metrics.get("f1_std", float("nan")),
                mcc=metrics.get("mcc_mean", float("nan")),
                ap=metrics.get("average_precision_mean", float("nan")),
                id=run["run_id"],
            )
        )
    header = (
        "| Configuracion | F1 media | F1 desvio | MCC media | AP media | Run ID |\n"
        "|---|---:|---:|---:|---:|---|\n"
    )
    return header + "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/research/reference-v3-results.json")
    )
    parser.add_argument(
        "--table-output", type=Path, default=Path("docs/research/reference-v3-table.md")
    )
    parser.add_argument("--tracking-uri")
    parser.add_argument("--exported-at")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not args.overwrite and (args.output.exists() or args.table_output.exists()):
        raise FileExistsError("Output exists; use --overwrite explicitly.")
    payload = export_experiment(
        args.experiment, tracking_uri=args.tracking_uri, exported_at=args.exported_at
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.table_output.write_text(render_table(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
