# Fix Anomaly Feature Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que `is_anomaly` llegue como variable predictora real al modelo en `run_end_to_end_pipeline` (hoy se calcula pero nunca se usa), evitando fuga metodológica al ajustar el detector solo sobre `train`, y re-ejecutar/documentar los experimentos de HU7 (`+anomalías`, `completa`) que ese defecto invalidaba.

**Architecture:** `data_quality.anomaly_detection` se divide en `fit_anomaly_detector`/`apply_anomaly_detector` (nuevo, backward-compatible) manteniendo `detect_anomalies` como atajo de ambos. `architecture_integration.pipeline.run_end_to_end_pipeline` usa esas dos funciones nuevas: ajusta sobre `train`, aplica a `train` y `test`, y agrega `"is_anomaly"` a `feature_columns`. `experiment_runner.synthetic_augmentation.add_synthetic_rows` generaliza el redondeo binario (hoy solo aplicado a `target_column`) a cualquier columna booleana entre `feature_columns`, para que la configuración `completa` no genere `is_anomaly` fraccionario en filas sintéticas.

**Tech Stack:** Python (scikit-learn `IsolationForest`, pandas, pytest), MLflow (re-ejecución real, sin cambios de código en `mlflow_logging.py`).

**Spec:** `openspec/changes/fix-anomaly-feature-integration/proposal.md` y `openspec/changes/fix-anomaly-feature-integration/specs/architecture-integration/spec.md`.

## Global Constraints

- No se agregan dependencias nuevas.
- Cada tarea termina con los tests de esa tarea en verde antes de pasar a la siguiente; al final de la Tarea 3, correr toda la suite (`pytest -q`) para confirmar que nada se rompió.
- `MLFLOW_TRACKING_URI` nunca se hardcodea en `src/` — la Tarea 4 lo setea como variable de entorno al invocar el re-run, no en código.
- Dataset real para la Tarea 4: `data_ingestion.storage.load_dataset("melchor_romero_2024_consolidado")`.
- Parámetros de pipeline para la Tarea 4 (consistentes con `openspec/specs/architecture-integration/spec.md`, ya verificados: 286 filas de train / 71 de test): `label_column="soil_moisture"`, `feature_columns=["soil_moisture", "solar_radiation", "relative_humidity"]`, `split_date=date(2024, 10, 19)`, modelo `build_candidate_models(random_state=seed)["random_forest"]`.
- Semillas para la Tarea 4: `[0, 1, 2, 3, 4]` — la lista original de la primera ejecución de HU7 no quedó registrada en el repo (fue una ejecución ad hoc contra el servidor MLflow real, ver `openspec/changes/add-experiment-execution/proposal.md`, "Código afectado: ninguno nuevo"); se documenta explícitamente esta elección al escribir los resultados.
- `n_synthetic_samples=100` para la configuración `completa` (mismo valor ya documentado en `openspec/specs/experiment-runner/spec.md`).

---

### Task 1: Separar fit de transform en la detección de anomalías

**Files:**
- Modify: `src/data_quality/anomaly_detection.py`
- Test: `tests/test_anomaly_detection.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `fit_anomaly_detector(df: pd.DataFrame, columns: list[str], contamination: float = 0.05, random_state: int = 42) -> IsolationForest` y `apply_anomaly_detector(df: pd.DataFrame, columns: list[str], detector: IsolationForest) -> pd.DataFrame` (agrega la columna booleana `is_anomaly`, no reajusta el detector). `detect_anomalies` conserva su firma y comportamiento actuales. Consumidos por Tarea 2.

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_anomaly_detection.py`, cambiar la línea de import (línea 5):

```python
from data_quality.anomaly_detection import detect_anomalies, evaluate_with_injected_anomalies
```

por:

```python
from data_quality.anomaly_detection import (
    apply_anomaly_detector,
    detect_anomalies,
    evaluate_with_injected_anomalies,
    fit_anomaly_detector,
)
```

Agregar al final del archivo:

