# Informe exacto del verificador de evidencia — snapshot `b9fefbf`

Rol nominal: `evidence_checker` (`.codex/agents/evidence_checker.toml`,
`gpt-5.6-luna`, esfuerzo `low`, `sandbox_mode = read-only`).
Sustituto efectivo: subagente `general-purpose` de Claude Code, modelo
solicitado `opus`, contexto separado, solo lectura **instruida** (el harness no
coloca el proceso en un sandbox). Sustitución declarada en
`session-identity.json`.

El texto que sigue es la respuesta del lector, conservada sin alterar su
veredicto ni su redacción sustantiva. El orquestador no la reescribe.

---

# EVIDENCE CHECKER — MECHANICAL REPORT
**Snapshot:** `b9fefbf36037ca259f4b17b68642d330bc489d39` · repo `/home/gus/work/AAI_Hydric_Stress_scientific_closure`
No file was modified; no git write command was run.

## ITEM 1 — Git identity — **VERIFIED**

| Check | Command | Result |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `b9fefbf36037ca259f4b17b68642d330bc489d39` |
| Branch | `git rev-parse --abbrev-ref HEAD` | `feat/scientific-closure` |
| Upstream | `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'` | `origin/feat/scientific-closure` (exit 0) |
| Working tree | `git status --porcelain=v1 --untracked-files=all` | **empty output**, exit 0 → clean |
| HEAD == origin | `git rev-parse origin/feat/scientific-closure` | `b9fefbf360…` → **identical** |
| Whitespace | `git diff --check` | no output, **exit 0** |

`git for-each-ref --points-at HEAD` → `refs/heads/feat/scientific-closure`, `refs/remotes/origin/feat/scientific-closure`.

## ITEM 2 — Declared sha256 vs. recomputed — **VERIFIED, 2 flags**

Method: recursive scan of all `*.json`/`*.jsonl` under `openspec/scientific-closure/**` (44 files contain `sha256`), extracting every object carrying both a path-like key and a 64-hex `*sha256*` key; each recomputed with `hashlib.sha256` streaming the file on disk.

**Raw run: 139 (path, sha256) assertions → 106 MATCH / 22 MISMATCH / 11 MISSING.**

Every non-MATCH was then adjudicated against the declaring document's own stated root/semantics:

**`evidence-manifest.json` specifically — 31/31 MATCH, zero exceptions.** 29 `governance_evidence` + 2 `scientific_inputs`, all recomputed byte-for-byte. Declared `count.governance_files: 29` equals the list length.

Adjudication of the 33 non-MATCH:

| Cause | Count | Resolution |
|---|---|---|
| `transfer-manifest.json` relative paths resolved against its own `primary_root`/`backup_root` | 6 | **MATCH at both roots** (12 hashes computed, all equal) |
| `checker-remediation-linux.json` declares hashes of its stated `backup` `/mnt/c/Repo/AAI_Hydric_Stress_scientific_closure` | 3 | **MATCH at backup root** (incl. `bf39fff5…`, `ee40b2dd…`, `5f32a4bf…`) |
| CRLF-rendering keys (`crlf_transformation_sha256`, `sha256_crlf_rendering`, `historical_expected_sha256`) in objects whose `git_blob_sha256`/`lf_sha256` **do** match | 8 | Resolver artifact; LF hashes MATCH. The CRLF value `d47cdb8c…` is explicitly documented as a line-ending rendering, not a disk hash |
| `constraints_sha256_lf` paired with the venv *directory* path in `execution-manifest.json` | 1 | Resolver artifact; `aa05b7b1…` MATCHES `docker/experiment-v4/constraints.txt` |
| `snapshot-v1-superseded.json` — by name/content a record of the superseded v1 state | 10 | Historical record; the superseding `implementation-snapshot.json` (v1.1) declares 13 entries, **all 13 MATCH** |
| `registration-validation.json` `snapshot[11]` `b939730a…` | 1 | **Reproduced at commit `fe55bef9`** (pre-commit snapshot of `tests/test_scientific_closure_governance.py`) |
| `validation-read-only-probe.tmp` (never committed; absent from Linux repo) | 4 | MATCH at backup root; `git log --all` confirms never tracked |
| **Flagged — see D-2** | 1 | `implementation-snapshot.json` `supersedes.initial_snapshot_sha256` |
| **Flagged — see D-3** | 1 | `model-catalog.json` external cache |

