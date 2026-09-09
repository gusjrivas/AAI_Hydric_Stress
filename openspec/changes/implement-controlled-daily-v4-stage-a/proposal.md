# Change: Implement controlled_daily_v4 Stage A runner

## Trazabilidad

- **Épica:** 4. Evaluación experimental — continuación de `add-controlled-daily-v4-external-pergamino` (exclusivamente documental) hacia su primera implementación de código.
- **Capacidad OpenSpec:** `experiment-runner`, cumpliendo el delta de especificación ya propuesto en `openspec/changes/add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md` (no se modifica ese archivo ni el resto de ese *change*, ya mergeado — este *change* es nuevo y separado).
- **Fase de CRISP-DM:** Modelado (Etapa A: nested CV, selección multimodelo, congelamiento de hiperparámetros).
- **Insumo de diseño:** `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md`, `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `docs/research/controlled-daily-v4-external-pergamino-protocol.md`, `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`.

## Why

`add-controlled-daily-v4-external-pergamino` dejó el protocolo formalizado (ADR-0011 + documento reproducible + manifiesto + delta de spec), explícitamente `PROTOCOL_ONLY`, sin ningún código. Este *change* implementa el runner de la **Etapa A** (desarrollo y selección, 2015–2022) descripta en ese protocolo, con tests exhaustivos sobre datos sintéticos, dejando la ejecución real sobre Pergamino, y las Etapas B/C, explícitamente pendientes y fuera de alcance.

## What Changes

- **Entorno reproducible dedicado** (`docker/experiment-v4/`): `Dockerfile` (base `python@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534` fijada por digest) + `constraints.txt` con versiones exactas resueltas en un contenedor limpio y validadas ejecutando allí la suite de tests (NumPy 2.4.6, SciPy 1.17.1, pandas 3.0.5, PyArrow 25.0.1, scikit-learn 1.9.0, joblib 1.6.0, threadpoolctl 3.6.0, pytest 9.1.1, ruff 0.16.6, black 26.5.1). No reemplaza las dependencias globales de `pyproject.toml`.
- **`src/experiment_runner/controlled_daily_v4/`** (nuevo subpaquete, 15 módulos): `config.py` (constantes normativas y fronteras temporales de A/B/C — B y C solo como referencia para poder rechazarlas explícitamente), `provenance.py` (validación de existencia/nombre/SHA-256/tamaño/encabezados/columnas/timezone/duplicados/alineación de los dos CSV de Pergamino, sin modificarlos), `ingestion.py` (parseo ERA5-Land/NASA POWER y construcción de la serie diaria continua completa, sin filtrar por etapa), `features.py` (lags/rolling causales, target estricto `<` fold-local, filtro de elegibilidad por `target_timestamp`), `models.py` (LR/RF/HGB/Soft Voting, `sample_weight` fold-local, sin `class_weight`), `splits.py` (`TimeSeriesSplit(3, gap=3)` outer/inner con invariante temporal verificado), `tuning.py` (selección de hiperparámetros por mediana de MCC sobre una lista de folds, reutilizado por inner-tuning y por congelamiento), `metrics.py` (MCC/AP/ROC-AUC/Brier/log loss/matriz de confusión/operativas, con convención explícita de `NaN` en casos degenerados), `bootstrap.py` (moving block bootstrap pareado y segment-aware), `selection.py` (ganador estable / `SIN_GANADOR_ESTABLE` con desempate por simplicidad predeclarada / `NO_VALID_SELECTION`), `freezing.py` (segunda pasada de `TimeSeriesSplit(3, gap=3)` sobre toda la Etapa A para congelar hiperparámetros finales), `artifacts.py` (esquemas versionados, escritura atómica, rechazo de sobreescritura accidental, nunca escribe en `docs/research/` ni en MLflow), `stage_a_runner.py` (orquestación completa) y `cli.py` (acepta únicamente `--stage A`, rechaza `B`/`C`, expone `--validate-inputs-only`, sin rutas ocultas a datasets formales ni a MLflow).
- **`tests/controlled_daily_v4_fixtures.py`** + 13 archivos `tests/test_controlled_daily_v4_*.py`: 67 tests unitarios y de integración, exclusivamente con datos sintéticos (nunca leen los CSV reales de Pergamino), cubriendo target estricto, causalidad, invariante temporal, grillas exactas, balanceo sin `class_weight`, selección/desempate, congelamiento, serialización atómica, CLI (rechazo de B/C, `--validate-inputs-only`, corrida completa), y ausencia de importación de `mlflow`.
- **`docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`**: sección `environment` actualizada de `PRECONDITION_FOR_EXECUTION` a `VALIDATED_FOR_TESTS_ONLY`, con las versiones exactas validadas — se aclara explícitamente que esto cubre reproducibilidad de tests/CI con datos sintéticos, no la ejecución real de la Etapa A sobre Pergamino, que sigue pendiente.

## Impact

- **Specs afectadas:** ninguna modificación de `openspec/specs/experiment-runner/spec.md` (canónico, capacidad vigente de `controlled_daily_v3`). El delta ya propuesto en `add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md` queda ahora satisfecho por código y tests (ver mapeo de escenarios en la sección de Verificación), pero ese archivo no se modifica — este *change* documenta la implementación por separado.
- **Código afectado:** exclusivamente el subpaquete nuevo `src/experiment_runner/controlled_daily_v4/` y sus tests; ningún módulo existente de `src/experiment_runner/`, `backend/`, `frontend/` ni `src/human_feedback/` fue tocado.
- **MLflow:** no se integra en absoluto en esta implementación (verificado por AST en los tests de CLI: ni `cli.py` ni `stage_a_runner.py` importan `mlflow`). No se registró ningún run ni modelo en el servidor compartido.
- **`controlled_daily_v3`:** sin alteración. `scientific-baseline-v3`, `technical-baseline-v1`, `technical-baseline-v2`: sin mover.
- **Fuera de alcance de este *change* (explícitamente no implementado):** ejecución real de la Etapa A sobre los CSV de Pergamino; Etapa B (2023); Etapa C (2024–2025, holdout permanece cerrado); Balcarce; integración con MLflow; cualquier resultado experimental — no existe ninguno todavía.

## Verificación

- Suite dirigida (67 tests, exclusivamente sintéticos) en el entorno reproducible (`docker/experiment-v4/`): **67 passed** (`docker run aai-hydric-v4-experiment:dev pytest -q tests/test_controlled_daily_v4_*.py`, ~131s).
- Suite completa del repositorio en un entorno con todas las dependencias del proyecto (`Dockerfile` raíz): **327 passed** (260 preexistentes + 67 nuevos), sin regresiones.
- `ruff check` y `black --check` en verde sobre `src`, `backend`, `tests` completos (no solo los archivos nuevos).
- `git diff --check` sin hallazgos.
- Build del contenedor experimental exitoso (`docker build -f docker/experiment-v4/Dockerfile`).

## Alternativas consideradas

- **Reutilizar `sklearn.pipeline.Pipeline` en vez de `ScaledLogisticRegression` a medida.** Descartada: pasar `sample_weight` a un sub-estimador dentro de un `Pipeline` requiere la sintaxis `nombre_paso__sample_weight`, que complica innecesariamente el despacho uniforme entre las cuatro familias (incluida su composición dentro de `VotingClassifier`, que no soporta ese prefijo de forma directa); una clase compatible con `BaseEstimator`/`ClassifierMixin` que expone `fit(X, y, sample_weight=None)` es más simple y igual de clonable.
- **Pasar `penalty='l2'` explícito a `LogisticRegression`.** Descartado tras detectar un `FutureWarning` real en scikit-learn 1.9.0 (el parámetro está deprecado a favor de `l1_ratio`): se omite el argumento y se documenta que el valor por defecto (`l1_ratio=0.0`) ya equivale a L2, sin alterar el comportamiento exigido por el protocolo.
- **Usar `sklearn.ensemble.VotingClassifier` con estimadores ya ajustados (`prefit`).** Descartado: `VotingClassifier` no soporta un modo prefit — siempre clona y reentrena sus estimadores base al llamar `.fit()`, que es exactamente el comportamiento que exige el protocolo ("Soft Voting reentrena sus tres modelos base").