```python
def test_apply_anomaly_detector_uses_train_boundaries_not_test_own_distribution():
    train_df = _stable_series_df(n=60, seed=0)
    detector = fit_anomaly_detector(train_df, columns=["temperature", "relative_humidity"])

    shifted_test_df = _stable_series_df(n=20, seed=1).copy()
    shifted_test_df["temperature"] = shifted_test_df["temperature"] + 100.0

    result = apply_anomaly_detector(
        shifted_test_df, columns=["temperature", "relative_humidity"], detector=detector
    )

    # Con un detector fiteado en train, todo el test desplazado queda fuera de
    # los límites aprendidos: la mayoría se marca anómala. Si en cambio se
    # fiteara un detector nuevo sobre el propio test (comportamiento viejo),
    # `contamination=0.05` forzaría ~5% marcado, sin importar el desplazamiento.
    assert result["is_anomaly"].mean() > 0.5


def test_fit_anomaly_detector_returns_a_fitted_isolation_forest():
    train_df = _stable_series_df(n=60, seed=0)

    detector = fit_anomaly_detector(train_df, columns=["temperature", "relative_humidity"])

    assert hasattr(detector, "predict")
    predictions = detector.predict(train_df[["temperature", "relative_humidity"]])
    assert set(predictions) <= {-1, 1}
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `pytest tests/test_anomaly_detection.py -v`
Expected: FAIL — `ImportError: cannot import name 'fit_anomaly_detector' from 'data_quality.anomaly_detection'`.

- [ ] **Step 3: Implementar las funciones**

Reemplazar el contenido de `src/data_quality/anomaly_detection.py` desde la línea 15 (`def detect_anomalies`) hasta la línea 31 (cierre de esa función) por:

```python
def fit_anomaly_detector(
    df: pd.DataFrame,
    columns: list[str],
    contamination: float = 0.05,
    random_state: int = 42,
) -> IsolationForest:
    """Ajusta un Isolation Forest sobre `columns` de `df` y lo devuelve
    sin transformar nada. Separado de `apply_anomaly_detector` para
    poder ajustar sobre un conjunto (ej. entrenamiento) y aplicar el
    mismo detector, sin reajustar, sobre otro (ej. evaluación) —
    evitando que el segundo conjunto influya en su propia marca de
    anomalía.
    """
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(df[columns])
    return model


def apply_anomaly_detector(
    df: pd.DataFrame, columns: list[str], detector: IsolationForest
) -> pd.DataFrame:
    """Aplica un detector ya ajustado (`fit_anomaly_detector`) sobre
    `columns` de `df` y devuelve una copia con la columna booleana
    `is_anomaly`. No reajusta el detector.
    """
    result = df.copy()
    predictions = detector.predict(result[columns])
    result["is_anomaly"] = predictions == -1
    return result


def detect_anomalies(
    df: pd.DataFrame,
    columns: list[str],
    contamination: float = 0.05,
    random_state: int = 42,
) -> pd.DataFrame:
    """Ajusta un Isolation Forest sobre `columns` y devuelve una copia de
    `df` con una columna booleana `is_anomaly`. No requiere etiquetas de
    anomalía previas. Atajo de `fit_anomaly_detector` + `apply_anomaly_detector`
    sobre el mismo `df`.
    """
    detector = fit_anomaly_detector(
        df, columns=columns, contamination=contamination, random_state=random_state
    )
    return apply_anomaly_detector(df, columns=columns, detector=detector)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_anomaly_detection.py -v`
Expected: PASS (los 5 tests: los 3 preexistentes más los 2 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/data_quality/anomaly_detection.py tests/test_anomaly_detection.py
git commit -m "feat: separa fit de transform en la detección de anomalías"
```

---

### Task 2: Usar `is_anomaly` como variable predictora en `run_end_to_end_pipeline`

**Files:**
- Modify: `src/architecture_integration/pipeline.py`
- Test: `tests/test_architecture_integration_pipeline.py`

**Interfaces:**
- Consumes: `fit_anomaly_detector`, `apply_anomaly_detector` (Tarea 1).
- Produces: sin cambios de firma. `result["feature_columns"]` incluye `"is_anomaly"` cuando `include_anomaly_detection=True`; no lo incluye cuando es `False`. Consumido por Tarea 4 (re-run) y por `backend/app/pipeline.py` (sin cambios necesarios ahí, `include_anomaly_detection` sigue en `False` por defecto en ese consumidor).

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_architecture_integration_pipeline.py`:

```python
def test_run_end_to_end_pipeline_includes_is_anomaly_as_a_feature_when_enabled():
    df = _synthetic_dataset()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=model,
        include_anomaly_detection=True,
    )

    assert "is_anomaly" in result["feature_columns"]
    assert "is_anomaly" in result["train"].columns


