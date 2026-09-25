# Encargo de corrección para Claude Code — Paso 2 (backend)

**Origen:** auditoría independiente `informe-auditoria-paso2.md`, snapshot `f17fe658bad4726202fe13784bb716c06468af9a`.
**Alcance:** SOLO los hallazgos confirmados abajo (Correcciones 1-4) más un ítem de aprobación normativa (Ítem 5, que NO autoriza implementación directa sin esa aprobación). No se autoriza ninguna otra corrección, ninguna mejora opcional (O-01..O-05), ninguna integración del ensamble v4, ni cambios en `controlled_daily_v3`, memoria técnica, UI, ni configuración experimental.

**Revisión de esta versión del encargo (consolidada, respecto de la versión anterior):**
- Se agregó la **Corrección 4 (F-06/F-07)**: antes figuraba solo en "explícitamente fuera de este encargo"; ahora es una corrección de alcance mínimo (preservar bytes vía `.gitattributes`, sin tocar la lógica de verificación).
- El **Ítem 4/5 (D-06)** pasa de "dos opciones a decidir desde cero" a una **propuesta mínima concreta y compatible** (campos, semántica, procedencia, comportamiento ante indeterminación), lista para aprobación — pero sigue sin autorización de implementación hasta que se apruebe explícitamente.
- Se mantienen sin cambios la Corrección 1 (D-01) y la Corrección 2 (F-08); se agregó la Corrección 3 (F-09) en la revisión previa.

Después de implementar, este trabajo requiere una nueva revisión independiente antes de cualquier cierre. Esto no autoriza merge a `main` ni declara el backend cerrado.

---

## Orden de dependencias

1. **Corrección 1 (D-01, documental)** — independiente, sin dependencias.
2. **Corrección 2 (F-08, funcional)** — independiente de las demás.
3. **Corrección 3 (F-09, funcional)** — independiente de las demás. Comparte el mismo mecanismo de lock (`data_ingestion.storage.interprocess_lock`) que la Corrección 2, pero en un módulo distinto (`human_feedback/registry.py`/`backend/app/routers/feedback.py` vs. `historical_replay/feedback.py`) — no hay dependencia de código entre ambas, pueden implementarse en cualquier orden o en paralelo.
4. **Corrección 4 (F-06/F-07, configuración de repositorio)** — independiente de las demás. No depende de ningún código tocado por las Correcciones 1-3; toca únicamente `.gitattributes` y el contenido en disco de `replay_packages/base-seed4-1157696b7b-v2/` (re-normalizado, no reescrito con datos distintos).
5. **Ítem 5 (D-06, propuesta pendiente de aprobación — NO es una tarea de implementación hasta que se apruebe)** — ver sección dedicada al final. No depende de las anteriores ni ellas dependen de él. Si se aprueba, pasa a ser una Corrección 5 en un encargo posterior, no en este.

No hay orden obligatorio entre los ítems 1, 2, 3, 4 y 5.

---

## Corrección 1 — D-01: actualizar la limitación T-01 obsoleta en la spec de human-feedback

**Prioridad:** alta (contradicción documental confirmada dentro de una fuente normativa vigente).

**Archivo:** `openspec/specs/human-feedback/spec.md`, línea 231 (sección con "Limitación conocida (T-01)").

**Comportamiento esperado:** la spec no debe afirmar que "no existe todavía un endpoint HTTP para consultar el linaje ni su cadena completa", porque `GET /lineage/{sensor_id}` está implementado, montado (`backend/app/main.py::app.include_router(lineage.router)`) y testeado (`backend/tests/test_lineage.py`) desde el commit `7cdea8b` ("feat: expone observabilidad para la demo").

