# Informe exacto del auditor independiente — reauditoría, snapshot `4940ffc`

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

Background find completed; those two references (`pip-freeze.txt`, `preexecution-environment.json`) are explicitly labelled *histórico* in a section about metadata this session could not verify live, are untouched by `4940ffc`, and are not asserted to exist in the tree. Not a finding.

# INDEPENDENT RE-AUDIT — snapshot `4940ffc`

**Commit re-audited:** `4940ffccbca34a2970a0eb4b54dcb7af03b2b62d`
**Branch:** `feat/scientific-closure` · **Upstream:** `origin/feat/scientific-closure`
**Scope:** the PREPARATION and its documentary record. No scientific campaign exists.
**Method:** every statement re-derived by command. Nothing accepted on the strength of a record — including the records written to close the previous audit.

## 1 — Identity, tree, remote

```
git rev-parse HEAD                → 4940ffccbca34a2970a0eb4b54dcb7af03b2b62d
git rev-parse --abbrev-ref HEAD   → feat/scientific-closure
git rev-parse --abbrev-ref @{u}   → origin/feat/scientific-closure
git status --porcelain=v1 -uall   → (no output)  CLEAN
git diff --check                  → (no output)  exit 0
git log --oneline 5b40a55..HEAD   → 4940ffc  (1 commit, 10 files)
git reflog refs/remotes/origin/…  → b9fefbf @2026-09-20T05:54:37Z (update by push)
                                     dc0d3f5 @03:52:42Z (update by push)
                                     ba539bd @03:17:29Z (fetch, forced-update)
git ls-remote origin refs/heads/… → b9fefbf36037ca259f4b17b68642d330bc489d39
```

Remote is **three commits behind** (`495555c`, `5b40a55`, `4940ffc` unpushed), as expected. The two preparation pushes are re-confirmed; the `forced-update` is fetch-side, not a force push. `origin/main` = `9fcbfd9f…`, unchanged; no local `main`.

## 2 — Ruling on AUD-F-01 … AUD-F-06

| ID | Ruling | Evidence |
|---|---|---|
| **AUD-F-01** | **CLOSED** | `scientific-closure-audit.json` now exists on disk **and in the index** (`git ls-files`), parses, and matches the name `requirements.json:252` declares. Verdict recorded as `"BLOCKED"` with `verdict_scope` "Suspensive, not terminal" — **not softened**: it carries both material findings *against the orchestrator's own work*, the rejection of PASS_WITH_LIMITATIONS, the six-of-ten claim failure, and the `disposition_required_by_the_repository_rule`. The SC-GOV-025 row no longer says "ya existe" and no longer pre-states a verdict; it names the real one and explicitly records that the previous wording "era falso y además prejuzgaba al auditor". One residual defect in this same file → **RA-02**. |
| **AUD-F-02** | **CLOSED** | `claim-evidence-review.json` now carries `attribution_correction_2026_09_20` and `reviewer.composition_of_this_artefact`: *"ORCHESTRATOR-COMPOSED item list (CER-01..CER-16) … It is NOT a transcription of either reader."* The item block is renamed `orchestrator_item_check`. **Both quoted conclusions verified present**: the critic's at `review-critic.md:87` (under its own heading "What I could not refute"), the auditor's at `review-audit.md:86` (in the very bullet raising AUD-F-02). SC-GOV-016 row rewritten, names the misattribution as such, adds limitation (b) "la estructura por ítems es del orquestador". **SC-GOV-016 remains defensible at PASS_WITH_LIMITATIONS**: the requirement asks that a sentence-by-sentence review exist and find no overstatement; it exists, and its substance was independently upheld twice — once by the critic while trying to refute it, once by the auditor in the same paragraph that rejected the credit. Minor residual on the word "verbatim" → **RA-03**. |
| **AUD-F-03** | **CLOSED** | Manifest regenerated. 27 governance + 2 scientific inputs = **29 declared sha256**. `checkpoints.json` present; **all 10 campaign files covered except the manifest itself**, which its `self_reference_limit` excuses correctly. |
| **AUD-F-04** | **CLOSED** | SC-GOV-002 row now carries C-19/AUD-F-04 in the auditor's own terms: "real, fue declarada voluntariamente y no ocultada, no relajó ningún gate, y es una razón más por la que `sc-02` no es `PASS`". |
| **AUD-F-05** | **CLOSED** | `next-session.txt` rewritten, dated 2026-09-20, Linux worktree, explicitly labels the 2026-09-19 version superseded and names the finding. `git diff b9fefbf..HEAD -- tests/` is **EMPTY** — the test was **not weakened**; `test_evidence_paths_and_safe_resume` still asserts the literal string at line 303. The string is present at `next-session.txt:32`, and is **genuinely true**: no A/B/C artefact, empty ledger, three external inputs absent. The file additionally states the invariant "no debe reformularse para esquivar esa prueba". |
| **AUD-F-06** | **CLOSED** | `session-identity.json` adds `captured_at_utc_note`, `session_started_utc_approx: 17:36Z`, `preflight_block_captured_utc: 17:46:04Z`, and names the W-01 start at 17:42:36Z. Corrected rather than restated. |

