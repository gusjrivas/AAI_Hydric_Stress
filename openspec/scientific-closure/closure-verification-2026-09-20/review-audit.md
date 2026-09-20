# Informe exacto del auditor independiente — snapshot `5b40a55`

Rol nominal: `scientific_auditor` (`.codex/agents/scientific_auditor.toml`,
`gpt-5.6-sol`, esfuerzo `xhigh`, `sandbox_mode = read-only`).
Sustituto efectivo: subagente `general-purpose` de Claude Code, modelo
solicitado `opus`, contexto separado, solo lectura **instruida** (el harness no
coloca el proceso en un sandbox). Sustitución declarada en
`session-identity.json`.

El texto que sigue es la respuesta del auditor, conservada sin alterar su
veredicto ni su redacción sustantiva. El orquestador no la reescribe. La
resolución de cada hallazgo está en `findings-resolution.json`.

---

# INDEPENDENT SCIENTIFIC AUDIT — snapshot `5b40a55`

**Commit audited:** `5b40a55ef62f19cfa9125aa29146e53976661692`
**Branch:** `feat/scientific-closure` · **Upstream:** `origin/feat/scientific-closure`
**Scope:** the PREPARATION and its documentary record. No scientific campaign exists, so nothing scientific is audited.
**Method:** every statement below was re-derived by command in this session. No claim was accepted on the strength of a record.

## 1 — Identity, tree, and the remote

```
git rev-parse HEAD                       → 5b40a55ef62f19cfa9125aa29146e53976661692
git rev-parse --abbrev-ref HEAD          → feat/scientific-closure
git rev-parse --abbrev-ref @{u}          → origin/feat/scientific-closure
git status --porcelain=v1 -uall          → (no output)  CLEAN
git diff --check                         → (no output)  exit 0
git diff --cached --stat                 → (no output)  nothing staged
git log --oneline b9fefbf..HEAD          → 5b40a55, 495555c   (2 commits)
git branch -vv                           → ahead 2
```

**Remote (the item the previous round missed):**

```
git reflog show refs/remotes/origin/feat/scientific-closure --date=iso
  b9fefbf @{2026-09-20 05:54:37 +0000}: update by push
  dc0d3f5 @{2026-09-20 03:52:42 +0000}: update by push
  ba539bd @{2026-09-20 03:17:29 +0000}: fetch origin: forced-update
git ls-remote origin refs/heads/feat/scientific-closure
  b9fefbf36037ca259f4b17b68642d330bc489d39
```

I confirm the governance breach independently: **two pushes during preparation**, against `AGENTS.md` ("En preparacion: sin push…") and against the SC-GOV-019 acceptance string. The audited commit `5b40a55` and its parent are **not** pushed; the remote is two commits behind. `origin/main` = `9fcbfd9f4dd…`, unchanged; no local `main` branch exists. The `forced-update` at `ba539bd` is a fetch-side ref update, not a force push. **VERIFIED.**

## 2 — Finding closure, C-01…C-20 and D-1…D-4