**Corrección mínima:**
- Eliminar o reescribir la limitación T-01 para reflejar que el endpoint `GET /lineage/{sensor_id}` existe, describe brevemente su comportamiento (solo lectura, fail-closed ante `LineageValidationError`, reutiliza `list_recalibration_lineage`), y referenciar el commit `7cdea8b` como origen del cambio.
- No modificar ningún informe histórico (`paso4-1-cierre-demo.md`, auditorías HU5/HU6, etc.) — la corrección es solo en la fuente vigente (`openspec/specs/human-feedback/spec.md`).
- No agregar, quitar ni modificar ningún campo del endpoint ni de `LineageResponse`/`LineageEntry` — esto es una corrección de redacción, no de código funcional.

**Prueba de aceptación:**
- `backend/tests/test_lineage.py` sigue pasando sin modificaciones (no se toca código de `backend/app/routers/lineage.py`).
- Revisión manual: la spec ya no contiene una afirmación de ausencia de endpoint que sea falsa respecto del snapshot vigente.

**Fuera de este cambio:** no describir en la spec el contenido semántico del endpoint más allá de lo que el código ya hace; no crear un nuevo requirement OpenSpec formal si no se considera necesario (alcance mínimo: corregir la limitación conocida existente).

**Compatibilidad con datos históricos:** ninguna — es un cambio de texto en una spec, no toca datos ni código de ejecución.

---

## Corrección 2 — F-08: pérdida y corrupción de datos en `ReplayFeedbackStore.append` bajo escritura concurrente

**Prioridad:** alta (defecto funcional confirmado y reproducible).

**Archivo:** `src/historical_replay/feedback.py`, clase `ReplayFeedbackStore`, método `append` (líneas 63-66 en el snapshot auditado).

**Escenario reproducible (evidencia, re-verificada con rigor adicional):** con 8 procesos escribiendo concurrentemente 200 registros JSONL cada uno (1600 esperados) al mismo archivo vía `ReplayFeedbackStore.append` (el método real, confirmado por import directo), sincronizados con `multiprocessing.Barrier` para forzar el arranque simultáneo, y con verificación explícita de que los 8 procesos terminan con `exitcode=0` sin excepciones silenciadas, el resultado observado en repeticiones sucesivas fue pérdida de entre el 19 % y el 26 % de las líneas esperadas (390-411 de 1600), confirmada también a nivel de bytes (119073 bytes de 493520 esperados ausentes en disco en una de las corridas), y ocasionalmente una línea corrupta. Se aisló que el efecto **no depende de la API de E/S usada por Python**: se reproduce de forma comparable usando `os.open`/`os.write` de bajo nivel con `O_APPEND` explícito en lugar de `open(..., "a")` de alto nivel — por lo que la causa no es "falta de manejo de O_APPEND en el código", sino una limitación de la garantía de atomicidad entre procesos de la escritura en modo append en este entorno Windows/NTFS, independiente de la capa de Python. Reproducir con los scripts de evidencia: `.../scratchpad/backend-audit-step2/fixtures/f08_replay_feedback_concurrency_v2.py` y `f08_mechanism_isolation.py` (datos 100% sintéticos, directorio temporal).

**Comportamiento esperado:** cada llamada a `append` debe persistir su registro sin pérdida ni corrupción, incluso si otro proceso escribe concurrentemente al mismo archivo. El contrato exacto de aislamiento entre `package_id`s (un archivo por paquete) debe mantenerse sin cambios.

**Impacto funcional y sobre afirmaciones del capítulo 3:** la demo de reproducción histórica podría perder o corromper feedback registrado por un revisor si dos sesiones/pestañas escriben casi simultáneamente al mismo `package_id`. Esto afecta la fila "Feedback de reproducción" de la matriz de capítulo 3 (ver `matriz-capitulo3-auditada-2026-09-24.md`), que debe describirse como defecto corregido, no como limitación de cobertura de pruebas.