## ITEM 3 — `src/`, `docker/`, `pyproject.toml` vs `214735e4` — **VERIFIED**

```
git diff --stat 214735e4 HEAD -- src/           → no output, exit 0
git diff --stat 214735e4 HEAD -- docker/        → no output, exit 0
git diff --stat 214735e4 HEAD -- pyproject.toml → no output, exit 0
```
Stronger confirmation via tree/blob object identity:

| Path | `214735e4` | `HEAD` |
|---|---|---|
| `src` (tree) | `030805745797ba994ba5c6955b6348cd2540359b` | **identical** |
| `docker` (tree) | `84230fc453c809c0e4dcb7dc4f1f042862580434` | **identical** |
| `pyproject.toml` (blob) | `da4a2e917b9934c369867dee27e7343835013f58` | **identical** |

Byte-identity claim **holds**.

## ITEM 4 — Ancestry of `214735e4` — **VERIFIED**

```
git merge-base --is-ancestor 214735e4 HEAD                      → exit 0  (IS ancestor)
git merge-base --is-ancestor 214735e4 refs/remotes/origin/main  → exit 1  (NOT ancestor)
```
`origin/main` = `9fcbfd9f4dd4860a07f7e99d5b16d849ac81c4af`. Commit `214735e4` = *"docs: align v4 protocol provenance and preexecution runbook"*, Fri Sep 18 01:26:32 2026 -0300. Both claims **confirmed**.

## ITEM 5 — `sc-01` .. `sc-10` evidence inventory — **VERIFIED, fully consistent**

36 files total. Only `sc-01-evidence-scope` carries evidence artefacts (9 files incl. `verification-final.json`); `sc-02`..`sc-10` contain only `proposal.md`, `tasks.md`, `specs/scientific-closure/spec.md` — **every task box is `[ ]` unchecked**, each file stating *"Todas pendientes; la especificación no acredita ejecución."*

Cross-check of all 25 `requirements.json` expected artefacts (identical to the traceability.md *Evidencia esperada* column, verified row by row):

**PRESENT (12):** `session-identity.json`, `preservation.json`, `inventory.json`, `claims-assessment.json` (in `sc-01/`); `authorizations.json`, `agent-capabilities.json`, `workflow-events.jsonl`, `execution-manifest.json`, `recovery-rehearsal.json`, `checkpoints.json`, `structural-validation.json` (in `readiness-resolution-*/`); `provenance-assessment.json` (in `input-migration-*/`).

**ABSENT (13):** `audit.json`, `temporal-contract-check.json`, `A/gate-review.json`, `B/gate-review.json`, `B/custody-review.json`, `C/holdout-review.json`, `statistical-review.json`, `claim-evidence-review.json`, `scientific-closure-audit.json`, `auxiliary/{R,H,N,S}/review.json`. No `auxiliary/`, `A/`, `B/`, `C/` directory exists anywhere in the repo.

This partition matches `traceability.md` **exactly** (each absent artefact declared BLOCKED or NOT_APPLICABLE with *"no existe"*) and `changes.json` (`sc-01` PASS; `sc-02`..`sc-10` BLOCKED; `sc-07`..`sc-10` `conditional: true`). **No over-claim detected.**

## ITEM 6 — Stage A/B/C outputs — **VERIFIED ABSENT**

Patterns searched (`frozen_config.json`, `decision.json`, `holdout_ledger*`, `*ledger*`, `oof*`, `predictions*`, `metrics*.json`, `gate-review*`, `stage_[abc]*output*`) across the repo and all three external roots.

- **Repo:** zero hits except *source code and tests* — `src/experiment_runner/controlled_daily_v4/holdout_ledger.py`, `tests/test_controlled_daily_v4_holdout_ledger.py` (+ `__pycache__`). No output artefact of any kind.
- **`/home/gus/scientific-closure-inputs`:** zero hits.
- **`/home/gus/scientific-closure-backup`:** zero hits.
- **`/home/gus/scientific-closure-runtime`:** hits only under a clean-checkout log copy (same source files) and the rehearsal tree.

```
/home/gus/scientific-closure-runtime/ledger/     → EMPTY (only . and ..)
/home/gus/scientific-closure-runtime/evidence/   → EMPTY (only . and ..)
```
Both created Sep 20 04:21. `holdout.sqlite` does **not** exist.

