# Change: Add experiment automation capability

## Trazabilidad

- **Épica:** 4. Evaluación experimental.
- **Historia de usuario:** HU7 — Diseño y ejecución del plan experimental (segundo de tres sub-proyectos: procedimiento automatizado y registro de resultados).
- **Fase de CRISP-DM:** Evaluación.
- **Insumo de diseño:** [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) (diseño experimental, 4 configuraciones, 5 semillas), [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) (orquestador de punta a punta), [ADR-0004](../../../docs/adr/0004-orquestacion-experimentos-mlflow-minio.md) (servidor MLflow + Postgres + MinIO).

## Why

El diseño experimental (`add-experiment-design`) define qué comparar y con qué métricas, pero no hay todavía ningún procedimiento que efectivamente ejecute una configuración con múltiples semillas ni que registre sus parámetros/métricas en MLflow — la infraestructura de ADR-0004 existe y fue verificada con un experimento de humo, pero ningún código de modelado real la usó todavía.

## What Changes

- **Procedimiento automatizado de experimentación**: función que, dada una configuración (flags de detección de anomalías y aumento sintético) y una lista de semillas, ejecuta el orquestador de punta a punta (`architecture_integration.pipeline.run_end_to_end_pipeline`) una vez por semilla — agregando datos sintéticos con `experiment_runner.synthetic_augmentation.add_synthetic_rows` cuando la configuración lo pide — y devuelve las métricas de cada semilla en una tabla.
- **Registro de parámetros, versiones y resultados**: función que registra en MLflow, para una configuración ya ejecutada, un *run* padre con los parámetros de la configuración (flags, cantidad de semillas) y las métricas agregadas (media/desvío), y un *run* hijo anidado por cada semilla con sus propios parámetros (semilla) y métricas individuales — patrón estándar de MLflow (*nested runs*) para poder comparar configuraciones agregadas y auditar corridas individuales.
- **Compatibilidad de versión del cliente MLflow**: se agrega `mlflow` como dependencia del proyecto (no solo del servidor Docker), fijada al mismo rango que el servidor (`mlflow>=2.14,<3`, ADR-0004) para evitar incompatibilidades de API entre cliente y servidor.

## Impact

- **Specs afectadas:** `experiment-runner` (extiende el spec existente).
- **Specs futuras que dependen de esta:** el tercer *change* de HU7 (ejecución real) usa este procedimiento para correr las 4 configuraciones sobre el dataset real y registrar los resultados en el servidor MLflow real (`http://localhost:5000`, ADR-0004).
- **Código afectado:** `src/experiment_runner/runner.py`, `src/experiment_runner/mlflow_logging.py`; `pyproject.toml` (dependencia `mlflow`).
- **Fuera de alcance de este change:** ejecución real contra el servidor MLflow de docker-compose (tercer *change*, requiere Docker Desktop levantado); ejecución de las 4 configuraciones completas sobre el dataset real (tercer *change*).

## Alternativas consideradas

- **Un run plano por semilla, sin anidar**: se descarta porque dificulta comparar visualmente las 4 configuraciones agregadas en la UI de MLflow frente al patrón estándar de *nested runs*, que sí lo permite sin código adicional.
- **No fijar la versión del cliente MLflow**: se descarta porque el servidor Docker está fijado a `mlflow>=2.14,<3` (ADR-0004); dejar el cliente sin fijar arriesga una incompatibilidad de API silenciosa al conectar contra el servidor real.

## Estado: implementado

Ver [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) para los requisitos vigentes y la verificación con datos reales.
