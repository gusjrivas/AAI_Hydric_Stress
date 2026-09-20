# Informe exacto del crítico independiente — snapshot `b9fefbf`

Rol nominal: `scientific_critic` (`.codex/agents/scientific_critic.toml`,
`gpt-5.6-sol`, esfuerzo `high`, `sandbox_mode = read-only`).
Sustituto efectivo: subagente `general-purpose` de Claude Code, modelo
solicitado `opus`, contexto separado, solo lectura **instruida** (el harness no
coloca el proceso en un sandbox). Sustitución declarada en
`session-identity.json`.

El texto que sigue es la respuesta del lector, conservada sin alterar su
veredicto ni su redacción sustantiva. El orquestador no la reescribe. La
resolución de cada hallazgo está en `findings-resolution.json`.

---

I have enough verified evidence. Findings below — each one I re-verified myself with the commands shown.

## Findings

**C-01 — MATERIAL — The intended "TERMINAL BLOCKED" verdict contradicts the repo's own normative semantics.**
Challenged: the orchestrator's framing of BLOCKED as terminal.
`openspec/scientific-closure/traceability.md:49-52` states verbatim: *"**`BLOCKED` no es un estado terminal.** El checker normativo ... considera terminales únicamente `PASS` y `NOT_APPLICABLE`, y su grafo de transiciones admite `BLOCKED → APPROVED`."* Verified mechanically in `scripts/check_scientific_closure.py:39` (`"BLOCKED": {"APPROVED"}`) and `:369,:403` (terminal set = `{PASS, NOT_APPLICABLE}`). `AGENTS.md` likewise: *"BLOCKED se registra y suspende dependientes"* — suspend, not close.
Must change: the verdict may be `BLOCKED` / `SUSPENDED_PENDING_EXTERNAL_INPUT`, never "TERMINAL". The blocker is resolvable by an operator action (merge), so terminality is unsupported.

**C-02 — MATERIAL — The branch was pushed to GitHub, twice; three records assert it was not, and SC-GOV-019's own acceptance criterion forbids it.**
```
$ git reflog show refs/remotes/origin/feat/scientific-closure --date=iso
b9fefbf ...@{2026-09-20 05:54:37 +0000}: update by push
dc0d3f5 ...@{2026-09-20 03:52:42 +0000}: update by push
$ git ls-remote origin refs/heads/feat/scientific-closure
b9fefbf36037ca259f4b17b68642d330bc489d39
```
Commit `b9fefbf` is dated 05:54:29 — the push followed 8 seconds later. Against this:
- `AGENTS.md:36`: *"En preparacion: sin push, main/UI, merge, rebase, tag, release, PR ni A/B/C."*
- `requirements.json` SC-GOV-019 acceptance: *"... no git add -A ni **push en preparación**."*
- `readiness-resolution-linux-2026-09-20/review-audit.json:24`: *"no push (remote still at dc0d3f5)"*
- `readiness-resolution-linux-2026-09-20/review-audit-2.json:38`: *"origin/feat/scientific-closure still at dc0d3f5; no push"*

`traceability.md:92` records SC-GOV-019 as `PASS_WITH_LIMITATIONS` and enumerates only the criteria that were met (`git diff --check`, explicit `git add` paths), silently dropping the push clause from the same acceptance string. No reviewer caught this because all three ran without network — but the reflog is local and would have shown it. Must change: SC-GOV-019 cannot stand at PASS_WITH_LIMITATIONS; the pushes must be recorded, and the two audit records corrected.

**C-03 — MATERIAL — `traceability.md` denies the existence of the very critique and audit it relies on.**
`traceability.md:117-119`: *"Los registros de `readiness-resolution-linux-2026-09-20` **no** han recibido crítica ni auditoría independiente al momento de escribir esta sección."* Contradicted inside the same section at `:79` (*"la auditoría independiente derrotó la primera versión de este mecanismo (hallazgo A-01)"*), `:80` (*"hallazgo F-02 del crítico"*), `:89` (*"crítica adversarial independiente"*), and by three files in that exact directory: `review-critic.json` (snapshot `a881207`), `review-audit.json` (`ccd3a9c`), `review-audit-2.json` (`8e31f78`). Four `PASS_WITH_LIMITATIONS` rows are justified by findings the closing paragraph says never happened.