**Corrección mínima propuesta:** aplicar el mismo mecanismo de lock interproceso ya existente y probado en el repositorio (`data_ingestion.storage.interprocess_lock`, usado por `human_feedback/operational_repository.py`) alrededor de la apertura y escritura del archivo en `ReplayFeedbackStore.append`. Concretamente:
- Adquirir `interprocess_lock` sobre un archivo de lock dedicado (p. ej. `<package_id>.jsonl.lock`, junto al `.jsonl`, nunca el propio `.jsonl` como lock) antes de abrir el archivo en modo append y escribir la línea, liberándolo inmediatamente después.
- Mantener el formato de archivo (JSON-lines, un archivo por `package_id`) y la ubicación (fuera de `replay_packages/`, fuera de `data/feedback__<sensor_id>.parquet`) sin cambios.
- No introducir un mecanismo nuevo de locking distinto del ya usado y probado en el proyecto, salvo que `interprocess_lock` resulte inaplicable por alguna razón técnica — en ese caso, documentar por qué y proponer alternativa antes de implementar.
- No agregar deduplicación, control de idempotencia por request, ni transacciones más allá de evitar la pérdida/corrupción bajo concurrencia (eso es O-04, evolución posterior fuera de este encargo).

**Prueba de aceptación:**
- Adaptar o incorporar una versión del fixture `f08_replay_feedback_concurrency.py` como test versionado (p. ej. en `tests/test_historical_replay_feedback.py`), usando `multiprocessing` con una barrera para forzar escritura simultánea real (no solo repetición secuencial), y verificar:
  - número de líneas resultantes == número de registros escritos (sin pérdida);
  - cada línea es JSON válido y corresponde a exactamente un registro (sin corrupción/interleaving);
  - no se asume orden entre escritores.
- Los tests existentes de `tests/test_historical_replay_feedback.py` y `backend/tests/test_replay.py` (feedback) siguen pasando sin regresión (nota: `backend/tests/test_replay.py` requiere el paquete real `replay_packages/base-seed4-1157696b7b-v2`; si el entorno de quien implemente reproduce el mismo bloqueo de entorno documentado en `informe-auditoria-paso2.md` §2, debe investigarlo — no está cubierto por esta auditoría ni por este encargo, que se limita a F-08).

**Restricciones de ejecución:**
- No modificar `replay_packages/` ni ningún archivo de feedback ya persistido.
- No modificar el contrato público (`register_feedback`, `visible_feedback_for`, endpoints `POST`/`GET /replay/predictions/{origen}/feedback`) más allá de lo estrictamente necesario para introducir el lock dentro de `append`.
- No extender esto a un mecanismo transaccional completo ni a idempotencia por request (eso es O-04).

**Compatibilidad con datos históricos:** el formato JSON-lines no cambia; archivos de feedback ya escritos (si existen) siguen siendo válidos y legibles sin migración.

---

---

## Corrección 3 — F-09: "lost update" en el ciclo `load→update→save` del feedback legacy

**Prioridad:** alta (defecto funcional confirmado y reproducible, distinto de la Corrección 2).

**Archivos:** `backend/app/routers/feedback.py` (`confirm_feedback`/`reject_feedback`, o los nombres equivalentes que llaman a `load_feedback_log`→`update_feedback`→`save_feedback_log`), y/o `src/human_feedback/registry.py`.

**Escenario reproducible (evidencia):** dos procesos cargan el mismo `feedback_log` (Parquet temporal sintético, nunca datos reales) con `load_feedback_log`, sincronizados con `multiprocessing.Barrier` justo después de la lectura, cada uno modifica una fila distinta con `update_feedback` (la función real) y guarda con `save_feedback_log` (la función real). Resultado: ambos procesos terminan con `exitcode=0` sin excepción, pero **la actualización del proceso que escribe primero desaparece por completo** del archivo final — el segundo proceso sobreescribe el archivo completo con su propia copia en memoria, que todavía tenía la fila del primero en su estado anterior. A diferencia de la Corrección 2, aquí no hay corrupción de bytes: cada escritura individual es atómica (gracias al lock ya existente dentro de `data_ingestion.storage.save_dataset`/`atomic_write_bytes`), pero ese lock protege solo el paso de escritura, no el ciclo completo lectura-modificación-escritura. Reproducir con `.../scratchpad/backend-audit-step2/fixtures/f09_legacy_feedback_concurrency.py`.