def test_run_end_to_end_pipeline_excludes_is_anomaly_when_disabled():
    df = _synthetic_dataset()
    model = build_candidate_models(random_state=0)["logistic_regression"]

    result = run_end_to_end_pipeline(
        df,
        label_column="soil_moisture",
        feature_columns=["soil_moisture", "solar_radiation"],
        split_date=df["timestamp"].iloc[45].date(),
        model=model,
        include_anomaly_detection=False,
    )

    assert "is_anomaly" not in result["feature_columns"]
```

Nota: el segundo test (`..._excludes_is_anomaly_when_disabled`) ya pasa con el código actual (hoy `is_anomaly` nunca es feature) — se agrega igual para fijar el contrato del Scenario "Sin detección de anomalías, el comportamiento no cambia" de la spec, no porque sea un test que deba fallar primero.

- [ ] **Step 2: Correr los tests y verificar el estado esperado**

Run: `pytest tests/test_architecture_integration_pipeline.py -v`
Expected: `test_run_end_to_end_pipeline_includes_is_anomaly_as_a_feature_when_enabled` FAIL (`AssertionError: assert 'is_anomaly' in [...]` — no está en la lista); `test_run_end_to_end_pipeline_excludes_is_anomaly_when_disabled` PASS; los demás tests preexistentes PASS.

- [ ] **Step 3: Implementar el cambio**

En `src/architecture_integration/pipeline.py`, cambiar la línea de import (línea 23):

```python
from data_quality.anomaly_detection import detect_anomalies
```

por:

```python
from data_quality.anomaly_detection import apply_anomaly_detector, fit_anomaly_detector
```

Y reemplazar el bloque (líneas 72-78):

```python
    if include_anomaly_detection:
        train = detect_anomalies(
            train, columns=feature_columns, contamination=contamination, random_state=random_state
        )
        test = detect_anomalies(
            test, columns=feature_columns, contamination=contamination, random_state=random_state
        )
```

por:

```python
    if include_anomaly_detection:
        detector = fit_anomaly_detector(
            train, columns=feature_columns, contamination=contamination, random_state=random_state
        )
        train = apply_anomaly_detector(train, columns=feature_columns, detector=detector)
        test = apply_anomaly_detector(test, columns=feature_columns, detector=detector)
        feature_cols = feature_cols + ["is_anomaly"]