The only non-empty files anywhere are the backup-rehearsal fixtures (`backups/rehearsal-20260920/{source,backup,restored}/`), and their contents are **self-declaredly synthetic**:
- `fixture_metrics.json` → `{"fixture": true, "scientific": false, "mcc": {"value": null, "status": "undefined", "undefined_reason": "fixture_has_no_run"}}`
- `fixture_predictions.csv` → one row, dated `2000-01-01`/`2000-01-04`, `y_true=0, y_prob=0.1`
- `fixture_holdout.sqlite` → single table `attempts`, one row: `('fixture/protocol/site/depth/2024-2025', 'RESERVED')`

**No real (non-fixture) result exists anywhere reachable.** No holdout value was read.

## ITEM 7 — Input datasets — **VERIFIED, all MATCH**

| File | sha256 | Size | Lines |
|---|---|---|---|
| `pergamino_era5land_soil_hourly_2015_2025.csv` | `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` | 3 954 003 | 96 436 (96 432 data rows) |
| `pergamino_nasa_power_daily_2015_2025.csv` | `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` | 127 568 | 4 031 (4 018 data rows) |

Declared-hash comparison — **MATCH in all five declaring locations**:

| Declaring document | ERA5 | NASA POWER |
|---|---|---|
| `transfer-manifest.json` (primary + backup roots) | MATCH | MATCH |
| `source-inventory.json` (against `/mnt/c` source) | MATCH | MATCH |
| `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` (L124, L185; sizes also match) | MATCH | MATCH |
| `evidence-manifest.json` `scientific_inputs` | MATCH | MATCH |
| `execution-manifest.json` `inputs` | MATCH | MATCH |

Primary and backup copies are byte-identical to each other.

**Date range only** (no values read): ERA5 column 1 is `time`, header at line 4 → first `2015-01-01T00:00`, last `2025-12-31T23:00`. NASA POWER header ends line 12, columns `YEAR,DOY,...` → first `2015,1`, last `2025,365`.

## ITEM 8 — Environment vs `constraints.txt` — **VERIFIED, 10/10 MATCH**

`Python 3.11.16` (`3.11.16 (main, Sep 1 2026, 14:18:37) [Clang 22.1.3]`).

| Package | venv-v4 | constraints.txt | |
|---|---|---|---|
| numpy | 2.4.6 | 2.4.6 | MATCH |
| scipy | 1.17.1 | 1.17.1 | MATCH |
| pandas | 3.0.5 | 3.0.5 | MATCH |
| pyarrow | 25.0.1 | 25.0.1 | MATCH |
| scikit-learn | 1.9.0 | 1.9.0 | MATCH |
| joblib | 1.6.0 | 1.6.0 | MATCH |
| threadpoolctl | 3.6.0 | 3.6.0 | MATCH |
| pytest | 9.1.1 | 9.1.1 | MATCH |
| ruff | 0.16.6 | 0.16.6 | MATCH |
| black | 26.5.1 | 26.5.1 | MATCH |

All 13 transitive pins in `constraints.txt` also match the venv freeze. The `runtime-environment.json` record reproduces exactly (23 packages), and its `package_set_comparison` correctly qualifies the 26-vs-23 delta as `pip`/`setuptools`/`wheel` only — I confirmed that against the historic `pip-freeze.txt`. The record explicitly and repeatedly non-claims equivalence with the historic image `sha256:55bc923e…`; no image exists.

## ITEM 9 — Verification commands — **VERIFIED, all exit 0**

```
$ PYTHONPATH=src …/venv-v4/bin/python scripts/check_scientific_closure.py
scientific-closure checker: PASS (estructura; runtime no verificado)
EXIT=0

$ …/venv-v4/bin/ruff check scripts/check_scientific_closure.py tests/test_scientific_closure_governance.py \
    tests/test_scientific_closure_checker.py tests/test_readonly_role_sandbox.py
All checks passed!
EXIT=0

$ …/venv-v4/bin/black --check <same four files>
All done!
4 files would be left unchanged.
EXIT=0
```
Full pytest suite was **not** run, per instruction.

## DISCREPANCIES FLAGGED