**6 of 6 CLOSED.** No finding recorded APPLIED was found absent.

## 3 — Adversarial sweep: did closing them introduce new defects?

Yes — two, plus three observations. Details in §9. The material one (**RA-01**) is again in the orchestrator's record of its own work, and again in the commit under audit. That is now three rounds for three.

## 4 — Requirement matrix

**Arithmetic VERIFIED mechanically** (regex over the 25 bolded rows):

```
rows=25   PASS=0   PASS_WITH_LIMITATIONS=8   BLOCKED=17   NOT_APPLICABLE=0
duplicate ids: none
requirements.json: 25 ids; missing from matrix: []   extra: []
```

Matches the `Resumen mecánico` paragraph exactly, including its id lists.

**Row support.** All eight PASS_WITH_LIMITATIONS rows cite artefacts that exist on disk (checked individually: `sc-01/{session-identity,preservation,inventory,claims-assessment}.json`, `closure-verification-…/claim-evidence-review.json`, `provenance-and-licence-assessment.json` + `input-migration-…/provenance-assessment.json`, `workflow-events.jsonl`, `structural-validation.json`). SC-GOV-020's 11/11 claim is **scoped correctly** to the eleven `scientific-closure` items — I reproduced `OK=11 FAIL=0`; a repo-wide `validate --all --strict` returns 11 passed / 42 failed, but **no record claims `--all` passes**, so this is not an overstatement. The 17 BLOCKED rows are BLOCKED by artefact absence, which I confirmed. The closing paragraph is correctly scoped ("sobre el snapshot indicado en cada informe") and does not claim the published snapshot was audited.

## 5 — Evidence integrity

```
closure-verification-2026-09-20/evidence-manifest.json
declared sha256 entries: 29   MATCH=29  MISMATCH=0  MISSING=0
count.governance_files=27 + scientific_inputs=2 = 29  ✓ consistent
```

`tree_clean_at_generation: false` is **HONEST** and better than its predecessor: the note explains it is false *by construction* (generated over the tree containing the corrections it hashes, immediately before the publishing commit) and declines to restate the previous `true`. `self_reference_limit` correctly declines to name the publishing commit and gives the recovery range `git log --oneline 5b40a55..HEAD` → `4940ffc`. `uncorroborated_hash_declared` (D-2) preserved. All 7 campaign JSONs parse.

**However**, `relationship_to_the_previous_manifest` contains a false count → **RA-01**.

## 6 — Reader-report preservation

`git diff b9fefbf..HEAD --name-status` touches 19 files; within campaign directories the only **M** is `readiness-resolution-linux-2026-09-20/evidence-manifest.json`, which is not a reader report. `review-critic.md` / `review-evidence-checker.md` / `review-audit.md` are all **A** (added), and `git diff 5b40a55..HEAD` over the first two is **empty** — `4940ffc` added `review-audit.md` and touched no other reader report. The two audit records asserting "no push" are **verbatim** (`git diff b9fefbf..HEAD` over each is empty; the string survives). No `review-*`/`audit-*`/`critique-*`/`checker-*`/`reader-reports` file anywhere under `openspec/scientific-closure/**` was edited. **VERIFIED.**

