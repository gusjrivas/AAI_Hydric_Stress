# Alerting UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First working UI (FastAPI backend + React frontend) that runs the existing forecast pipeline, shows the generated alerts, and lets a human confirm or reject each one, persisting that feedback to disk.

**Architecture:** `backend/` is a thin FastAPI facade over the already-existing `src/` Python packages (`architecture_integration`, `human_feedback`, `predictive_modeling`, `data_ingestion`) — it contains zero business logic, only HTTP plumbing. `frontend/` is a Vite + React + TypeScript SPA that talks to the backend over HTTP only. Both are first-time scaffolding in this repo (ADR-0003 already reserved these folder names).

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, httpx (for `TestClient`), pytest; Node 20+/npm, Vite, React 18, TypeScript, Vitest, React Testing Library.

**Spec:** `openspec/changes/add-alerting-ui/proposal.md` and `openspec/changes/add-alerting-ui/specs/alerting-ui/spec.md`

## Global Constraints

- Backend is a thin facade over `src/` (ADR-0003): it must only call functions already defined in `architecture_integration`, `human_feedback`, `predictive_modeling`, `data_ingestion` — never reimplement modeling/data logic in `backend/`.
- Frontend consumes only the backend HTTP API (frontend-react skill) — no direct Python/data access from `frontend/`.
- React: functional components + hooks only. No Redux/Zustand or other state library.
- Frontend organized by feature (`frontend/src/features/<name>/`), not by file type.
- The dataset name is configurable via the `ALERTING_UI_DATASET` environment variable (default `melchor_romero_2024_consolidado`) — never hardcode the dataset name inside a route handler.
- `POST /forecast/run`'s response never includes which model produced the verdict — only `fecha`, `alerta` (bool), `probabilidad` (float).
- Backend tests use FastAPI's `TestClient` against the real app (no mocking of FastAPI internals); feedback persistence in tests must use a temporary directory (via dependency override), never the real project `data/` folder.
- Frontend tests use React Testing Library + Vitest, asserting on what the user sees (text, buttons), not internal component state.
- CORS: the backend allows only `http://localhost:5173` (the Vite dev server origin).

---

### Task 1: Backend scaffolding + `POST /forecast/run`

**Files:**
- Modify: `pyproject.toml` (add `backend` optional-dependencies group)
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/forecast.py`
- Create: `backend/app/main.py`
- Create: `backend/conftest.py`
- Test: `backend/tests/test_forecast.py`

**Interfaces:**
- Consumes: `architecture_integration.pipeline.run_end_to_end_pipeline` (existing), `predictive_modeling.models.build_candidate_models` (existing), `data_ingestion.storage.load_dataset` (existing), `human_feedback.schema.init_feedback_log` (existing), `human_feedback.registry.upsert_feedback_log`/`load_feedback_log`/`save_feedback_log` (existing).
- Produces: `backend.app.config.get_feedback_data_dir() -> Path` (FastAPI dependency, overridable in tests), `backend.app.config.DATASET_NAME: str`, `backend.app.config.FEEDBACK_LOG_NAME: str`, `backend.app.schemas.Verdict`, `backend.app.schemas.ForecastRunResponse`, `backend.app.main.app` (the FastAPI instance later tasks import and extend).

- [ ] **Step 1: Add the `backend` optional-dependencies group to the root `pyproject.toml`**

Open `pyproject.toml` and add this new group right after the existing `dev` group inside `[project.optional-dependencies]`:

```toml
backend = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "httpx>=0.27",
]
```

- [ ] **Step 2: Install the new dependency group**

Run: `pip install -e ".[dev,backend]"`
Expected: installs successfully, `fastapi`/`uvicorn`/`httpx` now importable.

- [ ] **Step 3: Create the empty package files**

Create `backend/app/__init__.py` with empty content (just makes `app` a package).

Create `backend/app/routers/__init__.py` with empty content.

- [ ] **Step 4: Create `backend/conftest.py` so `backend/tests` can import the `app` package**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 5: Write `backend/app/config.py`**

```python
"""Configuración del backend (fachada delgada, ADR-0003). El nombre del
dataset es configurable por variable de entorno para no acoplar las
rutas a un dataset fijo cuando exista una fuente de datos en vivo.
"""