**C-04 — MATERIAL — `checkpoints.json` reproduces the exact defect audit finding A-04 closed, and `traceability.md` launders it into a PASS.**
`checkpoints.json`: `head_at_capture: ccd3a9c`, `commits_in_session_at_capture: 8`, 8 entries; `self_reference_limit` says the missing commit *"is exactly ONE commit"*. But `git log --oneline dc0d3f5..HEAD | wc -l` = **10** — two commits are absent (`8e31f78`, `b9fefbf`). The record's own text cites *"audit finding A-04"* for precisely this error in its previous version. `traceability.md:92` repeats the false "salvo el commit final" claim.

**C-05 — MATERIAL — SC-GOV-006 moved to PASS_WITH_LIMITATIONS while its blocking findings remain recorded as open.**
`checker-remediation-linux.json:182`: `"CRIT-SUB-01": "OPEN/BLOCKED, no resuelto"`. `current-execution-checkpoint.md:268`: *"`CRIT-SUB-01` | `OPEN/BLOCKED`; carga, aislamiento y permisos efectivos de los cinco perfiles no acreditados"*. `preparation-resumption-audit-2026-09-19.md:25`: *"`AUD-SUB-02` — **bloqueante**: SC-GOV-006 exige carga y permisos efectivos"*. `readiness-linux-2026-09-19/registration-reviews.json:128`: *"No cierra ... CRIT-SUB-01, SC-GOV-006"*. The only claimed closure is `decisions.md` GD-17, which says bubblewrap *"Resuelve el **fondo** de"* those findings — a hedge, and it addresses read-only shell enforcement, not profile loading, which is what AUD-SUB-02 was about. `agent-capabilities.json` concedes the `.codex/agents` profiles *"are not loadable"* in this runtime and `effective_model_introspectable: false`. No recorded transition from blocking to closed.

**C-06 — MATERIAL — The traceability table declares a HEAD that is ten commits stale.**
`traceability.md:74`: *"el HEAD vigente es `dc0d3f5b4dbed235078c1bc93a3c863b6f65d3c6`"*. Actual HEAD is `b9fefbf`; `git log --oneline dc0d3f5..HEAD | wc -l` = 10. Repeated at `traceability.md:76` and `inventory.md:46`. This is exactly the "superseded snapshot described as current" failure mode.

**C-07 — MATERIAL — Event-log count is wrong.** `traceability.md:80` (SC-GOV-007): *"(17 eventos ...)"*. `wc -l workflow-events.jsonl` = **23**; `b9fefbf` added 6 (second auditor pass) and the row was not updated.

**C-08 — MATERIAL — `decisions.md` GD-13 declares ADR-0011 condition 2 closed; its own cited evidence and the ADR's named manifest both say otherwise.**
GD-13: *"cerrar así la condición 2 de ADR-0011"*. But `provenance-and-licence-assessment.json` says `"adr_0011_condition_2": "RESOLVED_IN_SUBSTANCE_BY_EXPLICIT_DECISION, NOT YET REFLECTED IN THE MANIFEST"`, and `controlled-daily-v4-external-pergamino-manifest.yaml:91,148,149` still read `PENDING_CONFIRMATION` (last touched by `214735e`, outside this campaign). ADR-0011:72 defines condition 2 over exactly those fields. Note: the *synthesis* (§2, limitation 5) states this correctly — `decisions.md` is the overstatement, and `risks.md:35` (RK-05 `MITIGADO CON RESIDUAL`) inherits it.

**C-09 — MATERIAL — Three requirements carry a *terminal* status on an explicitly unaudited decision, with artefact absence undisclosed.**
`traceability.md:94,96,97`: SC-GOV-021/023/024 = `NOT_APPLICABLE`, which the checker treats as terminal (equal in finality to PASS). Their declared artefacts `auxiliary/{R,N,S}/review.json` do not exist anywhere in the tree, and unlike every BLOCKED row, these rows never say so. Their entire basis is `claims.md`, which at `:45-46` states the R/H/N/S decision *"permanece pendiente de crítica y auditoría independiente"*. Terminal status on a self-declared unaudited decision contradicts `AGENTS.md` (*"Cerrar un change solo con PASS del auditor"*).

