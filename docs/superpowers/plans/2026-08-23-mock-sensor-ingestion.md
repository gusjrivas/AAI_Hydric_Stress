# Mock Sensor Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conectar una fuente de datos en vivo (mock, sin sensor real todavía) al backend de `alerting-ui`, vía un endpoint de ingesta genérico y un generador sintético por random walk acotado.

**Architecture:** `data_ingestion.storage.append_reading` agrega una fila a un dataset existente o lo crea. `data_ingestion.mock_sensor` genera lecturas plausibles encadenadas (una por día para el backfill, una por invocación para el tráfico en vivo), sin mantener estado propio — siempre parte de la última fila ya persistida. El backend expone `POST /sensors/readings`, un endpoint genérico que no sabe si el llamador es un sensor real o el mock. Dos scripts CLI hacen de "sensor sintético": uno para el backfill inicial, otro para simular una lectura nueva por invocación.

**Tech Stack:** Python (numpy para el random walk, FastAPI/Pydantic para el endpoint, requests para el cliente HTTP del script), pytest.

**Spec:** `openspec/changes/add-mock-sensor-ingestion/proposal.md`, `openspec/changes/add-mock-sensor-ingestion/specs/data-ingestion/spec.md`, `openspec/changes/add-mock-sensor-ingestion/specs/alerting-ui/spec.md`, `docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md`.

## Global Constraints

- No se agregan dependencias nuevas (`numpy`, `requests`, `fastapi`, `pydantic` ya están en el proyecto).
- El generador (`generate_next_reading`) NUNCA produce `et0` — se deriva en preprocesamiento, igual que las fuentes reales (`nasa_power.py`).
- Los valores generados DEBEN quedar dentro de `data_quality.rules.get_range(column)` — reusar esa función, no inventar rangos nuevos.
- El endpoint `POST /sensors/readings` es genérico: no debe importar nada de `data_ingestion.mock_sensor` ni saber que existe un mock — solo persiste la lectura que recibe.
- El dataset en vivo es el que apunte `DATASET_NAME` (`ALERTING_UI_DATASET`) en cada deployment — nunca se hardcodea un nombre distinto ni se toca `melchor_romero_2024_consolidado` en ningún test.
- `src/architecture_integration/pipeline.py` no se modifica.
- Los scripts nuevos (`scripts/seed_mock_sensor_dataset.py`, `scripts/simulate_sensor_readings.py`) siguen la convención ya establecida en `scripts/` de este repo: sin test automatizado dedicado, verificados manualmente y documentados con el resultado real.
- Cada tarea termina con sus tests en verde; al final de la Tarea 3, correr `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`.

---

### Task 1: `append_reading` en el contrato de acceso a datos

