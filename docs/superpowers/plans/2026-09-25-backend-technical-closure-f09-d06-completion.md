# F-09 Completion (forecast.py) + D-06 Implementation (estado/causa in /replay/history) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two gaps the user explicitly re-authorized on top of the already-merged-to-branch corrections in `fix/backend-technical-closure` (PR #216): (1) protect `backend/app/routers/forecast.py`'s feedback read-merge-write cycle with the same lock discipline as `confirm_feedback`/`reject_feedback`, and (2) implement (not just propose) `estado`/`causa` fields on `GET /replay/history` satisfying RH-05/RH-08, while leaving `medicion_original` and the UI untouched.

**Architecture:** F-09 completion extends the existing `human_feedback.registry.update_feedback_log_atomically` with an opt-in `create_if_missing` mode (backward compatible — default behavior unchanged) and adds one new function, `register_forecast_feedback`, that `forecast.py` calls instead of its current unlocked load/concat/save. D-06 adds a new pure classification module (`historical_replay/history_state.py`) that computes `(estado, causa, valor_imputado)` per historical date from the already-existing `reconstruct_imputation_markers` output, wires it into `backend/app/routers/replay.py::get_history`, and adds the two new fields to `ReplayHistoryRow`. Neither task touches `medicion_original`, `schemas_replay.py`'s other models, the frontend, or `_verify_file_integrity`.

**Tech Stack:** Python (FastAPI, pandas), pytest, `multiprocessing.get_context("spawn")` for real concurrency tests (repo convention, see `tests/test_controlled_daily_v4_holdout_ledger.py`).

**Spec:** User's authorization message (this session, 2026-09-25, "Continuá en `fix/backend-technical-closure`..."), `openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md` (RH-05 lines 122-147, RH-08 lines 235-247), `openspec/specs/human-feedback/spec.md` (F-09's existing lock pattern), `docs/design/backend-audit-step2-encargo-correccion.md` (original F-09 scope, now explicitly widened).

## Global Constraints

- No merge to `main`. Commits go on `fix/backend-technical-closure`; PR #216 gets updated, not re-created.
- F-09: reuse `data_ingestion.storage.interprocess_lock` only — no new locking primitive. Never acquire the same lock twice in one call stack.
- F-09: preparation (`execute_configured_pipeline`, `load_predictor_by_id`, `register_predictor`, `init_prediction_feedback`) stays OUTSIDE the lock — only the read-merge-write of the feedback log is protected.
- F-09: never hold a `DataFrame` read before acquiring the lock inside the locked section — re-read the file under the lock.
- F-09: handle the file not existing yet, including two concurrent first-emissions.
- D-06: `soil_moisture` keeps its exact current meaning — the literal raw/original source value, including `null` — never replaced by an imputed estimate.
- D-06: never label a present raw value `"imputada"` merely because processing exists in another representation — raw present always means `estado="medida"`.
- D-06: never accompany a `null` `soil_moisture` with a state that implies an estimate is being shown without a clearly separate, clearly-derived field backing it.
- D-06: `causa` is required (non-null, concrete, non-generic) whenever `estado != "medida"`; distinguishes drift vs. out-of-range vs. genuinely-missing causes.
- D-06: integrity errors (`IntegrityError` from `package_loader`) must keep rejecting the request outright — never caught and turned into `no_determinado`.
- D-06: no change to `medicion_original`'s behavior, to `schemas_replay.py` models other than `ReplayHistoryRow`, or to any frontend file.
- D-06: no new inference/recalibration — only reuse of `reconstruct_imputation_markers`, already verified against the historical commit.
- Every new concurrency test uses `multiprocessing.get_context("spawn")` with module-level worker functions (repo convention).
- Report new test results explicitly — do not reuse the prior 42-test run as evidence for this widened scope.

## Review Focus

