"""Admission policy for historical-replay candidates (spec `historical-replay`,
RH-11), maintained OUTSIDE any package — in versioned project code, not in
data a package carries about itself.

A manifest's own `admission_contract` block may *describe* accreditation
(who reviewed it, when, why); it never *grants* it. Granting is decided
here, by comparing a candidate's actual field values against this fixed
policy — never by reading a `verified_candidates` list back out of the same
manifest being validated, which a self-declared candidate could always
satisfy trivially by including itself.

Deliberately not a generic or extensible model registry: a single hardcoded
tuple, limited to candidates that received a manual review equivalent to
the one already done for `base-seed4`
(`paso1-revision-dirigida.md` §2.2 — confirmed fixed model, no folds, by
direct reading of `src/experiment_runner/runner.py` and
`src/architecture_integration/pipeline.py` at the commit that produced the
run). Admitting another candidate means editing this file after an
equivalent review, not adding a row to a data-driven registry.
"""

from __future__ import annotations

from dataclasses import dataclass


class AdmissionPolicyError(ValueError):
    """A candidate does not match this fixed, externally maintained
    admission policy — matching only `(experiment_id, run_id_child)` is not
    enough; every declared field must agree, and an id match alone with a
    field mismatch is reported as such, not silently accepted."""


@dataclass(frozen=True)
class AdmittedCandidate:
    experiment_id: str
    run_id_child: str
    run_id_parent: str
    config_name: str
    seed: int
    commit_sha: str
    dataset_sha256: str
    model_identity_verified_by: str
    note: str


ADMITTED_CANDIDATES: tuple[AdmittedCandidate, ...] = (
    AdmittedCandidate(
        experiment_id="4",
        run_id_child="1157696b7bb941e394c5af530c762b07",
        run_id_parent="6d516bb9f778450f8fbe2e5492818e57",
        config_name="base",
        seed=4,
        commit_sha="2a40ee68c52d2eb5e2040a36b1029f756f9c048a",
        dataset_sha256="121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e",
        model_identity_verified_by=("code_review_commit_2a40ee68c52d2eb5e2040a36b1029f756f9c048a"),
        note=(
            "Modelo fijo confirmado por lectura directa de "
            "src/experiment_runner/runner.py y "
            "src/architecture_integration/pipeline.py en el commit de "
            "ejecucion (paso1-revision-dirigida.md SS2.2); no es una "
            "deteccion automatica generica."
        ),
    ),
)


def find_admitted_candidate(*, experiment_id: str, run_id_child: str) -> AdmittedCandidate | None:
    for candidate in ADMITTED_CANDIDATES:
        if candidate.experiment_id == experiment_id and candidate.run_id_child == run_id_child:
            return candidate
    return None


def verify_admitted(
    *,
    experiment_id: str,
    run_id_child: str,
    run_id_parent: str,
    config_name: str,
    seed: int,
    commit_sha: str,
    dataset_sha256: str,
) -> AdmittedCandidate:
    """Raise `AdmissionPolicyError` unless every field matches the fixed
    policy exactly; return the matching `AdmittedCandidate` otherwise."""
    admitted = find_admitted_candidate(experiment_id=experiment_id, run_id_child=run_id_child)
    if admitted is None:
        raise AdmissionPolicyError(
            f"Candidato no admitido: (experiment_id={experiment_id!r}, "
            f"run_id_child={run_id_child!r}) no figura en la política de "
            "admisión mantenida fuera del paquete (src/historical_replay/admission_policy.py)."
        )
    mismatches = [
        f"{field}: política={expected!r} vs. candidato={actual!r}"
        for field, expected, actual in (
            ("run_id_parent", admitted.run_id_parent, run_id_parent),
            ("config_name", admitted.config_name, config_name),
            ("seed", admitted.seed, seed),
            ("commit_sha", admitted.commit_sha, commit_sha),
            ("dataset_sha256", admitted.dataset_sha256, dataset_sha256),
        )
        if expected != actual
    ]
    if mismatches:
        raise AdmissionPolicyError(
            "El candidato coincide en (experiment_id, run_id_child) con una "
            "entrada admitida, pero difiere de la política en: " + "; ".join(mismatches)
        )
    return admitted