**Files:**
- Modify: `src/data_ingestion/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `data_ingestion.schema.normalize_to_schema`, `PROVENANCE_COLUMN`, `TIMESTAMP_COLUMN` (ya existentes, sin modificar).
- Produces: `append_reading(name: str, row: dict, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame`. Consumido por Tarea 3.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_storage.py`:

```python
def test_append_reading_creates_dataset_when_missing(tmp_path):
    from data_ingestion.storage import append_reading

    row = {"timestamp": pd.Timestamp("2026-01-01"), "temperature": 25.0, "origen": "real"}

    updated = append_reading("nuevo_dataset", row, data_dir=tmp_path)

    assert len(updated) == 1
    assert updated.loc[0, "temperature"] == 25.0
    assert updated.loc[0, "origen"] == "real"
    reloaded = load_dataset("nuevo_dataset", data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded, updated)


def test_append_reading_adds_row_to_existing_dataset(tmp_path):
    from data_ingestion.storage import append_reading

    existing = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01"]), "temperature": [25.0]})
    save_dataset("con_historia", existing, data_dir=tmp_path)

    row = {"timestamp": pd.Timestamp("2026-01-02"), "temperature": 26.0, "origen": "real"}
    updated = append_reading("con_historia", row, data_dir=tmp_path)

    assert len(updated) == 2
    assert list(updated["timestamp"]) == list(pd.to_datetime(["2026-01-01", "2026-01-02"]))


def test_append_reading_sorts_by_timestamp_even_if_out_of_order(tmp_path):
    from data_ingestion.storage import append_reading

    existing = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-05"]), "temperature": [25.0]})
    save_dataset("desordenado", existing, data_dir=tmp_path)

    row = {"timestamp": pd.Timestamp("2026-01-02"), "temperature": 20.0, "origen": "real"}
    updated = append_reading("desordenado", row, data_dir=tmp_path)

    assert list(updated["timestamp"]) == list(pd.to_datetime(["2026-01-02", "2026-01-05"]))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ImportError: cannot import name 'append_reading' from 'data_ingestion.storage'` en los 3 tests nuevos; los tests preexistentes de ese archivo siguen en PASS.

- [ ] **Step 3: Implementar la función**

En `src/data_ingestion/storage.py`, agregar el import al inicio del archivo (después de `import pandas as pd`):

```python
from data_ingestion.schema import PROVENANCE_COLUMN, TIMESTAMP_COLUMN, normalize_to_schema
```

Y agregar al final del archivo:

```python
def append_reading(name: str, row: dict, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Agrega `row` (un dict con al menos `timestamp`) como una fila
    nueva al dataset `name`, normalizada al esquema completo. Crea el
    dataset si todavía no existe. Devuelve el dataset actualizado, ya
    guardado, ordenado por `timestamp`.
    """
    provenance = row.get(PROVENANCE_COLUMN, "real")
    new_row = normalize_to_schema(pd.DataFrame([row]), provenance=provenance)

    try:
        existing = load_dataset(name, data_dir=data_dir)
        updated = pd.concat([existing, new_row], ignore_index=True)
    except FileNotFoundError:
        updated = new_row

    updated = updated.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
    save_dataset(name, updated, data_dir=data_dir)
    return updated
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (todos: los preexistentes más los 3 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/data_ingestion/storage.py tests/test_storage.py
git commit -m "feat: agrega append_reading para ingerir una lectura nueva a un dataset"
```

---

### Task 2: Generador mock por random walk acotado

**Files:**
- Create: `src/data_ingestion/mock_sensor.py`
- Test: `tests/test_mock_sensor.py`

**Interfaces:**
- Consumes: `data_ingestion.schema.PROVENANCE_COLUMN`, `TIMESTAMP_COLUMN`, `REQUIRED_COLUMNS`, `normalize_to_schema`; `data_ingestion.storage.DEFAULT_DATA_DIR`, `save_dataset`; `data_quality.rules.get_range` (todos ya existentes, sin modificar).
- Produces: `generate_next_reading(previous: pd.Series | None, timestamp: pd.Timestamp, random_state: int | None = None) -> dict` y `seed_mock_dataset(name: str, start_date: date, end_date: date, random_state: int = 42, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame`. Consumidos por Tarea 4 (scripts).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_mock_sensor.py`:

```python
import pandas as pd

from data_ingestion.mock_sensor import generate_next_reading, seed_mock_dataset
from data_ingestion.schema import REQUIRED_COLUMNS, TIMESTAMP_COLUMN
from data_quality.rules import get_range


def test_generate_next_reading_without_history_stays_within_physical_range():
    reading = generate_next_reading(None, pd.Timestamp("2026-01-01"), random_state=0)

    for column in REQUIRED_COLUMNS:
        if column in (TIMESTAMP_COLUMN, "et0"):
            continue
        low, high = get_range(column)
        assert low <= reading[column] <= high
    assert reading["origen"] == "sintetico"
    assert "et0" not in reading


def test_generate_next_reading_stays_close_to_previous_value():
    previous = pd.Series(
        {
            "soil_moisture": 0.3,
            "temperature": 20.0,
            "relative_humidity": 60.0,
            "precipitation": 0.0,
            "solar_radiation": 15.0,
            "wind_speed": 3.0,
        }
    )

    reading = generate_next_reading(previous, pd.Timestamp("2026-01-02"), random_state=0)

    low, high = get_range("temperature")
    max_step = (high - low) * 0.1  # tolerancia generosa: varios desvíos del paso (2% del rango)
    assert abs(reading["temperature"] - previous["temperature"]) <= max_step


def test_seed_mock_dataset_produces_one_row_per_day(tmp_path):
    generated = seed_mock_dataset(
        "mock_seed",
        start_date=pd.Timestamp("2026-01-01").date(),
        end_date=pd.Timestamp("2026-01-05").date(),
        data_dir=tmp_path,
    )

    assert len(generated) == 5
    assert list(generated[TIMESTAMP_COLUMN]) == list(pd.date_range("2026-01-01", "2026-01-05"))
    assert (generated["origen"] == "sintetico").all()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_mock_sensor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data_ingestion.mock_sensor'`.

- [ ] **Step 3: Implementar el módulo**

Crear `src/data_ingestion/mock_sensor.py`:

```python
"""Generador de lecturas sintéticas de sensor por random walk acotado
(spec data-ingestion, requirements "Generación de lecturas sintéticas
por random walk acotado" y "Backfill inicial de un dataset en vivo").
No mantiene estado propio: cada lectura se genera a partir de la
anterior, que se lee del propio dataset persistido (ADR-0007).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_ingestion.schema import (
    PROVENANCE_COLUMN,
    REQUIRED_COLUMNS,
    TIMESTAMP_COLUMN,
    normalize_to_schema,
)
from data_ingestion.storage import DEFAULT_DATA_DIR, save_dataset
from data_quality.rules import get_range

_STEP_FRACTION = 0.02  # tamaño del paso aleatorio, como fracción del ancho del rango físico


def generate_next_reading(
    previous: pd.Series | None, timestamp: pd.Timestamp, random_state: int | None = None
) -> dict[str, Any]:
    """Genera una lectura sintética para `timestamp`, columna
    obligatoria por columna obligatoria (excepto `et0`, que se deriva
    en preprocesamiento), dando un paso aleatorio chico desde
    `previous` (o partiendo del punto medio del rango físico si no hay
    lectura anterior), recortado a `data_quality.rules.get_range`.
    """
    rng = np.random.default_rng(random_state)
    reading: dict[str, Any] = {TIMESTAMP_COLUMN: timestamp}

    for column in REQUIRED_COLUMNS:
        if column in (TIMESTAMP_COLUMN, "et0"):
            continue
        low, high = get_range(column)
        step = (high - low) * _STEP_FRACTION
        if previous is not None and pd.notna(previous.get(column)):
            base = float(previous[column])
        else:
            base = (low + high) / 2
        value = base + rng.normal(0.0, step)
        reading[column] = float(np.clip(value, low, high))

    reading[PROVENANCE_COLUMN] = "sintetico"
    return reading


def seed_mock_dataset(
    name: str,
    start_date: date,
    end_date: date,
    random_state: int = 42,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    """Genera un backfill de lecturas sintéticas encadenadas, una por
    día entre `start_date` y `end_date` (incluidos), y las guarda bajo
    `name`. Devuelve el dataset generado, ya guardado.
    """
    dates = pd.date_range(start_date, end_date, freq="D")

    rows = []
    previous: pd.Series | None = None
    for offset, timestamp in enumerate(dates):
        reading = generate_next_reading(previous, timestamp, random_state=random_state + offset)
        rows.append(reading)
        previous = pd.Series(reading)

    generated = normalize_to_schema(pd.DataFrame(rows), provenance="sintetico")
    save_dataset(name, generated, data_dir=data_dir)
    return generated
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_mock_sensor.py -v`
Expected: PASS (los 3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data_ingestion/mock_sensor.py tests/test_mock_sensor.py
git commit -m "feat: agrega el generador mock de lecturas de sensor por random walk acotado"
```

---

### Task 3: Endpoint `POST /sensors/readings`

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/config.py`
- Create: `backend/app/routers/sensors.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_sensors.py`

**Interfaces:**
- Consumes: `append_reading` (Tarea 1); `DATASET_NAME` (`backend/app/config.py`, ya existente).
- Produces: `POST /sensors/readings` devolviendo `SensorReadingResponse`. Última tarea con tests automatizados — consumida manualmente por la Tarea 4.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_sensors.py`:

```python
import pandas as pd
from app.config import DATASET_NAME, get_dataset_data_dir
from app.main import app
from data_ingestion.storage import load_dataset, save_dataset
from fastapi.testclient import TestClient


def test_ingest_reading_creates_dataset_when_missing(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    response = client.post(
        "/sensors/readings",
        json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0, "procedencia": "sintetico"},
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 1

    app.dependency_overrides.clear()


def test_ingest_reading_appends_to_existing_dataset(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})
    response = client.post(
        "/sensors/readings", json={"timestamp": "2026-01-02T00:00:00", "temperature": 26.0}
    )

    assert response.status_code == 200
    assert response.json()["filas_totales"] == 2

    app.dependency_overrides.clear()


def test_ingest_reading_defaults_procedencia_to_real(tmp_path):
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})

    df = load_dataset(DATASET_NAME, data_dir=tmp_path)
    assert df.loc[0, "origen"] == "real"

    app.dependency_overrides.clear()