**C-10 — MATERIAL — No independent review exists of the published snapshot.**
`review-critic.json` → `a881207`; `review-audit.json` → `ccd3a9c`; `review-audit-2.json` → `8e31f78`. `b9fefbf` applied NF-01..NF-05 *after* the last review and has had no independent pass until now. `AGENTS.md`: *"Cerrar un change solo con PASS del auditor sobre el snapshot revisado."* No closure verdict may be issued on `b9fefbf` on the strength of reviews of its predecessors.

### Minor

- **C-11** — Sandbox test count stated three ways, all wrong: `decisions.md` GD-17 *"8 pruebas"*, `traceability.md:79` *"10 pruebas"*, `blocker-reassessment.json` LNX-03 *"Covered by 8 tests"*; actual `grep -c "def test_" tests/test_readonly_role_sandbox.py` = **11**. (`validation-results.json` has it right, with the 8→9→10→11 history.)
- **C-12** — `evidence-manifest.json:213` `published_in_commit` recovery hint is stale: *"recoverable with git log --oneline dc0d3f5..HEAD"* returns 5 commits, not 1; the `commit` field is `8e31f78`, so the hint should read `8e31f78..HEAD`.
- **C-13** — `risks.md:41` RK-11 `MITIGADO` **unqualified**, with *"enforcement real verificado"*, while `role-sandbox-enforcement.json` scopes it to *"LINUX PROCESSES"* and states *"a third layer is not excluded"*; two escapes (A-01 demonstrated, NF-01) were found by reviewers, not by the mechanism's tests. `risks.md:40` RK-10 `MITIGADO CON RESIDUAL` describes a hazard ("rol no cargado") that the residual column confirms **occurred**.
- **C-14** — `traceability.md:91` cites `input-migration-linux-2026-09-20/storage-and-backup-independence.json`; that file exists only under `readiness-resolution-linux-2026-09-20/`.
- **C-15** — SC-GOV-017: `requirements.json` declares evidence `provenance-assessment.json`; `traceability.md:90` credits a differently-named file (`provenance-and-licence-assessment.json`).
- **C-16** — `traceability.md:80` (SC-GOV-007) omits the single-writer exception that `agent-capabilities.json` declares: *"EXCEPTION, declared: ...traceability.md was written first by the implementer and then ... by the orchestrator"* — the file recording the status is the file whose rule was broken.
- **C-17** — The duplicate `## 16` is called *"preexistente"* (`code-identity-and-adr0011.json`, synthesis §8.1). `git log -S` shows it was introduced by `214735e` (2026-09-18) **on this branch**, which is not an ancestor of `origin/main`. Preexisting relative to this session, yes; preexisting relative to the merged protocol, no. Reword.

### Observations

- **C-18** — Blocker (b) is environment-specific, not absolute. `final-preparation-audit.md:26,60` records the approved image `sha256:55bc923e…` being **executed** on 2026-09-19 (*"15 tests, 15 OK, 0.552 s"*) from the Windows host. No document reconciles that with the 2026-09-20 *"daemon Docker es inalcanzable"*. I confirmed independently that it is genuinely unreachable **here** (`/var/run/docker.sock` absent; Docker Desktop proxy sockets root-owned; `sudo -n true` → *"interactive authentication is required"*; podman/skopeo/umoci/nerdctl/buildah all absent). Resolvable by the operator, not by this session.
- **C-19** — `authorizations.json` volunteers a `residual_irregularity`: evidence for `sc-02` was produced before `sc-02` was approved, contrary to `operations.md`. Honest, and should be carried into any verdict.
- **C-20** — The subagent flagged `final-preparation-audit.md:35` (*"Los diez `sc-*` continúan `PLANNED`"*) as an unlabelled contradiction of `changes.json`. I checked: it **does** carry a dated header identifying itself as a prior audit scoped to `1827252d`. Downgraded to observation; a cross-reference would still help.

### What I could not refute

