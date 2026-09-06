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

> **Esta descripción corresponde a la decisión inicial. La política vigente se encuentra actualizada en la sección "Actualización 2026-09-06 — maduración temporal de la recalibración" más abajo.**

### Infraestructura

`backend` pasa a depender de `mlflow` en `docker-compose.yml` (`depends_on: mlflow` y `MLFLOW_TRACKING_URI` en su entorno), revirtiendo ese punto puntual de ADR-0005.

## Alternativas consideradas

- **(B) MLflow Model Serving como servicio HTTP separado**: descartada por ahora (ver Contexto) — el problema de recarga de versión no tiene solución limpia sin agregar orquestación de despliegue real. **Queda anotado explícitamente como punto de mejora a no pasar por alto en una futura iteración**, cuando el proyecto necesite un patrón de serving más cercano a producción (decisión explícita del autor, no un descarte definitivo).
- **Persistencia propia (archivo `.joblib` en `data/`, sin MLflow)**: descartada porque MLflow ya está levantado (ADR-0004) específicamente para versionar artefactos de modelado; inventar un mecanismo paralelo duplicaría esa responsabilidad sin necesidad.
- **Recalibrar solo sobre las fechas de test corregidas (sin combinar con train)**: descartada porque `recalibrate_model` reemplaza etiquetas por fecha dentro del conjunto de entrenamiento que se le pasa — si ese conjunto no incluye las fechas corregidas (que viven en el período de test), la corrección no tiene ningún efecto. Combinar `train ∪ test` es lo que le da sentido real a "recalibrar": el período reciente, con las correcciones humanas aplicadas, pasa a formar parte del entrenamiento.

  > Esta alternativa describe la disyuntiva evaluada en la decisión inicial (`recalibrate_model`, combinar `train ∪ test` ingenuamente). La política vigente (`recalibrate_predictor`, ver la actualización más abajo) resuelve este mismo problema sin combinar indiscriminadamente ambas particiones: incorpora únicamente observaciones cuyo target ya maduró, verificando procedencia temporal en vez de asumir una partición fija.

## Consecuencias

- Docker Desktop (o un daemon Docker equivalente) con el stack completo (`mlflow`, `postgres`, `minio`) corriendo pasa a ser un prerequisito para que `/recalibrate` funcione y para que `/forecast/run` recupere el modelo recalibrado más reciente. Si MLflow no está disponible, `load_latest_recalibrated_model()` debe fallar de forma explícita, de modo que el problema de infraestructura sea visible y `/forecast/run` no continúe silenciosamente mediante un reentrenamiento desde cero.
- `/forecast/run` deja de ser puramente idempotente respecto del dataset: su resultado ahora también depende de si existe un modelo recalibrado registrado, y de cuál sea.
- Si el dataset consolidado cambia de esquema (nuevas columnas, otro `feature_columns`), un modelo recalibrado viejo podría fallar al predecir sobre features nuevas. Este ADR no resuelve ese caso — se documenta como limitación conocida, no como escenario soportado en esta iteración.
- La opción (B) queda pendiente como mejora explícita para una iteración futura de despliegue más productivo; no debe perderse de vista ni tratarse como descartada permanentemente.

## Actualización 2026-09-06 — maduración temporal de la recalibración

La formulación original de este ADR ("reentrena sobre `train ∪ test`") describe la primera implementación conceptual del disparo de recalibración, pero fue posteriormente reemplazada/endurecida por un mecanismo temporalmente explícito, ya implementado y testeado: `src/human_feedback/recalibration.py::recalibrate_predictor`. Esta sección documenta el comportamiento vigente del código; no introduce ningún cambio en esta iteración.

El mecanismo vigente:

- no incorpora indiscriminadamente `train` y `test`;
- utiliza únicamente observaciones cuyo `target_timestamp` ya maduró (es decir, cuyo objetivo temporal ya existe y pudo observarse), y cuya validación humana (`validated_at`) ocurrió después de esa maduración;
- verifica procedencia temporal completa de cada corrección (`target_timestamp`, `validated_at`, `model_version`, `target_threshold`), fallando explícitamente ante feedback con horizonte, umbral o procedencia incompatible;
- preserva las correcciones humanas aplicadas previamente (`applied_feedback`) y las reaplica junto con las nuevas;
- hace avanzar `trained_through` sin retroceder, de modo que una observación incorporada de este modo deja de considerarse evidencia out-of-sample futura de ese mismo predictor.

Documentado formalmente en `openspec/specs/human-feedback/spec.md`, requirement "Recalibración temporalmente controlada con retroalimentación madura".

## Actualización 2026-09-06 — linaje explícito de recalibraciones (mejora técnica post-H-01)

H-01 (`fix/hitl-multiversion-recalibration`, PR #182) corrigió que `recalibrate_predictor` rechazara ciclos HITL sucesivos por acumular `model_version` de más de un predictor en el `feedback_log`. Esta actualización complementa esa corrección con trazabilidad explícita: no cambia el mecanismo de recalibración ni el Model Registry adoptado en este ADR, agrega un registro auxiliar sobre la infraestructura ya decidida.

`register_recalibrated_model` (`src/human_feedback/model_registry.py`) acepta ahora un `lineage: RecalibrationLineage | None` opcional. Cuando se provee, persiste un artefacto JSON (`recalibration_lineage.json`) dentro del mismo run de MLflow que registra al predictor sucesor, junto con parámetros indexables (`recalibration_id`, `source_model_id`, `successor_model_id`, `dataset_fingerprint`). Se descartó deliberadamente introducir un almacén de linaje separado (tabla propia, archivo paralelo): el Model Registry de MLflow ya es la fuente de verdad versionada de cada predictor recalibrado (ver más arriba), y cada evento de linaje corresponde exactamente 1:1 con la versión que registra — anexarlo al mismo run evita una segunda fuente de verdad que pudiera desincronizarse.

`POST /recalibrate/{sensor_id}` construye el evento (`RecalibrationLineage`) con `source_model_id` = `model_id` del predictor vigente antes de recalibrar, `successor_model_id` = el nuevo `model_id`, y `feedback_references` construidas únicamente a partir de las fechas nuevas/pendientes que devuelve `recalibrate_predictor` (nunca de todo el `feedback_log`). `RecalibrationResponse` gana un campo opcional `recalibration_id` (retrocompatible, `None` por defecto) para correlacionar la respuesta HTTP con el evento persistido.

Documentado formalmente en `openspec/specs/human-feedback/spec.md`, requirement "Linaje explícito de recalibraciones HITL".

## Referencias

- [ADR-0003: Stack web (backend/frontend) y ciclo de vida de desarrollo automatizado con IA](0003-stack-web-y-ciclo-de-vida-automatizado.md)
- [ADR-0004: Orquestación de experimentos con MLflow, backend Postgres y almacenamiento de artefactos MinIO](0004-orquestacion-experimentos-mlflow-minio.md)
- [ADR-0005: Dockerización de backend y frontend (alerting-ui)](0005-dockerizacion-backend-frontend.md) — este ADR revierte puntualmente su decisión de no acoplar alerting-ui a MLflow.
- `openspec/specs/human-feedback/spec.md` — limitación que este ADR resuelve.
- `openspec/changes/add-recalibration-trigger/` — spec delta y plan de implementación.
