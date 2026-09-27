# Backend Technical Closure Fixes (D-01, F-08, F-09, F-06/F-07) + D-06 Proposal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the four corrections authorized by `informe-auditoria-paso2.md` / `encargo-correccion-claude-code.md` (D-01 doc fix, F-08 replay-feedback concurrency lock, F-09 legacy-feedback lost-update lock, F-06/F-07 `.gitattributes` byte preservation for `replay_packages/`), prepare (but do NOT implement) the D-06 API-extension proposal, and open a PR for independent re-review. No merge, no UI changes, no memory changes, no A/B/C, no holdout access, no model training on real data.

**Architecture:** Work happens in a clean git worktree checked out from `origin/main` (== audited snapshot `f17fe658bad4726202fe13784bb716c06468af9a`, verified zero drift). Each correction is an independent, narrowly-scoped change: D-01 touches only a spec doc; F-08 and F-09 both reuse the existing `data_ingestion.storage.interprocess_lock` primitive in two unrelated modules; F-06/F-07 is a `.gitattributes` + working-tree renormalization change with no code touched. D-06 produces a design document only.

**Tech Stack:** Python (FastAPI backend, pandas/pyarrow storage layer), pytest, `multiprocessing` for concurrency fixtures, git worktrees, git attributes (`-text`).

**Spec:** `C:\Users\gusta\AppData\Local\Temp\claude\C--Repo-AAI-Hydric-Stress\5c0c69c9-9439-4c37-b808-abe4f67ff31b\scratchpad\backend-audit-step2\encargo-correccion-claude-code.md` (encargo), `.../informe-auditoria-paso2.md` (audit), `.../matriz-capitulo3-auditada-2026-09-24.md` (matrix) — all three read in full this session, not from summaries.

## Global Constraints

- Snapshot verified: `origin/main` HEAD == `f17fe658bad4726202fe13784bb716c06468af9a` (zero commits ahead) — no reconciliation needed against a drifted `main`.
- No merge to `main`. No push of anything except the new branch. No PR self-merge.
- No changes to `controlled_daily_v3`, memoria técnica, UI, or experimental configuration.
- No changes to `_verify_file_integrity`/`_sha256_of` in `package_loader.py`, and no recomputation of any `custody_sha256` in any `manifest.json`.
- No new locking mechanism beyond `data_ingestion.storage.interprocess_lock` unless it proves inapplicable (it does not, for either F-08 or F-09).
- No nested acquisition of the same lock path in one call stack (F-09 must not call `save_dataset`/`save_feedback_log`, which lock internally, from inside an outer `interprocess_lock` block on the same path).
- D-06 is preparation only — no edits to `schemas_replay.py`, `history_view.py`, or `replay.py` for the new `estado` field.
- Historical/committed data files under `replay_packages/` must not change *value* — only byte-representation (line endings) may normalize, and only via `git add --renormalize`, never by hand-editing JSON.
- Every fixture/report copied into the branch preserves its original SHA-256 (verify before and after copy).
- Git safety: before any `git add`/`git commit`, run `git status`/`git diff --stat` and confirm no foreign uncommitted changes leak in — the current checkout (`C:\Repo\AAI_Hydric_Stress`) has unrelated uncommitted modifications under `replay_packages/` and untracked `docs/design/*2026-09-24.md` files that belong to the user's other work; the new worktree starts clean from `origin/main` and never touches the original checkout.

## Review Focus

- **Windows `core.autocrlf=true` reintroducing the F-06/F-07 bug after `--renormalize`:** a later `git clone`/checkout on a machine with `autocrlf=true` must still produce byte-identical files — verified in Task 5 with an actual `-c core.autocrlf=true` clone, not just `git diff --stat` on the current worktree.
- **F-09 fix silently reintroducing a deadlock via nested locks:** if `update_feedback_log_atomically` accidentally called `save_feedback_log`/`save_dataset` (which lock internally) while already holding the same lock path, both processes would eventually hit `StorageLockTimeout` instead of a clean pass — Task 3's test must run under a real `multiprocessing.Barrier`, not just call the function twice sequentially, to surface this.
- **F-08 fix changing the on-disk format or the isolation-per-`package_id` contract:** the lock file (`<package_id>.jsonl.lock`) must never be confused with the data file itself, and two different `package_id`s must remain independent — Task 2's test checks both.
- **D-01 correction accidentally rewriting historical audit reports:** only `openspec/specs/human-feedback/spec.md` may change; `paso4-1-cierre-demo.md` and any HU5/HU6 audit doc must stay untouched — checked explicitly in Task 1's step 3.
- **Confusing `-text` normalization with content rewriting:** Task 5 must show, file by file, that `predictions.json`/`manifest.json`/`run_metadata.json`/`effective_configuration.json` have identical *logical* content before/after (e.g. `git show :file | python -c "import json,sys; json.load(sys.stdin)"` succeeds and the parsed JSON is unchanged), not just that `git diff --stat` is quiet.

---

## Task 0: Isolated worktree + branch, snapshot check, provenance copy

**Files:**
- Create (outside the repo tree): a new worktree directory, e.g. `C:\Repo\AAI_Hydric_Stress_fix_backend_closure`
- Create: `docs/design/backend-audit-step2-informe-auditoria-paso2.md` (copy)
- Create: `docs/design/backend-audit-step2-matriz-capitulo3-auditada.md` (copy)
- Create: `docs/design/backend-audit-step2-encargo-correccion.md` (copy)
- Create: `docs/design/backend-audit-step2-fixtures/` (copy of the 4 fixture scripts referenced by F-08/F-09: `f08_replay_feedback_concurrency.py`, `f08_replay_feedback_concurrency_v2.py`, `f08_mechanism_isolation.py`, `f09_legacy_feedback_concurrency.py`)
- Create: `docs/design/backend-audit-step2-provenance.md` (hash manifest of every copied file, source path, and note that they come from an out-of-repo scratchpad, not from the audited worktree)

**Interfaces:**
- Consumes: nothing yet.
- Produces: a clean worktree at branch `fix/backend-technical-closure`, tracked from `origin/main`, that every later task edits. Produces the copied audit materials that Tasks 1-6 and the PR description cite by relative path instead of the temp scratchpad path.

