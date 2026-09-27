# Encargo del Paso 2 — auditoría independiente del backend

**Base a auditar:** `f17fe658bad4726202fe13784bb716c06468af9a`

**Preparado:** 2026-09-24 (America/Buenos_Aires)
**Estado:** encargo preliminar; no autoriza ejecución científica, apertura de holdouts ni cambios funcionales.

## 1. Mandato y reglas de evidencia

La auditoría debe resolver las preguntas siguientes de forma independiente y sobre un snapshot congelado. Debe distinguir lectura de código, prueba existente, resultado recién ejecutado, evidencia histórica reportada y aspecto no comprobado. Un PASS técnico no equivale a suficiencia científica ni a cierre del Trabajo Final.

Trazabilidad global: HU2 `data-ingestion`, HU4 `predictive-modeling`, HU5 `human-feedback`, HU6 `architecture-integration`, HU7 `experiment-runner`, UI `alerting-ui`, reproducción histórica HU7/HU8; fases CRISP-DM preparación, modelado, evaluación y despliegue/integración experimental. Estas comprobaciones no deben cambiar hipótesis, alcance, arquitectura ni configuración experimental.

Restricciones comunes:

- fijar el SHA ejecutable y registrar rama, worktree, imagen/entorno, comandos, exit codes y outputs;
- preservar las ocho modificaciones ajenas bajo `replay_packages/` y cualquier otro cambio preexistente;
- no usar resultados restringidos para completar inventarios, no abrir holdouts y no inferir evidencia faltante;
- no ejecutar A/B/C ni auxiliares salvo autorización científica específica posterior; este encargo no la concede;
- no entrenar, inferir o recalibrar sobre datos reales por defecto; usar fixtures/artefactos autorizados y aislamiento;
- no modificar v3, memoria, UI, main ni evidencia histórica; no push/merge/rebase/tag/release/PR;
- si una comprobación necesita modelos/bundles serializados, obtener autorización y registrar su identidad antes de cargarlos;
- conservar resultados negativos válidos y documentar limitaciones; no “corregir” evidencia para obtener PASS.

## 2. Prioridad 1 — posibles problemas funcionales

### F-01. Identidad y ejecución del pronóstico legacy

- **Pregunta:** ¿`POST /forecast/{sensor_id}/run` usa, en orden, predictor recalibrado compatible, caché del mismo sensor+fingerprint y RF explícito, y conserva una emisión previa en vez de reemplazarla?
- **Motivo e impacto potencial:** una precedencia o mutación incorrecta alteraría el modelo atribuido a una decisión y la trazabilidad de feedback.
- **Archivos/contratos:** `backend/app/routers/forecast.py`, `backend/app/pipeline.py`, `human_feedback/model_registry.py`, `schema.py`, contrato `FittedPredictor`.
- **Prueba existente o comprobación propuesta:** ejecutar `backend/tests/test_forecast.py`, `test_pipeline.py` y casos dirigidos de cache hit/miss, contrato incompatible y reemisión de misma fecha.
- **Artefactos/dependencias:** dataset sintético por sensor, MLflow aislado o dobles controlados, directorio temporal de feedback.
- **Restricciones de ejecución:** sin datos reales, sin modelo de producción, sin entrenamiento fuera del fixture.
- **Evidencia necesaria:** comando/salida, identidad de fixture, trazas de predictor elegido, Parquet antes/después y respuesta API.

### F-02. Causalidad y contrato temporal legacy

- **Pregunta:** ¿features, split, target `t+3`, fecha de emisión y fecha objetivo evitan información futura, y el orden real de imputación causal sobre la serie completa es equivalente al split-crudo-antes-de-imputar exigido por la spec?
- **Motivo e impacto potencial:** una fuga temporal invalidaría la descripción operativa y podría afectar HU4/HU6.
- **Archivos/contratos:** `predictive_modeling/{feature_engineering,labeling,contract}.py`, `architecture_integration/pipeline.py`, `openspec/specs/architecture-integration/spec.md`, ADR-0009.
- **Prueba existente o comprobación propuesta:** pruebas existentes más fixtures que comparen split-before-impute con `prepare_daily_features` sobre serie completa y un caso que modifique solo una observación futura.
- **Artefactos/dependencias:** fixture temporal pequeño con timestamps y valores conocidos.
- **Restricciones de ejecución:** no usar holdouts ni resultados históricos.
- **Evidencia necesaria:** matriz de fechas/target, diff de features antes/después, límites exactos del split y conclusión explícita de cumplimiento/equivalencia o desvío; no inferir leakage sin prueba.

