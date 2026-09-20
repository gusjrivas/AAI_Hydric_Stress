# Informe exacto del auditor independiente — tercer ciclo, snapshot `8830476`

Rol nominal: `scientific_auditor` (`.codex/agents/scientific_auditor.toml`,
`gpt-5.6-sol`, esfuerzo `xhigh`, `sandbox_mode = read-only`).
Sustituto efectivo: subagente `general-purpose` de Claude Code, modelo
solicitado `opus`, contexto separado, solo lectura **instruida** (el harness no
coloca el proceso en un sandbox). Sustitución declarada en
`session-identity.json`.

El texto que sigue es la respuesta del auditor, conservada sin alterar su
veredicto ni su redacción sustantiva. El orquestador no la reescribe. La
resolución de cada hallazgo está en `findings-resolution.json`, y la decisión de
detener la iteración —recomendada por este mismo informe— queda registrada allí
como `KL-01`.

---

I have everything I need.

# FINAL INDEPENDENT AUDIT — third cycle

**Object:** commit `88304765076cf51a21c059bcef0807c00609868d`, branch `feat/scientific-closure`. Read-only; I wrote no file in the repo and ran no git write command.

## 1. Identity — VERIFIED

```
HEAD      88304765076cf51a21c059bcef0807c00609868d
branch    feat/scientific-closure
upstream  origin/feat/scientific-closure
git status --porcelain=v1 --untracked-files=all   -> empty (clean)
git diff --check                                  -> empty, exit 0
git log --oneline 4940ffc..HEAD                   -> 8830476 (single commit)
git ls-remote origin refs/heads/feat/scientific-closure -> b9fefbf36037…
reflog origin/…: b9fefbf @2026-09-20 05:54 (push), dc0d3f5 @03:52, ba539bd @03:17 (forced-update fetch)
```
Remote is 4 commits behind (`495555c`, `5b40a55`, `4940ffc`, `8830476` unpushed) — as expected; no push has occurred. `8830476` touches 8 files, all documentary.

## 2. Rulings on RA-01..RA-05

**RA-01 — CLOSED.** Recomputed every declared sha256 in `readiness-resolution-linux-2026-09-20/evidence-manifest.json` (31 real entries = 29 `governance_evidence` + 2 `scientific_inputs`):

```
MATCH=25  MISMATCH=6  MISSING=0
```
The six: `traceability.md`, `decisions.md`, `risks.md`, `inventory.md`, `current-execution-checkpoint.md`, `docs/research/scientific-closure-synthesis-2026-09-20.md`. All three locations now state **six** with the full path list and match my recomputation exactly:
- that file's `corrections_2026_09_20.entries_that_no_longer_match_HEAD` (6 path objects);
- `closure-verification-2026-09-20/evidence-manifest.json` → `relationship_to_the_previous_manifest`;
- `findings-resolution.json` finding `E-06`.

Diff against `git show b9fefbf:…/evidence-manifest.json`: 31 entries before and after, **0 removed, 0 added, 0 hash altered**; every scalar field unchanged; the only change is the added `corrections_2026_09_20` key. The annotation now carries `always_current_check` instructing recomputation rather than trusting the list — the failure mode itself is removed, not just the instance.

**RA-02 — CLOSED.** `scientific-closure-audit.json` `disposition_required_by_the_repository_rule` now states the re-audit in past tense and names only `review-audit-2.md`, which exists. `audit-2.json` appears solely as a quotation of the erroneous prior wording. (Sub-note: `findings-resolution.json` RA-02 describes the fix as "now conditional"; the applied text is past-tense factual, not conditional. Descriptive imprecision only, no false world-claim.)

**RA-03 — CLOSED.** `verbatim_conclusion` → `quoted_conclusion` in both reader blocks, with `quotation_fidelity_note` declaring the quotes faithful-but-not-byte-exact and deferring to the .md originals. Residual "the reviewer" wordings in CER-16 and two limitations are now attributed to "the independent critic" / "the independent readers".