| ID | Ruling | Evidence I used |
|---|---|---|
| C-01 | **CLOSED** | `traceability.md` §"Estado por requisito" and `current-execution-checkpoint.md` both state BLOCKED is non-terminal and the verdict suspensive; `check_scientific_closure.py` terminal set = {PASS, NOT_APPLICABLE}, graph admits BLOCKED→APPROVED |
| C-02 | **CLOSED** | SC-GOV-019 = BLOCKED; GD-19 in `decisions.md`; RK-14, RK-15 in `risks.md`; synthesis §14 item 1; reflog re-verified by me |
| C-03 | **CLOSED** | Closing paragraph now names `review-critic.json`, `review-audit.json`, `review-audit-2.json`; all three exist in `readiness-resolution-linux-2026-09-20/` |
| C-04 / D-1 | **CLOSED** | New `closure-verification-2026-09-20/checkpoints.json` states the *rule*, not a count. It lists 1 commit (`495555c`); it is published by `5b40a55`; the rule holds exactly |
| C-05 | **CLOSED** | SC-GOV-006 = BLOCKED; GD-17 reworded to drop CRIT-SUB-01; RK-10 → `ABIERTO — MATERIALIZADO` |
| C-06 | **CLOSED** | Neither `traceability.md` nor `inventory.md` fixes a HEAD SHA any more (diff verified); `grep 'HEAD vigente'` returns only preserved reader reports and the correction note |
| C-07 | **CLOSED** | Row says 23 at snapshot `b9fefbf`; `wc -l workflow-events.jsonl` = **23** |
| C-08 | **CLOSED** | GD-13 corrected to `RESOLVED_IN_SUBSTANCE… NOT YET REFLECTED IN THE MANIFEST`; RK-05 inherits it; SC-GOV-017 row states it; manifest still shows `license_status: PENDING_CONFIRMATION` (line 149) — consistent |
| C-09 | **CLOSED** | SC-GOV-021/023/024 = BLOCKED; GD-23; RK-17; `claims.md` records the consequence and the artefact absence |
| C-10 | **PARTIALLY_CLOSED** | The checker and critic reports on `b9fefbf` are preserved. The *final independent audit* on the published snapshot is this one and **did not exist** at `5b40a55` — yet `traceability.md` says it does (see AUD-F-01) |
| C-11 | **CLOSED** | `grep -c 'def test_' tests/test_readonly_role_sandbox.py` = **11**; GD-17 and SC-GOV-006 row both say 11 with the 8→9→10→11 history |
| C-12 | **CLOSED** | `corrections_2026_09_20.C-12_stale_recovery_hint` added as annotation; original field untouched |
| C-13 | **CLOSED** | RK-11 → `MITIGADO CON RESIDUAL` scoped to Linux processes; RK-10 → `ABIERTO — MATERIALIZADO` |
| C-14 | **CLOSED** | SC-GOV-018 row cites the two files with no directory misattribution |
| C-15 | **CLOSED** | SC-GOV-017 row states `provenance-assessment.json` exists under `input-migration-…` with the declared name; verified on disk |
| C-16 | **CLOSED** | SC-GOV-007 row limitation (d) states the declared single-writer exception |
| C-17 | **CLOSED** | SC-GOV-002 row says pre-existing to the session but not to the merged protocol. I confirmed: `main`'s protocol has no second `## 16`; the branch diff adds it |
| C-18 | **CLOSED** | GD-21; SC-GOV-009 row; synthesis §14; adds the runbook consequence the critic did not state |
| C-19 | **PARTIALLY_CLOSED** | Recorded in `findings-resolution.json` as "CARRIED INTO THE VERDICT", but **not** propagated to the SC-GOV-002 row or the checkpoint. I carry it here (AUD-F-04) |
| C-20 | **CLOSED (no edit, correctly)** | `final-preparation-audit.md` lines 1–9 do carry a dated header scoping it to `1827252d`. Leaving it is right |
| D-2 | **CLOSED as recorded** | `uncorroborated_hash_declared` names `39f3d55e…` in the new manifest and excludes it from the verified count. No hash edited |
| D-3 | **CLOSED as recorded** | Recorded in `findings-resolution.json`; the defect is not repeated — the new manifest hashes no mutable external cache |
| D-4 | **CLOSED** | (a) generation-time state, disclosed; new manifest declares `tree_clean_at_generation: true`, which is correct. (b) = C-06, applied |

**No finding recorded as APPLIED was found absent.** Two are overstated in their claimed completeness (C-10, C-19) and are raised below.

## 3 — Requirement states

**Arithmetic — VERIFIED.** PASS 0; PASS_WITH_LIMITATIONS 8 (001, 003, 004, 005, 007, 016, 017, 020) = 8; BLOCKED 17 (002, 006, 008–015, 018, 019, 021–025) = 17; NOT_APPLICABLE 0. Total 25. `requirements.json` contains exactly 25 ids, 001–025.

**Row-by-row support.** I checked each row's cited evidence against disk and against `changes.json`/`requirements.json`.

