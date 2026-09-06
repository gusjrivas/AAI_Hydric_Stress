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

### Microajustes 2026-09-06 — validación semántica y orden de persistencia

Sobre la misma rama (`feat/hitl-recalibration-lineage`, previo al merge de la PR): se detectó que un `RecalibrationLineage` mal formado (sensor inconsistente, `source_model_id == successor_model_id`, referencias de otro predictor, duplicadas o ausentes, `trained_through` retrocedido) podía construirse y registrarse sin ningún control. Se agregó validación semántica obligatoria (`RecalibrationLineage.__post_init__`, ejecutada tanto al crear el evento como al reconstruirlo con `from_dict`) y una segunda validación cruzada en `register_recalibrated_model` (`sensor_id`, `successor_model_id`, `successor_trained_through`, `contract_version`, `pipeline_version` deben coincidir con el predictor que efectivamente se registra), ambas antes de escribir nada en MLflow. `feedback_references` pasó de lista a tupla (inmutable) tras `__post_init__`.

Se corrigió también el orden de escritura dentro del run de MLflow: el artefacto y los parámetros de linaje se persisten **antes** de `mlflow.sklearn.log_model(..., registered_model_name=...)` (el paso que registra la versión), no después. Antes de este cambio, era posible que el registro del predictor (y por lo tanto una versión visible en el Model Registry) se completara sin que el linaje llegara a persistirse si algo fallaba entre medio — una versión "sin memoria" de qué la originó. Con el nuevo orden, una versión registrada nunca queda sin su artefacto de linaje; el caso inverso (un run con linaje pero sin versión registrada, si la interrupción ocurre entre ambos pasos) es un run huérfano aceptado explícitamente, y `load_recalibration_lineage`/`list_recalibration_lineage` lo excluyen por construcción al recorrer solo versiones ya registradas. Como consecuencia, `mlflow_model_version` ya no se calcula ni se graba en el artefacto en el momento de escribirlo (la versión todavía no existe en ese punto): se resuelve dinámicamente en cada lectura, a partir de la versión de MLflow efectivamente asociada al `run_id`, en vez de depender de una reescritura posterior del artefacto.

No cambia el mecanismo de recalibración, el Model Registry adoptado, ni el contrato de `POST /recalibrate/{sensor_id}` frente a un uso correcto — es endurecimiento de robustez y trazabilidad sobre el mismo diseño.

## Actualización 2026-09-06 — T-01: auditabilidad fail-closed y provenance por contenido

Auditoría técnica final detectó dos brechas de auditabilidad en el linaje, ambas cerradas en la misma rama (`fix/hitl-lineage-auditability`, previo a PR), sin tocar el mecanismo de recalibración ni el Model Registry:

**Lectura fail-closed.** Antes, `load_recalibration_lineage`/`list_recalibration_lineage` colapsaban a `None`/omisión silenciosa cualquier problema al reconstruir un linaje: una versión histórica sin linaje, un artefacto ausente, un fallo de descarga, JSON corrupto o una violación semántica eran indistinguibles. Se introdujo un marcador canónico de "declaración de linaje": los parámetros indexables que `register_recalibrated_model` ya persistía (`recalibration_id`, `source_model_id`, `successor_model_id`, `dataset_fingerprint`). Una versión sin esos parámetros nunca declaró linaje → `None` (retrocompatible). Una versión que sí los tiene pero no puede reconstruirse correctamente (artefacto ausente, error de descarga, JSON inválido, semántica inválida, o inconsistencia entre el artefacto y esos parámetros) levanta `LineageValidationError` con contexto (versión, `run_id`) — nunca degrada a `None`. `list_recalibration_lineage` propaga ese error en vez de devolver una cadena parcial.