**RA-04 — CLOSED, mechanically.** The new `counts` block reproduces exactly:
```
declared total_findings 41            actual len(findings) 41
declared by_severity  {LOW:1, MATERIAL:15, MATERIAL_FOR_REPRODUCIBILITY:1,
                       MINOR:11, NOTE:1, NOT_VERIFIABLE:1, OBSERVATION:11}
recomputed            identical
```
The stated counting rule runs as written.

**RA-05 — CLOSED.** `checkpoints.json push_policy.this_session` now reads "The intention is a single push at the end" with an explicit correction note and an instruction to check `git ls-remote`. C-10's resolution now names the three snapshots each review actually covered (`b9fefbf`, `5b40a55`, `4940ffc`).

## 3. Hunt for a fourth instance — FOUND

**FA-01 · MINOR · correctable in session: YES**
*Location:* `findings-resolution.json:353` (`disagreements_with_readers`), `findings-resolution.json:133` (C-16 resolution), `traceability.md:99` (SC-GOV-007 row).
*Expected:* a stated reader count that matches the reader reports preserved at this commit.
*Observed:* all three say **three readers** / **tres lectores**; there are now **four**.
*Reproduction:*
```
ls closure-verification-2026-09-20/review-*.md | wc -l   -> 4
# review-*.md present per commit: b9fefbf 0 | 495555c 2 | 5b40a55 2 | 4940ffc 3 | HEAD 4
# "three readers" occurrences:    b9fefbf 0 | 495555c 1 | 5b40a55 1 | 4940ffc 2 | HEAD 2
```
The string was **true at `4940ffc` and made false by `8830476` itself**, which added `review-audit-2.md`. Read literally, "every material finding from all three readers was accepted" also fails to cover RA-01, a MATERIAL finding from the fourth. `traceability.md` was not touched by this commit and carries the stale count untouched. This is the fourth consecutive instance of the class, at reduced severity.

**FA-02 · MINOR · correctable: YES**
*Location:* `findings-resolution.json:7` (`sources`).
*Expected:* the source index covers every source appearing in `findings[]`.
*Observed:* it lists `critic`, `evidence_checker`, `orchestrator`, `auditor` only. Five findings in the same file carry `source: "auditor (re-audit of 4940ffc)"` with exact report `review-audit-2.md`, which the block does not list. Same class: a summary index made incomplete by the same commit's additions.

**FA-03 · OBSERVATION · correctable: YES**
*Location:* `findings-resolution.json:355` (`audit_cycle`).
*Observed:* records only `cycle_1` (`5b40a55`); cycle 2 (`4940ffc` → RA-01..RA-05) is absent, although `checkpoints.json` `audit_cycles` records it and this same file carries the cycle-2 findings. Its `rule` ends "Cycle 1 did not produce that, so nothing was closed on its strength" — silent on cycle 2.

**FA-04 · OBSERVATION · correctable: YES**
*Location:* `findings-resolution.json:6` (`snapshot_reviewed`) — single scalar `b9fefbf`, while the file now resolves findings raised against three distinct snapshots.

**FA-05 · OBSERVATION · correctable: YES**
`readiness-resolution-…/evidence-manifest.json` was modified by this commit, and its post-edit hash is recorded in no manifest. The closure-verification manifest covers the whole campaign directory and key repo files but not the previous campaign's manifest it annotates — the same species of omission as AUD-F-03. The file is git-tracked, so integrity is not lost.

**Checks that passed:** every path asserted to exist in the eight touched files exists; `checkpoints.json` `files: 10` for `4940ffc` reproduces (10 files); "manifest 29/29" was correct at `4940ffc` (29 entries) and "25/25" correct at `5b40a55` (25 entries); `workflow-events.jsonl` is 23 lines as SC-GOV-007 states; no present-tense claim about the push survives. The closure-verification manifest **does** cover every file of its directory except itself (10 of 11).

