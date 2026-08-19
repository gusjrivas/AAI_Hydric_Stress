# Change: Add recalibration trigger to alerting UI

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historias de usuario:** HU5 (recalibración supervisada, mecanismo ya implementado) + HU6 (integración de la arquitectura experimental) — cierra el loop de retroalimentación humana que `add-alerting-ui` dejó explícitamente fuera de alcance.
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [ADR-0006](../../../docs/adr/0006-recalibracion-disparada-desde-la-ui.md) (disparo desde la UI, MLflow como registro), [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) (mecanismo de recalibración ya existente), [`openspec/specs/alerting-ui/spec.md`](../../specs/alerting-ui/spec.md) (capacidad que este *change* extiende).

## Why

`add-alerting-ui` dejó explícito que "el mecanismo (`human_feedback.recalibration`) ya existe (HU5) pero conectarlo a un botón de la interfaz queda para después de que esta base funcione". Hoy confirmar/rechazar una alerta solo persiste la validación — no tiene ningún efecto sobre el modelo, lo cual generó una pregunta real al usar la interfaz: "¿confirmar actualiza el modelo?". Este *change* responde que sí puede, de forma explícita y manual.

## What Changes

- **`src/architecture_integration/pipeline.py`**: agrega parámetro `skip_fit: bool = False` a `run_end_to_end_pipeline`. Si `True`, usa el `model` recibido tal cual (ya entrenado) en vez de `clone(model).fit(...)` — necesario para predecir con un modelo recalibrado sin descartar su ajuste.
- **`src/human_feedback/model_registry.py`** (nuevo): `register_recalibrated_model(model, params, metrics) -> str` (registra una versión en el Model Registry de MLflow) y `load_latest_recalibrated_model() -> object | None` (recupera la versión más reciente, o `None` si no hay ninguna todavía).
- **Backend** (`backend/`):
  - Nuevo `backend/app/pipeline.py`: helper compartido que factoriza la lógica de `/forecast/run` (cálculo de `split_date`, elección de modelo — recalibrado si existe, nuevo si no — y llamada a `run_end_to_end_pipeline`), para que `/recalibrate` la reutilice sin duplicarla.
  - `POST /forecast/run` (modificado): usa el helper; si hay un modelo recalibrado registrado, predice con ese en vez de entrenar uno nuevo.
  - `POST /recalibrate` (nuevo): corre el pipeline, junta `train ∪ test` (con las etiquetas reales), integra el feedback persistido con esas predicciones, selecciona las observaciones rechazadas con corrección, reentrena y registra el resultado en MLflow. `400` explícito si no hay ninguna corrección pendiente de aplicar.
- **Frontend** (`frontend/`): botón "Recalibrar modelo" en `ForecastPage`, visible solo cuando hay al menos una alerta rechazada pendiente de aplicar (con contador), y un mensaje explícito tras usarlo indicando la versión registrada y cuántas correcciones se aplicaron.
- **Infraestructura**: `docker-compose.yml` agrega `depends_on: mlflow` y `MLFLOW_TRACKING_URI` al servicio `backend` (ver ADR-0006, revierte ese punto de ADR-0005).

## Impact

- **Specs afectadas:** extiende `alerting-ui` (nuevo requirement de recalibración); actualiza la limitación ya conocida en `human-feedback` que este *change* resuelve.
- **Código afectado:** `src/architecture_integration/pipeline.py`, `src/human_feedback/` (nuevo módulo), `backend/app/` (nuevo router + helper compartido), `frontend/src/features/forecast/`, `docker-compose.yml`.
- **Fuera de alcance de este change**:
  - **MLflow Model Serving como servicio HTTP separado** (Opción B evaluada en ADR-0006): queda como mejora explícita para una futura iteración de despliegue más productivo, no descartada.
  - **Disparo automático de recalibración** (por umbral de correcciones acumuladas): se mantiene manual, un botón explícito.
  - **Manejo de cambios de esquema del dataset entre una recalibración y la siguiente**: si el dataset consolidado cambia de columnas, un modelo recalibrado viejo podría fallar al predecir; no se resuelve en esta iteración (ver ADR-0006, Consecuencias).

## Alternativas consideradas

Ver ADR-0006 — las alternativas de persistencia/serving del modelo recalibrado ya se documentaron ahí para no duplicar la discusión.

- **Recalibrar solo con las observaciones de test, sin combinarlas con train**: descartada — `recalibrate_model` reemplaza etiquetas por fecha dentro del conjunto que recibe; si ese conjunto no incluye las fechas corregidas, la corrección no tiene ningún efecto (ver ADR-0006).
- **Endpoint de recalibración que también devuelve las métricas del modelo recalibrado (precision/recall/F1)**: se descarta para esta iteración — calcular esas métricas requeriría un conjunto de validación separado del propio conjunto de entrenamiento recalibrado (que ya usó train+test), lo cual es una pieza de diseño propia (walk-forward validation) fuera del alcance de "cerrar el loop básico".