Verified mechanically and found sound — I tried to break these and failed:

- **Custody is clean.** `/home/gus/scientific-closure-runtime/evidence/` and `/ledger/` are empty. The only SQLite files are `backups/rehearsal-20260920/{source,backup,restored}/ledger/fixture_holdout.sqlite`, whose single row is `('fixture/protocol/site/depth/2024-2025', 'RESERVED')`. Fixture metrics carry `"fixture": true, "scientific": false, mcc: null`; fixture predictions are dated year 2000. No Stage A/B/C artefact, no ledger, no 2024-2025 value.
- **Evidence manifest integrity: 31/31 SHA-256 recomputed, zero mismatches, zero missing.** Its self-reference limitation is explicitly declared (NF-03).
- **Executable identity holds at the current snapshot**, not just the one recorded: `git diff 214735e HEAD -- src` / `-- docker pyproject.toml` / `-- protocol,manifest,adr` all empty. ADR-0011 sha256 identical on both refs (`a8dabbc4…`).
- **The synthesis does not overstate.** Read against `claims.md`: no result claimed, no fixture presented as science, no holdout implied touched. It pre-empts the subtlest custody point itself — that hashing the full CSV in Stage A touches 2024-2025 bytes — and correctly distinguishes hashing from reading values. §5 correctly labels the Stage C `--validate-inputs-only` prohibition as *"Regla implementada en código, NO en el protocolo"*.
- **Protocol <-> code agreement**: the normative support gates are really implemented — `selection.py:97` `sum(np.isfinite(scores)) < 2` → `NO_VALID_SELECTION`; `bootstrap.py:117,274` the 0.8 replicate floor; `config.py:43,47,49` delta=0.05, seeds 20250109/42.
- Checker exits 0 on HEAD (`PASS (estructura; runtime no verificado)`); requirement IDs 1–25 complete; summary arithmetic 9+13+3=25 correct; `scientific-baseline-v3` and both technical baselines unmoved; no session commit touched `frontend/` (the diff vs `origin/main` there is main advancing past the merge-base — I checked and dismissed it as a false positive).

## Verdict on ADR-0011 condition 4

**NOT_SATISFIED — I agree with the orchestrator, and the conservatism is correct, not excessive.**

Both directions, argued:

*For "over-conservative":* the ADR itself is merged **byte-identically** (`a8dabbc4…` on both refs — condition 4 names "este ADR **y** el protocolo"), a protocol document of that name *is* on main, and the diff is only 42 additions / 2 deletions.

*Against, and decisive:* the divergence is **normative, not cosmetic**. (a) `origin/main`'s §4 still asserts the feature contract is *"heredado de `controlled_daily_v3`, sin modificación"* — factually false against `features.py:33-42`, which defines an eight-feature v4 contract. Executing under main's text would preregister a false contract and invite exactly the v3→v4 confound the branch corrected. (b) main **lacks** the section titled *"Condiciones de interpretación y soporte previas a ejecución"*, which is where the support floors (>=2/3 folds with defined MCC, >=4000/5000 replicates, `NO_VALID_SELECTION`), the onset definitions and the undefined-metric JSON contract are declared — the criteria under which a run would be *judged*. (c) Two documents the branch protocol makes normative, `docs/research/scientific-closure-decisions.md` and `scientific-closure-runbook.md`, are **absent from main entirely** (`git cat-file -e refs/remotes/origin/main:...` fails for both).

So neither text supports a legitimate Stage A: the branch protocol isn't merged, and main's protocol is substantively wrong. Withholding the campaign is right. And `AGENTS.md:36` independently forbids merge/PR/push in preparation, so it is unresolvable in-session regardless of capability.

**But the verdict must be `BLOCKED`, not `TERMINAL BLOCKED`** (C-01), and it cannot be issued on `b9fefbf` at all until C-02..C-10 are addressed, because that snapshot has had no independent pass (C-10) and several of the records the verdict would rest on are false or self-contradictory at HEAD. Note also that C-02 changes the practical picture: the branch is already on GitHub, so the merge path is mechanically open to the operator — further evidence the blocker is suspensive, not terminal.

CRITIC_MATERIAL_FINDINGS(10)