**Comportamiento esperado:** dos actualizaciones concurrentes de feedback (incluso sobre filas distintas del mismo log) no deben perderse entre sí. Cada actualización confirmada/rechazada por una persona debe persistir, o la operación debe fallar explícitamente (p. ej. con un conflicto de versión) en vez de desaparecer silenciosamente.

**Impacto funcional y sobre afirmaciones del capítulo 3:** afecta la fila "Feedback legacy" de la matriz de capítulo 3. La memoria no debe describir esto como "limitación de cobertura de pruebas"; es un defecto conocido con corrección mínima pendiente.

**Corrección mínima propuesta:** extender el ciclo `load_feedback_log`→`update_feedback`→`save_feedback_log` (tal como lo usan `confirm_feedback`/`reject_feedback` en `backend/app/routers/feedback.py`) para que ocurra dentro de una única adquisición de `data_ingestion.storage.interprocess_lock` (el mismo mecanismo ya usado y probado en el proyecto, análogo al patrón `_locked_document` de `human_feedback/operational_repository.py`), de modo que ningún otro proceso pueda leer/escribir el mismo archivo de feedback mientras el ciclo está en curso. Alternativa igualmente válida: agregar una función en `human_feedback/registry.py` (p. ej. `update_feedback_log_atomically(name, data_dir, update_fn)`) que encapsule lock + load + `update_fn` + save como una sola unidad, y usarla desde el router en lugar de las tres llamadas sueltas.

**Prueba de aceptación:**
- Adaptar `f09_legacy_feedback_concurrency.py` (o una versión reducida) como test versionado (p. ej. en `backend/tests/test_feedback.py` o `tests/test_feedback_registry.py`), usando `multiprocessing` con barrera para forzar el interleaving real, y verificar que ambas actualizaciones concurrentes sobreviven (o que una de las dos falla explícitamente con un código de error claro, si se opta por un modelo de conflicto en vez de serialización).
- Los tests existentes de `backend/tests/test_feedback.py` siguen pasando sin regresión.

**Restricciones de ejecución:**
- No modificar ningún archivo de feedback ya persistido en `data/`.
- No introducir un mecanismo de lock nuevo y distinto del ya usado en el proyecto (`interprocess_lock`), salvo justificación técnica explícita.
- No extender esto a un sistema de revisión optimista completo (eso sería una reingeniería mayor, fuera de este encargo); el objetivo mínimo es que dos actualizaciones concurrentes no se pisen silenciosamente.

**Compatibilidad con datos históricos:** el formato Parquet no cambia; ningún dato histórico se migra ni se reescribe.

---

## Corrección 4 — F-06/F-07: preservar los bytes de `replay_packages/` frente a la conversión de finales de línea de Git

**Prioridad:** alta (bloquea toda validación HTTP end-to-end del paquete histórico real; causa raíz confirmada, no hipotética).

**Causa raíz confirmada:** con `core.autocrlf=true` (configuración de desarrollo en Windows), un checkout reescribe los finales de línea de los archivos de texto de `replay_packages/base-seed4-1157696b7b-v2/` (`manifest.json`, `predictions.json`, `run_metadata.json`, `effective_configuration.json`), alterando sus bytes en disco respecto de los committeados. `src/historical_replay/package_loader.py::_sha256_of` calcula el hash sobre `path.read_bytes()` (bytes crudos en disco), que ya no coincide con `custody_sha256` del manifiesto (calculado sobre los bytes originales al empaquetar) → `_verify_file_integrity` lanza `IntegrityError` → las requests HTTP contra ese paquete devuelven 503. Verificado archivo por archivo comparando el blob de git contra el working tree. Es la misma clase de problema ya visto una vez en este repo (commit `90183d3`, para `data_quality/imputation.py`/`temporal.py`), pero **no corregida ahí de la misma forma** — ver la restricción de diseño más abajo, porque en este caso la solución de aquel commit (normalizar CRLF→LF antes de hashear, en código) **no es aplicable**.