from __future__ import annotations

import os
from pathlib import Path

from data_ingestion.storage import DEFAULT_DATA_DIR

DATASET_NAME = os.environ.get("ALERTING_UI_DATASET", "melchor_romero_2024_consolidado")
FEEDBACK_LOG_NAME = os.environ.get("ALERTING_UI_FEEDBACK_LOG", "feedback_ui")

FEATURE_COLUMNS = ["soil_moisture", "solar_radiation", "relative_humidity"]
LABEL_COLUMN = "soil_moisture"
RANDOM_STATE = 42


def get_feedback_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persiste el registro de
    retroalimentación. Overrideable en tests (`app.dependency_overrides`)
    para no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR
```

- [ ] **Step 6: Write `backend/app/schemas.py`**

```python
"""Modelos Pydantic de request/response (spec alerting-ui)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Verdict(BaseModel):
    fecha: date
    alerta: bool
    probabilidad: float


class ForecastRunResponse(BaseModel):
    verdicts: list[Verdict]
    train_rows: int
    test_rows: int


class FeedbackRow(BaseModel):
    fecha: date
    alerta_generada: int
    estado_validacion: str
    etiqueta_corregida: int | None = None
    observacion: str | None = None


class FeedbackListResponse(BaseModel):
    rows: list[FeedbackRow]


class RejectRequest(BaseModel):
    etiqueta_corregida: int
    observacion: str
```

- [ ] **Step 7: Write the failing test for the forecast endpoint**

Create `backend/tests/test_forecast.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_feedback_data_dir
from app.main import app


def test_run_forecast_returns_verdicts(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/forecast/run")

    assert response.status_code == 200
    body = response.json()
    assert body["train_rows"] > 0
    assert body["test_rows"] > 0
    assert len(body["verdicts"]) == body["test_rows"]
    first = body["verdicts"][0]
    assert set(first.keys()) == {"fecha", "alerta", "probabilidad"}

    app.dependency_overrides.clear()
```

Note: this test imports `app.main`, which doesn't exist yet — that's what makes it fail correctly in Step 8. `GET /feedback` isn't exercised here; Task 2's tests cover it directly (including reading back a feedback log that `/forecast/run` persisted).

- [ ] **Step 8: Run the test to verify it fails**

Run (from repo root): `cd backend && python -m pytest tests/test_forecast.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` (or `'app.main'`).

- [ ] **Step 9: Write `backend/app/routers/forecast.py`**

```python
"""Router de ejecución de pronóstico (spec alerting-ui, requirement
"Ejecución de pronóstico desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from architecture_integration.pipeline import run_end_to_end_pipeline
from data_ingestion.storage import load_dataset
from human_feedback.registry import load_feedback_log, save_feedback_log, upsert_feedback_log
from human_feedback.schema import init_feedback_log
from predictive_modeling.models import build_candidate_models

from ..config import (
    DATASET_NAME,
    FEATURE_COLUMNS,
    FEEDBACK_LOG_NAME,
    LABEL_COLUMN,
    RANDOM_STATE,
    get_feedback_data_dir,
)
from ..schemas import ForecastRunResponse, Verdict

router = APIRouter()


@router.post("/forecast/run", response_model=ForecastRunResponse)
def run_forecast(data_dir: Path = Depends(get_feedback_data_dir)) -> ForecastRunResponse:
    df = load_dataset(DATASET_NAME)
    split_date = df["timestamp"].sort_values().iloc[int(len(df) * 0.8)].date()

    model = build_candidate_models(random_state=RANDOM_STATE)["random_forest"]
    result = run_end_to_end_pipeline(
        df,
        label_column=LABEL_COLUMN,
        feature_columns=FEATURE_COLUMNS,
        split_date=split_date,
        model=model,
        include_anomaly_detection=False,
        random_state=RANDOM_STATE,
    )

    dates = result["test"]["timestamp"].reset_index(drop=True)
    alerts = result["alerts"].reset_index(drop=True)
    y_proba = result["y_proba"].reset_index(drop=True)

    try:
        existing_feedback = load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
        merged_feedback = upsert_feedback_log(existing_feedback, dates, alerts)
    except FileNotFoundError:
        merged_feedback = init_feedback_log(dates, alerts)
    save_feedback_log(FEEDBACK_LOG_NAME, merged_feedback, data_dir=data_dir)

    verdicts = [
        Verdict(fecha=d.date(), alerta=bool(a), probabilidad=float(p))
        for d, a, p in zip(dates, alerts, y_proba)
    ]
    return ForecastRunResponse(
        verdicts=verdicts,
        train_rows=len(result["train"]),
        test_rows=len(result["test"]),
    )
```

- [ ] **Step 10: Write `backend/app/main.py`**

```python
"""Punto de entrada de la app FastAPI (spec alerting-ui)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import forecast

app = FastAPI(title="Alerting UI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router)
```

- [ ] **Step 11: Run the test to verify it passes**

Run (from repo root): `cd backend && python -m pytest tests/test_forecast.py -v`
Expected: PASS.

- [ ] **Step 12: Commit**

```bash
git add pyproject.toml backend/
git commit -m "feat(backend): add FastAPI scaffolding and POST /forecast/run"
```

---

### Task 2: Feedback endpoints (`GET /feedback`, confirm, reject)

**Files:**
- Create: `backend/app/routers/feedback.py`
- Modify: `backend/app/main.py` (include the feedback router)
- Modify: `backend/tests/test_forecast.py` (uncomment the `GET /feedback` assertions from Task 1, Step 7)
- Test: `backend/tests/test_feedback.py`

**Interfaces:**
- Consumes: `human_feedback.schema.update_feedback` (existing), `human_feedback.registry.load_feedback_log`/`save_feedback_log` (existing), `app.config.get_feedback_data_dir`/`FEEDBACK_LOG_NAME` (Task 1), `app.schemas.FeedbackRow`/`FeedbackListResponse`/`RejectRequest` (Task 1), `app.main.app` (Task 1).
- Produces: nothing new consumed by later tasks (this is the API surface the frontend, Task 3, will call directly over HTTP).

- [ ] **Step 1: Write the failing tests for the feedback endpoints**

Create `backend/tests/test_feedback.py`:

```python
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from app.main import app
from human_feedback.registry import save_feedback_log
from human_feedback.schema import init_feedback_log


def _seed_feedback_log(data_dir: Path) -> str:
    dates = pd.to_datetime(["2024-10-19", "2024-10-20"])
    alerts = pd.Series([1, 0])
    log = init_feedback_log(dates, alerts)
    save_feedback_log(FEEDBACK_LOG_NAME, log, data_dir=data_dir)
    return "2024-10-19"


def test_list_feedback_returns_404_when_no_forecast_ran_yet(tmp_path: Path):
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_list_feedback_returns_persisted_rows(tmp_path: Path):
    _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.get("/feedback")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 2
    assert rows[0]["estado_validacion"] == "pendiente"
    app.dependency_overrides.clear()


def test_confirm_feedback_updates_state(tmp_path: Path):
    fecha = _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(f"/feedback/{fecha}/confirm")

    assert response.status_code == 200
    assert response.json()["estado_validacion"] == "confirmada"

    persisted = client.get("/feedback").json()["rows"]
    updated_row = next(r for r in persisted if r["fecha"] == fecha)
    assert updated_row["estado_validacion"] == "confirmada"
    app.dependency_overrides.clear()


def test_reject_feedback_stores_correction_and_observation(tmp_path: Path):
    fecha = _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        f"/feedback/{fecha}/reject",
        json={"etiqueta_corregida": 0, "observacion": "no habia estres real"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado_validacion"] == "rechazada"
    assert body["etiqueta_corregida"] == 0
    assert body["observacion"] == "no habia estres real"
    app.dependency_overrides.clear()


def test_confirm_unknown_date_returns_404(tmp_path: Path):
    _seed_feedback_log(tmp_path)
    app.dependency_overrides[get_feedback_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post("/feedback/2099-01-01/confirm")

    assert response.status_code == 404
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from repo root): `cd backend && python -m pytest tests/test_feedback.py -v`
Expected: FAIL — `404 Not Found` for all of them (no `/feedback` route registered yet), i.e. assertion errors on status codes.

- [ ] **Step 3: Write `backend/app/routers/feedback.py`**

```python
"""Router de consulta y validación humana de alertas (spec alerting-ui,
requirement "Consulta y validación humana de alertas").
"""

from __future__ import annotations

from datetime import date as date_type
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import update_feedback

from ..config import FEEDBACK_LOG_NAME, get_feedback_data_dir
from ..schemas import FeedbackListResponse, FeedbackRow, RejectRequest

router = APIRouter()


def _load_or_404(data_dir: Path) -> pd.DataFrame:
    try:
        return load_feedback_log(FEEDBACK_LOG_NAME, data_dir=data_dir)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Todavía no se corrió ningún pronóstico."
        ) from error


def _find_date_or_404(log: pd.DataFrame, fecha: date_type) -> pd.Timestamp:
    target = pd.Timestamp(fecha)
    if not (log["fecha"] == target).any():
        raise HTTPException(status_code=404, detail=f"No hay una alerta para la fecha {fecha}.")
    return target


def _row_to_schema(row: pd.Series) -> FeedbackRow:
    etiqueta = row["etiqueta_corregida"]
    observacion = row["observacion"]
    return FeedbackRow(
        fecha=row["fecha"].date(),
        alerta_generada=int(row["alerta_generada"]),
        estado_validacion=row["estado_validacion"],
        etiqueta_corregida=None if pd.isna(etiqueta) else int(etiqueta),
        observacion=None if observacion is None else observacion,
    )


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(data_dir: Path = Depends(get_feedback_data_dir)) -> FeedbackListResponse:
    log = _load_or_404(data_dir)
    return FeedbackListResponse(rows=[_row_to_schema(row) for _, row in log.iterrows()])


@router.post("/feedback/{fecha}/confirm", response_model=FeedbackRow)
def confirm_feedback(
    fecha: date_type, data_dir: Path = Depends(get_feedback_data_dir)
) -> FeedbackRow:
    log = _load_or_404(data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(log, fecha=target, estado_validacion="confirmada")
    save_feedback_log(FEEDBACK_LOG_NAME, updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)


@router.post("/feedback/{fecha}/reject", response_model=FeedbackRow)
def reject_feedback(
    fecha: date_type,
    body: RejectRequest,
    data_dir: Path = Depends(get_feedback_data_dir),
) -> FeedbackRow:
    log = _load_or_404(data_dir)
    target = _find_date_or_404(log, fecha)
    updated = update_feedback(
        log,
        fecha=target,
        estado_validacion="rechazada",
        etiqueta_corregida=body.etiqueta_corregida,
        observacion=body.observacion,
    )
    save_feedback_log(FEEDBACK_LOG_NAME, updated, data_dir=data_dir)
    row = updated.loc[updated["fecha"] == target].iloc[0]
    return _row_to_schema(row)
```

- [ ] **Step 4: Register the feedback router in `backend/app/main.py`**

Modify `backend/app/main.py` — change the import and include line:

```python
from .routers import feedback, forecast
```

```python
app.include_router(forecast.router)
app.include_router(feedback.router)
```

- [ ] **Step 5: Run all backend tests to verify they pass**

Run (from repo root): `cd backend && python -m pytest tests/ -v`
Expected: all PASS (Task 1's test plus the 5 new tests in this task).

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): add GET /feedback, confirm, and reject endpoints"
```

---

### Task 3: Frontend scaffolding + forecast/alerts page

**Files:**
- Create: `frontend/` (via `npm create vite@latest`, see Step 1)
- Create: `frontend/src/features/forecast/api.ts`
- Create: `frontend/src/features/forecast/ForecastPage.tsx`
- Create: `frontend/src/features/forecast/ForecastPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/package.json` (add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`)
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/setupTests.ts`

**Interfaces:**
- Consumes: `POST http://localhost:8000/forecast/run` (Task 1), `GET http://localhost:8000/feedback` (Task 2), `POST http://localhost:8000/feedback/{fecha}/confirm` (Task 2), `POST http://localhost:8000/feedback/{fecha}/reject` (Task 2) — over HTTP only, matching the JSON shapes of `ForecastRunResponse`/`FeedbackListResponse`/`FeedbackRow` from `backend/app/schemas.py`.
- Produces: `frontend/src/features/forecast/api.ts` exports `runForecast()`, `listFeedback()`, `confirmAlert(fecha: string)`, `rejectAlert(fecha: string, etiquetaCorregida: number, observacion: string)` — all `Promise`-returning, used only inside `ForecastPage.tsx` in this task.

- [ ] **Step 1: Scaffold the Vite project**

Run (from repo root): `npm create vite@latest frontend -- --template react-ts`
Expected: creates `frontend/` with the standard Vite React+TS template.

Run: `cd frontend && npm install`
Expected: installs successfully.

- [ ] **Step 2: Install testing dependencies**

Run (from `frontend/`): `npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`
Expected: installs successfully.

- [ ] **Step 3: Configure Vitest**

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    globals: true,
  },
});
```

Create `frontend/src/setupTests.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

Add this script to `frontend/package.json`'s `"scripts"` section (alongside the existing `dev`/`build`/`preview`):

```json
"test": "vitest run"
```

- [ ] **Step 4: Delete the default Vite boilerplate content**

Delete the contents of `frontend/src/App.css` (leave the file empty) and remove the default logo imports/content from `frontend/src/App.tsx` — it gets fully replaced in Step 7.

- [ ] **Step 5: Write `frontend/src/features/forecast/api.ts`**

```typescript
const API_BASE_URL = "http://localhost:8000";

export interface Verdict {
  fecha: string;
  alerta: boolean;
  probabilidad: number;
}

export interface ForecastRunResponse {
  verdicts: Verdict[];
  train_rows: number;
  test_rows: number;
}

export interface FeedbackRow {
  fecha: string;
  alerta_generada: number;
  estado_validacion: string;
  etiqueta_corregida: number | null;
  observacion: string | null;
}

export interface FeedbackListResponse {
  rows: FeedbackRow[];
}

export async function runForecast(): Promise<ForecastRunResponse> {
  const response = await fetch(`${API_BASE_URL}/forecast/run`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Error al correr el pronóstico: ${response.status}`);
  }
  return response.json();
}

export async function listFeedback(): Promise<FeedbackListResponse> {
  const response = await fetch(`${API_BASE_URL}/feedback`);
  if (!response.ok) {
    throw new Error(`Error al obtener el feedback: ${response.status}`);
  }
  return response.json();
}

export async function confirmAlert(fecha: string): Promise<FeedbackRow> {
  const response = await fetch(`${API_BASE_URL}/feedback/${fecha}/confirm`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Error al confirmar la alerta: ${response.status}`);
  }
  return response.json();
}

export async function rejectAlert(
  fecha: string,
  etiquetaCorregida: number,
  observacion: string,
): Promise<FeedbackRow> {
  const response = await fetch(`${API_BASE_URL}/feedback/${fecha}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ etiqueta_corregida: etiquetaCorregida, observacion }),
  });
  if (!response.ok) {
    throw new Error(`Error al rechazar la alerta: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 6: Write the failing tests for `ForecastPage`**

Create `frontend/src/features/forecast/ForecastPage.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ForecastPage } from "./ForecastPage";
import * as api from "./api";

describe("ForecastPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("runs the forecast and shows the resulting alerts", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));

    await waitFor(() => {
      expect(screen.getByText("2024-10-31")).toBeInTheDocument();
    });
    expect(screen.getByText(/pendiente/i)).toBeInTheDocument();
  });

  it("confirms an alert and updates its displayed state", async () => {
    vi.spyOn(api, "runForecast").mockResolvedValue({
      train_rows: 286,
      test_rows: 1,
      verdicts: [{ fecha: "2024-10-31", alerta: true, probabilidad: 0.72 }],
    });
    vi.spyOn(api, "listFeedback").mockResolvedValue({
      rows: [
        {
          fecha: "2024-10-31",
          alerta_generada: 1,
          estado_validacion: "pendiente",
          etiqueta_corregida: null,
          observacion: null,
        },
      ],
    });
    vi.spyOn(api, "confirmAlert").mockResolvedValue({
      fecha: "2024-10-31",
      alerta_generada: 1,
      estado_validacion: "confirmada",
      etiqueta_corregida: null,
      observacion: null,
    });

    render(<ForecastPage />);
    await userEvent.click(screen.getByRole("button", { name: /correr pronóstico/i }));
    await waitFor(() => screen.getByText("2024-10-31"));

    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));

    await waitFor(() => {
      expect(screen.getByText(/confirmada/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 7: Run the tests to verify they fail**

Run (from `frontend/`): `npm run test`
Expected: FAIL — `Cannot find module './ForecastPage'` (or similar), since `ForecastPage.tsx` doesn't exist yet.

- [ ] **Step 8: Write `frontend/src/features/forecast/ForecastPage.tsx`**

```typescript
import { useState } from "react";
import {
  confirmAlert,
  FeedbackRow,
  listFeedback,
  rejectAlert,
  runForecast,
  Verdict,
} from "./api";

export function ForecastPage() {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRunForecast() {
    setLoading(true);
    setError(null);
    try {
      const result = await runForecast();
      setVerdicts(result.verdicts);
      const feedbackResult = await listFeedback();
      setFeedback(feedbackResult.rows);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(fecha: string) {
    const updated = await confirmAlert(fecha);
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
  }

  async function handleReject(fecha: string) {
    const updated = await rejectAlert(fecha, 0, "Rechazada desde la interfaz");
    setFeedback((rows) => rows.map((row) => (row.fecha === fecha ? updated : row)));
  }

  function stateFor(fecha: string): string {
    return feedback.find((row) => row.fecha === fecha)?.estado_validacion ?? "pendiente";
  }

  return (
    <div>
      <h1>Pronóstico de estrés hídrico</h1>
      <button onClick={handleRunForecast} disabled={loading}>
        {loading ? "Corriendo..." : "Correr pronóstico"}
      </button>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Alerta</th>
            <th>Probabilidad</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {verdicts.map((verdict) => (
            <tr key={verdict.fecha}>
              <td>{verdict.fecha}</td>
              <td>{verdict.alerta ? "Sí" : "No"}</td>
              <td>{verdict.probabilidad.toFixed(2)}</td>
              <td>{stateFor(verdict.fecha)}</td>
              <td>
                <button onClick={() => handleConfirm(verdict.fecha)}>Confirmar</button>
                <button onClick={() => handleReject(verdict.fecha)}>Rechazar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 9: Update `frontend/src/App.tsx` to render the page**

```typescript
import { ForecastPage } from "./features/forecast/ForecastPage";

function App() {
  return <ForecastPage />;
}

export default App;
```

- [ ] **Step 10: Run the tests to verify they pass**

Run (from `frontend/`): `npm run test`
Expected: PASS (both tests in `ForecastPage.test.tsx`).

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Vite+React+TS app with the forecast/alerts page"
```

---

### Task 4: CI, docs, and manual end-to-end verification

**Files:**
- Modify: `.github/workflows/ci.yml` (add `backend-quality` and `frontend-quality` jobs, path-filtered)
- Modify: `docs/seguimiento-tareas.md`
- Modify: `openspec/specs/architecture-integration/spec.md` and `openspec/specs/human-feedback/spec.md` (note that both are now exposed via `alerting-ui`)
- Create: `openspec/specs/alerting-ui/spec.md` (living spec)
- Modify: `openspec/changes/add-alerting-ui/proposal.md` (add "Estado: implementado" pointer)
- Modify: `openspec/changes/add-alerting-ui/tasks.md` (check all boxes with evidence)

**Interfaces:**
- Consumes: nothing new — this task only wires up CI and documents what Tasks 1-3 already built.
- Produces: nothing consumed by later tasks (this plan's last task).

- [ ] **Step 1: Add CI jobs for backend and frontend**

Modify `.github/workflows/ci.yml` — add two new jobs after `python-quality`:

```yaml
  backend-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependencias
        run: pip install -e ".[dev,backend]"

      - name: Lint (ruff)
        run: ruff check backend/app

      - name: Formato (black)
        run: black --check backend/app

      - name: Tests (pytest)
        run: cd backend && python -m pytest

  frontend-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Instalar dependencias
        run: cd frontend && npm ci

      - name: Tests (vitest)
        run: cd frontend && npm run test

      - name: Build
        run: cd frontend && npm run build
```

- [ ] **Step 2: Verify the CI YAML is valid**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: no error (confirms valid YAML syntax before pushing).

- [ ] **Step 3: Manual end-to-end verification**

Run the backend (from repo root, in one terminal): `cd backend && uvicorn app.main:app --reload --port 8000`
Expected: server starts, logs `Uvicorn running on http://127.0.0.1:8000`.

Run the frontend (from repo root, in a second terminal): `cd frontend && npm run dev`
Expected: Vite dev server starts, logs a `http://localhost:5173` URL.

Open `http://localhost:5173` in a browser. Click "Correr pronóstico". Confirm:
- A table appears with real dates from `data/melchor_romero_2024_consolidado.parquet` and their alert/probability.
- Clicking "Confirmar" on a row changes its displayed state to `confirmada`.
- Clicking "Rechazar" on a row changes its displayed state to `rechazada`.
- Refreshing the page and clicking "Correr pronóstico" again preserves the states of rows already validated (confirms `upsert_feedback_log` behavior end-to-end).

Record the real numbers observed (train/test row counts, how many alerts, at least one confirm/reject) — these go into the spec update in Step 4.

- [ ] **Step 4: Create the living spec `openspec/specs/alerting-ui/spec.md`**

```markdown
# Spec: alerting-ui

Capacidad implementada (Épica 3, HU5+HU6 — primera exposición de retroalimentación humana y pipeline completo a través de una interfaz de usuario). Origen: `openspec/changes/add-alerting-ui/`. Este documento es la fuente de verdad vigente de la capacidad.

## Requirements

### Requirement: Ejecución de pronóstico desde la interfaz

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset consolidado configurado, y devolver un veredicto por fecha (alerta sí/no, probabilidad) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico produce alertas y persiste el feedback inicial

- **GIVEN** un dataset consolidado disponible bajo el nombre configurado por variable de entorno
- **WHEN** se invoca el endpoint de ejecución de pronóstico
- **THEN** se devuelve una lista de veredictos por fecha (fecha, alerta, probabilidad), y el registro de retroalimentación queda persistido con esas fechas en estado `pendiente` (o conservando su estado previo si ya existían)

Implementado en `backend/app/routers/forecast.py` (`POST /forecast/run`), testeado en `backend/tests/test_forecast.py`. Verificado manualmente contra el dataset real y el frontend real: [completar con los números observados en la Task 4, Step 3 — filas de train/test, cantidad de alertas].

### Requirement: Consulta y validación humana de alertas

El sistema DEBE poder listar el registro de retroalimentación persistido, y permitir confirmar o rechazar una alerta puntual identificada por fecha.

#### Scenario: Confirmar una alerta vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de confirmación para esa fecha
- **THEN** el registro persistido queda con esa fecha en estado `confirmada`

#### Scenario: Rechazar una alerta con corrección vía la API

- **GIVEN** un registro de retroalimentación con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca el endpoint de rechazo para esa fecha, con una etiqueta corregida y una observación
- **THEN** el registro persistido queda con esa fecha en estado `rechazada`, con la corrección y la observación guardadas

Implementado en `backend/app/routers/feedback.py` (`GET /feedback`, `POST /feedback/{fecha}/confirm`, `POST /feedback/{fecha}/reject`), testeado en `backend/tests/test_feedback.py`. Verificado manualmente end-to-end con el frontend real: confirmar/rechazar una alerta actualiza el estado mostrado, y persiste entre corridas del pronóstico (una fecha ya validada no vuelve a `pendiente` al correr el pronóstico de nuevo).

## Limitaciones conocidas

- Un único modelo fijo (Random Forest, configuración base) genera el veredicto; el motor de selección/ensamble entre varios modelos queda para una iteración futura (`openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance").
- No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real.
- El disparo de recalibración supervisada (HU5) no está conectado a la UI todavía.
- El registro de retroalimentación asume un único pronóstico por fecha calendario — no distingue entre pronósticos recalculados en momentos distintos para la misma fecha objetivo. Esto no se expone con el dataset histórico estático actual, pero deberá resolverse antes de soportar datos de sensores en vivo con recálculo continuo.
- El backend entrena el modelo en cada corrida (sin cachear); aceptable con el tamaño de dataset actual (~357 filas), a revisar si el dataset crece significativamente.
```

- [ ] **Step 5: Add pointer notes in `architecture-integration` and `human-feedback` specs**

Append this line to the end of the `## Limitaciones conocidas` section (or right after the header if there's no such section) of `openspec/specs/architecture-integration/spec.md`:

```markdown
- Expuesto por primera vez a través de una interfaz de usuario en `openspec/specs/alerting-ui/spec.md` (`POST /forecast/run`).
```

Append this line to the end of the `## Limitaciones conocidas` section of `openspec/specs/human-feedback/spec.md`:

```markdown
- Expuesto por primera vez a través de una interfaz de usuario en `openspec/specs/alerting-ui/spec.md` (`GET /feedback`, confirmar/rechazar).
```

- [ ] **Step 6: Add the "Estado: implementado" pointer to the change proposal**

Append to the end of `openspec/changes/add-alerting-ui/proposal.md`:

```markdown

## Estado: implementado

Ver [`openspec/specs/alerting-ui/spec.md`](../../specs/alerting-ui/spec.md) para los requisitos vigentes y la verificación end-to-end real.
```

- [ ] **Step 7: Check all boxes in `openspec/changes/add-alerting-ui/tasks.md` with evidence**

Replace each `- [ ]` line with `- [x]` and append a short evidence note (file path + test file) matching what Tasks 1-3 actually built, plus the real numbers observed in Task 4 Step 3 for the manual E2E line.

- [ ] **Step 8: Update `docs/seguimiento-tareas.md`**

Add a new section after the "HU8" section (before "Infraestructura de desarrollo (ADR-0003)"):

```markdown
## Interfaz de usuario (alerting-ui, HU5+HU6)

Primer scaffolding real de `backend/` y `frontend/` (ADR-0003), anticipado desde HU5 y construido después de completar HU1-HU8. Expone el pipeline completo (HU6) y el mecanismo de retroalimentación humana (HU5) a través de una interfaz de usuario.

| Tarea | Estado | Evidencia / motivo |
|---|---|---|
| Backend: `POST /forecast/run` | ✅ | `backend/app/routers/forecast.py`; `backend/tests/test_forecast.py`. |
| Backend: `GET /feedback`, confirmar, rechazar | ✅ | `backend/app/routers/feedback.py`; `backend/tests/test_feedback.py`. |
| Frontend: página de pronóstico y alertas | ✅ | `frontend/src/features/forecast/ForecastPage.tsx`; `frontend/src/features/forecast/ForecastPage.test.tsx`. |
| Verificación manual end-to-end (backend + frontend + dataset real) | ✅ | Ver `openspec/specs/alerting-ui/spec.md` para los números reales observados. |
| CI (jobs `backend-quality`, `frontend-quality`) | ✅ | `.github/workflows/ci.yml`. |

**Fuera de alcance, documentado para la próxima iteración**: motor de selección/ensamble entre varios modelos, ingesta de datos de sensores en vivo, disparo de recalibración desde la UI, robustez ante escasez/ruido en producción (ver `openspec/changes/add-alerting-ui/proposal.md`, "Fuera de alcance de este change").
```

- [ ] **Step 9: Run the full Python test suite one more time to confirm nothing broke**

Run (from repo root): `pytest`
Expected: all existing tests still PASS (this plan added `backend/` as a separate test root; it should not interfere with the root `tests/` suite).

- [ ] **Step 10: Commit**

```bash
git add .github/workflows/ci.yml docs/seguimiento-tareas.md openspec/
git commit -m "docs: document alerting-ui spec, CI jobs, and update seguimiento-tareas"
```

---

## Self-Review Notes (for whoever executes this plan)

- Task 1's test file references `GET /feedback` before that route exists (Task 2) — the plan explicitly has you comment those three lines out in Task 1 and uncomment them in Task 2. Don't skip the comment step; a real `404` there would make Task 1's test fail for the wrong reason.
- The `_row_to_schema` conversion in `feedback.py` relies on `observacion` being `None` (not `NaN`) for unset values — this matches `human_feedback/schema.py`'s existing convention (`pd.Series([None] * len(dates), dtype="object")`), already fixed in HU5 to avoid a pandas `None`/`NA` mismatch after a Parquet round-trip. Do not "helpfully" change it to use `pd.isna(observacion)` for the string column — `pd.isna` on a plain string returns `False` correctly, but on `None` it returns `True`, so the current code (`None if observacion is None else observacion`) already works; just don't overcomplicate it.