### F-03. Integridad de emisión v2 y compatibilidad de bundles

- **Pregunta:** ¿la API v2 captura una única instantánea, valida calendario UTC, carga/valida modelo y calibrador, obtiene efectivamente el score del calibrador y aplica `score >= decision_threshold` con los estados de probabilidad declarados?
- **Motivo e impacto potencial:** mezclar bytes/metadata o aceptar bundle incompatible rompería reproducibilidad y atribución del pronóstico.
- **Archivos/contratos:** `producer_v2.py::create_forecasts`, `producer_emission.py`, `operational_inference.py`, `operational_contract.py`, `operational_preparation.py`.
- **Prueba existente o comprobación propuesta:** pruebas existentes; spies separados sobre modelo/calibrador; asserts de `display_probability=None`, `not_qualified`, `incompatible_assessment`; negativos por sensor/horizonte/calibrador incompatibles.
- **Artefactos/dependencias:** bundles de fixture autorizados con SHA, dataset temporal y reloj UTC fijado.
- **Restricciones de ejecución:** no cargar bundles reales sin autorización; no hacer nueva inferencia sobre datos del Trabajo Final.
- **Evidencia necesaria:** inventario/hash del bundle, metadata validada, componente invocado, score/threshold/alerta, estados de probabilidad, snapshot hash y causa de indisponibilidad.

### F-04. Idempotencia, concurrencia e inmutabilidad v2

- **Pregunta:** ¿un reintento idéntico reproduce la misma respuesta; una clave reutilizada con otro contenido o snapshot falla; dos emisores no duplican/reescriben éxitos?
- **Motivo e impacto potencial:** duplicaciones o reemplazos silenciosos degradarían evidencia operacional.
- **Archivos/contratos:** `human_feedback/operational_repository.py`, `data_ingestion/storage.py`, `backend/tests/test_producer_v2_emission.py`.
- **Prueba existente o comprobación propuesta:** pruebas de idempotencia, lock timeout, snapshot conflict y carrera multiproceso sobre directorio temporal.
- **Artefactos/dependencias:** filesystem temporal compatible con locks, dos procesos controlados, fixture de bundle.
- **Restricciones de ejecución:** no apuntar a `data/` compartido ni a repositorio operacional real.
- **Evidencia necesaria:** documento JSON final, hashes, respuestas HTTP, número de invocaciones a capture/predict y logs de locks.

### F-05. Disponibilidad real de bundles operativos

- **Pregunta:** ¿existen bundles desplegados para sensores/horizontes previstos y qué identidad de modelo/calibrador/threshold contienen?
- **Motivo e impacto potencial:** el código puede estar implementado y, sin embargo, todos los slots resultar no disponibles.
- **Archivos/contratos:** configuración de `get_producer_bundle_root`, `operational_inference.py`, metadata de bundle.
- **Prueba existente o comprobación propuesta:** inventario de solo lectura y validación estructural; inferencia mínima solo si se autoriza expresamente.
- **Artefactos/dependencias:** directorio de bundles autorizado, hashes y entorno compatible.
- **Restricciones de ejecución:** no cargar serializados durante inventario; separar existencia de operabilidad.
- **Evidencia necesaria:** lista de rutas/SHAs/metadata, sensores/horizontes cubiertos y estado `comprobado/no comprobado`.

### F-06. Integridad y admisión del paquete histórico

- **Pregunta:** ¿el paquete configurado satisface esquema, inventario, custodia, parent/child FINISHED, política fija, procedencia, fechas de training, horizonte y cutoff?
- **Motivo e impacto potencial:** una identidad o hash discordante invalidaría la reproducción atribuida al candidato admitido.
- **Archivos/contratos:** `historical_replay/{admission_policy,package_loader,records}.py`, dependencia `get_historical_replay_package`.
- **Prueba existente o comprobación propuesta:** `tests/test_historical_replay_admission_policy.py`, `test_historical_replay_package_loader.py`, `test_build_replay_package.py`; validación contra copia autorizada sin interpretar resultados.
- **Artefactos/dependencias:** paquete autorizado o manifiesto/inventario permitido, política versionada.
- **Restricciones de ejecución:** no abrir valores/resultados restringidos ni regenerar paquete; hashing mecánico solamente.
- **Evidencia necesaria:** hashes, campos de identidad, resultado de cada gate y cualquier mismatch exacto.