- Two concurrent first-time forecast emissions for a brand-new sensor (file doesn't exist yet) — both must survive without one clobbering the other or corrupting the parquet file.
- A forecast emission concurrent with a reject that includes `etiqueta_corregida`/`observacion` — those fields must survive, not just the state.
- `ImputationSourceDriftError` during `/replay/history` — every row must degrade to `no_determinado` with a causa naming the drift, never partially "medida" for the rows that happen to have raw values (raw-present rows still classify as `medida` even under drift, since `estado="medida"` doesn't depend on markers at all — this is the one interaction between the two branches worth double-checking explicitly).
- Re-emission after a human confirm/reject: the immutability rule (`fresh[~fresh.fecha.isin(existing.fecha)]`) must still hold under the new atomic path — a second emission must not resurrect a `pendiente` row over one a human already validated.
- `causa` text leaking future information: since `reconstruct_imputation_markers` runs over the *whole* packaged dataset (not truncated to `simulated_clock`), verify a `causa` for a pre-clock row never differs depending on rows *after* the clock (i.e. confirm the ffill-only, backward-looking nature empirically, not just by re-reading the docstring).

---

## Task 1: Extend `update_feedback_log_atomically` with `create_if_missing`

**Files:**
- Modify: `src/human_feedback/registry.py:41-60`
- Test: `tests/test_feedback_registry.py`

**Interfaces:**
- Consumes: existing `dataset_lock_path`, `interprocess_lock`, `load_dataset`, `atomic_write_bytes` (all already imported in `registry.py`).
- Produces: `update_feedback_log_atomically(name: str, update_fn: Callable[[pd.DataFrame | None], pd.DataFrame], data_dir: Path = DEFAULT_DATA_DIR, *, create_if_missing: bool = False) -> pd.DataFrame`. Default (`create_if_missing=False`) is byte-for-byte the current behavior (`update_fn` receives a real `DataFrame`, `FileNotFoundError` propagates before `update_fn` runs) — Task 4's router code is the only caller that passes `create_if_missing=True`, receiving `None` as `update_fn`'s argument when the file is absent.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_feedback_registry.py`:

```python
def test_update_feedback_log_atomically_creates_the_file_when_missing_and_requested(tmp_path):
    def _apply(existing):
        assert existing is None
        return init_feedback_log(
            pd.to_datetime(["2024-02-01"]), pd.Series([1])
        )

    result = update_feedback_log_atomically(
        "feedback_new", _apply, data_dir=tmp_path, create_if_missing=True
    )

    assert len(result) == 1
    loaded = load_dataset("feedback_new", data_dir=tmp_path)
    pd.testing.assert_frame_equal(loaded, result)


def test_update_feedback_log_atomically_still_raises_when_missing_and_not_requested(tmp_path):
    def _apply(existing):
        raise AssertionError("update_fn must not run when the file is missing and create_if_missing=False")

    with pytest.raises(FileNotFoundError):
        update_feedback_log_atomically("feedback_missing", _apply, data_dir=tmp_path)
```

Add `import pytest` at the top of the test file if not already present.

- [ ] **Step 2: Run test to verify it fails**

Run (from the worktree root, using the established `;`-joined absolute `PYTHONPATH`):
```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_feedback_registry.py -k "creates_the_file_when_missing or still_raises_when_missing" -q
```
Expected: `TypeError: update_feedback_log_atomically() got an unexpected keyword argument 'create_if_missing'`.

- [ ] **Step 3: Implement**

Replace the function in `src/human_feedback/registry.py`:

```python
def update_feedback_log_atomically(
    name: str,
    update_fn: Callable[[pd.DataFrame | None], pd.DataFrame],
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    create_if_missing: bool = False,
) -> pd.DataFrame:
    """Ejecuta `load -> update_fn -> save` como una única unidad bajo el
    mismo lock interproceso que ya protege `save_dataset` (F-09): sin
    esto, dos ciclos concurrentes pueden leer la misma versión y el
    segundo en escribir sobreescribe silenciosamente la actualización
    del primero ("lost update"). Escribe directamente con
    `atomic_write_bytes` (no vía `save_dataset`) para no anidar una
    segunda adquisición del mismo lock dentro de esta.

    Por defecto (`create_if_missing=False`, el comportamiento previo,
    usado por `confirm_feedback`/`reject_feedback`), un archivo ausente
    propaga `FileNotFoundError` antes de invocar `update_fn`. Con
    `create_if_missing=True` (usado por `register_forecast_feedback`,
    F-09 completado para `forecast.py`), un archivo ausente pasa `None`
    a `update_fn`, que debe construir el registro inicial — sin eso, dos
    primeras emisiones concurrentes para el mismo sensor competirían
    por crear el archivo fuera de este lock."""
    lock_path = dataset_lock_path(name, data_dir)
    with interprocess_lock(lock_path):
        try:
            log = load_dataset(name, data_dir=data_dir)
        except FileNotFoundError:
            if not create_if_missing:
                raise
            log = None
        updated = update_fn(log)
        buffer = io.BytesIO()
        updated.to_parquet(buffer, index=False)
        atomic_write_bytes(data_dir / f"{name}.parquet", buffer.getvalue())
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Same command as Step 2. Expected: both tests pass.

- [ ] **Step 5: Run the existing F-09 tests to confirm no regression**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_feedback_registry.py backend/tests/test_feedback.py -q
```
Expected: all pass (the default-path test from the earlier F-09 fix must be unaffected).

- [ ] **Step 6: Commit**

```
git add src/human_feedback/registry.py tests/test_feedback_registry.py
git commit -m "feat(F-09): agregar create_if_missing a update_feedback_log_atomically"
```

---

## Task 2: `register_forecast_feedback` + wire into `forecast.py`

**Files:**
- Modify: `src/human_feedback/registry.py` (add function, after `update_feedback_log_atomically`)
- Modify: `backend/app/routers/forecast.py:12-14,53-62`
- Test: `tests/test_feedback_registry.py` (single-process immutability regression test)
- Test: new file `tests/test_forecast_feedback_concurrency.py` (real multi-process concurrency tests — the acceptance criteria the user asked for; calls the real `register_forecast_feedback` and the real `backend/app/routers/feedback.py::confirm_feedback`/`reject_feedback` directly, never a reimplementation)

**Interfaces:**
- Consumes: Task 1's `update_feedback_log_atomically(..., create_if_missing=True)`.
- Produces: `human_feedback.registry.register_forecast_feedback(name: str, fresh: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame`. `forecast.py::run_forecast` calls this instead of its current inline load/concat/save block; the returned `DataFrame` is used exactly as `merged_feedback` was used before (unchanged downstream: `issued = merged_feedback[merged_feedback.fecha.isin(fresh.fecha)]`, the 409 maturity check, the `Verdict` list construction).

- [ ] **Step 1: Write the failing single-process test (immutability + basic merge)**

Add to `tests/test_feedback_registry.py`:

```python
def test_register_forecast_feedback_creates_the_log_when_absent(tmp_path):
    fresh = init_prediction_feedback(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-03-01", "2024-03-02"]),
                "alert": [1, 0],
                "y_proba": [0.7, 0.2],
            }
        ),
        "model-a",
        horizon_days=3,
        threshold=0.5,
    )

    result = register_forecast_feedback("feedback_forecast", fresh, data_dir=tmp_path)

    assert len(result) == 2
    assert set(result["fecha"]) == set(fresh["fecha"])


def test_register_forecast_feedback_does_not_replace_an_already_registered_prediction(tmp_path):
    first = init_prediction_feedback(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-03-01"]),
                "alert": [1],
                "y_proba": [0.9],
            }
        ),
        "model-a",
        horizon_days=3,
        threshold=0.5,
    )
    register_forecast_feedback("feedback_reemission", first, data_dir=tmp_path)

    second = init_prediction_feedback(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-03-01"]),
                "alert": [0],
                "y_proba": [0.1],
            }
        ),
        "model-b",
        horizon_days=3,
        threshold=0.5,
    )
    result = register_forecast_feedback("feedback_reemission", second, data_dir=tmp_path)

    row = result.loc[result["fecha"] == pd.Timestamp("2024-03-01")].iloc[0]
    assert row["model_version"] == "model-a"
    assert row["y_proba"] == 0.9