**Versionado del contrato de linaje y provenance por contenido.** `RecalibrationLineage` gana `lineage_version` (constantes `LINEAGE_VERSION_1`/`LINEAGE_VERSION_2`/`CURRENT_LINEAGE_VERSION` en `lineage.py`) — un eje de versionado del **esquema del evento**, deliberadamente distinto de `contract_version` (que sigue versionando el contrato de modelado del predictor, sin relación con el linaje). `LINEAGE_VERSION_1` es la forma histórica (sin `dataset_sha256`, la que ya existía); `LINEAGE_VERSION_2` exige `dataset_sha256`: el SHA-256 del contenido binario exacto del dataset usado en la recalibración, calculado incrementalmente (`compute_dataset_sha256`) para no cargarlo completo en memoria. `dataset_fingerprint` (`(mtime, size)`) no se reemplaza — sigue siendo la clave económica de caché/invalidación en `execute_configured_pipeline`; `dataset_sha256` es provenance nueva y adicional, calculada una sola vez por recalibración (no en cada lectura del dataset), evitando el cómputo innecesario que el enunciado pedía no introducir. `from_dict` nunca reinterpreta un evento `LINEAGE_VERSION_1` persistido (sin las claves nuevas) como si ya cumpliera `LINEAGE_VERSION_2`.

Documentado formalmente en `openspec/specs/human-feedback/spec.md`, mismo requirement, escenarios agregados.

## Actualización 2026-09-06 — microajuste: detección de declaraciones parciales de linaje

> **Corrige la sección anterior:** el párrafo "Lectura fail-closed" de la actualización T-01 de más arriba describe el marcador de declaración como "los cuatro parámetros (`recalibration_id`, `source_model_id`, `successor_model_id`, `dataset_fingerprint`) presentes en conjunto" — equivalente a `all(...)`. Esa formulación quedó superada por este microajuste y ya no describe el comportamiento vigente (ver más abajo). Tampoco debe leerse como que loguear esos parámetros desde el mismo bloque de código de `register_recalibrated_model` sea una operación atómica: MLflow no lo garantiza.

`_run_declares_lineage` usaba `all(...)` sobre los cuatro parámetros para decidir si una versión declaraba linaje. Eso dejaba sin cubrir el caso intermedio: un run con **algunos** de esos parámetros (p. ej. una interrupción a mitad del bloque que los loguea) se clasificaba como "histórico sin linaje" y devolvía `None`, en vez de fallar explícitamente por estar incompleto — exactamente el escenario *fail-open* que T-01 buscaba cerrar.

Corregido separando dos conjuntos con roles distintos:

- **Marcadores de declaración** (`_LINEAGE_DECLARATION_MARKERS`: `recalibration_id`, `source_model_id`, `successor_model_id`, `lineage_version`) — la presencia de **cualquiera** de ellos (`any(...)`, no `all(...)`) ya clasifica el run como "declara linaje". `dataset_fingerprint` se excluye deliberadamente de este conjunto: por sí solo no es específico de una recalibración HITL (nada impide, en principio, que otro tipo de run lo loguee) y no debe bastar para inferir una declaración de linaje.
- **Parámetros obligatorios** (`_LINEAGE_REQUIRED_PARAMS`: los cuatro originales, incluyendo `dataset_fingerprint`) — una vez que un run ya se clasificó como "declara linaje", debe tener **todos** estos parámetros; si falta alguno, `_require_complete_lineage_declaration` levanta `LineageValidationError` indicando cuáles faltan, junto con la versión y el `run_id`.

`register_recalibrated_model` ahora también loguea `lineage_version` como parámetro MLflow indexable (antes solo vivía dentro del artefacto JSON), precisamente para que sirva como marcador de declaración adicional. Un evento `LINEAGE_VERSION_1` persistido por la implementación anterior a este microajuste (sin ese parámetro) sigue detectándose correctamente por los otros tres marcadores.

Documentado formalmente en `openspec/specs/human-feedback/spec.md`, mismo requirement, párrafo "Lectura fail-closed" reescrito.

## Actualización 2026-09-06 — revisión dirigida T-01: R1 (consistencia parámetro↔artefacto) y R2 (instantánea dataset↔hash)

Revisión dirigida sobre T-01 encontró dos P2, resueltos en la misma rama (`fix/hitl-lineage-auditability`, previo a PR):