### F-07. Revelación causal y observaciones faltantes en replay

- **Pregunta:** ¿antes del origen, entre origen/target y después del target se exponen exactamente los campos permitidos, y los faltantes/inconsistencias se tratan sin fabricar observaciones?
- **Motivo e impacto potencial:** una revelación anticipada o una imputación silenciosa invalidaría el carácter causal de la demo.
- **Archivos/contratos:** `projection.py`, `history_view.py`, `observations.py`, `backend/app/routers/replay.py`, `schemas_replay.py`.
- **Prueba existente o comprobación propuesta:** `test_historical_replay_projection.py`, `history_view.py`, `observations.py`, `imputation_markers.py`, más pruebas API en tres fechas de reloj.
- **Artefactos/dependencias:** registros/frames sintéticos; no se necesita paquete real.
- **Restricciones de ejecución:** fixtures sin valores restringidos; no mover reloj o persistencia reales.
- **Evidencia necesaria:** respuestas serializadas con presencia/ausencia de campos y errores ante asociaciones ambiguas.

### F-08. Concurrencia del feedback de replay

- **Pregunta:** ¿qué ocurre si dos procesos agregan feedback simultáneamente al mismo JSONL de un `package_id`, y cómo se aíslan sesiones mediante directorios configurados?
- **Motivo e impacto potencial:** `ReplayFeedbackStore.append` no muestra lock explícito y un informe posterior retractó la garantía de concurrencia.
- **Archivos/contratos:** `historical_replay/feedback.py`, `backend/app/routers/replay.py`, `tests/test_historical_replay_feedback.py`, `paso4-1-1-cierre.md` §3.
- **Prueba existente o comprobación propuesta:** prueba multiproceso repetible sobre archivo temporal; verificar líneas completas, cantidad, orden no asumido y parseabilidad.
- **Artefactos/dependencias:** directorio temporal y registros sintéticos.
- **Restricciones de ejecución:** no escribir en `replay_feedback/` real ni dentro de paquetes.
- **Evidencia necesaria:** comando, número de escritores/intentos, hash y parseo del JSONL resultante. Si no hay garantía requerida, documentar modelo de un solo escritor.

### F-09. Madurez y procedencia del feedback legacy

- **Pregunta:** ¿confirm/reject rechazan targets inmaduros o registros sin `target_timestamp`/`model_version`, qué ocurre con `target_timestamp=NaT`, y conservan `validated_at`/corrección correcta bajo actualizaciones concurrentes?
- **Motivo e impacto potencial:** feedback anticipado o sin identidad contaminaría una recalibración posterior.
- **Archivos/contratos:** `backend/app/routers/feedback.py`, `human_feedback/{schema,registry}.py`, spec human-feedback.
- **Prueba existente o comprobación propuesta:** pruebas existentes; casos `NaT`, justo antes/después del cierre UTC y dos ciclos `load`→update→`save` concurrentes.
- **Artefactos/dependencias:** log Parquet temporal y reloj controlado.
- **Restricciones de ejecución:** no modificar feedback real.
- **Evidencia necesaria:** filas antes/después, códigos HTTP, timestamps normalizados y resultado de carrera; distinguir reemplazo atómico de transacción/CAS/idempotencia, hoy no acreditadas.

### F-10. Recalibración, preservación y cadena de linaje

- **Pregunta:** ¿solo se aplican correcciones nuevas, maduras, rechazadas y compatibles; se reaplican correcciones previas; el sucesor y linaje son íntegros y los pronósticos originales quedan intactos?
- **Motivo e impacto potencial:** pérdida de correcciones, procedencia inconsistente o mutación retroactiva afectaría HU5 y la explicación de mejora supervisada.
- **Archivos/contratos:** `human_feedback/{recalibration,lineage,model_registry}.py`, routers `recalibration.py`, `lineage.py`.
- **Prueba existente o comprobación propuesta:** `backend/tests/test_recalibration.py`, `test_lineage.py`, `test_models_active.py`; `tests/test_recalibration.py`, `test_recalibration_lineage.py`, `test_model_registry.py`; escenarios de fuente/umbral/horizonte incompatibles y cadena corrupta.
- **Artefactos/dependencias:** MLflow aislado o doubles fieles, predictor/frames sintéticos y snapshot temporal.
- **Restricciones de ejecución:** no registrar modelos en el servicio compartido; no recalibrar datos reales; no afirmar mejora por éxito técnico.
- **Evidencia necesaria:** source/successor IDs, feedback refs, trained-through, SHA-256, versión MLflow y comparación inmutable de emisiones.