## 4. Evidence integrity — VERIFIED

`closure-verification-2026-09-20/evidence-manifest.json`: 30 declared entries (28 governance + 2 inputs) recomputed → **MATCH 30, MISMATCH 0, MISSING 0**. Includes all six files this commit touched, confirming the manifest was genuinely regenerated last. `tree_clean_at_generation: false` is correctly explained and `commit_at_generation` = `4940ffc` is consistent.

## 5. Reader-report preservation — VERIFIED

`git diff --name-status b9fefbf..HEAD -- openspec/scientific-closure/` shows all four `review-*.md` as **A** (added), never **M**. The only `M` files are governance documents and the previous manifest; **no** `review-*`/`audit-*`/`critique-*`/`checker-*`/`reader-reports*` file was edited anywhere under that tree. The two prior-campaign audit records that wrongly assert "no push" (`readiness-resolution-…/review-audit.json`, `review-audit-2.json`) are byte-identical — both show empty diffs **and** both hash-MATCH their `8e31f78` declarations, and the string "no push" survives in each.

`review-audit-2.md` (176 lines) faithfully carries the re-auditor's report, including `REAUDIT_VERDICT: BLOCKED`, its scope paragraph, section 11 "**No.**" refusing to sign a PASS on the preparation record, and its confirmation of `SCIENTIFIC_CLOSURE_BLOCKED`. A stray leading fragment from the subagent's output is preserved verbatim — correct behaviour; editing it would breach preservation.

## 6. Requirement matrix — VERIFIED

Parsed the 25 status rows of `traceability.md`:
```
rows 25, unique ids 25   PASS 0 | PASS_WITH_LIMITATIONS 8 | BLOCKED 17 | NOT_APPLICABLE 0
```
matching `requirements.json` (25 unique `SC-` ids) and the declared summary at lines 119-121, whose explicit id lists are correct. The 8 PWL rows cite artefacts that exist at this commit; the 17 BLOCKED rows are blocked by artefact absence, which I confirmed.

## 7. Invariants — VERIFIED

| Invariant | Result |
|---|---|
| Stage A/B/C artefacts | `…/evidence/` **empty** |
| Ledger initialised | `…/ledger/` **empty**; no `*.sqlite` in repo |
| Holdout 2024-2025 value read | no metrics/predictions/frozen_config anywhere |
| `git diff 214735e HEAD -- src docker pyproject.toml` | **empty**; tree/blob OIDs identical (`src` `0308057…`, `docker` `84230fc…`, `pyproject` `da4a2e9…`) |
| `git diff b9fefbf..HEAD -- src scripts tests docker pyproject.toml` | **empty** → the 545-test carry-over is legitimate |
| ADR-0011 precondition 4 | **NOT SATISFIED** — `214735e` is not an ancestor of `origin/main`; `scientific-closure-decisions.md`, `scientific-closure-runbook.md`, `protocolo-experimental-v4.md` all absent from `main` |
| Baselines / main | `origin/main` at `9fcbfd9`, unmodified; v3 protocol unmoved |
| Files changed outside the campaign dir | exactly one: `docs/research/scientific-closure-synthesis-2026-09-20.md` |

## 8. Re-run verification — all reproduce

| Command | Result | Exit |
|---|---|---|
| `check_scientific_closure.py` (PYTHONPATH=src, venv-v4) | `PASS (estructura; runtime no verificado)` | **0** |
| `pytest tests/test_scientific_closure_governance.py tests/test_scientific_closure_checker.py` | `48 passed, 14 subtests passed` | **0** |
| `ruff check` (4 branch-owned files) | `All checks passed!` | **0** |
| `black --check` (same 4) | `4 files would be left unchanged` | **0** |
| OpenSpec `@fission-ai/openspec@1.13.1 --strict`, 10 `sc-*` changes + spec | **OK=11 FAIL=0** | **0** |