```

Add `from human_feedback.registry import register_forecast_feedback` and `from human_feedback.schema import init_prediction_feedback` to the test file's imports (alongside the existing `init_feedback_log, update_feedback` import).

- [ ] **Step 2: Run to verify it fails**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_feedback_registry.py -k register_forecast_feedback -q
```
Expected: `ImportError: cannot import name 'register_forecast_feedback'`.

- [ ] **Step 3: Implement `register_forecast_feedback`**

Add to `src/human_feedback/registry.py`, right after `update_feedback_log_atomically`:

```python
def register_forecast_feedback(
    name: str, fresh: pd.DataFrame, data_dir: Path = DEFAULT_DATA_DIR
) -> pd.DataFrame:
    """Fusiona atómicamente las filas recién emitidas de un pronóstico
    (`fresh`, ya construidas por `human_feedback.schema.init_prediction_feedback`)
    en el registro de retroalimentación de `name`: las filas existentes
    (predicciones, revisiones, correcciones y metadatos ya persistidos)
    nunca se sobreescriben — solo se agregan las fechas de `fresh`
    ausentes del registro vigente. Reutiliza el mismo lock interproceso
    que protege `confirm_feedback`/`reject_feedback` (F-09), incluyendo
    el caso de que el archivo todavía no exista (dos primeras emisiones
    concurrentes para el mismo sensor no compiten por crearlo fuera del
    lock)."""

    def _merge(existing: pd.DataFrame | None) -> pd.DataFrame:
        if existing is None:
            return fresh
        return pd.concat(
            [existing, fresh[~fresh["fecha"].isin(existing["fecha"])]],
            ignore_index=True,
        )

    return update_feedback_log_atomically(
        name, _merge, data_dir=data_dir, create_if_missing=True
    )
```

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: both new tests pass.

- [ ] **Step 5: Wire `forecast.py` to use it**

In `backend/app/routers/forecast.py`, replace the import line:

```python
from human_feedback.registry import register_forecast_feedback
```
(replacing `from human_feedback.registry import load_feedback_log, save_feedback_log`)

Replace the merge block:

```python
    feedback_log_name = feedback_log_name_for(sensor_id)
    merged_feedback = register_forecast_feedback(feedback_log_name, fresh, data_dir=feedback_dir)
```
(replacing the `try:`/`except FileNotFoundError:` block that built `merged_feedback` via `load_feedback_log`/`pd.concat`/`save_feedback_log`)

Everything below (`issued = merged_feedback[...]`, the 409 check, the `Verdict` construction, the response) stays exactly as-is — only the merge-and-persist step changes.

- [ ] **Step 6: Run the existing forecast router tests**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest backend/tests/test_forecast.py -q
```
Expected: `test_run_forecast_returns_verdicts` and `test_run_forecast_isolates_feedback_between_sensors` still fail with the same pre-existing `ConnectionRefusedError` to `localhost:59999` documented in the ledger (no MLflow server in this environment) — confirm the failure is the *same* connection error, not a new one caused by this change (i.e. the traceback must show the `ConnectionRefusedError` happening inside MLflow/model-registry code, not inside `register_forecast_feedback`). If any *other* test in that file exists and doesn't depend on MLflow, it must pass.

- [ ] **Step 7: Write the real multi-process concurrency tests**

Create `tests/test_forecast_feedback_concurrency.py`:

```python
"""F-09 completion: forecast.py's emission cycle now goes through the same
atomic lock as confirm/reject (`human_feedback.registry.register_forecast_feedback`).
These tests call the REAL functions the routers use directly — no
reimplementation, no isolated-helper-only coverage — under real OS
process concurrency (repo convention: `multiprocessing.get_context("spawn")`,
see `tests/test_controlled_daily_v4_holdout_ledger.py`). MLflow/model
training is not involved: `register_forecast_feedback` never touches
MLflow, and `confirm_feedback`/`reject_feedback` never did either — the
risk this file tests is purely the storage-locking contract, so no
doubles are needed for those two real functions.
"""

from __future__ import annotations

import multiprocessing
from datetime import date as date_type
from pathlib import Path

import pandas as pd
import pytest

from app.routers.feedback import confirm_feedback, reject_feedback
from app.schemas import RejectRequest
from data_ingestion.storage import load_dataset
from human_feedback.registry import register_forecast_feedback
from human_feedback.schema import init_feedback_log, init_prediction_feedback, update_feedback

NAME = "feedback_concurrency_forecast"