### F-11. Recorrido de reviews v2 hacia aprendizaje

- **Pregunta:** ¿la apertura a las 00:00 UTC, `requires_mature_revalidation` para reviews del mismo día y la madurez posterior funcionan como se declara; existe luego un consumidor de reviews elegibles o solo se expone elegibilidad?
- **Motivo e impacto potencial:** describir reviews v2 como feedback aplicado sería una sobreafirmación si falta el consumidor.
- **Archivos/contratos:** `OperationalRepository.submit_review`, `_training_eligibility`, routers v2, `human_feedback.recalibration.py`.
- **Prueba existente o comprobación propuesta:** pruebas de borde temporal/estado, traza estática de llamadas/imports y prueba contractual de que una review humana no es medición objetiva ni altera por sí sola modelo/bundle.
- **Artefactos/dependencias:** fixtures v2; no necesita modelo real.
- **Restricciones de ejecución:** no implementar el puente en esta auditoría.
- **Evidencia necesaria:** grafo de llamadas, estado persistido y conclusión explícita `conectado/no conectado/no comprobado`.

### F-12. Contratos del ensamble y artefactos v4

- **Pregunta:** ¿los pesos 1/3, el `sample_weight` fold-local, la selección por MCC/bootstrap y los artefactos congelados coinciden entre implementación y contratos?
- **Motivo e impacto potencial:** confundir combinación con balanceo o configuración con modelo entrenado alteraría la descripción metodológica del capítulo 3.
- **Archivos/contratos:** `controlled_daily_v4/{config,models,selection,stage_a_runner,artifacts,transfer_contract}.py`; protocolo v4; ADR-0010/0011.
- **Prueba existente o comprobación propuesta:** pruebas unitarias/sintéticas específicas de modelos, soft voting, selección, artifacts y transfer contract.
- **Artefactos/dependencias:** fixtures sintéticos solamente, constraints fijados.
- **Restricciones de ejecución:** no A/B/C real, no holdout, no lectura de resultados cerrados.
- **Evidencia necesaria:** salida de tests, pesos efectivos del estimador ajustado en fixture, configs base y schema del artefacto.

## 3. Prioridad 2 — contradicciones documentales

### D-01. Endpoint de linaje: documentación histórica frente al snapshot

- **Pregunta:** ¿qué fuente afirma que no hay endpoint y desde qué commit dejó de ser cierto?
- **Motivo e impacto potencial:** el capítulo podría omitir una capacidad implementada o atribuirla a un período equivocado.
- **Archivos/contratos:** `backend/app/routers/lineage.py`, `backend/app/main.py`, specs human-feedback/alerting-ui, auditorías HU5/HU6.
- **Prueba existente o comprobación propuesta:** historia Git de archivos y test `backend/tests/test_lineage.py`.
- **Artefactos/dependencias:** metadatos Git; no servicio requerido.
- **Restricciones de ejecución:** no reescribir informes históricos; proponer corrección solo en fuente vigente.
- **Evidencia necesaria:** commits/fechas, router montado y texto exacto de ambos lados.

### D-02. RF operativo versus selección/ensamble experimental

- **Pregunta:** ¿todas las fuentes vigentes distinguen que legacy usa RF/recalibrado/cache y v2 bundles, mientras v4 evalúa familias/ensamble?
- **Motivo e impacto potencial:** atribuir selección automática o soft voting a la UI sería incorrecto.
- **Archivos/contratos:** `backend/app/pipeline.py`, `producer_emission.py`, specs alerting-ui/predictive-modeling, auditoría HU6.
- **Prueba existente o comprobación propuesta:** traza estática completa desde endpoints e imports; revisión documental dirigida.
- **Artefactos/dependencias:** snapshot Git.
- **Restricciones de ejecución:** no convertir la integración del ensamble en requisito de cierre sin obligación normativa.
- **Evidencia necesaria:** mapa de llamadas y lista de afirmaciones documentales compatibles/incompatibles.

### D-03. `model_version` versus `model_id`