Note on method: my first OpenSpec sweep reported 10/11 because I invented the id `sc-10-final-closure`; the real change is `sc-10-aux-robustness`, and the CLI reports a nonexistent change as "no deltas" rather than "not found". Corrected — 11/11 confirmed. The full 545-test suite was not run, as instructed.

## 9. Session outcome — CONFIRMED

`SCIENTIFIC_CLOSURE_BLOCKED`, explicitly suspensive. I re-verified all three external grounds independently:
1. **ADR-0011 precondition 4** — unsatisfied (evidence in §7).
2. **No container runtime** — the only `docker` on PATH is `/mnt/c/Program Files/Docker/…`, a Windows binary; `docker info` fails; no `podman`. The runbook routes every A/B/C command and ledger initialisation through `docker`.
3. **No independent storage** — `df` puts `…/backups` and the repo both on `/dev/sdf`, the same host volume.

None is correctable in-session; all three are ordinary operator actions, so BLOCKED is suspensive, not terminal.

**`PASS_WITH_LIMITATIONS` could NOT be claimed.** It would require every approved claim to rest on evidence or an accepted limitation. Six of ten (CL-01, CL-02, CL-03, CL-06, CL-09, CL-10) rest on neither — they are `PENDING`, which designates missing future evidence, the opposite of an accepted limitation. Seventeen of twenty-five requirements are unresolved and zero are PASS.

## 10. Would I sign a PASS on the preparation record?

**No — but the reason has changed character, and that matters more than the finding.**

RA-01..RA-05 are genuinely and fully closed, verified mechanically rather than accepted on the record's word. Custody, code identity, leakage, baselines, `main`, requirement statuses and reader-report preservation are all intact. Every verification command reproduces at exit 0. This is a materially better record than `4940ffc`.

What remains is **FA-01 and FA-02**: a stated reader count that this very commit falsified, and a source index that omits the reader whose findings the commit was written to close. Under the standard this repository applied to AUD-F-01 and RA-01 — a record must describe what exists — these are the same defect, so PASS cannot be signed.

**On whether to keep iterating: stop.** This is now demonstrably a fixed point, not a backlog. Severity is strictly decreasing — C-04/AUD-F-01 MATERIAL in the normative matrix, RA-01 MATERIAL in the evidence-integrity layer, FA-01/FA-02 MINOR in narrative and index fields — and the generating mechanism is structural, not careless: each correction cycle adds a reader and a finding set, which falsifies any cardinality the previous cycle wrote about those same sets. A fourth correction cycle would add a fifth reader and predictably produce a fifth instance. The orchestrator has already found the correct remedy and applied it in exactly one place — the manifest's `always_current_check`, which instructs recomputation instead of stating a number. The terminal action is to generalise that remedy: replace the remaining stated cardinalities with derivations or scope each to a named snapshot (`sources`, `audit_cycle`, `snapshot_reviewed`, the two "three readers" sentences, `traceability.md:99`), then **stop and record the class as a known limitation of the record** rather than chase instances. Continuing to iterate would spend audit capacity on a self-regenerating documentary artefact while the three genuinely disqualifying items — all external — remain untouched by any amount of further correction.

None of FA-01..FA-05 touches custody, leakage, code identity, any requirement status, or any scientific claim.

FINAL_AUDIT_VERDICT: BLOCKED

*Scoped to:* the preparation `sc-02-runtime-readiness` and its documentary record at commit `88304765076cf51a21c059bcef0807c00609868d`. It is **not** a verdict on any scientific campaign, because none exists. It is **suspensive, not terminal**: its documentary grounds (FA-01, FA-02) are correctable in this session, and its three external grounds are ordinary operator actions. The session-outcome ruling `SCIENTIFIC_CLOSURE_BLOCKED (suspensive)` is independently **confirmed** and I would sign that today; what I decline to sign is a PASS on the preparation *record*.