- [ ] **Step 1: Confirm no drift and fetch**

Run (already done once this session, re-verify inside the plan execution):
```bash
git -C /c/Repo/AAI_Hydric_Stress fetch origin --quiet
git -C /c/Repo/AAI_Hydric_Stress rev-parse origin/main
git -C /c/Repo/AAI_Hydric_Stress rev-list --count f17fe658bad4726202fe13784bb716c06468af9a..origin/main
```
Expected: `rev-parse` prints `f17fe658bad4726202fe13784bb716c06468af9a`; `rev-list --count` prints `0`. If it is not `0`, stop and re-read the diff between the audited SHA and `origin/main` for the four affected files before continuing (do not blindly apply the corrections on top of unreviewed drift).

- [ ] **Step 2: Create the worktree and branch**

```bash
git -C /c/Repo/AAI_Hydric_Stress worktree add /c/Repo/AAI_Hydric_Stress_fix_backend_closure -b fix/backend-technical-closure origin/main
```
Expected: new directory created, `git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure status` shows `On branch fix/backend-technical-closure`, `nothing to commit, working tree clean`.

- [ ] **Step 3: Verify hashes of the source encargo/audit/matrix files before copying**

```bash
sha256sum \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/informe-auditoria-paso2.md" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/matriz-capitulo3-auditada-2026-09-24.md" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/encargo-correccion-claude-code.md" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/fixtures/f08_replay_feedback_concurrency.py" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/fixtures/f08_replay_feedback_concurrency_v2.py" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/fixtures/f08_mechanism_isolation.py" \
  "C:/Users/gusta/AppData/Local/Temp/claude/C--Repo-AAI-Hydric-Stress/5c0c69c9-9439-4c37-b808-abe4f67ff31b/scratchpad/backend-audit-step2/fixtures/f09_legacy_feedback_concurrency.py"
```
Record the output verbatim — it goes into `docs/design/backend-audit-step2-provenance.md` in Step 5.

- [ ] **Step 4: Copy the files into the worktree**

Copy each source file to its destination path listed above (plain file copy, byte-for-byte, no format conversion — use a binary-safe copy, not an editor round-trip).

- [ ] **Step 5: Verify hashes match after copy, write the provenance manifest**

Re-run `sha256sum` on the 7 copied files inside the worktree and diff against Step 3's output — they must match exactly. Then write `docs/design/backend-audit-step2-provenance.md`:

```markdown
# Procedencia de materiales de auditoría copiados

Origen: carpeta temporal de scratchpad de la sesión de auditoría (fuera del
repositorio), NO reproducible desde el árbol de trabajo. Copiados
byte-a-byte (hash verificado antes y después) al abrir la rama
`fix/backend-technical-closure` desde `origin/main`
(`f17fe658bad4726202fe13784bb716c06468af9a`, sin commits de diferencia).

| Archivo en esta rama | SHA-256 | Origen |
| --- | --- | --- |
| `docs/design/backend-audit-step2-informe-auditoria-paso2.md` | `<hash>` | scratchpad `backend-audit-step2/informe-auditoria-paso2.md` |
| `docs/design/backend-audit-step2-matriz-capitulo3-auditada.md` | `<hash>` | scratchpad `backend-audit-step2/matriz-capitulo3-auditada-2026-09-24.md` |
| `docs/design/backend-audit-step2-encargo-correccion.md` | `<hash>` | scratchpad `backend-audit-step2/encargo-correccion-claude-code.md` |
| `docs/design/backend-audit-step2-fixtures/f08_replay_feedback_concurrency.py` | `<hash>` | scratchpad `fixtures/f08_replay_feedback_concurrency.py` |
| `docs/design/backend-audit-step2-fixtures/f08_replay_feedback_concurrency_v2.py` | `<hash>` | scratchpad `fixtures/f08_replay_feedback_concurrency_v2.py` |
| `docs/design/backend-audit-step2-fixtures/f08_mechanism_isolation.py` | `<hash>` | scratchpad `fixtures/f08_mechanism_isolation.py` |
| `docs/design/backend-audit-step2-fixtures/f09_legacy_feedback_concurrency.py` | `<hash>` | scratchpad `fixtures/f09_legacy_feedback_concurrency.py` |

Estos documentos no reemplazan al informe de auditoría original; se
copian para que la revisión de este PR no dependa de una carpeta temporal
fuera del control de versiones.
```
Fill in the real hashes from Step 3/5, not placeholders.

- [ ] **Step 6: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add docs/design/backend-audit-step2-informe-auditoria-paso2.md docs/design/backend-audit-step2-matriz-capitulo3-auditada.md docs/design/backend-audit-step2-encargo-correccion.md docs/design/backend-audit-step2-fixtures docs/design/backend-audit-step2-provenance.md
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "docs: preservar informe de auditoría, matriz y fixtures del cierre técnico paso 2"
```

---

## Task 1: D-01 — update the obsolete T-01 limitation about the lineage endpoint

**Files:**
- Modify: `openspec/specs/human-feedback/spec.md:231` (in the worktree at `C:\Repo\AAI_Hydric_Stress_fix_backend_closure`)

**Interfaces:**
- Consumes: nothing (pure text fix).
- Produces: nothing consumed by later tasks; this task is independent.

- [ ] **Step 1: Read the exact current line**

The current text at line 231 is:
```
**Limitación conocida (T-01):** no existe todavía un endpoint HTTP para consultar el linaje ni su cadena completa — solo las funciones Python (`load_recalibration_lineage`/`list_recalibration_lineage`), consistente con no ampliar la arquitectura por conveniencia.
```

- [ ] **Step 2: Replace it**

Replace the line with:
```
**Actualización (T-01, corregida — commit `7cdea8b`):** el endpoint `GET /lineage/{sensor_id}` (`backend/app/routers/lineage.py::get_lineage`) expone la cadena de linaje reconstruida por `list_recalibration_lineage`: es de solo lectura, reutiliza exactamente esa función (sin lógica de negocio propia), y falla explícitamente con HTTP 409 si `LineageValidationError` detecta una declaración de linaje parcial o inconsistente — nunca degrada a una respuesta vacía o parcial. Testeado en `backend/tests/test_lineage.py`.
```
Do not touch anything else on the line, do not change `LineageResponse`/`LineageEntry` fields, do not touch any other file.

- [ ] **Step 3: Confirm no other file changed and no historical report was touched**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure diff --stat
```
Expected: exactly one file, `openspec/specs/human-feedback/spec.md`, `1 file changed, 1 insertion(+), 1 deletion(-)`. Confirm `paso4-1-cierre-demo.md` and any HU5/HU6 audit doc do not appear.