- The eight `PASS_WITH_LIMITATIONS` rows each cite an artefact that **exists** and each states a live limitation. None is overstated except as noted for SC-GOV-016.
- **SC-GOV-016 (raised to PASS_WITH_LIMITATIONS) — OVERSTATED IN ITS ATTRIBUTION, not in its status.** The artefact `closure-verification-2026-09-20/claim-evidence-review.json` exists and its *substance* is sound: I re-read the synthesis against `claims.md` and found no overstatement, no result claimed, no fixture presented as science, no implication the holdout was touched. But the row says the review was "realizada por un crítico independiente … y **transcrita sin alterar su veredicto**", and the JSON declares `reviewer.exact_report = "review-critic.md"`. The preserved `review-critic.md` contains **none** of CER-06, CER-07, CER-08, CER-11, CER-12, CER-13, CER-14, and no 16-item structure at all. See AUD-F-02.
- **SC-GOV-006, 019, 021, 023, 024 (degraded to BLOCKED) — correctly degraded, none under-stated.** I re-derived each: `CRIT-SUB-01` is still `OPEN/BLOCKED` in `checker-remediation-linux.json`; the two pushes are real; `auxiliary/{R,N,S}/review.json` do not exist and `claims.md` still declares GD-12 unaudited. Degradation to BLOCKED (not NOT_APPLICABLE) is the defensible reading, since NOT_APPLICABLE is terminal in the checker's own graph.
- **SC-GOV-025 — the status BLOCKED is right; the justification is false.** See AUD-F-01.

No row is degraded further than the evidence requires. The statement "ninguno se degradó por evidencia nueva en contra, sino porque el estado anterior excedía la evidencia" is accurate.

## 4 — Cross-document consistency

I grepped the whole of `openspec/` and `docs/` for each falsified statement. Every stale claim now survives **only inside preserved reader reports**, which is correct by the repository's own preservation rule.

- `"HEAD vigente"` / `dc0d3f5` as current → only in `review-critic.md`, `review-evidence-checker.md`, and the correction note. **Resolved.**
- `"17 eventos"` → only in `review-critic.md`. **Resolved.**
- `NOT_APPLICABLE` for 021/023/024 → only in the correction texts. **Resolved.**
- `changes.json` (unchanged at this commit): `sc-01` PASS, `sc-02`…`sc-10` BLOCKED, `sc-07`…`sc-10` `conditional: true`. Matches `traceability.md`'s header paragraph and every row. **Consistent.**
- `requirements.json` expected-evidence names match the matrix column one-for-one (I dumped all 25).
- `claims.md`, `decisions.md`, `risks.md`, `inventory.md`, `current-execution-checkpoint.md`, synthesis §14 — mutually consistent, and consistent with `traceability.md`, on every point I tested.

**One surviving contradiction, introduced by these corrections:** `traceability.md` SC-GOV-025 asserts an artefact that does not exist (AUD-F-01). **One stale pointer:** `next-session.txt`, linked from `README.md` as "Prompt siguiente", is the superseded 2026-09-19 operator prompt — Windows path `C:\Repo\…`, and "No push, merge, rebase…" — contradicting the 2026-09-20 instruction, and not labelled superseded (AUD-F-05).

## 5 — Evidence integrity

I recomputed **every** sha256 declared in `closure-verification-2026-09-20/evidence-manifest.json`:

```
declared sha256 entries: 25   (23 governance_evidence + 2 scientific_inputs)
MATCH=25  MISMATCH=0  MISSING=0
```

Declared `count.governance_files: 23` equals the list length. **VERIFIED.**

**Self-reference limitation — HONEST.** `commit_at_generation: 495555c`; the publishing commit is `5b40a55`, whose parent I verified is `495555c`. The manifest correctly declines to name it. `tree_clean_at_generation: true` is accurate. `uncorroborated_hash_declared` (D-2) is a genuine and unusual act of self-disclosure.

**Prior manifest annotation — NON-DESTRUCTIVE.** Compared against `git show b9fefbf:…/readiness-resolution-linux-2026-09-20/evidence-manifest.json`:

```
old entries: 31   new entries: 31
removed: set()    added: set()    changed hashes: {}
new-only top-level keys: {'corrections_2026_09_20'}   old-only: set()
no pre-existing top-level key differs
```