*Limitation I must state:* I can verify the reader reports were not **edited after commit**, and that their content is internally consistent and adverse to the orchestrator. I **cannot** verify they are verbatim transcriptions of what the subagents actually returned — no independent channel exists. That rests on the orchestrator's attestation.

## 7 — Invariants

| Check | Command | Result |
|---|---|---|
| Code identity | `git diff --stat 214735e4… HEAD -- src/ docker/ pyproject.toml` | **EMPTY — byte-identical** |
| Branch-owned code | `git diff b9fefbf..HEAD -- src scripts tests docker pyproject.toml` | **EMPTY** |
| Stage A/B/C artefacts | `find` repo + runtime + inputs for `frozen_config.json`, `decision.json`, `gate-review*`, `*holdout*.sqlite` | **NONE** — only 3 `backups/rehearsal-20260920/*/ledger/fixture_holdout.sqlite` (self-declared fixtures) |
| Ledger | `ls -la …/runtime/ledger/` and `…/evidence/` | **BOTH EMPTY** |
| 2024-2025 holdout | no stage artefact, no ledger, no reserved value | **NOT READ** |
| ADR-0011 precond. 4 | ADR sha256 `a8dabbc4…` identical HEAD ↔ `origin/main`; but `main`'s protocol **lacks** "Condiciones de interpretación y soporte previas a ejecución" (grep count 0 vs 1); `scientific-closure-decisions.md` and `scientific-closure-runbook.md` **absent from main**; `214735e` **not an ancestor** of `origin/main` | **GENUINELY NOT_SATISFIED** — the text requires *"este ADR **y el protocolo detallado**"* merged; the ADR is, the current protocol is not |
| Baselines | `ce22e47f…` / `74a5081c…` / `db4e8c79…` | **UNMOVED** |
| `main` | `origin/main` = `9fcbfd9f…`; no local `main` | **NOT MODIFIED** |
| Leakage | no `src/`, `scripts/`, `tests/`, data change | **NONE INTRODUCED** |

## 8 — Verification re-run (exit codes)

```
PYTHONPATH=src …/venv-v4/bin/python scripts/check_scientific_closure.py
  scientific-closure checker: PASS (estructura; runtime no verificado)        EXIT=0

…/venv-v4/bin/python -m pytest -q tests/test_scientific_closure_governance.py \
                                  tests/test_scientific_closure_checker.py
  48 passed, 14 subtests passed in 0.71s                                      EXIT=0

ruff check   <4 branch-owned files>   All checks passed!                      EXIT=0
black --check <same 4>                4 files would be left unchanged         EXIT=0

PATH=/home/gus/scientific-closure-runtime/env/node/bin:$PATH   (node v22.20.0 Linux)
  npx @fission-ai/openspec@1.13.1 validate <10 sc-* changes + spec> --strict
  SCOPED OpenSpec: OK=11 FAIL=0                                               EXIT=0
```

The 545-test suite was **not** re-run, per instruction; the carry-over is legitimate — `git diff b9fefbf..HEAD` over `src scripts tests docker pyproject.toml` is empty, so the executable state at `4940ffc` is bit-for-bit the state that was tested.

## 9 — New findings

