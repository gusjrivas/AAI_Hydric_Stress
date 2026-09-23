import pytest

from historical_replay.admission_policy import (
    ADMITTED_CANDIDATES,
    AdmissionPolicyError,
    find_admitted_candidate,
    verify_admitted,
)

REAL = ADMITTED_CANDIDATES[0]


def test_finds_the_real_admitted_candidate():
    found = find_admitted_candidate(
        experiment_id=REAL.experiment_id, run_id_child=REAL.run_id_child
    )

    assert found == REAL


def test_unknown_experiment_or_run_is_not_found():
    assert find_admitted_candidate(experiment_id="99", run_id_child="unknown") is None


def test_verify_admitted_accepts_exact_match():
    admitted = verify_admitted(
        experiment_id=REAL.experiment_id,
        run_id_child=REAL.run_id_child,
        run_id_parent=REAL.run_id_parent,
        config_name=REAL.config_name,
        seed=REAL.seed,
        commit_sha=REAL.commit_sha,
        dataset_sha256=REAL.dataset_sha256,
    )

    assert admitted == REAL


def test_verify_admitted_rejects_unknown_ids():
    with pytest.raises(AdmissionPolicyError):
        verify_admitted(
            experiment_id="4",
            run_id_child="not-the-real-run",
            run_id_parent=REAL.run_id_parent,
            config_name=REAL.config_name,
            seed=REAL.seed,
            commit_sha=REAL.commit_sha,
            dataset_sha256=REAL.dataset_sha256,
        )


def test_verify_admitted_rejects_id_match_with_field_mismatch():
    # Mismo (experiment_id, run_id_child) que el admitido, pero con otro
    # dataset_sha256: no basta con coincidir en el identificador.
    with pytest.raises(AdmissionPolicyError):
        verify_admitted(
            experiment_id=REAL.experiment_id,
            run_id_child=REAL.run_id_child,
            run_id_parent=REAL.run_id_parent,
            config_name=REAL.config_name,
            seed=REAL.seed,
            commit_sha=REAL.commit_sha,
            dataset_sha256="0" * 64,
        )