def _fresh(dates, y_proba, model_version="model-x"):
    return init_prediction_feedback(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(dates),
                "alert": [1] * len(dates),
                "y_proba": y_proba,
            }
        ),
        model_version,
        horizon_days=3,
        threshold=0.5,
    )


def _seed_confirmable_log(data_dir: Path, fecha: str) -> None:
    dates = pd.to_datetime([fecha])
    log = init_feedback_log(dates, pd.Series([1]))
    log["target_timestamp"] = dates + pd.Timedelta(days=3)
    log["model_version"] = "seed-model"
    log["y_proba"] = [0.8]
    log["target_threshold"] = 0.5
    log["issued_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
    log["validated_at"] = pd.NaT
    from human_feedback.registry import save_feedback_log

    save_feedback_log(NAME, log, data_dir=data_dir)


def _worker_emit(data_dir, barrier, dates, y_proba, model_version):
    barrier.wait()
    register_forecast_feedback(NAME, _fresh(dates, y_proba, model_version), data_dir=data_dir)


def _worker_confirm(data_dir, barrier, fecha):
    barrier.wait()
    confirm_feedback(fecha=date_type.fromisoformat(fecha), sensor_id="sensor-x", data_dir=data_dir)


def _worker_reject(data_dir, barrier, fecha, etiqueta, observacion):
    barrier.wait()
    reject_feedback(
        fecha=date_type.fromisoformat(fecha),
        body=RejectRequest(etiqueta_corregida=etiqueta, observacion=observacion),
        sensor_id="sensor-x",
        data_dir=data_dir,
    )


def test_concurrent_emission_and_confirmation_preserve_both(tmp_path):
    _seed_confirmable_log(tmp_path, "2024-04-01")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p_emit = ctx.Process(
        target=_worker_emit, args=(tmp_path, barrier, ["2024-04-10"], [0.6], "model-new")
    )
    p_confirm = ctx.Process(target=_worker_confirm, args=(tmp_path, barrier, "2024-04-01"))
    p_emit.start()
    p_confirm.start()
    p_emit.join(timeout=60)
    p_confirm.join(timeout=60)
    assert p_emit.exitcode == 0
    assert p_confirm.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 2
    confirmed = final.loc[final["fecha"] == pd.Timestamp("2024-04-01")].iloc[0]
    assert confirmed["estado_validacion"] == "confirmada"
    emitted = final.loc[final["fecha"] == pd.Timestamp("2024-04-10")].iloc[0]
    assert emitted["model_version"] == "model-new"


def test_concurrent_emission_and_rejection_preserve_correction_and_observation(tmp_path):
    _seed_confirmable_log(tmp_path, "2024-04-01")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p_emit = ctx.Process(
        target=_worker_emit, args=(tmp_path, barrier, ["2024-04-11"], [0.4], "model-new")
    )
    p_reject = ctx.Process(
        target=_worker_reject, args=(tmp_path, barrier, "2024-04-01", 0, "no habia estres real")
    )
    p_emit.start()
    p_reject.start()
    p_emit.join(timeout=60)
    p_reject.join(timeout=60)
    assert p_emit.exitcode == 0
    assert p_reject.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 2
    rejected = final.loc[final["fecha"] == pd.Timestamp("2024-04-01")].iloc[0]
    assert rejected["estado_validacion"] == "rechazada"
    assert int(rejected["etiqueta_corregida"]) == 0
    assert rejected["observacion"] == "no habia estres real"
    emitted = final.loc[final["fecha"] == pd.Timestamp("2024-04-11")].iloc[0]
    assert emitted["model_version"] == "model-new"


def test_two_concurrent_emissions_with_disjoint_dates_do_not_lose_rows(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(
        target=_worker_emit, args=(tmp_path, barrier, ["2024-05-01", "2024-05-02"], [0.5, 0.5], "model-a")
    )
    p1 = ctx.Process(
        target=_worker_emit, args=(tmp_path, barrier, ["2024-05-03", "2024-05-04"], [0.5, 0.5], "model-b")
    )
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 4
    assert set(final["fecha"]) == {pd.Timestamp(d) for d in ["2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04"]}


def test_two_concurrent_emissions_with_an_overlapping_date_do_not_duplicate_identity(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-06-01"], [0.9], "model-a"))
    p1 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-06-01"], [0.1], "model-b"))
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    matching = final.loc[final["fecha"] == pd.Timestamp("2024-06-01")]
    assert len(matching) == 1
    assert matching.iloc[0]["model_version"] in ("model-a", "model-b")


def test_concurrent_initial_creation_for_a_brand_new_sensor_preserves_a_valid_log(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    p0 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-07-01"], [0.5], "model-a"))
    p1 = ctx.Process(target=_worker_emit, args=(tmp_path, barrier, ["2024-07-02"], [0.5], "model-b"))
    p0.start()
    p1.start()
    p0.join(timeout=60)
    p1.join(timeout=60)
    assert p0.exitcode == 0
    assert p1.exitcode == 0

    final = load_dataset(NAME, data_dir=tmp_path)
    assert len(final) == 2
    assert set(final["fecha"]) == {pd.Timestamp("2024-07-01"), pd.Timestamp("2024-07-02")}
```

- [ ] **Step 8: Run it to verify it fails before the wiring (sanity — revert Step 5 temporarily is NOT required since Task 1+3 already made `register_forecast_feedback` lock-safe by construction; instead, run it now to confirm it PASSES, proving the fix)**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_forecast_feedback_concurrency.py -q
```
Expected: all 5 tests pass. Re-run 3 times (`for i in 1 2 3; do ... done`) to check for flakiness, same as prior F-08/F-09 tests in this branch.

- [ ] **Step 9: Run the full named surface for this task**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_feedback_registry.py tests/test_forecast_feedback_concurrency.py backend/tests/test_feedback.py -q
```
Expected: all pass (forecast.py's own MLflow-dependent tests are checked separately in Step 6, not part of this line).

- [ ] **Step 10: Commit**

```
git add src/human_feedback/registry.py backend/app/routers/forecast.py tests/test_feedback_registry.py tests/test_forecast_feedback_concurrency.py
git commit -m "fix(F-09): completar el lock del ciclo de feedback en forecast.py (registrar emisiones)"
```

---

## Task 3: `historical_replay/history_state.py` — pure per-date classification

**Files:**
- Create: `src/historical_replay/history_state.py`
- Test: create `tests/test_historical_replay_history_state.py`

**Interfaces:**
- Consumes: the state constants already defined in `src/historical_replay/observations.py` (`MEASURED`, `IMPUTED`, `UNDETERMINED`, `MISSING_FROM_SOURCE` — import, do not redefine), and the DataFrame shape `reconstruct_imputation_markers` already produces (a `timestamp` column plus `<label_column>` and `<label_column>_imputado`).
- Produces: `@dataclass(frozen=True) class HistoryRowState: estado: str; causa: str | None; valor_imputado: float | None` and `classify_history_row(*, raw_value: float | None, target_date: date, label_column: str, imputation_markers_df: pd.DataFrame | None, undetermined_causa: str | None = None) -> HistoryRowState`. Task 4 imports both names.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_historical_replay_history_state.py`:

```python
from datetime import date

import pandas as pd

from historical_replay.history_state import HistoryRowState, classify_history_row
from historical_replay.observations import IMPUTED, MEASURED, MISSING_FROM_SOURCE, UNDETERMINED


def test_a_present_raw_value_is_always_medida_regardless_of_markers():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.31],
            "soil_moisture_imputado": [True],  # deliberately inconsistent/degenerate marker
        }
    )

    state = classify_history_row(
        raw_value=0.30,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == MEASURED
    assert state.causa is None
    assert state.valor_imputado is None


def test_missing_marker_dataframe_is_no_determinado_with_a_causa():
    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 2),
        label_column="soil_moisture",
        imputation_markers_df=None,
    )

    assert state.estado == UNDETERMINED
    assert state.causa is not None
    assert "2024-01-02" in state.causa
    assert state.valor_imputado is None


def test_missing_marker_dataframe_uses_the_caller_supplied_causa_when_given():
    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 2),
        label_column="soil_moisture",
        imputation_markers_df=None,
        undetermined_causa="ImputationSourceDriftError: fuente de imputación cambió.",
    )

    assert state.estado == UNDETERMINED
    assert state.causa == "ImputationSourceDriftError: fuente de imputación cambió."


def test_date_absent_from_markers_is_no_determinado():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.30],
            "soil_moisture_imputado": [False],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 5),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == UNDETERMINED
    assert "2024-01-05" in state.causa


def test_raw_absent_and_marker_says_not_imputed_is_sin_dato_en_fuente():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [None],
            "soil_moisture_imputado": [False],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == MISSING_FROM_SOURCE
    assert state.causa is not None
    assert state.valor_imputado is None


def test_raw_absent_and_marker_says_imputed_is_imputada_with_a_separate_derived_value():
    markers = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "soil_moisture": [0.28],
            "soil_moisture_imputado": [True],
        }
    )

    state = classify_history_row(
        raw_value=None,
        target_date=date(2024, 1, 1),
        label_column="soil_moisture",
        imputation_markers_df=markers,
    )

    assert state.estado == IMPUTED
    assert state.causa is not None
    assert state.valor_imputado == 0.28
```

- [ ] **Step 2: Run to verify it fails**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests/test_historical_replay_history_state.py -q
```
Expected: `ModuleNotFoundError: No module named 'historical_replay.history_state'`.

- [ ] **Step 3: Implement**

Create `src/historical_replay/history_state.py`:

```python
"""Per-date measurement state and cause for `GET /replay/history` (spec
`historical-replay`, requirements RH-05/RH-08). Distinct from
`observations.link_observation`, which serves a single prediction's
already-revealed target measurement (`medicion_original`, unchanged by
this module): here, `soil_moisture` in the API response is always the
literal raw source value (including `null`), never substituted by an
estimate — a present raw value is always `medida`, regardless of what any
reconstructed marker says about a different representation of the series.
When a value is genuinely absent from the source but was filled by the
causal imputation pipeline, that fact is exposed as `imputada` with the
reconstructed value in its own clearly-derived field (`valor_imputado`),
never inside `soil_moisture`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from historical_replay.observations import IMPUTED, MEASURED, MISSING_FROM_SOURCE, UNDETERMINED


@dataclass(frozen=True)
class HistoryRowState:
    estado: str
    causa: str | None
    valor_imputado: float | None


def _undetermined(target_date: date, undetermined_causa: str | None) -> HistoryRowState:
    causa = undetermined_causa or (
        f"marcador de imputación no recomputado para la fecha {target_date.isoformat()}."
    )
    return HistoryRowState(estado=UNDETERMINED, causa=causa, valor_imputado=None)


def classify_history_row(
    *,
    raw_value: float | None,
    target_date: date,
    label_column: str,
    imputation_markers_df: pd.DataFrame | None,
    undetermined_causa: str | None = None,
) -> HistoryRowState:
    """`imputation_markers_df=None` covers both "markers could not be
    reconstructed at all for this response" (pass `undetermined_causa`
    naming e.g. `ImputationSourceDriftError`) and, from the caller's
    per-row loop, is never passed differently per date — the per-date
    "marker doesn't cover this date" case is detected internally instead
    and always uses the generic causa unless `undetermined_causa` was
    already supplied by the caller for the whole response."""
    if raw_value is not None:
        return HistoryRowState(estado=MEASURED, causa=None, valor_imputado=None)

    if imputation_markers_df is None:
        return _undetermined(target_date, undetermined_causa)

    marker_dates = pd.to_datetime(imputation_markers_df["timestamp"]).dt.date
    marker_matches = imputation_markers_df.loc[marker_dates == target_date]
    if marker_matches.empty:
        return _undetermined(target_date, undetermined_causa)

    imputed = bool(marker_matches.iloc[0][f"{label_column}_imputado"])
    if not imputed:
        return HistoryRowState(
            estado=MISSING_FROM_SOURCE,
            causa=(
                "ausente en la fuente incluso tras aplicar interpolate_missing_causal "
                f"para la fecha {target_date.isoformat()}."
            ),
            valor_imputado=None,
        )

    reconstructed_cell = marker_matches.iloc[0][label_column]
    valor_imputado = None if pd.isna(reconstructed_cell) else float(reconstructed_cell)
    return HistoryRowState(
        estado=IMPUTED,
        causa=(
            "interpolate_missing_causal completó esta fecha "
            f"({target_date.isoformat()}) a partir de un valor causal anterior; "
            f"identificado por el marcador {label_column}_imputado."
        ),
        valor_imputado=valor_imputado,
    )
```

- [ ] **Step 4: Run to verify it passes**

Same command as Step 2. Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```
git add src/historical_replay/history_state.py tests/test_historical_replay_history_state.py
git commit -m "feat(D-06): agregar historical_replay.history_state con estado/causa por fecha"
```

---

## Task 4: Wire `estado`/`causa`/`valor_imputado` into `/replay/history`

**Files:**
- Modify: `backend/app/schemas_replay.py:92-94` (`ReplayHistoryRow`)
- Modify: `backend/app/routers/replay.py:232-248` (`get_history`)
- Modify: `openspec/changes/add-causal-historical-replay/traceability.md` (RH-05, RH-08 rows)
- Test: `backend/tests/test_replay.py` (extend, using the real package — same convention as the file's other tests)

**Interfaces:**
- Consumes: Task 3's `classify_history_row`/`HistoryRowState`; existing `historical_replay.imputation_markers.{reconstruct_imputation_markers, ImputationSourceDriftError}`; existing `historical_replay.history_view.filtered_history` (unchanged).
- Produces: `ReplayHistoryRow` gains `estado: Literal["medida", "imputada", "no_determinado", "sin_dato_en_fuente"]`, `causa: str | None = None`, `valor_imputado: float | None = None` — additive, `fecha`/`soil_moisture` unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_replay.py` (after `test_history_is_filtered_by_the_simulated_clock`):

```python
def test_history_rows_expose_estado_and_causa():
    client = _client_with_real_package()
    try:
        response = client.get("/replay/history", params={"simulated_date": "2024-10-19"})
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert len(rows) > 0
        for row in rows:
            assert row["estado"] in ("medida", "imputada", "no_determinado", "sin_dato_en_fuente")
            if row["soil_moisture"] is not None:
                # Un valor crudo presente nunca se etiqueta "imputada": es
                # siempre "medida", sin importar ningún marcador (RH-05).
                assert row["estado"] == "medida"
                assert row["causa"] is None
            if row["estado"] != "medida":
                assert row["causa"] is not None and row["causa"] != ""
    finally:
        _clear_overrides()


def test_history_estado_becomes_no_determinado_under_imputation_source_drift(monkeypatch):
    from historical_replay import imputation_markers

    monkeypatch.setitem(
        imputation_markers._VERIFIED_SOURCE_SHA256,
        "data_quality.imputation",
        "0" * 64,
    )
    client = _client_with_real_package()
    try:
        response = client.get("/replay/history", params={"simulated_date": "2024-10-19"})
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert len(rows) > 0
        for row in rows:
            if row["soil_moisture"] is None:
                assert row["estado"] == "no_determinado"
                assert "ImputationSourceDriftError" in row["causa"]
            else:
                assert row["estado"] == "medida"
    finally:
        _clear_overrides()


def test_history_response_is_unaffected_by_dates_after_the_simulated_clock():
    client = _client_with_real_package()
    try:
        early = client.get("/replay/history", params={"simulated_date": "2024-10-19"}).json()
        later_run_same_query = client.get(
            "/replay/history", params={"simulated_date": "2024-10-19"}
        ).json()
        assert early == later_run_same_query
    finally:
        _clear_overrides()
```

- [ ] **Step 2: Run to verify it fails**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest backend/tests/test_replay.py -k "estado_and_causa or imputation_source_drift" -q
```
Expected: `KeyError: 'estado'` (field doesn't exist in the response yet).

- [ ] **Step 3: Add the fields to `ReplayHistoryRow`**

In `backend/app/schemas_replay.py`, replace:

```python
class ReplayHistoryRow(BaseModel):
    fecha: date
    soil_moisture: float | None = None
```
with:

```python
class ReplayHistoryRow(BaseModel):
    fecha: date
    soil_moisture: float | None = None
    estado: Literal["medida", "imputada", "no_determinado", "sin_dato_en_fuente"]
    causa: str | None = None
    valor_imputado: float | None = None
```

- [ ] **Step 4: Wire the router**

In `backend/app/routers/replay.py`, add to the imports:

```python
from historical_replay.history_state import classify_history_row
from historical_replay.imputation_markers import (
    ImputationSourceDriftError,
    reconstruct_imputation_markers,
)
```

Replace `get_history`:

```python
@router.get("/history", response_model=ReplayHistoryResponse)
def get_history(
    simulated_date: date = Query(..., description="Fecha del reloj simulado."),
    package: LoadedReplayPackage = Depends(get_historical_replay_package),
) -> ReplayHistoryResponse:
    label_column = package.manifest["label_rule"]["label_column"]
    history = filtered_history(
        package.dataset, columns=[label_column], simulated_clock=simulated_date
    )

    try:
        markers = reconstruct_imputation_markers(package.dataset, [label_column])
        drift_causa = None
    except ImputationSourceDriftError as error:
        markers = None
        drift_causa = (
            f"ImputationSourceDriftError: {error} No se reconstruyen marcadores "
            "de imputación hasta revisar este cambio."
        )

    rows = []
    for _, row in history.iterrows():
        fecha = row["timestamp"].date()
        raw_value = None if pd.isna(row[label_column]) else float(row[label_column])
        state = classify_history_row(
            raw_value=raw_value,
            target_date=fecha,
            label_column=label_column,
            imputation_markers_df=markers,
            undetermined_causa=drift_causa,
        )
        rows.append(
            ReplayHistoryRow(
                fecha=fecha,
                soil_moisture=raw_value,
                estado=state.estado,
                causa=state.causa,
                valor_imputado=state.valor_imputado,
            )
        )
    return ReplayHistoryResponse(simulated_date=simulated_date, rows=rows)
```

- [ ] **Step 5: Run to verify it passes**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest backend/tests/test_replay.py -q
```
Expected: all pass (this exercises the real package, so it also re-confirms F-06/F-07 stayed fixed).

- [ ] **Step 6: Confirm `medicion_original` and other schemas are untouched**

```
git diff --stat -- backend/app/schemas_replay.py
```
Expected: only `ReplayHistoryRow`'s hunk appears; `MedicionOriginal`, `ReplayPredictionResponse`, etc. unchanged.

- [ ] **Step 7: Update `traceability.md`**

In `openspec/changes/add-causal-historical-replay/traceability.md`, replace the RH-05 row's cell content to add the new coverage (keep the existing unit-test references, append):

Replace:
```
| RH-05 — estados unificados de medición y ausencia de comparación inválida | **[implementada]** `tests/test_historical_replay_imputation_markers.py`, `tests/test_historical_replay_observations.py`; API: `medicion_original.estado` expuesto en `backend/tests/test_replay.py::test_observation_revealed_exactly_at_target_date` | Estados exhibidos y distinguidos explícitamente; ninguna comparación fabricada cuando falta `y_true` | `sin_dato_en_fuente`/`no_determinado` no ejercitados con datos reales de `base-seed4` |
```
with:
```
| RH-05 — estados unificados de medición y ausencia de comparación inválida | **[implementada]** `tests/test_historical_replay_imputation_markers.py`, `tests/test_historical_replay_observations.py`, `tests/test_historical_replay_history_state.py`; API: `medicion_original.estado` expuesto en `backend/tests/test_replay.py::test_observation_revealed_exactly_at_target_date`; estado por fila del historial pre-corte expuesto en `GET /replay/history` (`backend/tests/test_replay.py::test_history_rows_expose_estado_and_causa`, `test_history_estado_becomes_no_determinado_under_imputation_source_drift`) | Estados exhibidos y distinguidos explícitamente en ambos endpoints; ninguna comparación fabricada cuando falta `y_true`; `soil_moisture` sigue siendo siempre el valor crudo original (nunca sustituido), el valor imputado se expone solo en el campo derivado separado `valor_imputado` | `sin_dato_en_fuente`/`no_determinado` con datos reales de `base-seed4` solo se ejercitan de forma sintética (vía drift forzado en el test), porque el paquete real `base-seed4-1157696b7b-v2` no tiene huecos genuinos en el rango replayado |
```

Replace:
```
| RH-08 — estados con causa | **[implementada]** excepciones tipadas del lector y de `feedback.py` con mensaje exacto; a nivel API, errores HTTP con `detail` claro; a nivel interfaz, estados de carga/error/no-disponible/observación-no-disponible explícitos (`HistoricalReplayPage.tsx`) | Mensajes de excepción, respuesta HTTP y estado de UI con causa concreta | El estado `no_determinado`/`sin_dato_en_fuente` no se distingue todavía **por fila del historial pre-corte** (`GET /replay/history` no lo expone) — sí se distingue para la medición del objetivo ya revelado |
```
with:
```
| RH-08 — estados con causa | **[implementada]** excepciones tipadas del lector y de `feedback.py` con mensaje exacto; a nivel API, errores HTTP con `detail` claro; a nivel interfaz, estados de carga/error/no-disponible/observación-no-disponible explícitos (`HistoricalReplayPage.tsx`); `GET /replay/history` expone `causa` concreta por fila cuando `estado != "medida"` (`backend/tests/test_replay.py::test_history_rows_expose_estado_and_causa`) | Mensajes de excepción, respuesta HTTP y estado de UI con causa concreta; causa explícita también por fila del historial pre-corte | El frontend (`HistoricalReplayPage.tsx`) todavía no consume `causa`/`estado` por fila del historial — solo el backend los expone; no se rediseñó la UI en este cambio |
```

- [ ] **Step 8: Run the full replay + history-state surface**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest backend/tests/test_replay.py tests/test_historical_replay_history_state.py tests/test_historical_replay_history_view.py tests/test_historical_replay_observations.py tests/test_historical_replay_imputation_markers.py -q
```
Expected: all pass.

- [ ] **Step 9: Commit**

```
git add backend/app/schemas_replay.py backend/app/routers/replay.py openspec/changes/add-causal-historical-replay/traceability.md backend/tests/test_replay.py
git commit -m "feat(D-06): implementar estado/causa/valor_imputado en GET /replay/history (RH-05/RH-08)"
```

---

## Task 5: Full verification, PR body update, ledger

**Files:** none new.

- [ ] **Step 1: Run every test file this plan touched or depends on, in one pass**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest \
  tests/test_feedback_registry.py \
  tests/test_forecast_feedback_concurrency.py \
  tests/test_historical_replay_history_state.py \
  tests/test_historical_replay_history_view.py \
  tests/test_historical_replay_observations.py \
  tests/test_historical_replay_imputation_markers.py \
  backend/tests/test_feedback.py \
  backend/tests/test_replay.py \
  backend/tests/test_forecast.py \
  backend/tests/test_lineage.py \
  tests/test_historical_replay_feedback.py \
  -q
```
Record the exact pass/fail count. `backend/tests/test_forecast.py`'s two MLflow-dependent tests are expected to still fail with the same pre-existing `ConnectionRefusedError` (Task 2 Step 6 already confirmed this) — everything else must pass.

- [ ] **Step 2: Run the wider suite once more**

```
PYTHONPATH="<worktree>\src;<worktree>\backend" /c/tcnenv/Scripts/python.exe -m pytest tests backend/tests -q
```
Compare against the previously-recorded baseline (1255 passed, 12 skipped, 5 pre-existing environment failures) — the new count should be the old count plus this plan's new tests, with the same 5 (or fewer, never more) pre-existing failures. Any *new* failure outside the 5 known ones must be root-caused before continuing (`superpowers:systematic-debugging`), not waved through.

- [ ] **Step 3: Diff review for historical-evidence safety**

```
git diff --stat f17fe658bad4726202fe13784bb716c06468af9a..HEAD -- replay_packages config data
```
Expected: empty (this plan touches no historical evidence, no `replay_packages/` content, no `controlled_daily_v3`/`config/`).

- [ ] **Step 4: Update the ledger**

Append to the (recreated, if deleted) SDD-style ledger or a plain session note: record that the previous ruling declining to fix `forecast.py`/D-06 has been superseded by this explicit re-authorization, cite the two new commits ranges, and the new test counts (not reusing the prior 42-test figure as evidence for this widened scope, per the user's explicit instruction).

- [ ] **Step 5: Update PR #216's body**

Add a new section (do not delete prior content) documenting: the F-09 completion for `forecast.py`, the D-06 implementation (fields, semantics, traceability update), new test results, and remove/update the earlier "Limitación residual conocida (F-09, alcance del encargo)" section to state it is now resolved (link to the new commits), and remove/adjust the D-06 "pendiente de aprobación normativa, no implementada" line to reflect that it is now implemented, per this explicit authorization.

```
gh pr edit 216 --repo gusjrivas/AAI_Hydric_Stress --body-file <updated body file>
```

- [ ] **Step 6: Push**

```
git push
```
(No merge — same constraint as before.)

## Self-review notes

- **Spec coverage:** F-09's five listed acceptance scenarios (emission+confirm, emission+reject, two emissions disjoint, two emissions overlapping/no duplicate, initial creation race) each map to one test in Task 2 Step 7. D-06's nine listed acceptance scenarios map to: present value → medida (Task 3 test 1, Task 4 test `estado_and_causa`), absent value stays null (Task 4 test, `soil_moisture` assertions), imputed distinguished without silent substitution (Task 3 tests 5-6), marker unavailable/unverifiable → no_determinado with causa (Task 3 tests 2-4, Task 4 drift test), integrity errors keep rejecting (no new exception handling added around `get_historical_replay_package`, verified by inspection in Task 4 Step 4 — not swallowed), dates after the clock absent (unchanged `filtered_history`, re-confirmed by existing `test_only_rows_up_to_the_simulated_clock_are_returned` plus Task 4's new determinism test), future data doesn't change past fields (Review Focus item, Task 4 Step 5's full real-package run plus the determinism test), rewinding conserves hiding (unchanged, `filtered_history` untouched), previously-consumed fields stay compatible (additive-only schema change, Task 4 Step 6).
- **Placeholder scan:** none found — every step has literal code, every test has real assertions, `<worktree>` is a literal placeholder for the actual absolute path already established earlier in this session (`C:\Repo\AAI_Hydric_Stress_fix_backend_closure`), not a plan defect.
- **Type consistency:** `update_feedback_log_atomically`'s new `create_if_missing` parameter (Task 1) is consumed identically in `register_forecast_feedback` (Task 2); `classify_history_row`/`HistoryRowState` (Task 3) field names (`estado`, `causa`, `valor_imputado`) match exactly what Task 4's router code reads off `state.estado`/`state.causa`/`state.valor_imputado` and what `ReplayHistoryRow` exposes.
- **Review Focus:** covered above (concurrent first-creation, reject metadata survival, drift-during-mixed-rows, re-emission immutability under the new atomic path, no-future-leakage) — each has a dedicated test.