No hash altered, no entry removed, one key added. **VERIFIED.**

**Gap:** the manifest omits `closure-verification-2026-09-20/checkpoints.json`, published in the same commit and the declared SC-GOV-019 artefact (AUD-F-03).

## 6 — Reader-report preservation

`git diff b9fefbf..HEAD --name-only` touches 16 files. Within `openspec/scientific-closure/`, the only file under a campaign directory that was modified is `readiness-resolution-linux-2026-09-20/evidence-manifest.json`, which is **not** a reader report. **No earlier reader report — `review-critic.json`, `review-audit.json`, `review-audit-2.json`, `review-checker-cycle0/1.md`, `review-critic-final.md`, `critique-final.md`, `checker-final.md`, `audit-final.md`, `reader-reports.json` — was edited.** The two `review-audit*.json` that assert "no push" survive verbatim, with the correction held separately in `findings-resolution.json`. That is exactly the right handling.

`review-critic.md` and `review-evidence-checker.md` preserve both readers' verdicts intact, including `CRITIC_MATERIAL_FINDINGS(10)` and the checker's "VERIFIED 10 · DISCREPANCY 2 · NOT_VERIFIABLE 1 · NOTES 2". Neither was softened. **VERIFIED.**

## 7 — Protocol and custody compliance

| Check | Command | Result |
|---|---|---|
| Stage A/B/C artefacts | `find` for `frozen_config.json`, `decision.json`, `gate-review*`, `*holdout*.sqlite` across repo + all three external roots | **NONE.** Only `src/…/holdout_ledger.py` and its test |
| Ledger | `ls -la /home/gus/scientific-closure-runtime/ledger/` | **EMPTY** (also `evidence/`) |
| 2024-2025 holdout | no stage artefact, no ledger, only `backups/rehearsal-20260920/*/ledger/fixture_holdout.sqlite` (self-declared fixtures) | **NO VALUE READ** |
| Code identity | `git diff --stat 214735e4… HEAD -- src/ docker/ pyproject.toml` → empty; trees `src=0308057…`, `docker=84230fc…`, blob `pyproject.toml=da4a2e9…` identical on both refs | **BYTE-IDENTICAL** |
| ADR-0011 precond. 4 | ADR sha256 `a8dabbc4…` identical on HEAD and `origin/main`; protocol in `main` diverges 42+/2−; `main` §4 reads *"Contrato causal heredado de `controlled_daily_v3`, sin modificación"* while `features.py:33 FEATURE_COLUMNS` defines the v4 eight-feature contract; `main` lacks §16 *"Condiciones de interpretación y soporte previas a ejecución"*; `scientific-closure-decisions.md` and `scientific-closure-runbook.md` **absent from `main`**; `214735e4` not an ancestor of `origin/main` | **GENUINELY NOT_SATISFIED.** The divergence is normative. Executing under `main`'s text would preregister a false feature contract |
| Leakage | no change to `src/`, `scripts/`, `tests/`, no data file touched | **NONE INTRODUCED** |
| Baselines | `scientific-baseline-v3` = `ce22e47f…`; `technical-baseline-v1` = `74a5081c…`; `technical-baseline-v2` = `db4e8c79…` | **UNMOVED** |
| `main` | `origin/main` = `9fcbfd9f…`; no local `main`; no commit touches it | **NOT MODIFIED** |

## 8 — Verification results (re-run by me)

```
PYTHONPATH=src …/venv-v4/bin/python scripts/check_scientific_closure.py
  scientific-closure checker: PASS (estructura; runtime no verificado)     EXIT=0

…/venv-v4/bin/python -m pytest -q tests/test_scientific_closure_governance.py \
                                  tests/test_scientific_closure_checker.py
  48 passed, 14 subtests passed in 0.77s                                    EXIT=0

ruff check  <4 branch-owned files>   All checks passed!                     EXIT=0
black --check <same 4>               4 files would be left unchanged        EXIT=0

PATH=/home/gus/scientific-closure-runtime/env/node/bin:$PATH
npx @fission-ai/openspec@1.13.1 validate … --strict   (10 changes + 1 spec)
  OpenSpec strict: OK=11 FAIL=0 (of 11)
```

