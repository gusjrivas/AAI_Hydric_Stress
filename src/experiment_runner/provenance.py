"""Small, content-based experiment manifest, without another infrastructure service."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import subprocess


def experiment_provenance(dataset_path, *, pipeline_version="unknown"):
    def git(*args):
        try:
            return subprocess.check_output(
                ["git", *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"

    return {
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "commit_sha": (
            git("rev-parse", "HEAD")
            if git("rev-parse", "HEAD") != "unknown"
            else os.getenv("TRAINING_COMMIT_SHA", "unknown")
        ),
        "working_tree_status": (
            git("status", "--porcelain", "--untracked-files=no")
            if git("rev-parse", "HEAD") != "unknown"
            else os.getenv("TRAINING_WORKING_TREE_STATUS", "unknown")
        ),
        "pipeline_version": pipeline_version,
        "dependency_versions": {
            name: importlib.metadata.version(name)
            for name in ["pandas", "numpy", "scikit-learn", "mlflow", "pyarrow"]
        },
    }
