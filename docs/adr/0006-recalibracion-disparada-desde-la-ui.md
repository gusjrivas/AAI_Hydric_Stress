# ADR-0006: Disparo de recalibración desde la UI y reacoplamiento a MLflow

## Estado

Aceptado (2026-08-19)

## Contexto

El mecanismo de recalibración supervisada (`src/human_feedback/recalibration.py`: `select_recalibration_observations`, `recalibrate_model`) está implementado y testeado desde HU5, pero `openspec/specs/human-feedback/spec.md` documenta explícitamente la limitación pendiente: "la recalibración no se dispara automáticamente desde la interfaz de usuario ni se persiste el modelo recalibrado; ambas cosas requieren un flujo de despliegue que todavía no existe."

ADR-0005 decidió, deliberadamente, que `backend`/`frontend` (alerting-ui) no dependieran de MLflow, porque hasta ese momento la UI no tenía ningún motivo real para tocar el registro de experimentos. Cerrar el loop de retroalimentación humana (confirmar/rechazar → recalibrar → que el próximo pronóstico use el modelo recalibrado) cambia esa premisa: ahora sí hay un motivo concreto — usar el Model Registry de MLflow para versionar el modelo recalibrado, en lugar de inventar un mecanismo de persistencia propio.

Se evaluaron dos formas de servir el modelo recalibrado a `/forecast/run`:

- **(A) MLflow solo como registro**: el backend carga el modelo vía `mlflow.sklearn.load_model(...)` y predice en el mismo proceso, igual que hoy.
- **(B) MLflow como servicio de serving**: `mlflow models serve` como contenedor propio, con el backend llamando por HTTP a un endpoint de inferencia en vez de predecir localmente.

Se descarta la opción (B) **por ahora**, no porque sea inválida: `mlflow models serve` no recarga el modelo servido solo porque se registra una versión nueva — seguiría sirviendo la versión vieja hasta reiniciar ese contenedor. Resolver eso agrega un problema real de despliegue (quién dispara el reinicio, con qué garantías) que no tiene una solución limpia dentro de un `docker-compose` local de un prototipo de tesis. Adoptar (B) sin resolver ese problema sería un salto de red decorativo, no un paso real hacia producción.

## Decisión

### Opción adoptada: (A) MLflow como registro, backend predice en el mismo proceso

Se agrega un módulo `src/human_feedback/model_registry.py` con dos funciones:

- `register_recalibrated_model(model, params, metrics) -> str`: registra el modelo recalibrado como una nueva versión en el Model Registry de MLflow (`mlflow.sklearn.log_model(..., registered_model_name=...)`), devuelve el número de versión.
- `load_latest_recalibrated_model() -> object | None`: recupera la versión más reciente registrada, o `None` si todavía no se recalibró ningún modelo (primera corrida).

### Cambio en `architecture_integration.pipeline.run_end_to_end_pipeline`

Se agrega un parámetro `skip_fit: bool = False`: si `True`, usa `model` tal cual (ya entrenado) en vez de `clone(model).fit(...)`. Necesario porque `/forecast/run` debe poder predecir con el modelo recalibrado sin descartar su ajuste (un `clone()` de un modelo ya entrenado devuelve una copia sin entrenar).

### Cambio en `/forecast/run`

Antes de construir un modelo nuevo, intenta `load_latest_recalibrated_model()`. Si existe, lo usa con `skip_fit=True`; si no (primera vez), entrena uno nuevo como hoy.

### Nuevo endpoint `POST /recalibrate`

Reentrena sobre `train ∪ test` (con las etiquetas reales, corregidas donde el humano rechazó una alerta con corrección) y registra el resultado en MLflow. Detalle completo en `openspec/changes/add-recalibration-trigger/`.

### Infraestructura

`backend` pasa a depender de `mlflow` en `docker-compose.yml` (`depends_on: mlflow` y `MLFLOW_TRACKING_URI` en su entorno), revirtiendo ese punto puntual de ADR-0005.

## Alternativas consideradas

- **(B) MLflow Model Serving como servicio HTTP separado**: descartada por ahora (ver Contexto) — el problema de recarga de versión no tiene solución limpia sin agregar orquestación de despliegue real. **Queda anotado explícitamente como punto de mejora a no pasar por alto en una futura iteración**, cuando el proyecto necesite un patrón de serving más cercano a producción (decisión explícita del autor, no un descarte definitivo).
- **Persistencia propia (archivo `.joblib` en `data/`, sin MLflow)**: descartada porque MLflow ya está levantado (ADR-0004) específicamente para versionar artefactos de modelado; inventar un mecanismo paralelo duplicaría esa responsabilidad sin necesidad.
- **Recalibrar solo sobre las fechas de test corregidas (sin combinar con train)**: descartada porque `recalibrate_model` reemplaza etiquetas por fecha dentro del conjunto de entrenamiento que se le pasa — si ese conjunto no incluye las fechas corregidas (que viven en el período de test), la corrección no tiene ningún efecto. Combinar `train ∪ test` es lo que le da sentido real a "recalibrar": el período reciente, con las correcciones humanas aplicadas, pasa a formar parte del entrenamiento.

## Consecuencias

- Docker Desktop (o un daemon Docker equivalente) con el stack completo (`mlflow`, `postgres`, `minio`) corriendo pasa a ser un prerequisito para que `/recalibrate` funcione y para que `/forecast/run` recupere el modelo recalibrado más reciente. Si `mlflow` no está corriendo, `load_latest_recalibrated_model()` debe fallar de forma explícita (no silenciosa) para que quede claro por qué `/forecast/run` volvió a entrenar desde cero.
- `/forecast/run` deja de ser puramente idempotente respecto del dataset: su resultado ahora también depende de si existe un modelo recalibrado registrado, y de cuál sea.
- Si el dataset consolidado cambia de esquema (nuevas columnas, otro `feature_columns`), un modelo recalibrado viejo podría fallar al predecir sobre features nuevas. Este ADR no resuelve ese caso — se documenta como limitación conocida, no como escenario soportado en esta iteración.
- La opción (B) queda pendiente como mejora explícita para una iteración futura de despliegue más productivo; no debe perderse de vista ni tratarse como descartada permanentemente.

## Referencias

- [ADR-0003: Stack web (backend/frontend) y ciclo de vida de desarrollo automatizado con IA](0003-stack-web-y-ciclo-de-vida-automatizado.md)
- [ADR-0004: Orquestación de experimentos con MLflow, backend Postgres y almacenamiento de artefactos MinIO](0004-orquestacion-experimentos-mlflow-minio.md)
- [ADR-0005: Dockerización de backend y frontend (alerting-ui)](0005-dockerizacion-backend-frontend.md) — este ADR revierte puntualmente su decisión de no acoplar alerting-ui a MLflow.
- `openspec/specs/human-feedback/spec.md` — limitación que este ADR resuelve.
- `openspec/changes/add-recalibration-trigger/` — spec delta y plan de implementación.