I confirm E-01/GD-20 independently: with the Linux node first on `PATH`, all eleven validate clean. The full 545-test suite was **not** re-run, per instruction; the carry-over is legitimate because `git diff b9fefbf..HEAD -- src scripts tests` is **empty** — I verified this — so the executable state at `5b40a55` is bit-for-bit the state that was tested.

## 9 — Scientific sufficiency over the approved scope (SC-GOV-025)

Evaluating CL-01…CL-10 in `claims.md`:

- **CL-01, CL-02, CL-03, CL-09** — each carries an explicit `PENDING` gap requiring Stage A, B or C. None executed. **NOT SUPPORTED, and not covered by an accepted limitation** — `PENDING` in this document means *future evidence required*, which is the opposite of an accepted limitation.
- **CL-06** — H is `REQUIRED`, has no runner, and no evidence. An explicit open item, not a limitation.
- **CL-10** — requires "terminal A/B/C auditado, H auditado". None exists.
- **CL-04, CL-05, CL-07, CL-08** — supported by `REFERENCED` v3 evidence *under accepted limits*. These four are the only ones in an admissible state, and only because they explicitly decline to make a v4 claim.

**Scientific closure is NOT achieved.** What is missing, precisely: (a) an audited terminal Stage A producing either a transferable candidate or `NO_VALID_SELECTION`; (b) Stage B's verdict; (c) Stage C only if B validates; (d) an audited H comparison; (e) an independent audit of the sufficiency decision GD-12, absent which R/N/S `NOT_REQUIRED` cannot carry terminal status. Six of ten claims rest on evidence that does not exist and is not substituted by any accepted limitation.

## 10 — Findings raised by this audit

**AUD-F-01 — MATERIAL — correctable in-session**
- *Requirement:* SC-GOV-025 (and the AGENTS.md rule "Prohibido completar evidencia faltante mediante inferencias").
- *Location:* `openspec/scientific-closure/traceability.md`, SC-GOV-025 row.
- *Reproduction:* `ls openspec/scientific-closure/closure-verification-2026-09-20/` ; `git ls-files | grep scientific-closure-audit` ; `find . -name scientific-closure-audit.json`.
- *Expected:* the row describes an artefact that exists, or declares it absent.
- *Observed:* the row states *"El artefacto `closure-verification-2026-09-20/scientific-closure-audit.json` **ya existe**"* and goes on to state its verdict. **The file does not exist anywhere in the tree or the index at `5b40a55`.** The row also pre-states the independent auditor's conclusion before the audit was performed.
- *Why it matters:* this is the same defect class the session was convened to correct (C-09: crediting a nonexistent artefact; C-04: a record that falsifies itself). It appears in the normative status matrix, and it prejudges the auditor whose PASS the repository requires for closure.

**AUD-F-02 — MATERIAL — correctable in-session**
- *Requirement:* SC-GOV-016; AGENTS.md "El orquestador conserva informes exactos de lectores".
- *Location:* `closure-verification-2026-09-20/claim-evidence-review.json` (`reviewer.exact_report`) and the SC-GOV-016 row.
- *Reproduction:* compare CER-01…CER-16 against `review-critic.md`.
- *Expected:* content attributed to an independent reader is traceable to that reader's preserved exact report.
- *Observed:* CER-06, CER-07, CER-08, CER-11, CER-12, CER-13 and CER-14 appear nowhere in `review-critic.md`, which has no 16-item structure. The JSON nonetheless names `review-critic.md` as its `exact_report`, and the matrix says the review was "transcrita sin alterar su veredicto". The artefact is at least partly orchestrator-composed, and it is the **sole basis for the only status upgrade in this snapshot**. The substantive conclusion is correct — I re-verified it — but the attribution is not.