- **Pregunta:** ¿las APIs, schemas y memoria explican que el campo legacy `model_version` guarda el identificador lógico del predictor y no el número del Model Registry?
- **Motivo e impacto potencial:** confusión de identidad impediría reconstruir correctamente una emisión/recalibración.
- **Archivos/contratos:** `human_feedback/schema.py`, `model_registry.py`, spec human-feedback, auditoría HU6.
- **Prueba existente o comprobación propuesta:** inspección de serialización y tests de feedback/model registry.
- **Artefactos/dependencias:** fixtures.
- **Restricciones de ejecución:** conservar nombre por compatibilidad; no migrar datos durante auditoría.
- **Evidencia necesaria:** valor persistido, metadata MLflow correspondiente y redacción propuesta si falta precisión.

### D-04. Concurrencia de replay retractada

- **Pregunta:** ¿queda alguna fuente vigente que todavía afirme garantía de lock/concurrencia en `ReplayFeedbackStore`?
- **Motivo e impacto potencial:** una garantía documental falsa puede inducir operación multiusuario insegura.
- **Archivos/contratos:** `paso4-1-cierre-demo.md` §8, retractación en `paso4-1-1-cierre.md` §3, `feedback.py`.
- **Prueba existente o comprobación propuesta:** búsqueda documental + F-08.
- **Artefactos/dependencias:** ninguno adicional.
- **Restricciones de ejecución:** preservar informes históricos y señalar la retractación, no borrar el antecedente.
- **Evidencia necesaria:** inventario de menciones y resultado de prueba/decisión operacional.

### D-05. Resultados de pruebas previas frente al snapshot actual

- **Pregunta:** ¿a qué commit/imagen corresponden los 20/18/124 PASS reportados y son transferibles a `f17fe658...`?
- **Motivo e impacto potencial:** sin identidad ejecutable, esas cifras no demuestran el estado actual.
- **Archivos/contratos:** `paso4-1-cierre-demo.md`, `paso4-1-1-cierre.md`, manifests/logs permitidos.
- **Prueba existente o comprobación propuesta:** reconstruir identidad documental/ejecutable; ejecutar suites dirigidas en snapshot si está autorizado.
- **Artefactos/dependencias:** imagen/constraints y logs originales si existen.
- **Restricciones de ejecución:** no completar SHA faltante por inferencia.
- **Evidencia necesaria:** SHA, imagen, comando, fecha y salida; de faltar, mantener “evidencia previa reportada”.

### D-06. Spec, tareas, trazabilidad y contrato HTTP del replay

- **Pregunta:** ¿cuál es el contrato vigente para `y_proba`, baselines, procedencia completa, los dos umbrales y estados por fila, y por qué RH-02/03/05/06/08/13 difieren de schemas/router, tareas y trazabilidad?
- **Motivo e impacto potencial:** el capítulo 3 podría atribuir al backend campos que la API no entrega o presentar como completa una obligación que las tareas aún reconocen pendiente.
- **Archivos/contratos:** spec delta `historical-replay`, `backend/app/schemas_replay.py`, `backend/app/routers/replay.py`, `openspec/changes/add-causal-historical-replay/{tasks.md,traceability.md}`.
- **Prueba existente o comprobación propuesta:** matriz requisito→schema→router→test para RH-02/03/05/06/08/13 y serialización dirigida con fixtures.
- **Artefactos/dependencias:** snapshot Git y fixtures sintéticos; no requiere abrir el paquete real.
- **Restricciones de ejecución:** clasificar como deriva contractual hasta resolverla; no completar campos por inferencia ni reescribir evidencia histórica.
- **Evidencia necesaria:** decisión de contrato vigente, referencias exactas de ambos lados, cobertura de prueba y lista de documentos/código que requerirían un change posterior.

## 4. Prioridad 3 — mejoras opcionales, no requisitos de cierre

### O-01. Integración del ensamble v4 con backend/UI

- **Pregunta:** ¿aportaría valor publicar un candidato v4 auditado como bundle operativo y mostrar su identidad en UI?
- **Motivo e impacto potencial:** podría unificar evaluación y operación, pero también mezcla propósitos y requiere gobierno de promoción.
- **Archivos/contratos involucrados:** `controlled_daily_v4`, `operational_inference.py`, formato de bundle, schemas v2/UI.
- **Prueba o comprobación propuesta:** solo análisis de brecha/diseño y criterios de promoción; no implementar en auditoría.
- **Artefactos/dependencias:** contrato de exportación, firma/calibrador, política de aprobación.
- **Restricciones de ejecución:** **evolución potencial, no requisito de cierre**, salvo obligación vigente que la auditoría identifique expresamente. No usar holdout para seleccionar integración.
- **Evidencia necesaria:** decisión arquitectónica y fuente normativa; si no existe obligación, clasificar como opcional.