def test_ingest_reading_does_not_touch_other_datasets(tmp_path, monkeypatch):
    historical = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01"]), "temperature": [20.0]})
    save_dataset("melchor_romero_2024_consolidado", historical, data_dir=tmp_path)

    monkeypatch.setattr("app.routers.sensors.DATASET_NAME", "otro_dataset_en_vivo")
    app.dependency_overrides[get_dataset_data_dir] = lambda: tmp_path
    client = TestClient(app)

    client.post("/sensors/readings", json={"timestamp": "2026-01-01T00:00:00", "temperature": 25.0})

    reloaded_historical = load_dataset("melchor_romero_2024_consolidado", data_dir=tmp_path)
    pd.testing.assert_frame_equal(reloaded_historical, historical)

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && python -m pytest tests/test_sensors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.routers.sensors'` (o `404 Not Found` si la colección del módulo de test falla de otra forma al importar `get_dataset_data_dir`, que tampoco existe todavía).

- [ ] **Step 3: Agregar los schemas**

En `backend/app/schemas.py`, cambiar la línea de import (línea 5):

```python
from datetime import date
```

por:

```python
from datetime import date, datetime
```

Y agregar al final del archivo:

```python
class SensorReadingRequest(BaseModel):
    timestamp: datetime
    soil_moisture: float | None = None
    temperature: float | None = None
    relative_humidity: float | None = None
    precipitation: float | None = None
    solar_radiation: float | None = None
    wind_speed: float | None = None
    et0: float | None = None
    procedencia: str = "real"


class SensorReadingResponse(BaseModel):
    timestamp: datetime
    filas_totales: int
```