**D-1 — `checkpoints.json` self-reference count is off by one at the audited snapshot. (MATERIAL)**
The file declares `head_at_capture: ccd3a9c5…`, `commits_in_session_at_capture: 8`, and `self_reference_limit: "…It is exactly ONE commit, the last of the session… 8 commits listed, one not listed."`
Mechanically at HEAD: `git rev-list --count dc0d3f5..HEAD` = **10**; the file lists **8** (`c23b8c3, cc53346, 95f0058, 010a45e, a881207, 023a942, 619c8ef, ccd3a9c`). **Two** commits are unlisted — `8e31f78` and `b9fefbf` — not one. The file was last written *in* `8e31f78`, where the claim was true; commit `b9fefbf` followed and invalidated it. The file itself records that this exact defect class was previously raised as audit finding **A-04**, and the current wording was the correction for it. `traceability.md` SC-GOV-019 repeats the "salvo el commit final" (singular) wording.
By contrast `evidence-manifest.json` handles the same problem correctly: it declares `commit: 8e31f78` + `published_in_commit: the commit immediately following`, and `8e31f78`'s child is exactly `b9fefbf` = HEAD. Consistent.

**D-2 — `implementation-snapshot.json` `supersedes.initial_snapshot_sha256` is not reproducible. (NOT_VERIFIABLE)**
Declared `39f3d55ee0f161fed91e60374bb6aeca241257130fd932a26885fdcaa6c74226` for `snapshot-v1-superseded.json`. On disk that file hashes `0e13da72…` (which the same document's `files[]` list declares, and which MATCHES). An exhaustive scan of the entire git object store (`git cat-file --batch-all-objects`, every blob re-hashed) found **no object** with hash `39f3d55e…`; the file was committed exactly once (`5e10d6a`) already as `0e13da72…`. The declared pre-supersession hash is **self-attested only** and cannot be independently verified from this repository.

**D-3 — `model-catalog.json` external cache hash has drifted. (LOW; derived content intact)**
Declared `object.sha256 = 9bc78759…`, `size 228511`, `mtime_observed 2026-09-19 08:08:01`. Actual `/home/gus/.codex/models_cache.json` now hashes `fa460554c51191e5f9cf14fee30e5b6530e529630a533742bb56e29f533e3629`, same size `228511`, mtime `2026-09-20 03:43:42`. The file is a mutable cache outside repository custody. I re-ran the document's own recorded extraction command against the current file: the derived `stdout_sha256` reproduces **exactly** as `3c382e5663ed5754be9863982fce330d223489c818fcc0acc2248bb87c37e2ec`. The substantive recorded content is therefore intact; only the whole-file custody hash no longer holds.

**D-4 — Notes, not discrepancies.** `evidence-manifest.json` declares `tree_clean: false` (generation-time state, disclosed in `self_reference_limit`) while the audited snapshot is clean. `traceability.md` L74/L76 name `dc0d3f5…` as *"el HEAD vigente"*, now 10 commits behind `b9fefbf` (`dc0d3f5` confirmed an ancestor).

## SUMMARY TABLE

| Item | Subject | Status |
|---|---|---|
| 1 | Git identity, clean tree, HEAD==origin, diff --check | **VERIFIED** |
| 2 | Declared sha256 across `openspec/scientific-closure/**` (139 assertions) | **VERIFIED** (137 resolved MATCH) + D-2, D-3 |
| 2a | `evidence-manifest.json` specifically (31 entries) | **VERIFIED** — 31/31 MATCH |
| 3 | `src/`, `docker/`, `pyproject.toml` ≡ `214735e4` | **VERIFIED** |
| 4 | `214735e4` ancestor of HEAD, not of `origin/main` | **VERIFIED** |
| 5 | `sc-01`..`sc-10` artefacts vs traceability + requirements | **VERIFIED** (12 present / 13 absent, exact match) |
| 6 | No stage A/B/C output reachable | **VERIFIED ABSENT** (fixtures only) |
| 7 | Pergamino CSV hashes, sizes, line counts, date ranges | **VERIFIED** (MATCH in 5/5 declarations) |
| 8 | venv-v4 vs `constraints.txt` (10 packages) | **VERIFIED** — 10/10 MATCH |
| 9 | checker / ruff / black | **VERIFIED** — 3x exit 0 |

**Counts: VERIFIED 10 · DISCREPANCY 2 (D-1 material, D-3 low) · NOT_VERIFIABLE 1 (D-2) · NOTES 2 (D-4).**

The single item requiring an implementer decision is **D-1**: at snapshot `b9fefbf`, `checkpoints.json` asserts one unlisted commit where two exist, and `traceability.md` SC-GOV-019 carries the same singular wording. I make no judgement on its significance.