- [ ] **Step 4: Run the acceptance test**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest backend/tests/test_lineage.py -q
```
Expected: all tests pass, unchanged (this test exercises code, not the spec doc, so it must be unaffected).

- [ ] **Step 5: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add openspec/specs/human-feedback/spec.md
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "docs(D-01): corregir limitación T-01 obsoleta sobre el endpoint de linaje"
```

---

## Task 2: F-08 — lock `ReplayFeedbackStore.append` against concurrent writers

**Files:**
- Modify: `src/historical_replay/feedback.py:55-66` (class `ReplayFeedbackStore`)
- Test: `tests/test_historical_replay_feedback.py` (add to existing file)

**Interfaces:**
- Consumes: `data_ingestion.storage.interprocess_lock(lock_path: Path, timeout: float = 10.0) -> ContextManager[None]` (already exists, used identically by `human_feedback/operational_repository.py` and `data_ingestion/catalog.py`).
- Produces: `ReplayFeedbackStore.append` becomes safe under concurrent multi-process writers to the same `package_id`. No public signature changes — `ReplayFeedbackStore.__init__(storage_dir, *, package_id)`, `.append(record)`, `.list_for(timestamp_origen)` keep their exact signatures.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_historical_replay_feedback.py` (new imports at top: `import multiprocessing as mp`; keep existing imports):

```python
def _append_many(storage_dir, package_id, run_id, count, barrier):
    from datetime import datetime, timezone

    store = ReplayFeedbackStore(storage_dir, package_id=package_id)
    barrier.wait()
    for i in range(count):
        store.append(
            ReplayFeedbackRecord(
                timestamp_origen="2024-01-01",
                experiment_id="exp",
                run_id=run_id,
                estado_validacion="confirmada",
                etiqueta_corregida=1,
                observacion=f"{run_id}-{i}",
                registered_at=datetime.now(timezone.utc).isoformat(),
                simulated_at="2024-01-05",
            )
        )