**Comportamiento esperado:** los bytes de los archivos de `replay_packages/` en cualquier checkout (Windows con `autocrlf=true`, Linux/CI con `autocrlf=false`, o cualquier combinación) deben ser idénticos a los bytes committeados, de modo que `custody_sha256` coincida siempre, sin excepción de plataforma.

**Corrección mínima propuesta:** declarar en `.gitattributes` que los archivos de paquetes de reproducción histórica son artefactos de bytes fijos, exactamente con el mismo patrón que ya existe en este repo para otro caso análogo (`/config/producer-calibration-plan.frozen*.json -text`, ADR-0013):

```
# replay_packages/: paquetes de reproducción histórica con custody_sha256
# fijado en manifest.json — los bytes deben ser idénticos en cualquier
# checkout; autocrlf no debe alterarlos (ver F-06/F-07, Paso 2 auditoría).
/replay_packages/**/*.json -text
/replay_packages/**/*.parquet -text
```

Después de agregar `.gitattributes`, es necesario **re-normalizar el working tree existente** (`git add --renormalize replay_packages` o equivalente) para que los archivos ya afectados por `autocrlf` en checkouts previos vuelvan a coincidir con el blob de git, y verificar con `git diff --stat` que no hay más cambios que el efecto de `-text` (ningún dato de predicción ni metadata debe cambiar de valor, solo de bytes de fin de línea si correspondiera).

**Restricción de diseño explícita (obligatoria, pedida por el usuario):**
- **NO** modificar `_sha256_of`, `_verify_file_integrity`, ni ninguna otra función de verificación en `package_loader.py` para normalizar finales de línea antes de hashear, ni para aceptar de otro modo un archivo cuyos bytes en disco difieran de los committeados. La verificación de custodia debe seguir siendo estricta byte a byte.
- **NO** recalcular ni actualizar `custody_sha256` en ningún `manifest.json` para que "coincida" con una copia alterada — el objetivo es que los bytes en disco coincidan con el hash ya declarado (fijado en el momento de empaquetar), no al revés.
- Esto es deliberadamente distinto del enfoque tomado en el commit `90183d3` (normalizar CRLF→LF en código antes de hashear un módulo fuente): ahí se trataba de código fuente cuya identidad relevante es su contenido lógico; acá se trata de artefactos de evidencia científica cuya identidad de custodia es, por diseño, sus bytes exactos — normalizar en la verificación equivaldría a debilitar esa garantía para aceptar archivos potencialmente alterados.

**Prueba de aceptación:**
- En un checkout limpio con `core.autocrlf=true` (reproduciendo la configuración que causó el bloqueo), `_verify_file_integrity` sobre `replay_packages/base-seed4-1157696b7b-v2/` no lanza `IntegrityError`.
- `backend/tests/test_replay.py` (que depende de este paquete real) pasa sin el bloqueo documentado en `informe-auditoria-paso2.md` §2.
- `git diff --stat` tras `--renormalize` no muestra cambios de contenido lógico en `predictions.json`/`manifest.json`/`run_metadata.json`/`effective_configuration.json` — solo, si corresponde, normalización de fin de línea ya reflejada en el hash de custodia original.
- Ningún test de `_verify_file_integrity` existente que dependa de detectar una alteración real deja de fallar cuando corresponde (no se debilitó la detección).

**Compatibilidad con datos históricos:** los valores de predicciones/metadata no cambian; solo se fija la representación de bytes en el working tree para que coincida de forma estable con el blob de git y con `custody_sha256` en cualquier plataforma.

---

## Ítem 5 — D-06: propuesta mínima para exponer el estado por fila en `/replay/history` (pendiente de aprobación — NO es una tarea de implementación todavía)