### O-02. Categoría “posible alerta”

- **Pregunta:** ¿existe una necesidad de producto/norma para un estado intermedio además de alerta/sin alerta?
- **Motivo e impacto potencial:** podría comunicar incertidumbre, pero cambia semántica, contratos, UX y potencialmente calibración.
- **Archivos/contratos involucrados:** schemas legacy/v2, `alerts.py`, bundle metadata, frontend.
- **Prueba o comprobación propuesta:** análisis de requerimiento, impacto contractual y validación con responsables; no codificar en auditoría.
- **Artefactos/dependencias:** decisión normativa y criterio cuantitativo predeclarado.
- **Restricciones de ejecución:** **evolución potencial, no requisito de cierre**, salvo obligación vigente demostrada. No elegir umbrales mirando test/holdout.
- **Evidencia necesaria:** requisito aprobado, semántica y umbrales anteriores a evaluación.

### O-03. Estado de imputación por fila en `/replay/history`

- **Pregunta:** ¿la explicación para defensa necesita distinguir medida/imputada/no determinada en cada punto del historial?
- **Motivo e impacto potencial:** mejora transparencia, pero el contrato actual ya preserva causalidad sin ese detalle.
- **Archivos/contratos involucrados:** `history_view.py`, `observations.py`, `schemas_replay.py`, UI histórica.
- **Prueba o comprobación propuesta:** análisis de necesidad y diseño de contrato; no modificar paquete.
- **Artefactos/dependencias:** marcadores de imputación autorizados.
- **Restricciones de ejecución:** opcional; no fabricar estado cuando el paquete no lo aporta.
- **Evidencia necesaria:** decisión de alcance y disponibilidad real de marcadores.

### O-04. Endurecimiento de feedback JSONL de replay

- **Pregunta:** si la demo admite múltiples escritores, ¿conviene lock, almacenamiento transaccional o idempotencia por request?
- **Motivo e impacto potencial:** resolvería F-08 si el modelo de uso requiere concurrencia.
- **Archivos/contratos involucrados:** `historical_replay/feedback.py`, dependency/router replay.
- **Prueba o comprobación propuesta:** primero resolver F-08 y definir modelo operativo; luego change separado con pruebas de carrera.
- **Artefactos/dependencias:** filesystem objetivo y política de duplicados.
- **Restricciones de ejecución:** no corregir durante auditoría ni alterar feedback existente.
- **Evidencia necesaria:** requerimiento de concurrencia, diseño aprobado y tests repetibles.

### O-05. Puente de reviews v2 a recalibración

- **Pregunta:** ¿debe existir un consumidor explícito de correcciones v2 elegibles?
- **Motivo e impacto potencial:** cerraría un ciclo operativo, pero exige identidad de modelo, contrato de madurez, custodia de snapshot y política de promoción.
- **Archivos/contratos involucrados:** `OperationalRepository`, recalibración legacy, bundles y linaje.
- **Prueba o comprobación propuesta:** análisis de arquitectura después de F-11; change separado si se aprueba.
- **Artefactos/dependencias:** dataset/snapshot original, identidad del bundle, feedback refs y registry de destino.
- **Restricciones de ejecución:** opcional; no equiparar review con corrección aplicable sin contrato.
- **Evidencia necesaria:** decisión aprobada y trazabilidad HU5/HU6.

## 5. Criterio de salida del Paso 2

El Paso 2 debería producir, como mínimo:

1. snapshot, entorno y comandos reproducibles;
2. resultado por comprobación (`PASS`, `FAIL`, `BLOCKED` o `NO APLICA`) con evidencia enlazada;
3. hallazgos funcionales separados de contradicciones documentales y mejoras opcionales;
4. trazabilidad a HU/capacidad/CRISP-DM y efecto —o ausencia de efecto— sobre configuración experimental;
5. lista explícita de aspectos no comprobados y artefactos no abiertos;
6. encargo de corrección separado para todo hallazgo material, seguido de nueva revisión independiente.

La auditoría no debe autorizar su propio merge ni declarar “backend cerrado” solo por tests verdes. Un cierre posterior requerirá evaluación independiente del snapshot revisado y de las limitaciones restantes.