- [ ] **Step 4: Agregar la dependencia de directorio**

En `backend/app/config.py`, agregar al final del archivo:

```python
def get_dataset_data_dir() -> Path:
    """Dependencia de FastAPI: directorio donde persiste el dataset
    configurado. Overrideable en tests (`app.dependency_overrides`)
    para no escribir en el `data/` real del proyecto.
    """
    return DEFAULT_DATA_DIR
```

- [ ] **Step 5: Implementar el router**

Crear `backend/app/routers/sensors.py`:

```python
"""Router de ingesta de lecturas de sensores (spec alerting-ui,
requirement "Ingesta de lecturas de sensores desde la interfaz de
datos"). Genérico: no distingue si el llamador es un sensor real o un
generador sintético (ADR-0007).
"""

from __future__ import annotations

from pathlib import Path

from data_ingestion.schema import PROVENANCE_COLUMN
from data_ingestion.storage import append_reading
from fastapi import APIRouter, Depends

from ..config import DATASET_NAME, get_dataset_data_dir
from ..schemas import SensorReadingRequest, SensorReadingResponse

router = APIRouter()


@router.post("/sensors/readings", response_model=SensorReadingResponse)
def ingest_reading(
    reading: SensorReadingRequest, data_dir: Path = Depends(get_dataset_data_dir)
) -> SensorReadingResponse:
    row = reading.model_dump(exclude={"procedencia"})
    row[PROVENANCE_COLUMN] = reading.procedencia

    updated = append_reading(DATASET_NAME, row, data_dir=data_dir)

    return SensorReadingResponse(timestamp=reading.timestamp, filas_totales=len(updated))
```

- [ ] **Step 6: Registrar el router**

En `backend/app/main.py`, cambiar:

```python
from .routers import feedback, forecast, recalibration
```

por:

```python
from .routers import feedback, forecast, recalibration, sensors
```

y agregar, después de `app.include_router(recalibration.router)`:

```python
app.include_router(sensors.router)
```

- [ ] **Step 7: Correr los tests y verificar que pasan**