**Naturaleza de este ítem:** a diferencia de las Correcciones 1-4, esto **no** es un encargo de corrección de código que deba implementarse ya. Es una **propuesta de diseño concreta**, orientada explícitamente a **conservar el requisito vigente** (RH-05/RH-08 tal como están escritos, exponer el estado por fila), preparada para que quien tiene autoridad sobre la spec la apruebe antes de que se implemente.

**Contexto:** la spec delta vigente del change `add-causal-historical-replay` (`openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md`) contiene dos requirements **DEBE (MUST)**:
- **RH-05**, con un Scenario explícito sobre "una fecha del historial mostrado antes de la revelación cuyo marcador de imputación no fue recomputado", que exige que el estado quede como `no_determinado`, nunca como valor numérico inferido ni omitido.
- **RH-08**, que exige mostrar un estado explícito con causa concreta "en vez de omitir el campo".

`backend/app/schemas_replay.py::ReplayHistoryRow` no tiene ningún campo de estado (`fecha`, `soil_moisture: float | None` únicamente) — el endpoint `GET /replay/history` omite el campo que RH-05/RH-08 exigen. `openspec/changes/add-causal-historical-replay/traceability.md` marca RH-05/RH-08 como "[implementada]" pese a admitir esta brecha en su propio texto.

**Orientación del usuario para esta propuesta:** conservar el requisito vigente (RH-05/RH-08 tal como están escritos) en vez de acotar la spec. La propuesta debajo es la opción "extender la API", precisada al nivel de campos/semántica/procedencia/comportamiento ante indeterminación, para que la aprobación sea sobre un diseño concreto y no sobre una alternativa abstracta.

**Base técnica ya existente que hace esta propuesta de bajo riesgo (no requiere construir nada nuevo desde cero):**
- `src/historical_replay/imputation_markers.py::reconstruct_imputation_markers(df, columns)` ya reconstruye, de forma determinista y verificada contra el commit histórico (`verify_imputation_source_matches_verified_commit`), el marcador `<columna>_imputado` por fecha, reaplicando exactamente `data_quality.temporal.validate_daily_series` + `data_quality.imputation.interpolate_missing_causal` sobre el dataset ya empaquetado (mismo orden que `architecture_integration.pipeline.prepare_daily_features`).
- `src/historical_replay/observations.py` ya define las cuatro constantes de estado que RH-05/RH-08 requieren (`MEASURED="medida"`, `IMPUTED="imputada"`, `UNDETERMINED="no_determinado"`, `MISSING_FROM_SOURCE="sin_dato_en_fuente"`) y la lógica exacta para derivarlas (`link_observation`), hoy usada solo para `medicion_original.estado` (la medición del target ya revelada), **nunca para las filas de `/replay/history`**.
- El router (`backend/app/routers/replay.py:215`) ya invoca el código que consume `imputation_markers_df`, pero lo llama con `imputation_markers_df=None` — es decir, la brecha no es la ausencia de mecanismo, es que `history_view.py::filtered_history` nunca lo usa ni lo expone en `ReplayHistoryRow`.

**Propuesta mínima concreta (para aprobar, no para implementar todavía):**
1. **Campo nuevo:** agregar a `ReplayHistoryRow` (`backend/app/schemas_replay.py`) un campo `estado: Literal["medida", "imputada", "no_determinado", "sin_dato_en_fuente"]`, reutilizando exactamente las constantes ya definidas en `observations.py` (sin inventar una taxonomía nueva).
2. **Semántica por valor** (idéntica a la ya usada en `medicion_original.estado`, extendida a cada fila del historial en vez de solo al target):
   - `medida`: hay valor crudo en el dataset empaquetado para esa fecha y el marcador de imputación indica que no fue rellenado.
   - `imputada`: hay valor (crudo o reconstruido) para esa fecha y el marcador indica que sí fue rellenado por `interpolate_missing_causal`.
   - `sin_dato_en_fuente`: no hay valor crudo para esa fecha en el dataset empaquetado, y el marcador de imputación sí cubre esa fecha (se sabe con certeza que faltaba en la fuente).
   - `no_determinado`: no se pudo reconstruir el marcador para esa fecha (p. ej. `verify_imputation_source_matches_verified_commit` no aplica a esta versión del paquete, o la fecha queda fuera del rango cubierto por `reconstruct_imputation_markers`) — nunca se infiere un estado por defecto optimista.