**AUD-F-03 — MINOR — correctable in-session**
- *Location:* `closure-verification-2026-09-20/evidence-manifest.json`.
- *Observed:* the manifest lists 23 governance files and claims "every hash listed matches the state that is published", but omits `closure-verification-2026-09-20/checkpoints.json`, published in the same commit and the declared SC-GOV-019 artefact. The self-reference limitation excuses only the manifest itself.

**AUD-F-04 — MINOR — correctable in-session**
- *Observed:* C-19 (sc-02 evidence produced before sc-02 was approved, self-declared in `authorizations.json`) is recorded only in `findings-resolution.json`. The critic asked it be "carried into any verdict"; it is not reflected in the SC-GOV-002 row or the checkpoint. **I carry it here:** the ordering irregularity is real, was volunteered rather than concealed, relaxed no gate, and is one further reason `sc-02` is not PASS.

**AUD-F-05 — OBSERVATION**
- `openspec/scientific-closure/next-session.txt`, linked from `README.md` as the live "Prompt siguiente", is the superseded 2026-09-19 prompt (Windows path, "No push"). It contradicts the 2026-09-20 instruction and is not labelled superseded.

**AUD-F-06 — OBSERVATION**
- `session-identity.json` records `captured_at_utc: 17:46:04Z` as the session preflight, but `independent-verification.json` W-01 began at `17:42:36Z`. The session's largest verification preceded its own recorded start. Harmless; the ordering claim is loose.

**Confirmed, not new:** the two preparation pushes (C-02) are real, are correctly recorded as GD-19/RK-14, and correctly hold SC-GOV-019 at BLOCKED. They cannot be cured without rewriting published history, which is prohibited. Ratification belongs to the responsible person.

## 11 — Ruling on the intended session outcome

**I agree with `SCIENTIFIC_CLOSURE_BLOCKED`, explicitly suspensive.** The three external blockers are real and I re-verified each: ADR-0011 precondition 4 is unsatisfied on normative and not cosmetic grounds; no container runtime is reachable from this distro and the runbook routes every A/B/C command and the ledger initialisation through `docker`; no storage exists that is not backed by the same host volume. None is resolvable in-session; all three are ordinary operator actions. `BLOCKED` is non-terminal in the repository's own checker (terminal = {PASS, NOT_APPLICABLE}; the graph admits BLOCKED→APPROVED), so "suspensive" is the correct qualification and "terminal" would have been wrong.

**`SCIENTIFIC_CLOSURE_PASS_WITH_LIMITATIONS` could NOT legitimately be claimed.** It would require every approved claim to be supported by evidence or by an accepted limitation. Six of ten are supported by neither: they are marked `PENDING`, which designates missing future evidence, not an accepted limit. Seventeen of twenty-five requirements are unresolved. Claiming PASS_WITH_LIMITATIONS would be precisely the overstatement this session's own corrections were made to remove.

**What I would sign:** `SCIENTIFIC_CLOSURE_BLOCKED (suspensive)` for the session outcome. For this audit of the preparation record, I cannot sign PASS or PASS_WITH_LIMITATIONS, because the normative status matrix contains a statement that is false at this commit (AUD-F-01) and the single status upgrade rests on a misattributed artefact (AUD-F-02). Both are documentary and correctable in-session; neither touches custody, leakage, code identity or any scientific claim. Under the repository's own rule — material findings return to the implementer, and a change closes only on an auditor PASS over the reviewed snapshot — the correct disposition is to return AUD-F-01 and AUD-F-02, re-test, and re-audit the corrected snapshot.

Everything else I was asked to verify held: 25/25 hashes match, the executable tree is byte-identical to `214735e4`, no stage artefact exists, the ledger is empty, no reserved value was read, every reader report is preserved unedited, all reported verification commands reproduce at the stated exit codes, and twenty-two of the twenty-four reader findings are genuinely and fully closed.

**AUDIT_VERDICT: BLOCKED**

*Scoped to:* the preparation `sc-02-runtime-readiness` and its documentary record at commit `5b40a55ef62f19cfa9125aa29146e53976661692`. It is **not** a verdict on any scientific campaign, because none exists, and it is **suspensive**, not terminal: two of its grounds are correctable in this session, and three are external inputs owed by the responsible person.