```

(El detector se ajusta solo sobre `train`, tal como quedó decidido en `openspec/changes/fix-anomaly-feature-integration/proposal.md` — evita que `test` influya en su propia marca de anomalía.)

Actualizar también el docstring de la función (líneas 49-53), agregando una frase: "Si `include_anomaly_detection` es `True`, el detector se ajusta solo sobre el conjunto de entrenamiento y `is_anomaly` se agrega como variable predictora."

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_architecture_integration_pipeline.py -v`
Expected: PASS (los 6 tests: los 4 preexistentes más los 2 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/architecture_integration/pipeline.py tests/test_architecture_integration_pipeline.py
git commit -m "fix: incluye is_anomaly como variable predictora en run_end_to_end_pipeline"
```

---

### Task 3: Redondear columnas booleanas en filas sintéticas

**Files:**
- Modify: `src/experiment_runner/synthetic_augmentation.py`
- Test: `tests/test_synthetic_augmentation.py`

**Interfaces:**
- Consumes: nada de tareas anteriores directamente (pero resuelve un problema que la Tarea 2 expone: `is_anomaly` puede ahora estar en `feature_columns` cuando `add_synthetic_rows` se usa para la configuración `completa`).
- Produces: sin cambios de firma. `add_synthetic_rows` sigue devolviendo un DataFrame con las mismas columnas; ahora cualquier columna de `feature_columns`/`target_column` cuyo `dtype` en `train_df` sea `bool` queda en `{0, 1}` en las filas sintéticas, no fraccionaria.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_synthetic_augmentation.py`:

```python
def test_add_synthetic_rows_rounds_boolean_feature_columns_to_zero_or_one():
    train_df = _feature_engineered_train_df()
    train_df["is_anomaly"] = False
    train_df.loc[:5, "is_anomaly"] = True

    augmented = add_synthetic_rows(
        train_df,
        feature_columns=["feature_a_lag1", "feature_b_roll_mean3", "is_anomaly"],
        target_column="stress_label",
        n_samples=20,
        random_state=42,
    )

    synthetic_rows = augmented[augmented["origen"] == "sintetico"]
    assert set(synthetic_rows["is_anomaly"].unique()) <= {0, 1}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_synthetic_augmentation.py::test_add_synthetic_rows_rounds_boolean_feature_columns_to_zero_or_one -v`
Expected: FAIL — `set(synthetic_rows["is_anomaly"].unique())` contiene valores fraccionarios (ej. `0.37`), no un subconjunto de `{0, 1}`.

- [ ] **Step 3: Implementar el redondeo genérico**

En `src/experiment_runner/synthetic_augmentation.py`, reemplazar el cuerpo de `add_synthetic_rows` (líneas 30-42):

```python
    rng = np.random.default_rng(random_state)
    columns = feature_columns + [target_column]

    mean = train_df[columns].mean().to_numpy()
    covariance = train_df[columns].cov().to_numpy()

    samples = rng.multivariate_normal(mean, covariance, size=n_samples)
    synthetic = pd.DataFrame(samples, columns=columns)
    synthetic[target_column] = synthetic[target_column].round().clip(0, 1).astype(int)
    synthetic["origen"] = "sintetico"

    return pd.concat([train_df, synthetic], ignore_index=True)
```

por:

```python
    rng = np.random.default_rng(random_state)
    columns = feature_columns + [target_column]
    boolean_columns = [c for c in columns if train_df[c].dtype == bool]

    mean = train_df[columns].mean().to_numpy()
    covariance = train_df[columns].cov().to_numpy()

    samples = rng.multivariate_normal(mean, covariance, size=n_samples)
    synthetic = pd.DataFrame(samples, columns=columns)
    for column in boolean_columns:
        synthetic[column] = synthetic[column].round().clip(0, 1).astype(int)
    synthetic[target_column] = synthetic[target_column].round().clip(0, 1).astype(int)
    synthetic["origen"] = "sintetico"

    return pd.concat([train_df, synthetic], ignore_index=True)
```

Actualizar también el docstring de la función, agregando una frase: "Cualquier columna booleana entre `feature_columns` (ej. `is_anomaly`) también se redondea y recorta a `{0, 1}`."

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `pytest tests/test_synthetic_augmentation.py -v`
Expected: PASS (los 2 tests: el preexistente más el nuevo).

- [ ] **Step 5: Correr toda la suite del proyecto**

Run: `pytest -q`
Expected: PASS (todos, incluyendo `tests/test_experiment_runner.py` que usa `add_synthetic_rows` indirectamente vía `run_configuration`, y `backend/tests/` — que no se ven afectados porque `backend/app/pipeline.py` sigue llamando con `include_anomaly_detection=False` por defecto de HU5/HU6, sin cambios).

- [ ] **Step 6: Commit**

```bash
git add src/experiment_runner/synthetic_augmentation.py tests/test_synthetic_augmentation.py
git commit -m "fix: redondea columnas booleanas (ej. is_anomaly) en filas sintéticas"
```

---

### Task 4: Re-ejecutar `+anomalías`/`completa` y actualizar specs/docs con los resultados reales

**Files:**
- Modify: `openspec/specs/experiment-runner/spec.md`
- Modify: `openspec/specs/architecture-integration/spec.md`
- Modify: `openspec/specs/data-quality/spec.md`
- Modify: `docs/research/hu8-analisis-resultados.md`
- Modify: `docs/research/hu8-resultados-discusion-conclusiones.md`
- Modify: `docs/seguimiento-tareas.md`

**Interfaces:**
- Consumes: `run_end_to_end_pipeline` con `is_anomaly` como feature (Tarea 2), `add_synthetic_rows` con redondeo booleano (Tarea 3), `experiment_runner.runner.run_configuration`, `experiment_runner.mlflow_logging.log_configuration_results` (sin cambios de código, ya existentes).
- Produces: nada consumido por otra tarea — última tarea del plan.

- [ ] **Step 1: Levantar el servidor MLflow real**

```bash
docker compose up -d postgres minio minio-init mlflow
```

Esperar a que `mlflow` quede saludable (`docker compose ps`), igual que en la verificación original de HU7 (`openspec/changes/add-experiment-execution/proposal.md`).

- [ ] **Step 2: Re-ejecutar `+anomálias` y registrar en MLflow**

Correr, con el entorno virtual del proyecto activo y `MLFLOW_TRACKING_URI` apuntando al servidor real:

```bash
MLFLOW_TRACKING_URI=http://localhost:5000 python -c "
from datetime import date
from data_ingestion.storage import load_dataset
from experiment_runner.runner import run_configuration
from experiment_runner.mlflow_logging import log_configuration_results

df = load_dataset('melchor_romero_2024_consolidado')
seeds = [0, 1, 2, 3, 4]
feature_columns = ['soil_moisture', 'solar_radiation', 'relative_humidity']

results = run_configuration(
    df,
    label_column='soil_moisture',
    feature_columns=feature_columns,
    split_date=date(2024, 10, 19),
    model_name='random_forest',
    include_anomaly_detection=True,
    include_synthetic=False,
    seeds=seeds,
)
print(results)
print(results[['precision', 'recall', 'f1', 'roc_auc']].agg(['mean', 'std']))
log_configuration_results('anomalias-refit', {'include_anomaly_detection': True, 'include_synthetic': False}, results)
"
```

Anotar los valores impresos de `f1`/`roc_auc`/`precision`/`recall` (media y desvío) — se usan en el Step 5.

- [ ] **Step 3: Re-ejecutar `completa` y registrar en MLflow**

```bash
MLFLOW_TRACKING_URI=http://localhost:5000 python -c "
from datetime import date
from data_ingestion.storage import load_dataset
from experiment_runner.runner import run_configuration
from experiment_runner.mlflow_logging import log_configuration_results

df = load_dataset('melchor_romero_2024_consolidado')
seeds = [0, 1, 2, 3, 4]
feature_columns = ['soil_moisture', 'solar_radiation', 'relative_humidity']

results = run_configuration(
    df,
    label_column='soil_moisture',
    feature_columns=feature_columns,
    split_date=date(2024, 10, 19),
    model_name='random_forest',
    include_anomaly_detection=True,
    include_synthetic=True,
    seeds=seeds,
    n_synthetic_samples=100,
)
print(results)
print(results[['precision', 'recall', 'f1', 'roc_auc']].agg(['mean', 'std']))
log_configuration_results('completa-refit', {'include_anomaly_detection': True, 'include_synthetic': True, 'n_synthetic_samples': 100}, results)
"
```

Anotar los valores impresos igual que en el Step 2.

- [ ] **Step 4: Verificar que ya no son idénticas a `base`/`+sintéticos`**

Comparar a mano los números anotados en los Steps 2 y 3 contra la tabla ya publicada (`Base`: F1 0.4585±0.0423, ROC-AUC 0.5551±0.0191; `+Sintéticos`: F1 0.3123±0.0862, ROC-AUC 0.5083±0.0439). Si `+Anomálias` sigue dando *exactamente* los mismos números que `Base` (o `Completa` que `+Sintéticos`), el fix no tuvo efecto — parar y depurar antes de seguir (revisar que `is_anomaly` realmente tenga varianza distinta de cero en el `train` usado, y que el modelo Random Forest le esté dando importancia — no es un bug esperado si las Tareas 1-3 están bien implementadas, pero hay que confirmarlo con datos reales antes de documentar cualquier número).

- [ ] **Step 5: Actualizar `openspec/specs/experiment-runner/spec.md`**

Reemplazar la tabla de resultados (líneas 83-88):

```
| Configuración | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión (media) | Recall (media) |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| Completa | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
```

por la misma tabla con `Base` y `+Sintéticos` sin cambios, y `+Anomalías`/`Completa` con los valores reales medidos en los Steps 2-3.

Reemplazar el párrafo "**Hallazgo importante**..." (línea 90) por un párrafo que reporte los valores reales de `+Anomalías` y `Completa` frente a `Base`/`+Sintéticos`, indicando si la detección de anomalías tuvo un efecto medible (positivo, negativo, o despreciable) ahora que `is_anomaly` sí llega al modelo, y referenciando `openspec/changes/fix-anomaly-feature-integration/proposal.md` como el *change* que corrigió la integración.

En "## Limitaciones conocidas", reemplazar la primera viñeta (línea 130):

```
- **La detección de anomalías no afecta actualmente el desempeño del modelo**: `is_anomaly` no se incluye entre las variables predictoras en `run_end_to_end_pipeline` (HU6). Para que el factor "detección de anomalías" sea comparable de verdad, esto debería resolverse (ej. incluyendo `is_anomaly` como variable predictora, o filtrando filas anómalas del entrenamiento en vez de solo marcarlas) — se documenta como hallazgo para el análisis de HU8, no se corrige en este *change* para no alterar retroactivamente los resultados ya registrados.
```

por:

```
- ~~La detección de anomalías no afecta actualmente el desempeño del modelo...~~ **Actualización:** resuelto en `openspec/changes/fix-anomaly-feature-integration/`. `is_anomaly` ahora es una variable predictora real (detector ajustado solo sobre `train`, aplicado sin reajustar sobre `test`); ver la tabla de resultados actualizada arriba.
```

- [ ] **Step 6: Actualizar `openspec/specs/architecture-integration/spec.md`**

Agregar al final del archivo (después de la línea 62, dentro de "## Limitaciones conocidas" o como nueva sección "## Requirements" adicional) el requirement `openspec/changes/fix-anomaly-feature-integration/specs/architecture-integration/spec.md` completo (copiarlo tal cual, es el requirement "Uso de `is_anomaly` como variable predictora cuando la detección de anomalías está habilitada"), agregando debajo una línea de implementación con evidencia, ejemplo:

```
Implementado en `src/architecture_integration/pipeline.py` (`run_end_to_end_pipeline`) y `src/data_quality/anomaly_detection.py` (`fit_anomaly_detector`/`apply_anomaly_detector`). Testeado en `tests/test_architecture_integration_pipeline.py` y `tests/test_anomaly_detection.py`. Verificado sobre el dataset real: ver `openspec/specs/experiment-runner/spec.md` para el efecto medido sobre las métricas de `+anomálias`/`completa`.
```

Actualizar también la línea 29 ("Verificado sobre el dataset real... 15 filas marcadas `is_anomaly`...") agregando una frase indicando que, desde este *change*, esa columna también forma parte de las variables predictoras del modelo.

- [ ] **Step 7: Actualizar `openspec/specs/data-quality/spec.md`**

Agregar una frase al final del párrafo de implementación de "Detección de anomalías no supervisada" (línea 97): "Desde `openspec/changes/fix-anomaly-feature-integration/`, también existen `fit_anomaly_detector`/`apply_anomaly_detector` (fit/transform separados) para el caso donde `is_anomaly` se usa como variable predictora de un modelo (`architecture-integration`, HU6) y hace falta evitar que el conjunto de evaluación influya en su propia marca de anomalía."

No tocar la "Limitaciones conocidas" (línea 176) — esa nota es específica de `run_quality_pipeline` (HU3), que este *change* no modifica.

- [ ] **Step 8: Actualizar `docs/research/hu8-analisis-resultados.md`**

Reemplazar la tabla de la sección 1 (líneas 13-16) con los valores reales de `+Anomálias`/`Completa` obtenidos en los Steps 2-3 (mismo criterio que el Step 5 de esta tarea).

Reemplazar la frase de la sección 2 (línea 24, "**Inconsistencia real detectada**...") por una nota indicando que la inconsistencia quedó resuelta tras corregir la integración (`fix-anomaly-feature-integration`), con los valores reales ya no idénticos.

Reemplazar el primer punto de la sección 5 (línea 39, "**Detección de anomalías**: sin efecto medible...") por un párrafo que reporte el efecto real medido (positivo, negativo o despreciable) ahora que `is_anomaly` es una feature real, referenciando el *change* que lo corrigió.

- [ ] **Step 9: Actualizar `docs/research/hu8-resultados-discusion-conclusiones.md`**

Actualizar las menciones de "`+Anomalías` = `Base`" (línea 16), el punto "**Detección de anomalías**: no se observó ningún efecto..." (línea 36), la síntesis de la línea 41 (ajustar "dos (detección de anomalías, retroalimentación humana) no pudieron evaluarse..." si la detección de anomalías ya se evaluó de forma válida), la limitación de la línea 47, y la recomendación de la línea 71 ("Corregir la integración..." pasa a estar hecha) — cada una reflejando el resultado real obtenido, con referencia a `openspec/changes/fix-anomaly-feature-integration/`.

- [ ] **Step 10: Actualizar `docs/seguimiento-tareas.md`**

En la sección de HU7 (o agregando una entrada nueva si corresponde), documentar la corrección y re-ejecución con los números reales, siguiendo el formato ya usado en esa tabla (columna Estado ✅, columna Evidencia con archivos + valores medidos).

- [ ] **Step 11: Correr toda la suite una vez más**

Run: `pytest -q`
Expected: PASS (sin cambios de código en este paso, solo para confirmar que la suite sigue en verde antes de cerrar el *change*).

- [ ] **Step 12: Commit**

```bash
git add openspec/specs/experiment-runner/spec.md openspec/specs/architecture-integration/spec.md openspec/specs/data-quality/spec.md docs/research/hu8-analisis-resultados.md docs/research/hu8-resultados-discusion-conclusiones.md docs/seguimiento-tareas.md
git commit -m "docs: actualiza HU7/HU8 con los resultados reales tras corregir la integración de is_anomaly"
```