3. **Procedencia:** `estado` se deriva exclusivamente de `reconstruct_imputation_markers` sobre el dataset ya incluido y verificado por hash en el paquete (`dataset/*.parquet`), nunca de una nueva imputación ad hoc en el endpoint ni de un cálculo en tiempo de request sobre datos no empaquetados. Si `ImputationSourceDriftError` se dispara (código fuente de imputación cambiado sin actualizar el hash verificado), la fila debe quedar en `no_determinado` para todas las fechas afectadas, nunca fallar silenciosamente ni devolver un valor sin marcar.
4. **Comportamiento cuando no puede determinarse:** nunca omitir el campo (eso es exactamente lo que RH-08 prohíbe) y nunca sustituir por `medida` u otro valor optimista por defecto; el valor explícito es siempre `no_determinado`, con la misma garantía de "nunca fabricar observaciones" ya aplicada en `link_observation`.
5. **Compatibilidad:** campo aditivo en un modelo Pydantic (`ReplayHistoryRow`) — no rompe consumidores existentes que ignoren campos nuevos; no cambia `soil_moisture` ni el contrato de `medicion_original` ya existente.
6. **Corregir además** `openspec/changes/add-causal-historical-replay/traceability.md` para que RH-05/RH-08 dejen de marcarse "[implementada]" sin salvedad mientras esta brecha exista — reflejar el estado real ("parcialmente implementada: cubre `medicion_original`, pendiente en `/replay/history`") hasta que la Corrección 5 (si se aprueba) la cierre.

**Restricciones (se mantienen):** esta propuesta NO debe implementarse todavía. No se autoriza a Claude Code a decidir unilateralmente "extender vs. acotar la spec" ni a tocar `schemas_replay.py`/`history_view.py`/`replay.py` para esto sin aprobación explícita de quien tiene autoridad sobre la spec — eso sería tomar una decisión de alcance/arquitectura sin la advertencia explícita que exige `AGENTS.md`. Si se aprueba, la implementación (con pruebas de aceptación análogas a las de las Correcciones 2/3) debe encargarse por separado, como Corrección 5 de un encargo posterior.

---

## Explícitamente fuera de este encargo

- Integración del ensamble v4 con backend/UI (O-01).
- Categoría "posible alerta" (O-02).
- Extensión de `/replay/history` con estado por fila medida/imputada/no-determinado (O-03) — **ya no se clasifica como mejora opcional diferida**; ver Ítem 5 (D-06), que ahora incluye una propuesta mínima concreta pero sigue requiriendo aprobación normativa explícita antes de convertirse en tarea de implementación. No implementar esa propuesta sin esa aprobación.
- Endurecimiento transaccional/idempotencia por request más allá del lock mínimo de las Correcciones 2 y 3 (O-04).
- Puente de reviews v2 hacia recalibración (O-05).
- Cualquier chequeo de coherencia runtime adicional entre `model.joblib` y `calibrator.joblib` en bundles v2 (mencionado como limitación en F-03, no como defecto confirmado).
- Cualquier cambio a la lógica de verificación de `package_loader.py::_verify_file_integrity`/`_sha256_of` (normalizar finales de línea antes de hashear, o cualquier otra forma de aceptar bytes distintos de los committeados) — explícitamente excluido de la Corrección 4, que resuelve F-06/F-07 únicamente a nivel de `.gitattributes`/normalización del working tree, nunca debilitando la verificación.
- Caso `target_timestamp=NaT` en el feedback legacy (F-09) — sigue sin comprobación dirigida, no es un hallazgo confirmado.
