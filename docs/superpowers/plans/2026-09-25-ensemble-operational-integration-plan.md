# Integración operativa del ensamble v4 (Hito 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and test the ensemble contract (Hito 1) defined in `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` — activation, loading, aggregation, persistence, HTTP exposure via the real `/api/v2/sensors/{sensor_id}/forecasts` route, and feedback compatibility. Verified exclusively with synthetic fixtures (no real v4 artifacts exist). Hito 2 (real-enablement plan) is a separate document, not implemented here.

**Architecture:** A new module `src/predictive_modeling/ensemble_bundle.py` wraps the existing, unmodified `load_operational_bundle`/`predict_operational_bundle` three times per horizon and adds cross-component validation + aggregation. `producer_emission.py` branches once, per horizon, on a new `is_ensemble_configured` check — the single-model path is untouched. `schemas_v2.py` and `operational_repository.py` gain additive-only fields.

**Tech Stack:** Python, FastAPI, pandas, scikit-learn (`ScaledLogisticRegression`, `RandomForestClassifier`, `HistGradientBoostingClassifier` — reused from `controlled_daily_v4.models`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (Revisión 3) — read together with this plan; the spec is the argument, this plan is bite-sized execution.

## Changelog — corrections applied during implementation (2026-09-25)

The example code in the sections below is illustrative only, not a validated implementation — it was checked against the real interfaces (`HorizonContract`, `build_estimator`/`fit_estimator`, the real HTTP route, `SlotSeed`, `EnsembleDetail`) before use, and diverged from it where the sketch omitted required fields (`temporal_cuts`, `data_snapshot_sha256`) or used invalid params (`build_estimator(family, {})`).

7 corrections from Codex's review of this plan/spec were applied during implementation, module by module:
1. `_render_forecast` emits one nested `ensemble` object (never loose `ensemble_*` keys); `components` is one ordered list, tested end-to-end (emission, listing, individual lookup) — `src/human_feedback/operational_repository.py`, `backend/app/schemas_v2.py`.
2. Fixtures (`tests/helpers/synthetic_bundles.py`) reuse the real `HorizonContract`/`capture_environment`, include `temporal_cuts`/`data_snapshot_sha256`, and hash the bytes actually written to disk.
3. The three real v4 families are fit with valid `build_estimator` params and each genuinely calibrated on a disjoint synthetic partition via `CalibratedClassifierCV(FrozenEstimator(...), method="sigmoid")` (`operational_run.fit_seed`'s own pattern) — serialization/load/inference of all three plus the aggregate verified through the real, unmodified loader (`tests/test_ensemble_bundle_real_families.py`); `StubEstimator` doubles stay reserved for exact-probability cases (`tests/test_ensemble_bundle.py`). `attach_feature_names` requires an already-fitted estimator, checks the input count, and never overwrites incompatible names (`src/predictive_modeling/bundle_packaging.py`).
4. Manifest/weights/threshold validation rejects NaN/infinities/malformed structure without a fallback; per-horizon unavailability preserves family+cause (`src/predictive_modeling/ensemble_bundle.py`).
5. `EnsembleDetail` binds weights, hashes and a `model_validator` coherence check between probabilities/votes/category/components (`backend/app/schemas_v2.py`).
6. Compatibility verified against the real route (`POST /api/v2/sensors/{sensor_id}/forecasts`, `json={}`, `body["slots"]`) in `backend/tests/test_producer_v2_ensemble.py`; the `ensemble` key is omitted (never `null`) from the hashed idempotency payload for a single-model slot, so legacy retries hash identically (`tests/test_operational_repository_ensemble.py`).
7. No memoria técnica file was touched; absolute "no existen"/"nunca se ejecutó" phrasing was corrected to "no encontrado en lo inspeccionado" in the spec (section 2); Hito 2 remains an unexecuted planning document.

Two real bugs were caught by TDD during this pass (not corrections from review, but worth recording): a byte-identical-stub collision that tripped the intended cross-check for component independence (fixed by using distinct dummy probabilities per family — this happened twice, in two different test files), and a temporal-inadmissibility date mismatch between a fixture's default `trained_through`/`calibrated_through` and a test's `as_of_date`.

## Global Constraints

- Never modify `load_operational_bundle`, `predict_operational_bundle`, `_verify_file_integrity`/`_sha256_of`, anything under `replay_packages/`, or any file in `src/experiment_runner/controlled_daily_v4/` (`freezing.py`, `tuning.py`, stage runners, `models.py`) — only reuse.
- `decision_threshold` stays `0.5`, comparator `>=`, reused verbatim from each component's own bundle — never a new/optimized threshold.
- Weights are always exactly `1/3` per family under `ensemble_agreement_v1` — never renormalized when a component is missing.
- Real HTTP route: `POST /api/v2/sensors/{sensor_id}/forecasts` (verified in `producer_v2.py:380-385`) — never `/producer_v2/forecasts`.
- `display_probability=None`, `probability_status="not_qualified"`, `probability_reason_code="incompatible_assessment"` — reused verbatim, no new qualification logic.
- No training on real data, no A/B/C, no holdout access, no ensemble recalibration.
- Every new persisted field is additive; old records (no `ensemble_*` keys) must render without `KeyError`.

## Review Focus

- A component's `BundleUnavailable` (e.g. temporal inadmissibility) must produce a per-family, per-cause `reason_code` — not a generic "ensemble failed" message, and must not prevent other horizons in the same request from resolving.
- The `0.99, 0.49, 0.49` case (minority vote triggers `combined_alert=True`) flowing through to the feedback endpoint — confirming it must validate `combined_alert`, not `agreement_category`.
- A pre-existing single-model slot for `(sensor, as_of_date, horizon)`, then `ensemble/` gets configured for that sensor/horizon, then the same `(as_of_date, horizon)` is re-emitted — the original slot must be untouched (no recompute, no `forecast_id` change).
- Reading an old persisted forecast record (no `ensemble_*` keys at all) through `_render_forecast` — must not raise `KeyError`, must render `ensemble=None`.
- `attach_feature_names` applied to a calibrator (not just the model) — the loader checks `feature_names_in_` on **both** `model` and `calibrator` (`operational_inference.py:108-113`); forgetting the calibrator would silently break Nivel 2 tests.

---

## Task 1: `ensemble_bundle.py` — manifest, single-family loading, cross-checks

**Files:**
- Create: `src/predictive_modeling/ensemble_bundle.py`
- Test: `tests/test_ensemble_bundle.py`

**Interfaces:**
- Produces: `is_ensemble_configured(bundle_root: Path, *, sensor_id: str, horizon: int) -> bool`; `EnsembleBundle` (`manifest: dict`, `components: dict[str, OperationalBundle]`); `load_ensemble_bundle(bundle_root: Path, *, sensor_id: str, horizon: int) -> EnsembleBundle`; exceptions `EnsembleManifestMissingError`, `EnsembleManifestInvalidError`, `EnsembleComponentMissingError`, `EnsembleBundleIncompatible` (all `ValueError` subclasses, each carrying the exact family/field in their message); `SUPPORTED_FAMILIES = ("logistic_regression", "random_forest", "hist_gradient_boosting_classifier")`; `SUPPORTED_POLICY_VERSIONS = {"ensemble_agreement_v1"}`.
- Consumes: `predictive_modeling.operational_inference.{load_operational_bundle, OperationalBundle, BundleUnavailable}` (unmodified).

- [ ] **Step 1: Write failing tests for `is_ensemble_configured`**

```python
def test_is_ensemble_configured_false_when_neither_signal_present(tmp_path):
    assert not is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)

def test_is_ensemble_configured_true_when_ensemble_dir_exists(tmp_path):
    (tmp_path / "s1" / "horizon_1" / "ensemble").mkdir(parents=True)
    assert is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)

def test_is_ensemble_configured_true_when_only_manifest_file_exists(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    (d / "ensemble_manifest.json").write_text("{}")
    assert is_ensemble_configured(tmp_path, sensor_id="s1", horizon=1)
```
Run: `pytest tests/test_ensemble_bundle.py -k is_ensemble_configured -v` → Expected: `ImportError` (module doesn't exist).

- [ ] **Step 2: Implement `is_ensemble_configured`**

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from predictive_modeling.operational_inference import BundleUnavailable, OperationalBundle, load_operational_bundle

SUPPORTED_FAMILIES = ("logistic_regression", "random_forest", "hist_gradient_boosting_classifier")
SUPPORTED_POLICY_VERSIONS = {"ensemble_agreement_v1"}

_CROSS_CHECK_BUNDLE_FIELDS = ("decision_threshold", "feature_columns", "feature_names", "lags", "rolling_windows")
_CROSS_CHECK_CONTRACT_FIELDS = ("sensor_id", "horizon_days", "contract_version", "imputation", "variables")
_CROSS_CHECK_EVENT_FIELDS = ("variable", "threshold", "unit", "comparison")


class EnsembleManifestMissingError(ValueError):
    pass


class EnsembleManifestInvalidError(ValueError):
    pass


class EnsembleComponentMissingError(ValueError):
    pass


class EnsembleBundleIncompatible(ValueError):
    pass


def _horizon_dir(bundle_root: Path, sensor_id: str, horizon: int) -> Path:
    return Path(bundle_root) / sensor_id / f"horizon_{horizon}"


def is_ensemble_configured(bundle_root: Path, *, sensor_id: str, horizon: int) -> bool:
    horizon_dir = _horizon_dir(bundle_root, sensor_id, horizon)
    return (horizon_dir / "ensemble").exists() or (horizon_dir / "ensemble_manifest.json").exists()


@dataclass(frozen=True)
class EnsembleBundle:
    manifest: dict
    components: dict[str, OperationalBundle]
```

- [ ] **Step 3: Run to verify it passes**

`pytest tests/test_ensemble_bundle.py -k is_ensemble_configured -v` → Expected: 3 passed.

- [ ] **Step 4: Write failing tests for manifest validation (`load_ensemble_bundle`, manifest-level failures)**

```python
def _write_manifest(path, **overrides):
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": "ensemble_agreement_v1",
        "sensor_id": "s1",
        "horizon_days": 1,
        "contract_version": "producer_daily_h123_v1",
        "families": list(SUPPORTED_FAMILIES),
        "weights": {f: 1 / 3 for f in SUPPORTED_FAMILIES},
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest))
    return manifest


def test_load_ensemble_bundle_raises_when_manifest_missing(tmp_path):
    (tmp_path / "s1" / "horizon_1" / "ensemble").mkdir(parents=True)
    with pytest.raises(EnsembleManifestMissingError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_unsupported_policy_version(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_manifest(d / "ensemble_manifest.json", policy_version="future_v99")
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_non_uniform_weights(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_manifest(
        d / "ensemble_manifest.json",
        weights={"logistic_regression": 0.5, "random_forest": 0.25, "hist_gradient_boosting_classifier": 0.25},
    )
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)


def test_load_ensemble_bundle_raises_on_wrong_family_set(tmp_path):
    d = tmp_path / "s1" / "horizon_1"
    d.mkdir(parents=True)
    _write_manifest(d / "ensemble_manifest.json", families=["logistic_regression", "random_forest"])
    with pytest.raises(EnsembleManifestInvalidError):
        load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
```

- [ ] **Step 5: Run to verify RED**

Expected: `NameError`/`ImportError` (`load_ensemble_bundle` not defined yet).

- [ ] **Step 6: Implement manifest validation + per-family loading + cross-checks**

```python
def load_ensemble_bundle(bundle_root: Path, *, sensor_id: str, horizon: int) -> EnsembleBundle:
    horizon_dir = _horizon_dir(bundle_root, sensor_id, horizon)
    manifest_path = horizon_dir / "ensemble_manifest.json"
    if not manifest_path.exists():
        raise EnsembleManifestMissingError(f"ensemble_manifest.json ausente en {horizon_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise EnsembleManifestInvalidError(f"ensemble_manifest.json inválido: {error}") from error

    if manifest.get("format_version") != 1:
        raise EnsembleManifestInvalidError("format_version debe ser 1")
    if manifest.get("mode") != "ensemble":
        raise EnsembleManifestInvalidError("mode debe ser 'ensemble'")
    if manifest.get("sensor_id") != sensor_id or manifest.get("horizon_days") != horizon:
        raise EnsembleManifestInvalidError("sensor_id/horizon_days no coinciden con la ruta")
    if manifest.get("policy_version") not in SUPPORTED_POLICY_VERSIONS:
        raise EnsembleManifestInvalidError(f"policy_version no soportada: {manifest.get('policy_version')!r}")
    families = manifest.get("families")
    if not families or set(families) != set(SUPPORTED_FAMILIES) or len(families) != len(SUPPORTED_FAMILIES):
        raise EnsembleManifestInvalidError(f"families debe ser exactamente {SUPPORTED_FAMILIES}")
    weights = manifest.get("weights", {})
    for family in SUPPORTED_FAMILIES:
        if abs(weights.get(family, 0) - 1 / 3) > 1e-9:
            raise EnsembleManifestInvalidError(f"weights debe ser 1/3 uniforme; {family}={weights.get(family)!r}")

    components: dict[str, OperationalBundle] = {}
    for family in SUPPORTED_FAMILIES:
        family_dir = horizon_dir / "ensemble" / family
        if not family_dir.exists():
            raise EnsembleComponentMissingError(f"ensemble_component_missing:{family}")
        components[family] = load_operational_bundle(family_dir, sensor_id=sensor_id, horizon=horizon)

    _cross_check_components(components)
    return EnsembleBundle(manifest=manifest, components=components)


def _cross_check_components(components: dict[str, OperationalBundle]) -> None:
    families = sorted(components)
    reference_family = families[0]
    reference = components[reference_family].metadata
    for family in families[1:]:
        candidate = components[family].metadata
        for field in _CROSS_CHECK_BUNDLE_FIELDS:
            if candidate.get(field) != reference.get(field):
                raise EnsembleBundleIncompatible(
                    f"{field}: {reference.get(field)!r} ({reference_family}) != {candidate.get(field)!r} ({family})"
                )
        ref_contract, cand_contract = reference["contract"], candidate["contract"]
        for field in _CROSS_CHECK_CONTRACT_FIELDS:
            if ref_contract.get(field) != cand_contract.get(field):
                raise EnsembleBundleIncompatible(
                    f"contract.{field}: {ref_contract.get(field)!r} ({reference_family}) != "
                    f"{cand_contract.get(field)!r} ({family})"
                )
        ref_event, cand_event = ref_contract["event"], cand_contract["event"]
        for field in _CROSS_CHECK_EVENT_FIELDS:
            if ref_event.get(field) != cand_event.get(field):
                raise EnsembleBundleIncompatible(
                    f"event.{field}: {ref_event.get(field)!r} ({reference_family}) != "
                    f"{cand_event.get(field)!r} ({family})"
                )
```

- [ ] **Step 7: Run to verify it passes**

`pytest tests/test_ensemble_bundle.py -v` → all pass so far.

- [ ] **Step 8: Write + pass failing tests for component-missing and cross-check-incompatible, using real synthetic single-family bundles**

Add a test helper (in the same test file, reused by Task 3 too) that builds a minimal valid single-family bundle via `operational_run_artifacts`-equivalent (a small local helper writing `model.joblib`/`calibrator.joblib`/`contract.json`/`bundle.json` with stub `predict_proba`-capable objects — see Task 3 Step 1 for the shared fixture builder; import it here once written, or write a minimal local version now and consolidate in Task 3). Test: build all 3 family dirs valid except delete `random_forest`'s directory → `EnsembleComponentMissingError`. Test: build all 3 valid but give `hist_gradient_boosting_classifier` a different `event.threshold` in its `contract.json`/`bundle.json` → `EnsembleBundleIncompatible` mentioning `event.threshold`.

- [ ] **Step 9: Commit**

```bash
git add src/predictive_modeling/ensemble_bundle.py tests/test_ensemble_bundle.py
git commit -m "feat(ensemble): manifiesto, carga por familia y cross-checks (load_ensemble_bundle)"
```

---

## Task 2: `bundle_packaging.py` — `attach_feature_names` adapter

**Files:**
- Create: `src/predictive_modeling/bundle_packaging.py`
- Test: `tests/test_bundle_packaging.py`

**Interfaces:**
- Produces: `attach_feature_names(estimator: Any, feature_columns: list[str]) -> None` (mutates in place).
- Consumes: nothing new (plain numpy).

- [ ] **Step 1: Write failing test**

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from predictive_modeling.bundle_packaging import attach_feature_names


def test_attach_feature_names_sets_attribute_matching_fit_order():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    y = np.array([0, 1, 0, 1])
    model = RandomForestClassifier(n_estimators=2, random_state=0).fit(X, y)
    assert not hasattr(model, "feature_names_in_")

    attach_feature_names(model, ["temperature", "humidity"])

    assert list(model.feature_names_in_) == ["temperature", "humidity"]
```

- [ ] **Step 2: Run to verify RED**

`pytest tests/test_bundle_packaging.py -v` → `ImportError`.

- [ ] **Step 3: Implement**

```python
from __future__ import annotations

from typing import Any

import numpy as np


def attach_feature_names(estimator: Any, feature_columns: list[str]) -> None:
    """Restituye `feature_names_in_` sobre un estimador ya ajustado con un
    array (no un DataFrame) — scikit-learn solo autopuebla ese atributo
    cuando `.fit()` recibe un DataFrame; `controlled_daily_v4` ajusta
    deliberadamente con arrays (frozen, no se modifica). Esto no falsea
    metadatos: el estimador fue efectivamente ajustado con estas columnas,
    en este orden — solo se restituye el atributo convencional que el
    camino por array no generó."""
    estimator.feature_names_in_ = np.array(feature_columns, dtype=object)
```

- [ ] **Step 4: Run to verify it passes**

`pytest tests/test_bundle_packaging.py -v` → 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/predictive_modeling/bundle_packaging.py tests/test_bundle_packaging.py
git commit -m "feat(ensemble): adaptador attach_feature_names para empaquetar modelos ajustados con arrays"
```

---

## Task 3: Synthetic bundle-builder test fixtures (Nivel 1 stub + Nivel 2 real families)

**Files:**
- Create: `tests/helpers/synthetic_bundles.py`
- Test: exercised by Tasks 1, 4, 5's own test files (this task just builds the helper + a smoke test for itself)
- Test: `tests/helpers/test_synthetic_bundles.py`

**Interfaces:**
- Produces: `write_single_bundle(root: Path, *, sensor_id: str, horizon: int, decision_threshold: float = 0.5, event: dict | None = None, feature_columns: list[str] | None = None, model, calibrator, model_sha256_seed: str) -> None` (writes `model.joblib`/`calibrator.joblib`/`contract.json`/`bundle.json` at `root`, matching the real `bundle.json` shape from `operational_run_artifacts.py`); `write_ensemble_manifest(root: Path, *, sensor_id: str, horizon: int, contract_version: str) -> None`; `StubEstimator` (Nivel 1: fixed `predict_proba` output, `classes_=[0,1]`, `feature_names_in_` settable); `build_real_family_estimator(family: str, X, y) -> Any` (Nivel 2: calls `controlled_daily_v4.models.build_estimator`/`fit_estimator` unmodified, then `attach_feature_names`).

- [ ] **Step 1: Write the fixture module (no separate failing test first — this is test infrastructure, not production behavior; verify via Step 2's smoke test instead, per TDD's own guidance that test helpers are verified by the tests that use them)**

```python
"""Fixtures compartidas para pruebas de ensamble — nunca datos reales,
nunca artefactos v4 reales (no existen). Nivel 1 (stubs) para casos
exactos de probabilidad; Nivel 2 (familias reales de v4 ajustadas sobre
datos sintéticos) para la integración de carga/serialización real."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from predictive_modeling.bundle_packaging import attach_feature_names

DEFAULT_FEATURE_COLUMNS = ["temperature", "relative_humidity"]
DEFAULT_EVENT = {"variable": "soil_moisture", "threshold": 0.3, "unit": "m3/m3", "comparison": "lt"}


@dataclass
class StubEstimator:
    positive_probability: float
    classes_: list[int] = field(default_factory=lambda: [0, 1])
    feature_names_in_: np.ndarray | None = None

    def predict_proba(self, X):
        n = len(X)
        return np.array([[1 - self.positive_probability, self.positive_probability]] * n)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_single_bundle(
    root: Path,
    *,
    sensor_id: str,
    horizon: int,
    decision_threshold: float = 0.5,
    event: dict | None = None,
    feature_columns: list[str] | None = None,
    model: Any,
    calibrator: Any,
    contract_version: str = "producer_daily_h123_v1",
    trained_through: str = "2026-01-01",
    calibrated_through: str = "2026-01-15",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    feature_columns = feature_columns or DEFAULT_FEATURE_COLUMNS
    event = event or DEFAULT_EVENT

    model_bytes = io.BytesIO()
    joblib.dump(model, model_bytes)
    calibrator_bytes = io.BytesIO()
    joblib.dump(calibrator, calibrator_bytes)
    (root / "model.joblib").write_bytes(model_bytes.getvalue())
    (root / "calibrator.joblib").write_bytes(calibrator_bytes.getvalue())

    contract = {
        "artifact_state": "trained_bundle",
        "sensor_id": sensor_id,
        "horizon_days": horizon,
        "contract_version": contract_version,
        "imputation": "none_grid_gaps_preserved",
        "variables": [{"name": c, "unit": "unit"} for c in feature_columns],
        "event": event,
        "trained_through": trained_through,
        "calibrated_through": calibrated_through,
        "model_identity": {
            "version": f"{sensor_id}_h{horizon}_{contract_version}_model",
            "sha256": _sha256_bytes(model_bytes.getvalue()),
            "contract_version": contract_version,
            "horizon_days": horizon,
        },
        "calibrator_identity": {
            "version": f"{sensor_id}_h{horizon}_{contract_version}_calibrator",
            "sha256": _sha256_bytes(calibrator_bytes.getvalue()),
            "contract_version": contract_version,
            "horizon_days": horizon,
        },
    }
    (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")

    bundle = {
        "format_version": 1,
        "contract": contract,
        "decision_threshold": decision_threshold,
        "feature_columns": feature_columns,
        "feature_names": feature_columns,
        "lags": [],
        "rolling_windows": [],
        "environment": {"python": "3.11.16", "dependencies": {}},
        "files": {
            "model.joblib": _sha256_bytes(model_bytes.getvalue()),
            "calibrator.joblib": _sha256_bytes(calibrator_bytes.getvalue()),
            "contract.json": _sha256_bytes(json.dumps(contract).encode("utf-8")),
        },
    }
    (root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")


def write_ensemble_manifest(root: Path, *, sensor_id: str, horizon: int, contract_version: str) -> None:
    manifest = {
        "format_version": 1,
        "mode": "ensemble",
        "policy_version": "ensemble_agreement_v1",
        "sensor_id": sensor_id,
        "horizon_days": horizon,
        "contract_version": contract_version,
        "families": ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"],
        "weights": {
            "logistic_regression": 1 / 3,
            "random_forest": 1 / 3,
            "hist_gradient_boosting_classifier": 1 / 3,
        },
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "ensemble_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def build_real_family_estimator(family: str, X, y):
    from experiment_runner.controlled_daily_v4.models import build_estimator

    estimator = build_estimator(family, {})
    estimator.fit(X, y)
    return estimator
```

- [ ] **Step 2: Smoke test the helper itself**

```python
import numpy as np

from tests.helpers.synthetic_bundles import StubEstimator, write_single_bundle
from predictive_modeling.operational_inference import load_operational_bundle


def test_write_single_bundle_is_loadable_by_the_real_loader(tmp_path):
    model = StubEstimator(positive_probability=0.7)
    calibrator = StubEstimator(positive_probability=0.7)
    write_single_bundle(
        tmp_path, sensor_id="s1", horizon=1, model=model, calibrator=calibrator,
        feature_columns=["temperature", "relative_humidity"],
    )
    bundle = load_operational_bundle(tmp_path, sensor_id="s1", horizon=1)
    assert bundle.metadata["decision_threshold"] == 0.5
```
Run: `pytest tests/helpers/test_synthetic_bundles.py -v` → must pass first try (it's exercising the already-existing, unmodified `load_operational_bundle`) — if it fails, the fixture's `bundle.json`/`contract.json` shape is wrong relative to what the real loader expects; fix the fixture (not the loader) until it matches (`operational_inference.py:55-124`, re-read exact keys).

- [ ] **Step 3: Commit**

```bash
git add tests/helpers/synthetic_bundles.py tests/helpers/test_synthetic_bundles.py
git commit -m "test(ensemble): fixtures compartidas de bundles sintéticos (stub y familias reales)"
```

---

## Task 4: Aggregation — `predict_ensemble_bundle`, thresholds, `score_kind`, identity

**Files:**
- Modify: `src/predictive_modeling/ensemble_bundle.py`
- Test: `tests/test_ensemble_bundle.py` (extend)

**Interfaces:**
- Consumes: Task 1's `EnsembleBundle`; `predictive_modeling.operational_inference.predict_operational_bundle` (unmodified).
- Produces: `predict_ensemble_bundle(ensemble: EnsembleBundle, dataframe, *, sensor_id: str, units: dict, as_of_date: date) -> dict` with keys: `horizon_days, target_date, combined_probability, combined_alert, positive_votes, agreement_category, decision_threshold, trained_through, calibrated_through, ensemble_identity_sha256, components: dict[str, dict]` (per-family: `score, alert, decision_threshold, trained_through, calibrated_through, model_reference`); `compute_ensemble_identity(manifest, components) -> str`; `AGREEMENT_CATEGORIES = {3: "alerta_por_unanimidad", 2: "posible_alerta_acuerdo_parcial", 1: "sin_alerta_por_mayoria_con_discrepancia", 0: "sin_alerta_por_unanimidad"}`; exception `EnsembleTemporalInadmissibleError` (though in practice this surfaces as each component's own `BundleUnavailable("model_not_available_at_date")`, propagated per 3.1 — no separate check needed here since `predict_operational_bundle` already enforces it per component).

- [ ] **Step 1: Write the two exact discrepancy-case tests (the core acceptance test of this whole plan)**

```python
from datetime import date

from predictive_modeling.ensemble_bundle import (
    EnsembleBundle,
    predict_ensemble_bundle,
)
from predictive_modeling.operational_inference import OperationalBundle


def _bundle_with_probability(p: float, *, decision_threshold=0.5, trained_through="2026-01-01", calibrated_through="2026-01-15"):
    metadata = {
        "decision_threshold": decision_threshold,
        "contract": {
            "trained_through": trained_through,
            "calibrated_through": calibrated_through,
            "model_identity": {"version": "m", "sha256": "aaa"},
            "calibrator_identity": {"version": "c", "sha256": "bbb"},
            "contract_version": "producer_daily_h123_v1",
        },
        "files": {"model.joblib": "aaa", "calibrator.joblib": "bbb"},
    }
    return OperationalBundle(metadata=metadata, model=_ConstProb(p), calibrator=_ConstProb(p))


class _ConstProb:
    def __init__(self, p):
        self._p = p
        self.classes_ = [0, 1]

    def predict_proba(self, X):
        import numpy as np
        return np.array([[1 - self._p, self._p]] * len(X))


def _fake_predict_operational_bundle(monkeypatch, probabilities: dict[str, float]):
    from predictive_modeling import ensemble_bundle as mod

    def _fake(bundle, dataframe, *, sensor_id, units, as_of_date):
        p = bundle.model._p  # the _ConstProb instance we built above
        return {
            "alert": p >= bundle.metadata["decision_threshold"],
            "score": p,
            "decision_threshold": bundle.metadata["decision_threshold"],
            "model_reference": {
                "model_version": bundle.metadata["contract"]["model_identity"]["version"],
                "horizon_days": 1,
                "contract_version": bundle.metadata["contract"]["contract_version"],
                "trained_through": bundle.metadata["contract"]["trained_through"],
                "calibration_version": bundle.metadata["contract"]["calibrator_identity"]["version"],
            },
        }

    monkeypatch.setattr(mod, "predict_operational_bundle", _fake)


def test_discrepancy_case_majority_says_possible_alert_but_average_says_no(monkeypatch):
    components = {
        "logistic_regression": _bundle_with_probability(0.51),
        "random_forest": _bundle_with_probability(0.51),
        "hist_gradient_boosting_classifier": _bundle_with_probability(0.01),
    }
    _fake_predict_operational_bundle(monkeypatch, {})
    ensemble = EnsembleBundle(manifest={"weights": {k: 1 / 3 for k in components}, "policy_version": "ensemble_agreement_v1"}, components=components)

    result = predict_ensemble_bundle(ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1))

    assert result["positive_votes"] == 2
    assert result["agreement_category"] == "posible_alerta_acuerdo_parcial"
    assert abs(result["combined_probability"] - 0.34333333333333327) < 1e-9
    assert result["combined_alert"] is False


def test_discrepancy_case_minority_says_alert_but_average_agrees(monkeypatch):
    components = {
        "logistic_regression": _bundle_with_probability(0.99),
        "random_forest": _bundle_with_probability(0.49),
        "hist_gradient_boosting_classifier": _bundle_with_probability(0.49),
    }
    _fake_predict_operational_bundle(monkeypatch, {})
    ensemble = EnsembleBundle(manifest={"weights": {k: 1 / 3 for k in components}, "policy_version": "ensemble_agreement_v1"}, components=components)

    result = predict_ensemble_bundle(ensemble, dataframe=None, sensor_id="s1", units={}, as_of_date=date(2026, 6, 1))

    assert result["positive_votes"] == 1
    assert result["agreement_category"] == "sin_alerta_por_mayoria_con_discrepancia"
    assert abs(result["combined_probability"] - 0.6566666666666667) < 1e-9
    assert result["combined_alert"] is True
```
(Note: this test monkeypatches `predict_operational_bundle` at the module level used by `ensemble_bundle.py` — a deliberate Nivel 1 "doble controlado", per spec 3.8, isolating the aggregation arithmetic from the real per-bundle prediction path, which Task 1/3's other tests and Task 6's Nivel 2 test exercise separately.)

- [ ] **Step 2: Run to verify RED**

`pytest tests/test_ensemble_bundle.py -k discrepancy -v` → `ImportError`/`AttributeError` (`predict_ensemble_bundle` doesn't exist).

- [ ] **Step 3: Implement**

```python
import predictive_modeling.operational_inference as _operational_inference  # noqa: E402  (module-level import so tests can monkeypatch predict_operational_bundle on this module)
from predictive_modeling.operational_inference import predict_operational_bundle  # re-exported name used below

AGREEMENT_CATEGORIES = {
    3: "alerta_por_unanimidad",
    2: "posible_alerta_acuerdo_parcial",
    1: "sin_alerta_por_mayoria_con_discrepancia",
    0: "sin_alerta_por_unanimidad",
}


def compute_ensemble_identity(manifest: dict, components: dict) -> str:
    payload = {
        "policy_version": manifest["policy_version"],
        "weights": manifest["weights"],
        "components": {
            family: {
                "model_sha256": bundle.metadata["files"]["model.joblib"],
                "calibrator_sha256": bundle.metadata["files"]["calibrator.joblib"],
            }
            for family, bundle in sorted(components.items())
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def predict_ensemble_bundle(ensemble: EnsembleBundle, dataframe, *, sensor_id: str, units: dict, as_of_date) -> dict:
    per_family = {}
    for family, bundle in ensemble.components.items():
        per_family[family] = predict_operational_bundle(
            bundle, dataframe, sensor_id=sensor_id, units=units, as_of_date=as_of_date
        )

    decision_threshold = next(iter(per_family.values()))["decision_threshold"]
    probabilities = [r["score"] for r in per_family.values()]
    combined_probability = sum(probabilities) / len(probabilities)
    combined_alert = combined_probability >= decision_threshold
    positive_votes = sum(1 for r in per_family.values() if r["alert"])
    agreement_category = AGREEMENT_CATEGORIES[positive_votes]

    trained_through = max(r["model_reference"]["trained_through"] for r in per_family.values())
    calibrated_through = max(
        ensemble.components[family].metadata["contract"]["calibrated_through"] for family in per_family
    )

    return {
        "horizon_days": next(iter(per_family.values())).get("horizon_days"),
        "combined_probability": combined_probability,
        "combined_alert": combined_alert,
        "positive_votes": positive_votes,
        "agreement_category": agreement_category,
        "decision_threshold": decision_threshold,
        "trained_through": trained_through,
        "calibrated_through": calibrated_through,
        "ensemble_identity_sha256": compute_ensemble_identity(ensemble.manifest, ensemble.components),
        "components": {
            family: {
                "score": r["score"],
                "alert": r["alert"],
                "decision_threshold": r["decision_threshold"],
                "trained_through": r["model_reference"]["trained_through"],
                "calibrated_through": ensemble.components[family].metadata["contract"]["calibrated_through"],
                "model_reference": r["model_reference"],
            }
            for family, r in per_family.items()
        },
    }
```

- [ ] **Step 4: Run to verify it passes**

`pytest tests/test_ensemble_bundle.py -k discrepancy -v` → 2 passed, with the exact float assertions holding.

- [ ] **Step 5: Add and pass the remaining aggregation tests from spec 3.3/3.8**

4 vote combinations (3/3, 2/3, 1/3, 0/3) using simple round-number probabilities (e.g. all `0.9`/all `0.1`/mixed); boundary at exactly `0.5` for one component and for the average; a component `BundleUnavailable` propagating with family+cause preserved (patch `predict_operational_bundle` to raise `BundleUnavailable("model_not_available_at_date")` for one family, assert the exception surfaces with that family identifiable).

- [ ] **Step 6: Run full file, commit**

```bash
git add src/predictive_modeling/ensemble_bundle.py tests/test_ensemble_bundle.py
git commit -m "feat(ensemble): agregación (predict_ensemble_bundle), identidad determinista, casos de discrepancia"
```

---

## Task 5: `schemas_v2.py` — additive schema (score_kind, ModelReference.calibrated_through, EnsembleDetail)

**Files:**
- Modify: `backend/app/schemas_v2.py`
- Test: `backend/tests/test_schemas_v2_ensemble.py`

**Interfaces:**
- Produces: `EnsembleComponentVote`, `EnsembleDetail` (exact fields per spec 3.5); `ModelReference.calibrated_through: date | None = None` (additive); `ForecastResponse.score_kind: Literal["raw_model_score", "calibrated_probability", "ensemble_mean_of_calibrated_components"]`; `ForecastResponse.ensemble: EnsembleDetail | None = None`.

- [ ] **Step 1: Write failing test**

```python
from datetime import date

from app.schemas_v2 import EnsembleComponentVote, EnsembleDetail, ModelReference


def test_ensemble_detail_round_trips_through_the_schema():
    detail = EnsembleDetail(
        policy_version="ensemble_agreement_v1",
        ensemble_identity_sha256="a" * 64,
        components=[
            EnsembleComponentVote(
                family="logistic_regression",
                model_reference=ModelReference(
                    model_version="m1", horizon_days=1, contract_version="producer_daily_h123_v1",
                    trained_through=date(2026, 1, 1), calibration_version="c1", assessment_reference=None,
                ),
                calibrated_through=date(2026, 1, 15),
                score=0.51,
                decision_threshold=0.5,
                alert=True,
            )
        ],
        combined_probability=0.34333333333333327,
        combined_alert=False,
        positive_votes=2,
        agreement_category="posible_alerta_acuerdo_parcial",
        calibrated_through=date(2026, 1, 20),
    )
    assert detail.combined_alert is False


def test_model_reference_calibrated_through_is_optional_and_backward_compatible():
    ref = ModelReference(
        model_version="m1", horizon_days=1, contract_version="producer_daily_h123_v1",
        trained_through=date(2026, 1, 1), calibration_version="c1", assessment_reference=None,
    )
    assert ref.calibrated_through is None
```

- [ ] **Step 2: Run to verify RED**

`pytest backend/tests/test_schemas_v2_ensemble.py -v` → `ImportError: cannot import name 'EnsembleComponentVote'`.

- [ ] **Step 3: Implement**

In `backend/app/schemas_v2.py`, extend `ModelReference`:
```python
class ModelReference(StrictModel):
    model_version: str | None
    horizon_days: Literal[1, 2, 3]
    contract_version: str
    trained_through: date | None
    calibration_version: str | None
    assessment_reference: str | None
    calibrated_through: date | None = None
```
Add:
```python
class EnsembleComponentVote(StrictModel):
    family: Literal["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"]
    model_reference: ModelReference
    calibrated_through: date
    score: float
    decision_threshold: float
    alert: bool


class EnsembleDetail(StrictModel):
    policy_version: str
    ensemble_identity_sha256: str
    components: list[EnsembleComponentVote]
    combined_probability: float
    combined_alert: bool
    positive_votes: int
    agreement_category: Literal[
        "alerta_por_unanimidad",
        "posible_alerta_acuerdo_parcial",
        "sin_alerta_por_mayoria_con_discrepancia",
        "sin_alerta_por_unanimidad",
    ]
    calibrated_through: date
```
Update `ForecastResponse`:
```python
    score_kind: Literal["raw_model_score", "calibrated_probability", "ensemble_mean_of_calibrated_components"]
    ...
    ensemble: EnsembleDetail | None = None
```
(add `ensemble` as the last field, after `review`, to minimize diff noise around existing fields).

- [ ] **Step 4: Run to verify it passes**

`pytest backend/tests/test_schemas_v2_ensemble.py -v` → 2 passed.

- [ ] **Step 5: Run existing schema-adjacent tests for regression**

`pytest backend/tests/test_producer_v2*.py -q` → must still pass unmodified (additive-only change).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas_v2.py backend/tests/test_schemas_v2_ensemble.py
git commit -m "feat(ensemble): esquema aditivo EnsembleDetail/EnsembleComponentVote, score_kind y calibrated_through"
```

---

## Task 6: Persistence — `SlotSeed`, `request_payload`, `forecast_record`, `_render_forecast`, `input_snapshot`

**Files:**
- Modify: `src/human_feedback/operational_repository.py`
- Test: `tests/test_operational_repository_ensemble.py`

**Interfaces:**
- Consumes: Task 4's `predict_ensemble_bundle` output shape.
- Produces: `SlotSeed` gains 8 new optional fields (exact names per spec 3.5) with the coherence invariant; `record_batch`'s `request_payload` per-slot dict, `forecast_record`, and `_render_forecast` all include the same 8 fields; old records (missing keys) render `ensemble=None`-equivalent (i.e. all 8 keys read via `.get(...)` returning `None`).

- [ ] **Step 1: Write failing test for the `SlotSeed` coherence invariant**

```python
import pytest

from human_feedback.operational_repository import SlotSeed


def _base_kwargs():
    return dict(
        horizon_days=1, status="available", alert=True, score=0.7, score_kind="ensemble_mean_of_calibrated_components",
        decision_threshold=0.5, event_threshold={"variable": "soil_moisture", "value": 0.3, "unit": "m3/m3", "comparison": "lt"},
        model_reference={"model_version": "x", "horizon_days": 1, "contract_version": "v1",
                          "trained_through": None, "calibration_version": None, "assessment_reference": None},
    )


def test_slot_seed_allows_all_ensemble_fields_none_together():
    SlotSeed(**_base_kwargs())  # no error


def test_slot_seed_requires_ensemble_fields_together_not_partial():
    kwargs = _base_kwargs()
    kwargs["ensemble_policy_version"] = "ensemble_agreement_v1"
    with pytest.raises(ValueError):
        SlotSeed(**kwargs)  # other 7 ensemble_* fields still None -> incoherent


def test_slot_seed_requires_alert_to_match_combined_alert_in_ensemble_mode():
    kwargs = _base_kwargs()
    kwargs.update(
        alert=True,
        ensemble_policy_version="ensemble_agreement_v1",
        ensemble_identity_sha256="a" * 64,
        ensemble_components=[],
        ensemble_combined_probability=0.7,
        ensemble_combined_alert=False,  # deliberately inconsistent with top-level alert=True
        ensemble_positive_votes=2,
        ensemble_agreement_category="posible_alerta_acuerdo_parcial",
        ensemble_calibrated_through="2026-01-20",
    )
    with pytest.raises(ValueError):
        SlotSeed(**kwargs)
```

- [ ] **Step 2: Run to verify RED**

`pytest tests/test_operational_repository_ensemble.py -v` → `TypeError: __init__() got an unexpected keyword argument 'ensemble_policy_version'`.

- [ ] **Step 3: Implement the `SlotSeed` extension**

```python
@dataclass(frozen=True)
class SlotSeed:
    horizon_days: int
    status: str
    reason_code: str | None = None
    alert: bool | None = None
    score: float | None = None
    score_kind: str | None = None
    display_probability: float | None = None
    probability_status: str | None = None
    probability_reason_code: str | None = None
    decision_threshold: float | None = None
    event_threshold: dict[str, Any] | None = None
    model_reference: dict[str, Any] | None = None
    ensemble_policy_version: str | None = None
    ensemble_identity_sha256: str | None = None
    ensemble_components: list[dict[str, Any]] | None = None
    ensemble_combined_probability: float | None = None
    ensemble_combined_alert: bool | None = None
    ensemble_positive_votes: int | None = None
    ensemble_agreement_category: str | None = None
    ensemble_calibrated_through: str | None = None

    def __post_init__(self) -> None:
        if self.horizon_days not in SUPPORTED_HORIZONS:
            raise ValueError("horizon_days debe ser 1, 2 o 3.")
        if self.status not in {"available", "unavailable"}:
            raise ValueError("status debe ser available o unavailable.")
        if self.status == "unavailable" and not self.reason_code:
            raise ValueError("Un slot unavailable requiere reason_code.")
        if self.status == "available" and (
            self.alert is None
            or self.score is None
            or self.score_kind is None
            or self.decision_threshold is None
            or self.event_threshold is None
            or self.model_reference is None
        ):
            raise ValueError("Un slot available requiere sus campos obligatorios.")

        ensemble_fields = (
            self.ensemble_policy_version,
            self.ensemble_identity_sha256,
            self.ensemble_components,
            self.ensemble_combined_probability,
            self.ensemble_combined_alert,
            self.ensemble_positive_votes,
            self.ensemble_agreement_category,
            self.ensemble_calibrated_through,
        )
        all_none = all(f is None for f in ensemble_fields)
        all_present = all(f is not None for f in ensemble_fields)
        if not (all_none or all_present):
            raise ValueError("Los campos ensemble_* deben estar todos presentes o todos ausentes.")
        if all_present:
            if self.alert != self.ensemble_combined_alert:
                raise ValueError("alert debe coincidir con ensemble_combined_alert en modo ensamble.")
            if self.score != self.ensemble_combined_probability:
                raise ValueError("score debe coincidir con ensemble_combined_probability en modo ensamble.")
```

- [ ] **Step 4: Run to verify it passes**

`pytest tests/test_operational_repository_ensemble.py -v` → 3 passed.

- [ ] **Step 5: Write failing test for `request_payload`/`forecast_record`/`_render_forecast` propagation**

```python
from pathlib import Path

from human_feedback.operational_repository import OperationalRepository, SlotSeed


def test_ensemble_fields_persist_through_record_batch_and_render(tmp_path):
    repo = OperationalRepository(sensor_id="s1", data_dir=tmp_path)
    seed = SlotSeed(
        horizon_days=1, status="available", alert=False, score=0.343333, score_kind="ensemble_mean_of_calibrated_components",
        decision_threshold=0.5, event_threshold={"variable": "soil_moisture", "value": 0.3, "unit": "m3/m3", "comparison": "lt"},
        model_reference={"model_version": "ensemble-id", "horizon_days": 1, "contract_version": "v1",
                          "trained_through": "2026-01-01", "calibration_version": None, "assessment_reference": None},
        ensemble_policy_version="ensemble_agreement_v1",
        ensemble_identity_sha256="a" * 64,
        ensemble_components=[{"family": "logistic_regression", "score": 0.51}],
        ensemble_combined_probability=0.343333,
        ensemble_combined_alert=False,
        ensemble_positive_votes=2,
        ensemble_agreement_category="posible_alerta_acuerdo_parcial",
        ensemble_calibrated_through="2026-01-20",
    )
    # (call repo.record_batch(...) with this seed via whatever the real signature requires;
    #  read back via repo's public "get forecast" accessor; assert the rendered dict has
    #  ensemble_policy_version == "ensemble_agreement_v1" etc.)


def test_render_forecast_handles_old_records_without_ensemble_keys(tmp_path):
    # write a forecast_record dict by hand (simulating a pre-change persisted record,
    # with NO ensemble_* keys at all) directly into the repository's storage, then
    # read it back through the public accessor and assert no KeyError and that the
    # ensemble-related fields all read back as None.
    ...
```
(Fill in the exact `record_batch`/read-back call per the real `OperationalRepository` public API, read at implementation time — the plan's Task 1 research already confirmed the internal dict shapes; use the repository's existing test file, e.g. `tests/test_operational_repository.py` or `backend/tests/test_producer_v2_emission.py`, as the pattern reference for how existing tests call `record_batch`/`emit_snapshot` and read results back, and mirror that exactly.)

- [ ] **Step 6: Run to verify RED**

Expected: fails because `request_payload`/`forecast_record`/`_render_forecast` don't yet include the new fields (assertion errors, not exceptions).

- [ ] **Step 7: Implement propagation**

In `record_batch`'s per-slot `request_payload` dict (`operational_repository.py`, the dict comprehension building each slot's entry) add the 8 `ensemble_*` fields read off `seed.ensemble_*`. In the `forecast_record` dict construction, add the same 8 fields off `seed.ensemble_*`. In `_render_forecast`, add:
```python
"ensemble_policy_version": forecast.get("ensemble_policy_version"),
"ensemble_identity_sha256": forecast.get("ensemble_identity_sha256"),
"ensemble_components": forecast.get("ensemble_components"),
"ensemble_combined_probability": forecast.get("ensemble_combined_probability"),
"ensemble_combined_alert": forecast.get("ensemble_combined_alert"),
"ensemble_positive_votes": forecast.get("ensemble_positive_votes"),
"ensemble_agreement_category": forecast.get("ensemble_agreement_category"),
"ensemble_calibrated_through": forecast.get("ensemble_calibrated_through"),
```
(using `.get`, never direct indexing, per the Global Constraints).

- [ ] **Step 8: Run to verify it passes**

`pytest tests/test_operational_repository_ensemble.py -v` → all pass.

- [ ] **Step 9: `input_snapshot` shape for ensemble horizons**

In `producer_emission.py` (Task 7 also touches this file — coordinate: this step only prepares the `operational_repository.py` side reading it back, if any; the writing side is Task 7 Step 3). No changes needed here if `input_snapshot["bundles"][str(horizon)]` is opaque to `operational_repository.py` (verified: it's stored and returned as-is, never destructured by key beyond `str(horizon)` — confirm by reading the surrounding code at implementation time; if any code path does destructure it expecting single-bundle shape, that's a Task 7 concern to fix at the write site, not here).

- [ ] **Step 10: Run existing operational_repository tests for regression**

`pytest tests/test_operational_repository*.py backend/tests/test_producer_v2*.py -q` → must all still pass (additive-only).

- [ ] **Step 11: Commit**

```bash
git add src/human_feedback/operational_repository.py tests/test_operational_repository_ensemble.py
git commit -m "feat(ensemble): persistir detalle de ensamble en SlotSeed, request_payload, forecast_record y render (retrocompatible)"
```

---

## Task 7: Wire into `producer_emission.py` — activation branch, error propagation, no-recompute

**Files:**
- Modify: `src/architecture_integration/producer_emission.py`
- Test: `tests/test_producer_emission_ensemble.py`

**Interfaces:**
- Consumes: Task 1's `is_ensemble_configured`/`load_ensemble_bundle`, Task 4's `predict_ensemble_bundle`, Task 6's extended `SlotSeed`.
- Produces: `emit_forecasts` (or the per-horizon internal function) branches on `is_ensemble_configured` per horizon; on any ensemble exception, builds `SlotSeed(status="unavailable", reason_code=f"ensemble_{...}")` instead of raising; a component-level `BundleUnavailable` reason is embedded verbatim in that `reason_code`.

- [ ] **Step 1: Write failing test — single-model unaffected (regression)**

```python
def test_sensor_without_ensemble_dir_behaves_exactly_as_before(tmp_path):
    # build a plain single-model bundle at bundle_root/s1/horizon_1/ (no ensemble/ dir)
    # call the emission entry point, assert the resulting slot has ensemble_* all None
    # and alert/score matching what predict_operational_bundle alone would produce.
    ...
```

- [ ] **Step 2: Write failing test — ensemble configured, all 3 valid (happy path)**

Using Task 3's `write_single_bundle` ×3 under `.../ensemble/<family>/` plus `write_ensemble_manifest`, call the emission entry point, assert the resulting slot has `status="available"`, `ensemble_policy_version="ensemble_agreement_v1"`, and `alert == ensemble_combined_alert`.

- [ ] **Step 3: Write failing test — ensemble configured, one family missing → unavailable, other horizons unaffected**

Build ensemble dirs for horizon 1 (missing `random_forest`) and a normal single-model bundle for horizon 2 (no `ensemble/`). Assert horizon 1's slot is `unavailable` with `reason_code` containing `"random_forest"`, and horizon 2's slot is `available` (single-model), in the **same** emission call.

- [ ] **Step 4: Write failing test — re-emission does not recompute an existing slot**

Emit once for `as_of_date=D`, horizon 1, single-model (no ensemble). Then create `ensemble/` for horizon 1. Emit again for the **same** `as_of_date=D`. Assert the horizon-1 slot's `forecast_id` and `alert`/`score` are unchanged (still the original single-model result, `ensemble_policy_version is None`).

- [ ] **Step 5: Run all 4 to verify RED**

Expected: fails because the branch doesn't exist yet in `producer_emission.py` (either `ImportError` for helpers not yet wired, or wrong `ensemble_*` values).

- [ ] **Step 6: Implement the branch**

Locate the per-horizon resolution loop in `producer_emission.py` (the function building `captured["artifact"]["bundles"][str(horizon)]` and calling `load_operational_bundle`/`predict_operational_bundle`, per Task-0 research). Wrap it:
```python
if is_ensemble_configured(bundle_root, sensor_id=sensor_id, horizon=horizon):
    try:
        ensemble = load_ensemble_bundle(bundle_root, sensor_id=sensor_id, horizon=horizon)
        result = predict_ensemble_bundle(ensemble, dataframe, sensor_id=sensor_id, units=units, as_of_date=as_of_date)
    except (EnsembleManifestMissingError, EnsembleManifestInvalidError, EnsembleComponentMissingError,
            EnsembleBundleIncompatible, BundleUnavailable) as error:
        seed = SlotSeed(horizon_days=horizon, status="unavailable", reason_code=f"ensemble_{type(error).__name__}:{error}")
        # continue to the next horizon; do not fall back to load_operational_bundle
    else:
        seed = SlotSeed(
            horizon_days=horizon, status="available",
            alert=result["combined_alert"], score=result["combined_probability"],
            score_kind="ensemble_mean_of_calibrated_components",
            display_probability=None, probability_status="not_qualified", probability_reason_code="incompatible_assessment",
            decision_threshold=result["decision_threshold"],
            event_threshold=<reused from any one component's contract["event"], already cross-checked identical>,
            model_reference={
                "model_version": result["ensemble_identity_sha256"], "horizon_days": horizon,
                "contract_version": <shared contract_version>, "trained_through": result["trained_through"],
                "calibration_version": None, "assessment_reference": None,
            },
            ensemble_policy_version=ensemble.manifest["policy_version"],
            ensemble_identity_sha256=result["ensemble_identity_sha256"],
            ensemble_components=result["components"],
            ensemble_combined_probability=result["combined_probability"],
            ensemble_combined_alert=result["combined_alert"],
            ensemble_positive_votes=result["positive_votes"],
            ensemble_agreement_category=result["agreement_category"],
            ensemble_calibrated_through=result["calibrated_through"],
        )
        captured["artifact"].setdefault("bundles", {})[str(horizon)] = {
            "mode": "ensemble", "ensemble_manifest": ensemble.manifest,
            "components": {family: b.metadata for family, b in ensemble.components.items()},
        }
else:
    # existing single-model code path, entirely unchanged
    ...
```
Exact variable names/control flow to match the surrounding function precisely at implementation time (read the real function body before editing — this plan gives the shape, not a literal diff, since the exact surrounding loop/variable names were summarized, not quoted in full, by the research pass).

- [ ] **Step 7: Run all 4 tests to verify GREEN**

`pytest tests/test_producer_emission_ensemble.py -v` → 4 passed.

- [ ] **Step 8: Run the full existing producer_v2/emission regression suite**

`pytest backend/tests/test_producer_v2*.py tests/test_architecture_integration_pipeline.py -q` → must all still pass unmodified.

- [ ] **Step 9: Commit**

```bash
git add src/architecture_integration/producer_emission.py tests/test_producer_emission_ensemble.py
git commit -m "feat(ensemble): activar modo ensamble en producer_emission.py sin afectar el camino single-model"
```

---

## Task 8: HTTP integration test (real route) + feedback discrepancy test

**Files:**
- Test: `backend/tests/test_producer_v2_ensemble.py`

**Interfaces:**
- Consumes: everything above, through the real FastAPI app (`TestClient`).

- [ ] **Step 1: Write the end-to-end HTTP test**

```python
def test_forecast_emission_exposes_ensemble_detail_via_real_route(tmp_path, client_factory):
    # build ensemble bundles under a temp PRODUCER_BUNDLE_ROOT (override the dependency
    # the same way backend/tests/test_producer_v2_emission.py already does), then:
    response = client.post(f"/api/v2/sensors/{sensor_id}/forecasts", headers={"Idempotency-Key": "k1"})
    assert response.status_code in (200, 201)
    body = response.json()
    horizon_1 = next(f for f in body["forecasts"] if f["horizon_days"] == 1)
    assert horizon_1["ensemble"]["policy_version"] == "ensemble_agreement_v1"
    assert horizon_1["score_kind"] == "ensemble_mean_of_calibrated_components"
```
Follow the exact fixture-override pattern already used in `backend/tests/test_producer_v2_emission.py` (dependency override for `PRODUCER_BUNDLE_ROOT`/bundle root path) — read that file first and mirror it, don't invent a new override mechanism.

- [ ] **Step 2: Write the feedback discrepancy test**

```python
def test_confirming_an_ensemble_forecast_validates_combined_alert_not_the_vote(tmp_path, client_factory):
    # emit with components 0.99 / 0.49 / 0.49 (positive_votes=1, combined_alert=True)
    # POST .../reviews with action="confirm"
    # assert the resulting observed_label / training_eligibility reflects combined_alert=True,
    # not what a 1/3-vote minority would suggest.
```

- [ ] **Step 3: Run both, iterate until GREEN**

`pytest backend/tests/test_producer_v2_ensemble.py -v`.

- [ ] **Step 4: Run the complete affected surface**

```bash
pytest tests/test_ensemble_bundle.py tests/test_bundle_packaging.py tests/helpers/test_synthetic_bundles.py \
       tests/test_operational_repository_ensemble.py tests/test_producer_emission_ensemble.py \
       backend/tests/test_schemas_v2_ensemble.py backend/tests/test_producer_v2_ensemble.py \
       backend/tests/test_producer_v2*.py tests/test_architecture_integration_pipeline.py -q
```
All green.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_producer_v2_ensemble.py
git commit -m "test(ensemble): integración HTTP de punta a punta y caso de discrepancia en feedback"
```

---

## Task 9: Nivel 2 — three real v4 families fit on synthetic data, real serialization/load

**Files:**
- Test: `tests/test_ensemble_real_families_synthetic.py`

**Interfaces:**
- Consumes: Task 2's `attach_feature_names`, Task 3's `build_real_family_estimator`, `controlled_daily_v4.models.build_estimator`/`fit_estimator` (unmodified), Task 1's `load_ensemble_bundle`.

- [ ] **Step 1: Write the test**

```python
import numpy as np

from experiment_runner.controlled_daily_v4.models import build_estimator
from predictive_modeling.bundle_packaging import attach_feature_names
from predictive_modeling.ensemble_bundle import load_ensemble_bundle
from tests.helpers.synthetic_bundles import write_ensemble_manifest, write_single_bundle

FEATURE_COLUMNS = ["temperature", "relative_humidity"]


def _synthetic_frame(n=40, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(FEATURE_COLUMNS)))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y


def test_the_three_real_v4_families_pack_into_a_loadable_ensemble(tmp_path):
    X, y = _synthetic_frame()
    families = {
        "logistic_regression": build_estimator("logistic_regression", {}),
        "random_forest": build_estimator("random_forest", {}),
        "hist_gradient_boosting_classifier": build_estimator("hist_gradient_boosting_classifier", {}),
    }
    for family, model in families.items():
        model.fit(X, y)
        assert not hasattr(model, "feature_names_in_")  # confirms the real gap, before the adapter
        attach_feature_names(model, FEATURE_COLUMNS)

        calibrator = build_estimator("logistic_regression", {})  # any classifier works as a stub "calibrator" here for load-path purposes
        calibrator.fit(X, y)
        attach_feature_names(calibrator, FEATURE_COLUMNS)

        write_single_bundle(
            tmp_path / "s1" / "horizon_1" / "ensemble" / family,
            sensor_id="s1", horizon=1, model=model, calibrator=calibrator, feature_columns=FEATURE_COLUMNS,
        )
        # assert the three built models are genuinely different classes, never three RFs
    assert type(families["logistic_regression"]).__name__ != type(families["random_forest"]).__name__
    assert type(families["random_forest"]).__name__ != type(families["hist_gradient_boosting_classifier"]).__name__

    write_ensemble_manifest(tmp_path / "s1" / "horizon_1", sensor_id="s1", horizon=1, contract_version="producer_daily_h123_v1")

    ensemble = load_ensemble_bundle(tmp_path, sensor_id="s1", horizon=1)
    assert set(ensemble.components) == {"logistic_regression", "random_forest", "hist_gradient_boosting_classifier"}
```

- [ ] **Step 2: Run to verify it fails first for the right reason, then passes**

Run `pytest tests/test_ensemble_real_families_synthetic.py -v` before Task 2 existed conceptually (or temporarily comment out the `attach_feature_names` calls) to confirm `load_operational_bundle` really does reject the array-fit models with `BundleUnavailable`/`AttributeError` — this is the RED that proves the gap from spec 3.7 is real, not assumed. Then restore the `attach_feature_names` calls and confirm GREEN.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ensemble_real_families_synthetic.py
git commit -m "test(ensemble): integrar las 3 familias reales de v4 ajustadas sobre datos sintéticos (Nivel 2)"
```

---

## Task 10: Documentation — specs, traceability, Hito 2 document

**Files:**
- Modify: `openspec/specs/predictive-modeling/spec.md`
- Modify: `openspec/specs/experiment-runner/spec.md`
- Create: `docs/design/ensemble-real-enablement-plan.md` (Hito 2 — content per spec section 7, written as its own standalone document, not duplicating the spec)
- Modify: memoria técnica capítulo 3 (only the section described in spec §4 — additive, no rewrite of existing content)

- [ ] **Step 1: Add the ensemble requirement to `predictive-modeling` spec**

Marked `[implementado, verificado con fixtures y con las 3 familias ajustadas sobre datos sintéticos — sin artefactos reales]`, citing the four states from spec §1.

- [ ] **Step 2: Cross-reference in `experiment-runner` spec**

One paragraph: operational contract exists and is tested; real v4 artifacts still not produced (Hito 2).

- [ ] **Step 3: Write `docs/design/ensemble-real-enablement-plan.md`**

Full content per spec §7 (dataset, temporal splits, training, calibration, thresholds, compatible horizons, admissible historical-demo period, required scientific authorizations, antecedents-check-first step, four states differentiated).

- [ ] **Step 4: Add the capítulo 3 section**

Per spec §4 — new section only, no modification of existing scientific-results text, no attribution of this integration's policy to any prior scientific finding.

- [ ] **Step 5: Commit**

```bash
git add openspec/specs/predictive-modeling/spec.md openspec/specs/experiment-runner/spec.md docs/design/ensemble-real-enablement-plan.md <memoria-chapter-3-file>
git commit -m "docs(ensemble): actualizar specs, agregar plan de habilitación real (Hito 2) y sección de capítulo 3"
```

---

## Task 11: Final full-suite verification, PR

**Files:** none new.

- [ ] **Step 1: Run everything this plan touched, plus the wider suite**

```bash
pytest tests backend/tests -q
```
Compare against the pre-change baseline pass count — only new tests added, zero regressions in existing tests.

- [ ] **Step 2: Push, open PR (no merge)**

```bash
git push -u origin feat/ensemble-operational-integration
gh pr create --repo gusjrivas/AAI_Hydric_Stress --base main --head feat/ensemble-operational-integration \
  --title "feat: integración operativa del ensamble v4 (Hito 1) + plan de habilitación real (Hito 2)" \
  --body "..."
```
PR body must state explicitly: Hito 1 implemented and tested with synthetic fixtures only (including the 3 real v4 family classes fit on synthetic data); no real v4 artifacts exist or were produced; Hito 2 is a separate, unexecuted planning document; feedback confirms `combined_alert`, never the vote category; no recalibration introduced; real HTTP route used throughout.

## Self-review notes

- **Spec coverage:** every numbered point (1-8) of the Codex review is implemented by a task: activation/fallback → Tasks 1, 7; contract/temporality → Tasks 1, 4; aggregation/presentation → Task 4, 5; identity/persistence/idempotency → Tasks 4, 6; feedback/real API → Tasks 7, 8; three-family compatibility → Tasks 2, 3, 9; Hito 2/documentation → Task 10; plan/closure → this document itself, Task 11.
- **Placeholder scan:** the one intentionally-loose spot is Task 6 Step 5/Task 7 Step 6, which describe the exact edit shape but ask the implementer to read the real surrounding function body first (the research pass summarized, but did not quote in full, every line of `record_batch`'s dict comprehension and `producer_emission.py`'s per-horizon loop) — flagged explicitly in-line as "read the real function before editing," not a placeholder for undecided behavior.
- **Type consistency:** `predict_ensemble_bundle`'s return dict keys (Task 4) match exactly what Task 6's `SlotSeed` fields and Task 7's `producer_emission.py` wiring consume; `EnsembleDetail`/`EnsembleComponentVote` field names (Task 5) match the persisted `ensemble_*` field names (Task 6) one-to-one in spirit (schema is the wire shape, `SlotSeed` is the internal shape — mapping is 1:1 by name where applicable).
- **Review Focus:** the 5 items map to Task 7 Step 3 (per-family error, other horizons unaffected), Task 8 Step 2 (feedback discrepancy), Task 7 Step 4 (no-recompute), Task 6 Step 5's old-record test, Task 9 (calibrator's `feature_names_in_` explicitly asserted, not just the model's).