**RA-01 — MATERIAL — correctable in-session**
- *Requirement:* SC-GOV-019 / evidence-integrity accuracy; AGENTS.md "Toda ejecucion registra … hashes".
- *Location:* three places — (a) `readiness-resolution-linux-2026-09-20/evidence-manifest.json`, `corrections_2026_09_20.entries_that_no_longer_match_HEAD`; (b) **`closure-verification-2026-09-20/evidence-manifest.json`, `relationship_to_the_previous_manifest` — written in the commit under re-audit**; (c) `findings-resolution.json` finding `E-06`.
- *Reproduction:* recompute the 31 declared sha256 of the previous campaign's manifest against disk at HEAD.
- *Expected:* the number of superseded entries stated equals the number that actually mismatch.
- *Observed:* all three say **three**; **six** mismatch. Declared: `traceability.md`, `decisions.md`, `risks.md`. **Undeclared: `docs/research/scientific-closure-synthesis-2026-09-20.md`, `openspec/scientific-closure/inventory.md`, `openspec/scientific-closure/current-execution-checkpoint.md`** — each is listed in that manifest with a sha256, each was edited by this session (`495555c`, and `current-execution-checkpoint.md` again at `4940ffc`), each now mismatches. `MISMATCH count: 6, MISSING: 0`.
- *Why it matters:* the annotation states its own purpose as *"so that a later reader does not mistake a known, declared change for tampering"* — and it fails that purpose for **half** the affected files. A later reader recomputing finds three undeclared hash mismatches in a custody record. No hash was altered and no entry removed (I re-verified: 31 entries, no changed hashes), so nothing is concealed — but the count is false, and it was **restated in the commit under audit**. Correctable in minutes: change three → six and list the other three paths.

**RA-02 — MINOR — correctable in-session**
- *Location:* `closure-verification-2026-09-20/scientific-closure-audit.json`, `disposition_required_by_the_repository_rule`.
- *Observed:* *"This file records the FIRST audit of this campaign; the re-audit **is recorded in** `review-audit-2.md` and `audit-2.json`."* Present tense. **Neither file exists** at `4940ffc` (`find` + `git ls-files`). This is AUD-F-01's defect class recurring in the very artefact written to close AUD-F-01 — milder, because it is in a procedural field rather than the normative matrix and it pre-states no verdict, but it is the same error: a record asserting an artefact that does not exist. It additionally **predicts filenames** the next writer may not use, and `review-audit-2.json` **already exists under a different campaign** (`readiness-resolution-linux-2026-09-20/`), so the reference is ambiguous as well as premature.
- *Expected:* "the re-audit, **when performed**, will be recorded alongside this file", or nothing.

**RA-03 — OBSERVATION**
- *Location:* `claim-evidence-review.json`, `reviewer.independent_corroboration[*].verbatim_conclusion`; `orchestrator_item_check` CER-16; `limitations[1..2]`.
- *Observed:* the two quotations are **faithful but not verbatim**: the critic's `§5` → "Section 5", `código` → "codigo", em dashes → hyphens, markdown emphasis stripped; the auditor's `*substance*` → "substance". Substance is unaltered and neither verdict is softened — but a field named `verbatim_conclusion` in an artefact whose whole correction was about attribution should either be byte-exact or be named `quoted_conclusion`. Separately, CER-16 still reads "verified by **the reviewer** in source" and two `limitations` entries say "The reviewer ran without network" / "The reviewer's read-only status was instructed" — residual ambiguity after the file itself established that the item list is the orchestrator's.

**RA-04 — OBSERVATION**
- *Location:* `findings-resolution.json`, `counts`.
- *Observed:* `13+9+7+0+1+3 = 33` against `len(findings) = 36`; actual severity tally is MATERIAL 14, MINOR 10, OBSERVATION 8, plus NOT_VERIFIABLE/LOW/NOTE/MATERIAL_FOR_REPRODUCIBILITY 1 each. The `+2/+2/+2` delta for the six AUD-F findings **was correctly applied** (11/7/5 → 13/9/7), so the block was maintained; the residual gap of 3 is pre-existing and stems from undeclared category definitions (the `E-*` orchestrator self-findings carry no `accepted` key). Not false, but not mechanically reconcilable — which in a findings ledger it should be.

**RA-05 — OBSERVATION**
- *Location:* `checkpoints.json`, `push_policy.this_session`; `findings-resolution.json`, `C-10.resolution`.
- *Observed:* (a) *"Push **is performed** once, at the end, on the snapshot the final audit covers"* — an intention stated in the present tense in a record of facts; no push has occurred since `b9fefbf` (`ls-remote` confirms). (b) C-10's resolution says this session commissioned *"a final independent audit **on the snapshot this session publishes**"* — the audit covered `5b40a55`, an intermediate snapshot; the audit of the published snapshot is this re-audit, which did not exist when that sentence was written. Both are the loose-tense variant of the AUD-F-01 class.