**R1 — el parámetro `lineage_version` y el `lineage_version` del artefacto podían divergir sin detectarse.** La comparación de consistencia entre artefacto y parámetros solo cubría los cuatro `_LINEAGE_REQUIRED_PARAMS`; nunca cruzaba el parámetro `lineage_version` contra el campo homónimo del artefacto. Un run con parámetro `lineage_version=2` pero artefacto V1 (sin `dataset_sha256`), parámetro V1 con artefacto V2, o parámetro ausente con artefacto V2, se aceptaban incorrectamente. Corregido con `_validate_lineage_version_consistency` (`model_registry.py`): exige que, si el parámetro está presente, sea un entero soportado y coincida exactamente con el del artefacto; si está ausente, solo es válido cuando el artefacto es genuinamente `LINEAGE_VERSION_1`. Además, `RecalibrationLineage.from_dict` (`lineage.py`) se reforzó para normalizar toda estructura de artefacto inválida (no-dict, `{}`, listas, escalares, referencias de feedback mal formadas, campos ausentes/inesperados) a `LineageValidationError`, nunca a `TypeError`/`KeyError`/`AttributeError` sin envolver; `_load_lineage_for_version` agrega una red de seguridad equivalente. Todo mensaje de error incluye la versión del modelo y el `run_id` afectados.

**R2 — el `DataFrame` usado para recalibrar y el `dataset_sha256` registrado podían provenir de lecturas independientes del archivo.** La implementación anterior cargaba el dataset vía `load_dataset_or_raise` y, por separado, reabría el mismo archivo para calcular `dataset_sha256` (`get_dataset_path` + `compute_dataset_sha256`) — dos lecturas del mismo path en momentos distintos, sin garantía de que vieran el mismo contenido si el archivo cambiaba entre medio. Se agregó `data_ingestion.storage.DatasetSnapshot` (`load_dataset_snapshot`): lee los bytes del archivo una única vez, verifica `(mtime, size)` antes y después de esa lectura (aborta con `RuntimeError` si cambió), calcula el SHA-256 incrementalmente sobre esos mismos bytes, y construye el `DataFrame` desde ese contenido en memoria (`pd.read_parquet` sobre un buffer, no una segunda apertura del archivo) — así el `DataFrame` y el `dataset_sha256` provienen estructuralmente de la misma instantánea, no de una garantía externa de que dos lecturas coincidan. `cache_fingerprint` (el mismo `(mtime, size)` de `get_dataset_fingerprint`) se preserva sin cambios como clave de caché en `execute_configured_pipeline`. Se evaluó y descartó una copia temporal a disco (opción también sugerida): innecesaria dado el tamaño actual de los datasets de este prototipo, que ya se cargan enteros en memoria en otros puntos del pipeline.

`backend/app/pipeline.py::load_dataset_snapshot_or_raise` (usado solo por `POST /recalibrate/{sensor_id}`) envuelve `load_dataset_snapshot`, traduciendo `RuntimeError` a `ValueError` para que el router lo mapee a HTTP 400 sin llegar nunca a `register_recalibrated_model`. `POST /forecast/{sensor_id}/run` sigue usando `load_dataset_or_raise` sin cambios — no necesita `dataset_sha256`.

Documentado formalmente en `openspec/specs/human-feedback/spec.md`, mismo requirement, escenarios agregados.

## Referencias

- [ADR-0003: Stack web (backend/frontend) y ciclo de vida de desarrollo automatizado con IA](0003-stack-web-y-ciclo-de-vida-automatizado.md)
- [ADR-0004: Orquestación de experimentos con MLflow, backend Postgres y almacenamiento de artefactos MinIO](0004-orquestacion-experimentos-mlflow-minio.md)
- [ADR-0005: Dockerización de backend y frontend (alerting-ui)](0005-dockerizacion-backend-frontend.md) — este ADR revierte puntualmente su decisión de no acoplar alerting-ui a MLflow.
- `openspec/specs/human-feedback/spec.md` — limitación que este ADR resuelve.
- `openspec/changes/add-recalibration-trigger/` — spec delta y plan de implementación.
