"""Pruebas del constructor del paquete de reproducción histórica, con un
cliente MLflow simulado mínimo (sin red, sin servidor real) — el foco es
verificar que la restricción de admisión se aplica también aquí, antes de
tocar disco o red para descargar artefactos."""

import hashlib
from types import SimpleNamespace

import pytest

import scripts.build_replay_package as build_replay_package
from historical_replay.admission_policy import ADMITTED_CANDIDATES, AdmissionPolicyError

REAL = ADMITTED_CANDIDATES[0]


class _FakeRun:
    def __init__(self, *, run_id, experiment_id, status, run_name, params, tags=None, metrics=None):
        self.info = SimpleNamespace(
            run_id=run_id, experiment_id=experiment_id, status=status, run_name=run_name
        )
        self.data = SimpleNamespace(params=params, tags=tags or {}, metrics=metrics or {})


class _FakeMlflowClient:
    def __init__(self, runs, experiment_name="fake-experiment"):
        self._runs = runs
        self._experiment_name = experiment_name
        self.download_calls = []

    def get_run(self, run_id):
        return self._runs[run_id]

    def get_experiment(self, experiment_id):
        return SimpleNamespace(name=self._experiment_name)

    def download_artifacts(self, run_id, path):
        self.download_calls.append((run_id, path))
        raise AssertionError(
            "No debería intentar descargar artefactos: la admisión debe "
            "rechazarse antes de llegar acá."
        )


def _fake_child_and_parent(
    *, run_id_child, run_id_parent, dataset_sha256, commit_sha, config_name="base", seed="4"
):
    child = _FakeRun(
        run_id=run_id_child,
        experiment_id=REAL.experiment_id,
        status="FINISHED",
        run_name="fake-child",
        params={"config_name": config_name, "seed": seed},
        tags={"mlflow.parentRunId": run_id_parent},
    )
    parent = _FakeRun(
        run_id=run_id_parent,
        experiment_id=REAL.experiment_id,
        status="FINISHED",
        run_name="fake-parent",
        params={"commit_sha": commit_sha, "dataset_sha256": dataset_sha256},
    )
    return child, parent


def test_build_package_refuses_before_any_download_for_unadmitted_run(tmp_path, monkeypatch):
    dataset_path = tmp_path / "dataset.parquet"
    dataset_path.write_bytes(b"contenido de prueba, no el dataset real")
    fake_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    run_id_child = "run-jamas-revisado"
    run_id_parent = "run-padre-jamas-revisado"
    child, parent = _fake_child_and_parent(
        run_id_child=run_id_child,
        run_id_parent=run_id_parent,
        dataset_sha256=fake_hash,
        commit_sha="commit-no-revisado",
    )
    fake_client = _FakeMlflowClient({run_id_child: child, run_id_parent: parent})
    monkeypatch.setattr(build_replay_package.mlflow, "MlflowClient", lambda: fake_client)

    output_dir = tmp_path / "package_out"

    with pytest.raises(AdmissionPolicyError):
        build_replay_package.build_package(
            experiment_id=REAL.experiment_id,
            run_id_child=run_id_child,
            dataset_path=dataset_path,
            output_dir=output_dir,
        )

    assert not output_dir.exists()
    assert fake_client.download_calls == []


def test_build_package_refuses_when_discovered_commit_disagrees_with_policy(tmp_path, monkeypatch):
    # Mismo (experiment_id, run_id_child) que el candidato admitido, pero el
    # commit_sha realmente descubierto en el run padre no coincide con la
    # política — no debe aceptarse por coincidir solo en el identificador.
    dataset_path = tmp_path / "dataset.parquet"
    dataset_path.write_bytes(b"contenido de prueba")
    fake_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    child, parent = _fake_child_and_parent(
        run_id_child=REAL.run_id_child,
        run_id_parent=REAL.run_id_parent,
        dataset_sha256=fake_hash,
        commit_sha="commit-distinto-del-verificado",
        config_name=REAL.config_name,
        seed=str(REAL.seed),
    )
    fake_client = _FakeMlflowClient({REAL.run_id_child: child, REAL.run_id_parent: parent})
    monkeypatch.setattr(build_replay_package.mlflow, "MlflowClient", lambda: fake_client)

    output_dir = tmp_path / "package_out"

    with pytest.raises(AdmissionPolicyError):
        build_replay_package.build_package(
            experiment_id=REAL.experiment_id,
            run_id_child=REAL.run_id_child,
            dataset_path=dataset_path,
            output_dir=output_dir,
        )

    assert not output_dir.exists()