**Confirmed, not new:** the two preparation pushes remain real, correctly recorded (GD-19/RK-14/RK-15), correctly hold SC-GOV-019 at BLOCKED, and cannot be cured without rewriting published history. Ratification belongs to the responsible person.

## 10 — Ruling on the session outcome

**`SCIENTIFIC_CLOSURE_BLOCKED`, explicitly suspensive — CONFIRMED.** I re-verified all three external grounds independently: ADR-0011 precondition 4 is unsatisfied on **normative** grounds (the current protocol, and the two normative branch documents, are absent from `main`; executing under `main`'s text would preregister a feature contract that `features.py` falsifies); no container runtime is reachable from this distro while the runbook routes every A/B/C command and the ledger initialisation through `docker`; and no storage exists that is not backed by the same host volume. None is resolvable in-session; all three are ordinary operator actions. **BLOCKED is non-terminal** in the repository's own checker (terminal set `{PASS, NOT_APPLICABLE}`; the graph admits BLOCKED→APPROVED), so "suspensive" is the correct qualification.

**`PASS_WITH_LIMITATIONS` could NOT legitimately be claimed.** It would require every approved claim to be supported by evidence or an accepted limitation. Six of ten (CL-01, CL-02, CL-03, CL-06, CL-09, CL-10) are supported by neither — they are marked `PENDING`, which designates *missing future evidence*, the opposite of an accepted limitation. Seventeen of twenty-five requirements are unresolved and zero are PASS. I agree with the first auditor on every point of this ruling.

## 11 — Would I sign a PASS on the preparation record?

**No.** All six of the first audit's findings are genuinely closed, the custody and code-identity invariants are intact, 29/29 hashes match, every reader report is preserved unedited, every verification command reproduces at exit 0, and the corrections are candid — `findings-resolution.json` records its own `self_criticism` on both material findings, and the corrected `claim-evidence-review.json` is, as it says, "weaker in form and honest in kind". That is a materially better record than `5b40a55`.

But a PASS would mean signing that the preparation record contains no false statement, and it contains one: **RA-01**, a false count in the evidence-integrity layer, restated in the commit under audit. Under the standard this repository applied to AUD-F-01 — a record must describe what exists — consistency requires returning it.

**Exactly what remains, and nothing more:**
1. **RA-01** — correct "three" → "six" and list `scientific-closure-synthesis-2026-09-20.md`, `inventory.md`, `current-execution-checkpoint.md` in all three locations (previous manifest annotation, new manifest `relationship_to_the_previous_manifest`, `findings-resolution.json` E-06). Annotation only; alter no hash, remove no entry.
2. **RA-02** — reword the `audit-2` reference to the future conditional, or drop it.
3. *Optional:* RA-03 (rename `verbatim_conclusion` or make the quotes byte-exact; fix the residual "the reviewer"), RA-04 (define or drop the `counts` categories), RA-05 (put the push statement and C-10's wording in the correct tense).
4. Re-run checker, the two governance test files, ruff, black, scoped OpenSpec; re-audit the corrected snapshot.

None of these touches custody, leakage, code identity, any requirement status, or any scientific claim. All are documentary and correctable in this session in well under an hour. Three external inputs remain owed by the responsible person and are not correctable at all here.

REAUDIT_VERDICT: BLOCKED

*Scoped to:* the preparation `sc-02-runtime-readiness` and its documentary record at commit `4940ffccbca34a2970a0eb4b54dcb7af03b2b62d`. It is **not** a verdict on any scientific campaign, because none exists. It is **suspensive, not terminal**: one of its grounds (RA-01, with RA-02) is correctable in this session, and the three external grounds are ordinary operator actions. The session-outcome ruling `SCIENTIFIC_CLOSURE_BLOCKED (suspensive)` is **confirmed** and I would sign that today; what I decline to sign is a PASS on the preparation *record*.