Run: `cd backend && python -m pytest tests/test_sensors.py -v`
Expected: PASS (los 4 tests).

- [ ] **Step 8: Correr toda la suite del proyecto**

Run: `pytest -q` (raíz) y `cd backend && python -m pytest tests -q`
Expected: PASS en ambos, sin romper nada de `add-selection-caching` ni de ningún change anterior.

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas.py backend/app/config.py backend/app/routers/sensors.py backend/app/main.py backend/tests/test_sensors.py
git commit -m "feat: agrega el endpoint POST /sensors/readings"
```

---

### Task 4: Scripts CLI de backfill y simulación de tráfico

**Files:**
- Create: `scripts/seed_mock_sensor_dataset.py`
- Create: `scripts/simulate_sensor_readings.py`

**Interfaces:**
- Consumes: `seed_mock_dataset`, `generate_next_reading` (Tarea 2); `POST /sensors/readings` (Tarea 3, vía HTTP).
- Produces: nada consumido por otro código — última tarea del plan.

- [ ] **Step 1: Implementar el script de backfill**

Crear `scripts/seed_mock_sensor_dataset.py`:

```python
"""Genera un backfill inicial de lecturas sintéticas de sensor,
encadenadas por random walk acotado, y las guarda como un dataset
nuevo (ADR-0007).

Uso:
    python scripts/seed_mock_sensor_dataset.py --name sensores_en_vivo \
        --start 2026-05-01 --end 2026-07-29
"""

from __future__ import annotations

import argparse
from datetime import date

from data_ingestion.mock_sensor import seed_mock_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated = seed_mock_dataset(
        args.name, start_date=args.start, end_date=args.end, random_state=args.random_state
    )
    print(f"Backfill generado: {len(generated)} filas, dataset '{args.name}'.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Implementar el script de simulación de tráfico**

Crear `scripts/simulate_sensor_readings.py`:

```python
"""Simula una lectura de sensor y la envía al backend real vía HTTP
(ADR-0007) — cliente sintético del endpoint genérico POST
/sensors/readings, que no sabe que el llamador es un mock.

Uso:
    python scripts/simulate_sensor_readings.py --dataset sensores_en_vivo \
        --backend-url http://localhost:8000
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import requests

from data_ingestion.mock_sensor import generate_next_reading
from data_ingestion.storage import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--backend-url", default="http://localhost:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        existing = load_dataset(args.dataset)
        previous = existing.sort_values("timestamp").iloc[-1]
    except FileNotFoundError:
        previous = None

    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    reading = generate_next_reading(previous, timestamp)

    payload = {
        "timestamp": reading["timestamp"].isoformat(),
        "soil_moisture": reading.get("soil_moisture"),
        "temperature": reading.get("temperature"),
        "relative_humidity": reading.get("relative_humidity"),
        "precipitation": reading.get("precipitation"),
        "solar_radiation": reading.get("solar_radiation"),
        "wind_speed": reading.get("wind_speed"),
        "procedencia": "sintetico",
    }
    response = requests.post(f"{args.backend_url}/sensors/readings", json=payload, timeout=30)
    response.raise_for_status()
    print(f"Lectura enviada: {response.json()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verificación manual de punta a punta**

Con el stack corriendo (`docker compose up -d --build`, o `uvicorn app.main:app --port 8000` local desde `backend/`):

```bash
python scripts/seed_mock_sensor_dataset.py --name sensores_en_vivo --start 2026-05-01 --end 2026-07-29
python scripts/simulate_sensor_readings.py --dataset sensores_en_vivo --backend-url http://localhost:8000
```

Confirmar: el primer comando imprime `Backfill generado: 90 filas, dataset 'sensores_en_vivo'.`; el segundo imprime `Lectura enviada: {...'filas_totales': 91...}`. Correr el segundo comando una vez más y confirmar que `filas_totales` sube a 92, y que el valor de `temperature` de la nueva lectura está cerca del de la anterior (no un salto brusco). Documentar el resultado real (no asumido) en el commit de este step si difiere de lo esperado.

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_mock_sensor_dataset.py scripts/simulate_sensor_readings.py
git commit -m "feat: agrega los scripts de backfill y simulación de tráfico de sensores"
```