def test_append_survives_concurrent_writers_without_loss_or_corruption(tmp_path):
    n_writers = 6
    n_per_writer = 100
    barrier = mp.Barrier(n_writers)
    procs = [
        mp.Process(
            target=_append_many,
            args=(tmp_path, "pkg-concurrent", f"writer{i}", n_per_writer, barrier),
        )
        for i in range(n_writers)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0

    path = tmp_path / "pkg-concurrent.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == n_writers * n_per_writer

    seen = set()
    for line in lines:
        payload = json.loads(line)  # raises if any line is corrupted/interleaved
        key = (payload["run_id"], payload["observacion"])
        assert key not in seen
        seen.add(key)
    assert len(seen) == n_writers * n_per_writer


def test_append_lock_file_is_separate_from_the_data_file_and_packages_stay_isolated(tmp_path):
    store_a = ReplayFeedbackStore(tmp_path, package_id="package-a")
    store_b = ReplayFeedbackStore(tmp_path, package_id="package-b")
    from datetime import datetime, timezone

    record = ReplayFeedbackRecord(
        timestamp_origen="2024-01-01",
        experiment_id="exp",
        run_id="writer",
        estado_validacion="confirmada",
        etiqueta_corregida=1,
        observacion="solo-a",
        registered_at=datetime.now(timezone.utc).isoformat(),
        simulated_at="2024-01-05",
    )
    store_a.append(record)

    assert (tmp_path / "package-a.jsonl").exists()
    assert (tmp_path / "package-a.jsonl.lock").exists()
    assert not (tmp_path / "package-b.jsonl").exists()
    assert store_b.list_for("2024-01-01") == []
```

Add `import json` at the top of the test file alongside the existing imports.

- [ ] **Step 2: Run it to verify it fails (or is flaky) before the fix**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest tests/test_historical_replay_feedback.py -k concurrent -q
```
Expected: `test_append_survives_concurrent_writers_without_loss_or_corruption` fails (line count mismatch or a `json.JSONDecodeError`) or is nondeterministically failing across a couple of runs — consistent with the audit's finding of a race, not a 100%-every-time failure. Note the observed line count / error in the task's PR notes.

- [ ] **Step 3: Implement the minimal fix**

In `src/historical_replay/feedback.py`, add the import and update the class:

```python
from data_ingestion.storage import interprocess_lock
```
(add next to the existing `from pathlib import Path` import block)

```python
class ReplayFeedbackStore:
    """Append-only JSON-lines store, one file per `package_id`, isolated
    under its own directory — never `data/feedback__<sensor_id>.parquet`,
    never inside `replay_packages/`. Writes are serialized across
    processes via `interprocess_lock` on a dedicated `.lock` file next to
    the `.jsonl` (never the `.jsonl` itself as lock target), because
    append-mode writes are not guaranteed atomic between processes on
    this platform (F-08)."""

    def __init__(self, storage_dir: Path, *, package_id: str):
        self._path = Path(storage_dir) / f"{package_id}.jsonl"
        self._lock_path = Path(storage_dir) / f"{package_id}.jsonl.lock"

    def append(self, record: ReplayFeedbackRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with interprocess_lock(self._lock_path):
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest tests/test_historical_replay_feedback.py -q
```
Expected: all tests pass, including the two new ones, run at least 3 times in a row to build confidence against the nondeterministic race (`for i in 1 2 3; do PYTHONPATH=src python -m pytest tests/test_historical_replay_feedback.py -k concurrent -q || break; done`).

- [ ] **Step 5: Run the broader regression scope named in the encargo**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest tests/test_historical_replay_feedback.py backend/tests/test_replay.py -q
```
`backend/tests/test_replay.py` may still fail here with the F-06/F-07 `IntegrityError` if Task 4 has not run yet in this session — if so, record that explicitly as expected-at-this-point (not a new regression), per the encargo's own note in Corrección 2 ("si el entorno de quien implemente reproduce el mismo bloqueo... debe investigarlo"). Task 4 investigates and fixes it.

- [ ] **Step 6: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add src/historical_replay/feedback.py tests/test_historical_replay_feedback.py
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "fix(F-08): serializar ReplayFeedbackStore.append con interprocess_lock"
```

---

## Task 3: F-09 — protect the legacy feedback load→update→save cycle as one unit

**Files:**
- Modify: `src/human_feedback/registry.py` (add `update_feedback_log_atomically`)
- Modify: `data_ingestion/storage.py`? — **No.** Do not modify `storage.py`; `interprocess_lock`, `load_dataset`, and `atomic_write_bytes` are already public and sufficient.
- Modify: `backend/app/routers/feedback.py:79-113` (`confirm_feedback`, `reject_feedback`)
- Test: `tests/test_feedback_registry.py` (add)
- Test: `backend/tests/test_feedback.py` (no new test required here — existing tests must keep passing unmodified, per encargo)

**Interfaces:**
- Consumes: `data_ingestion.storage.interprocess_lock`, `data_ingestion.storage.load_dataset`, `data_ingestion.storage.atomic_write_bytes`, `data_ingestion.storage.DEFAULT_DATA_DIR` (all already imported elsewhere with these exact names).
- Produces: `human_feedback.registry.update_feedback_log_atomically(name: str, update_fn: Callable[[pd.DataFrame], pd.DataFrame], data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame` — later code (the router) calls this instead of the bare `load_feedback_log`/`save_feedback_log` pair. `save_feedback_log`/`load_feedback_log` keep existing signatures unchanged (still used by `list_feedback` for reads and by any other caller).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_feedback_registry.py` (add `import multiprocessing as mp` and `import tempfile` at top, alongside existing imports; the barrier-based worker must be a **module-level** function so it can be pickled by `multiprocessing`):

```python
def _worker_update_atomically(data_dir, name, barrier, fecha, estado):
    from human_feedback.registry import update_feedback_log_atomically
    from human_feedback.schema import update_feedback

    def _apply(log):
        return update_feedback(log, fecha=fecha, estado_validacion=estado)

    barrier.wait()
    update_feedback_log_atomically(name, _apply, data_dir=data_dir)


def test_update_feedback_log_atomically_survives_concurrent_updates_to_different_rows(tmp_path):
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    alerts = pd.Series([1, 1, 0, 0])
    initial = init_feedback_log(pd.Series(dates), alerts)
    save_feedback_log("feedback_concurrent", initial, data_dir=tmp_path)

    barrier = mp.Barrier(2)
    p0 = mp.Process(
        target=_worker_update_atomically,
        args=(tmp_path, "feedback_concurrent", barrier, dates[0], "confirmada"),
    )
    p1 = mp.Process(
        target=_worker_update_atomically,
        args=(tmp_path, "feedback_concurrent", barrier, dates[1], "rechazada"),
    )
    p0.start()
    p1.start()
    p0.join()
    p1.join()
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset("feedback_concurrent", data_dir=tmp_path)
    row0 = final.loc[final["fecha"] == dates[0]].iloc[0]
    row1 = final.loc[final["fecha"] == dates[1]].iloc[0]
    assert row0["estado_validacion"] == "confirmada"
    assert row1["estado_validacion"] == "rechazada"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest tests/test_feedback_registry.py -k atomically -q
```
Expected: `ImportError`/`AttributeError` (`update_feedback_log_atomically` does not exist yet).

- [ ] **Step 3: Implement `update_feedback_log_atomically` in `registry.py`**

Replace the full content of `src/human_feedback/registry.py` with (adds `io`, `Callable` imports, and the new function; keeps every existing function byte-identical otherwise):

```python
"""Persistencia, actualización y unión con predicciones del registro de
retroalimentación (spec human-feedback, requirements "Persistencia del
registro de retroalimentación", "Actualización del registro sin
pérdida de validaciones existentes" e "Integración de la
retroalimentación con los registros de predicción").
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from data_ingestion.storage import (
    DEFAULT_DATA_DIR,
    atomic_write_bytes,
    dataset_lock_path,
    interprocess_lock,
    load_dataset,
    save_dataset,
)
from human_feedback.schema import init_feedback_log


def save_feedback_log(name: str, log: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Guarda un registro de retroalimentación reutilizando el contrato
    `save_dataset` de `data-ingestion`.
    """
    return save_dataset(name, log, data_dir=data_dir)


def load_feedback_log(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Recupera un registro de retroalimentación reutilizando el
    contrato `load_dataset` de `data-ingestion`.
    """
    return load_dataset(name, data_dir=data_dir)


def update_feedback_log_atomically(
    name: str,
    update_fn: Callable[[pd.DataFrame], pd.DataFrame],
    data_dir: Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    """Ejecuta `load -> update_fn -> save` como una única unidad bajo el
    mismo lock interproceso que ya protege `save_dataset` (F-09): sin
    esto, dos ciclos concurrentes pueden leer la misma versión y el
    segundo en escribir sobreescribe silenciosamente la actualización
    del primero ("lost update"). Escribe directamente con
    `atomic_write_bytes` (no vía `save_dataset`) para no anidar una
    segunda adquisición del mismo lock dentro de esta."""
    lock_path = dataset_lock_path(name, data_dir)
    with interprocess_lock(lock_path):
        log = load_dataset(name, data_dir=data_dir)
        updated = update_fn(log)
        buffer = io.BytesIO()
        updated.to_parquet(buffer, index=False)
        atomic_write_bytes(data_dir / f"{name}.parquet", buffer.getvalue())
    return updated


def upsert_feedback_log(
    existing: pd.DataFrame, dates: pd.Series, alerts: pd.Series
) -> pd.DataFrame:
    """Combina un registro existente con alertas recién generadas: las
    fechas nuevas se agregan en estado `pendiente`; las fechas ya
    presentes en `existing` conservan su estado de validación,
    corrección y observación, sin importar el nuevo valor de alerta.
    """
    fresh = init_feedback_log(dates, alerts)
    new_dates_mask = ~fresh["fecha"].isin(existing["fecha"])

    return pd.concat([existing, fresh[new_dates_mask]], ignore_index=True)


def integrate_feedback_with_predictions(
    log: pd.DataFrame, predictions: pd.DataFrame
) -> pd.DataFrame:
    """Une, por fecha, el registro de retroalimentación con la
    probabilidad predicha y la etiqueta real de las predicciones.
    """
    return log.merge(predictions, on="fecha", how="inner")
```

- [ ] **Step 4: Add the public `dataset_lock_path` wrapper in `storage.py`**

`_dataset_lock_path` in `src/data_ingestion/storage.py:108-109` is private. Add a thin public wrapper right after it (do not rename or remove the private one, other internal call sites keep using it unchanged):

```python
def _dataset_lock_path(name: str, data_dir: Path) -> Path:
    return data_dir / ".locks" / f"{name}.lock"


def dataset_lock_path(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Public accessor for the lock path `save_dataset` uses internally,
    so callers that need to protect a load→modify→save cycle spanning
    multiple `data_ingestion.storage` calls (e.g.
    `human_feedback.registry.update_feedback_log_atomically`, F-09) can
    acquire the *same* lock without duplicating the naming scheme."""
    return _dataset_lock_path(name, data_dir)
```
Note `DEFAULT_DATA_DIR` is defined a few lines below `_dataset_lock_path` today (`storage.py:112`) — move `dataset_lock_path`'s definition to after `DEFAULT_DATA_DIR` is defined (i.e., place it right after `DEFAULT_DATA_DIR = ...` and before `save_dataset`), not literally between `_dataset_lock_path` and `DEFAULT_DATA_DIR`, to avoid a `NameError` at import time.

- [ ] **Step 5: Update the router to use the atomic cycle**

Replace `confirm_feedback` and `reject_feedback` in `backend/app/routers/feedback.py`:

```python
from human_feedback.registry import load_feedback_log, update_feedback_log_atomically
```
(replace the existing `from human_feedback.registry import load_feedback_log, save_feedback_log` import line)

```python
@router.post("/feedback/{sensor_id}/{fecha}/confirm", response_model=FeedbackRow)
def confirm_feedback(
    fecha: date_type,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    target = pd.Timestamp(fecha)

    def _apply(log: pd.DataFrame) -> pd.DataFrame:
        _find_date_or_404(log, fecha)
        _require_mature_target(log, target)
        return update_feedback(log, fecha=target, estado_validacion="confirmada")

    try:
        updated = update_feedback_log_atomically(
            feedback_log_name_for(sensor_id), _apply, data_dir=data_dir
        )
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error

    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)


@router.post("/feedback/{sensor_id}/{fecha}/reject", response_model=FeedbackRow)
def reject_feedback(
    fecha: date_type,
    body: RejectRequest,
    sensor_id: str = Depends(get_valid_sensor_id),
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    target = pd.Timestamp(fecha)

    def _apply(log: pd.DataFrame) -> pd.DataFrame:
        _find_date_or_404(log, fecha)
        _require_mature_target(log, target)
        return update_feedback(
            log,
            fecha=target,
            estado_validacion="rechazada",
            etiqueta_corregida=body.etiqueta_corregida,
            observacion=body.observacion,
        )

    try:
        updated = update_feedback_log_atomically(
            feedback_log_name_for(sensor_id), _apply, data_dir=data_dir
        )
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error

    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)
```
`_load_or_404` stays defined and in use by `list_feedback` — do not remove it.

- [ ] **Step 6: Run the new test to verify it passes**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src python -m pytest tests/test_feedback_registry.py -q
```
Expected: all pass, including `test_update_feedback_log_atomically_survives_concurrent_updates_to_different_rows`, re-run 3 times to check for flakiness.

- [ ] **Step 7: Run the existing regression suites named in the encargo**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src:backend python -m pytest backend/tests/test_feedback.py -q
```
Expected: all existing tests pass unmodified (404 on unknown date, isolation per sensor, confirm/reject happy paths) — this confirms the router refactor preserved external behavior exactly.

- [ ] **Step 8: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add src/human_feedback/registry.py src/data_ingestion/storage.py backend/app/routers/feedback.py tests/test_feedback_registry.py
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "fix(F-09): proteger el ciclo load->update->save del feedback legacy con un lock atómico"
```

---

## Task 4: F-06/F-07 — preserve `replay_packages/` bytes via `.gitattributes`

**Files:**
- Modify: `.gitattributes` (append)
- Renormalize (no manual edits): `replay_packages/base-seed4-1157696b7b-v2/manifest.json`, `predictions.json`, `run_metadata.json`, `effective_configuration.json`

**Interfaces:**
- Consumes: nothing (repo configuration only).
- Produces: a working tree whose `replay_packages/**/*.json` and `replay_packages/**/*.parquet` bytes are checkout-independent, for `backend/tests/test_replay.py` (already existing, unmodified) to consume against the real package.

- [ ] **Step 1: Reproduce the defect first, to have a documented before/after**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
git config core.autocrlf
PYTHONPATH=src python -c "
from pathlib import Path
from historical_replay.package_loader import load_package
try:
    load_package(Path('replay_packages/base-seed4-1157696b7b-v2'))
    print('LOADED_OK (unexpected before the fix if autocrlf=true)')
except Exception as e:
    print(type(e).__name__, e)
"
```
Record the output. If `core.autocrlf` is not `true` in this worktree, explicitly note that this reproduction step is machine-dependent (per the audit's own §2) and proceed to Step 5's clean-clone verification, which forces `autocrlf=true` regardless of the ambient config.

- [ ] **Step 2: Append the `.gitattributes` rule**

Append to `.gitattributes` (do not touch the existing `producer-calibration-plan` lines):
```
# replay_packages/: paquetes de reproducción histórica con custody_sha256
# fijado en manifest.json — los bytes deben ser idénticos en cualquier
# checkout; autocrlf no debe alterarlos (ver F-06/F-07, Paso 2 auditoría).
/replay_packages/**/*.json -text
/replay_packages/**/*.parquet -text
```

- [ ] **Step 3: Renormalize the working tree**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
git add .gitattributes
git add --renormalize replay_packages
git status
```
Expected: only files under `replay_packages/` (and `.gitattributes`) appear staged; if `git status` shows changes outside `replay_packages/`/`.gitattributes`, stop — something else is being touched.

- [ ] **Step 4: Verify no logical content changed, only bytes**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
git diff --stat --cached
for f in replay_packages/base-seed4-1157696b7b-v2/manifest.json replay_packages/base-seed4-1157696b7b-v2/predictions.json replay_packages/base-seed4-1157696b7b-v2/run_metadata.json replay_packages/base-seed4-1157696b7b-v2/effective_configuration.json; do
  python -c "
import json, sys
with open('$f', 'rb') as fh:
    raw = fh.read()
json.loads(raw.decode('utf-8'))
print('$f', 'valid JSON,', len(raw), 'bytes')
"
done
```
Compare parsed JSON content (not raw bytes) against `git show origin/main:<path>` for each file — they must be identical objects. Confirm none of the 4 files' `custody_sha256` fields (as declared inside `manifest.json`) were touched — only the on-disk bytes of the files *outside* the JSON's own `custody_sha256` string values may have changed (i.e., only line-ending bytes, if any were present).

- [ ] **Step 5: Verify the fix in an actual `core.autocrlf=true` clean checkout**

This is the acceptance test required by the encargo — do it against a disposable clone, not the shared worktree:
```bash
cd /c/Repo
rm -rf AAI_Hydric_Stress_autocrlf_check
git clone -c core.autocrlf=true /c/Repo/AAI_Hydric_Stress_fix_backend_closure AAI_Hydric_Stress_autocrlf_check
cd AAI_Hydric_Stress_autocrlf_check
git config core.autocrlf   # confirm it reports true
PYTHONPATH=src python -c "
from pathlib import Path
from historical_replay.package_loader import load_package
package = load_package(Path('replay_packages/base-seed4-1157696b7b-v2'))
print('LOADED_OK', package.manifest['schema_version'])
"
```
Expected: `LOADED_OK historical_replay_package_v2`, no `IntegrityError`. This is the direct reproduction of the audit's diagnostic (`f06f07_diagnose_503.py`), now passing.

- [ ] **Step 6: Run `backend/tests/test_replay.py` in that same clean clone**

Reading `replay_packages/base-seed4-1157696b7b-v2/` here is explicitly authorized: it is the acceptance criterion the encargo names verbatim for Corrección 4 ("`backend/tests/test_replay.py` ... pasa sin el bloqueo documentado"), it is an existing versioned regression suite (not an A/B/C run, not a holdout, not a real-data training run), and it only reads/serves the already-committed, byte-verified package. Proceed:
```bash
cd /c/Repo/AAI_Hydric_Stress_autocrlf_check
pip install -e . --no-deps --quiet  # or set PYTHONPATH=src:backend as done elsewhere in this plan
PYTHONPATH=src:backend python -m pytest backend/tests/test_replay.py -q
```
Expected: all tests pass (no 503s). If any *unrelated* dependency/environment issue blocks this (e.g. missing `httpx`/`fastapi` in the ambient interpreter, as the original audit noted for its own environment), record the exact blocker verbatim, mark this specific sub-check as **BLOCKED** (do not report a PASS with a substituted fixture), and state precisely what access/setup would unblock it — per the encargo's explicit instruction not to replace a blocked HTTP check with a synthetic-fixture PASS.

- [ ] **Step 7: Run the same suite back in the working worktree (non-clean-clone) for the normal test loop**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src:backend python -m pytest backend/tests/test_replay.py tests/test_historical_replay_feedback.py -q
```
Expected: all pass — this confirms Task 2's fix and Task 4's fix compose correctly (both touch the historical-replay area, neither regresses the other).

- [ ] **Step 8: Remove the disposable clone**

```bash
rm -rf /c/Repo/AAI_Hydric_Stress_autocrlf_check
```
(a throwaway verification clone, not part of the deliverable — do not commit it, do not leave it as a stray worktree)

- [ ] **Step 9: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add .gitattributes replay_packages
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "fix(F-06/F-07): fijar .gitattributes -text para replay_packages/ y renormalizar el working tree"
```

---

## Task 5: D-06 — write the approval-ready proposal (no implementation)

**Files:**
- Create: `docs/design/backend-d06-replay-history-estado-propuesta.md`

**Interfaces:**
- Consumes: nothing executable — this is a design document, not code.
- Produces: a document for the spec owner to approve or reject; if approved, a *future* encargo (Corrección 5) implements it — this task does not touch `schemas_replay.py`, `history_view.py`, or `replay.py`.

- [ ] **Step 1: Write the document**

Write `docs/design/backend-d06-replay-history-estado-propuesta.md` with these sections (content lifted and organized from the encargo's Ítem 5, not invented — this task is transcription/organization for approval, not new design work):

```markdown
# D-06 — Propuesta: exponer `estado` por fila en `GET /replay/history`

**Estado:** propuesta pendiente de aprobación normativa. NO implementada.
No autoriza a Claude Code (ni a ningún ejecutor) a modificar
`schemas_replay.py`, `history_view.py` ni `replay.py` sin aprobación
explícita de quien tiene autoridad sobre la spec `historical-replay`.

## Origen y obligación vigente

`openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md`
contiene dos requirements **DEBE (MUST)** vigentes:

- **RH-05** (líneas 122-140): para una fecha del historial mostrado antes
  de la revelación cuyo marcador de imputación no fue recomputado, el
  estado DEBE quedar en `no_determinado` — nunca `medida` ni un valor
  numérico inferido.
- **RH-08** (líneas 235-247): ante cualquier dato no resoluble, el
  sistema DEBE mostrar un estado explícito con causa concreta, "en vez
  de omitir el campo".

`backend/app/schemas_replay.py::ReplayHistoryRow` hoy solo tiene `fecha`
y `soil_moisture: float | None` — sin campo de estado. Esto es
exactamente lo que RH-08 prohíbe. `traceability.md` marca RH-05/RH-08
como "[implementada]" pese a admitir esta brecha en su propio texto.

## Base técnica ya existente (bajo riesgo, no requiere construir desde cero)

- `src/historical_replay/imputation_markers.py::reconstruct_imputation_markers`
  ya reconstruye el marcador `<columna>_imputado` de forma determinista y
  verificada (`verify_imputation_source_matches_verified_commit`).
- `src/historical_replay/observations.py` ya define las 4 constantes de
  estado (`MEASURED`, `IMPUTED`, `UNDETERMINED`, `MISSING_FROM_SOURCE`) y
  la lógica de derivación (`link_observation`), hoy usada solo para
  `medicion_original.estado`.
- `backend/app/routers/replay.py:215` ya invoca el código que consume
  `imputation_markers_df`, pero con `imputation_markers_df=None` — la
  brecha es que `history_view.py::filtered_history` nunca lo expone.

## Propuesta concreta

1. **Campo nuevo:** `ReplayHistoryRow.estado: Literal["medida", "imputada", "no_determinado", "sin_dato_en_fuente"]`,
   reutilizando exactamente las constantes de `observations.py`.
2. **Semántica por valor** (idéntica a la ya usada en
   `medicion_original.estado`, extendida a cada fila):
   - `medida`: hay valor crudo para esa fecha y el marcador indica que no
     fue rellenado.
   - `imputada`: hay valor (crudo o reconstruido) y el marcador indica
     que sí fue rellenado por `interpolate_missing_causal`.
   - `sin_dato_en_fuente`: no hay valor crudo para esa fecha y el
     marcador sí cubre esa fecha (se sabe con certeza que faltaba en la
     fuente).
   - `no_determinado`: no se pudo reconstruir el marcador para esa fecha
     (p. ej. `ImputationSourceDriftError`, o la fecha queda fuera del
     rango cubierto) — nunca se infiere un estado por defecto optimista.
3. **Procedencia:** `estado` se deriva exclusivamente de
   `reconstruct_imputation_markers` sobre `dataset/*.parquet` ya
   empaquetado y verificado por hash — nunca de una imputación ad hoc en
   el endpoint. Si `ImputationSourceDriftError` se dispara, la fila queda
   en `no_determinado` para todas las fechas afectadas, nunca falla
   silenciosamente ni devuelve un valor sin marcar.
4. **Comportamiento ante indeterminación:** nunca omitir el campo (lo
   que RH-08 prohíbe); nunca sustituir por `medida` u otro valor
   optimista por defecto; el valor explícito es siempre
   `no_determinado`.
5. **Compatibilidad:** campo aditivo en un modelo Pydantic — no rompe
   consumidores que ignoren campos nuevos; no cambia `soil_moisture` ni
   el contrato de `medicion_original` ya existente.
6. **Corrección de trazabilidad asociada (si se aprueba):**
   `openspec/changes/add-causal-historical-replay/traceability.md` debe
   reflejar "parcialmente implementada: cubre `medicion_original`,
   pendiente en `/replay/history`" para RH-05/RH-08 hasta que la
   Corrección 5 la cierre.

## Qué NO decide esta propuesta

No decide "extender la API" vs. "acotar la spec" — sigue la orientación
ya dada por el usuario de conservar el requisito vigente (RH-05/RH-08
tal como están escritos), y presenta la opción "extender" al nivel de
detalle necesario para que la aprobación sea sobre un diseño concreto.
Si se aprueba, la implementación (con pruebas de aceptación análogas a
las de las Correcciones 2/3 de este mismo cierre) se encarga por
separado, como Corrección 5 de un encargo posterior — no en este PR.

## Qué recibiría un consumidor de `/replay/history` en cada estado

| Estado | `soil_moisture` | `estado` | Significado para el consumidor |
| --- | --- | --- | --- |
| `medida` | valor numérico | `"medida"` | Observación cruda del dataset empaquetado, no rellenada. |
| `imputada` | valor numérico (reconstruido o crudo) | `"imputada"` | El marcador de imputación confirma que este valor fue completado por `interpolate_missing_causal`; no es una medición directa. |
| `sin_dato_en_fuente` | `null` | `"sin_dato_en_fuente"` | Se sabe con certeza que no había dato en la fuente para esa fecha; el marcador lo confirma. |
| `no_determinado` | `null` o el valor crudo si existe, pero sin garantía de estado | `"no_determinado"` | No se pudo reconstruir el marcador (drift de fuente de imputación, fecha fuera de rango). Nunca se infiere `medida` por defecto. |

Ningún estado se acompaña de un valor numérico cuando ese valor sería una
estimación no marcada como tal, y ningún `null` se presenta sin una causa
(`estado`) explícita — esto es exactamente lo que RH-05/RH-08 exigen.
```

- [ ] **Step 2: Confirm no code files changed**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure diff --stat
```
Expected: only `docs/design/backend-d06-replay-history-estado-propuesta.md` is new/staged; `backend/app/schemas_replay.py`, `history_view.py`, `replay.py` untouched.

- [ ] **Step 3: Commit**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure add docs/design/backend-d06-replay-history-estado-propuesta.md
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure commit -m "docs(D-06): propuesta concreta para aprobación — estado por fila en /replay/history (sin implementar)"
```

---

## Task 6: Full verification pass, push, PR

**Files:** none new — this task runs the full affected test surface and opens the PR.

**Interfaces:**
- Consumes: everything from Tasks 0-5.
- Produces: a pushed branch and an open PR describing per-finding results, the reviewed SHA, and the D-06 proposal status.

- [ ] **Step 1: Run every test file named across the encargo, in one pass**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src:backend python -m pytest \
  backend/tests/test_lineage.py \
  tests/test_historical_replay_feedback.py \
  tests/test_feedback_registry.py \
  backend/tests/test_feedback.py \
  backend/tests/test_replay.py \
  -q
```
Record the full output (pass/fail counts) — this is the "resultados por hallazgo" evidence for the PR description.

- [ ] **Step 2: Run the wider existing suite to catch unintended regressions**

```bash
cd /c/Repo/AAI_Hydric_Stress_fix_backend_closure
PYTHONPATH=src:backend python -m pytest tests backend/tests -q
```
Expected: same pass count as the audit's baseline (124 passed outside `test_replay.py`) plus the newly-added tests, plus `test_replay.py` now passing if Task 4 fully resolved the environment's `core.autocrlf`. Note any pre-existing skip/xfail unrelated to this work; do not investigate or fix unrelated failures — flag them in the PR description instead.

- [ ] **Step 3: Final `git status`/`git log` sanity check**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure status
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure log --oneline origin/main..HEAD
```
Expected: clean tree, and the log shows exactly the 6 commits from Tasks 0-5 (docs provenance, D-01, F-08, F-09, F-06/F-07, D-06) — no stray commits.

- [ ] **Step 4: Push and open the PR**

```bash
git -C /c/Repo/AAI_Hydric_Stress_fix_backend_closure push -u origin fix/backend-technical-closure
gh pr create --repo gusjrivas/AAI_Hydric_Stress \
  --base main --head fix/backend-technical-closure \
  --title "fix(backend): cierre técnico paso 2 — D-01, F-08, F-09, F-06/F-07 + propuesta D-06" \
  --body "$(cat <<'EOF'
## Resumen

Implementa las correcciones confirmadas del cierre técnico backend (paso 2),
según `encargo-correccion-claude-code.md` (snapshot auditado
`f17fe658bad4726202fe13784bb716c06468af9a`, sin drift respecto de
`origin/main`). Requiere nueva revisión independiente antes de cualquier
cierre — este PR no declara el backend cerrado y no debe mergearse sin esa
revisión.

- **D-01** (documental): corrige la limitación T-01 obsoleta en
  `openspec/specs/human-feedback/spec.md` sobre el endpoint de linaje
  (`GET /lineage/{sensor_id}`, ya implementado desde `7cdea8b`).
- **F-08** (funcional): `historical_replay.feedback.ReplayFeedbackStore.append`
  ahora serializa escrituras con `interprocess_lock` (mismo mecanismo que
  `human_feedback/operational_repository.py`). Nuevo test de concurrencia
  real con `multiprocessing.Barrier`.
- **F-09** (funcional): nuevo `human_feedback.registry.update_feedback_log_atomically`
  protege el ciclo `load->update->save` del feedback legacy como una sola
  unidad, sin anidar locks; `backend/app/routers/feedback.py` lo usa en
  `confirm_feedback`/`reject_feedback`.
- **F-06/F-07** (config. de repo): `.gitattributes` fija `-text` para
  `replay_packages/**/*.json` y `*.parquet`; working tree renormalizado.
  Verificado en un clon limpio con `core.autocrlf=true` (ver detalle abajo).
  No se tocó `_verify_file_integrity`/`_sha256_of` ni ningún `custody_sha256`.
- **D-06**: propuesta concreta en
  `docs/design/backend-d06-replay-history-estado-propuesta.md`,
  **pendiente de aprobación normativa**, no implementada.

## Resultados por hallazgo

<pegar aquí, antes de abrir el PR, la salida real de Task 6 Step 1 y Step 2:
pass/fail por archivo, y si `backend/tests/test_replay.py` quedó BLOCKED o
PASS en este entorno>

## SHA revisado

- Auditado: `f17fe658bad4726202fe13784bb716c06468af9a`
- `origin/main` en el momento de esta rama: `f17fe658bad4726202fe13784bb716c06468af9a` (0 commits de diferencia)

## Explícitamente pendiente / fuera de alcance

- D-06 sigue sin implementación — requiere aprobación explícita antes de
  convertirse en Corrección 5.
- Ninguna otra corrección de la auditoría (O-01..O-05, ensamble v4,
  `controlled_daily_v3`) fue tocada.
- No se hizo merge; requiere nueva revisión independiente.

## Test plan

- [ ] `backend/tests/test_lineage.py`
- [ ] `tests/test_historical_replay_feedback.py`
- [ ] `tests/test_feedback_registry.py`
- [ ] `backend/tests/test_feedback.py`
- [ ] `backend/tests/test_replay.py` (clon limpio `core.autocrlf=true`)
- [ ] Suite completa `tests` + `backend/tests`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Fill in the "Resultados por hallazgo" placeholder with real output before running `gh pr create` — do not leave it as a placeholder in the actual PR body.

- [ ] **Step 5: Report back**

Give the user: the PR URL, the reviewed SHA (`f17fe658bad4726202fe13784bb716c06468af9a`), a one-line result per finding (D-01/F-08/F-09/F-06/F-07), the D-06 proposal file path, and an explicit statement that the backend is not declared closed pending independent re-review.

---

## Self-review notes

- **Spec coverage:** Corrección 1 (Task 1), Corrección 2 (Task 2), Corrección 3 (Task 3), Corrección 4 (Task 4), Ítem 5/D-06 (Task 5 — prep only, no implementation), provenance copy (Task 0), verification+PR (Task 6) — all encargo items covered, nothing beyond scope (no O-01..O-05, no v4 integration, no `controlled_daily_v3` change).
- **Placeholder scan:** the only literal placeholder left is the PR body's "Resultados por hallazgo" and `<hash>` cells in the provenance table — both are explicitly called out as "fill in with real values before committing/creating the PR," not left as TODOs to guess at.
- **Type consistency:** `update_feedback_log_atomically(name, update_fn, data_dir)` signature is identical between its definition (Task 3 Step 3) and its two call sites (Task 3 Step 5); `dataset_lock_path(name, data_dir)` matches between definition (Task 3 Step 4) and its use inside `update_feedback_log_atomically`.
- **Review Focus:** covered above (autocrlf regression, nested-lock deadlock, lock-file/data-file confusion, spec-doc overreach, `-text` vs. content-rewrite confusion).
