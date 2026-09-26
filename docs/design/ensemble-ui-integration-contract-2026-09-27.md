# Contrato disponible para la integración de UI del ensamble (Hito 2)

**Estado:** documenta el contrato **realmente disponible y verificado** hasta esta fecha, incluida la UI de productor ya implementada sobre él. No declara validación científica ni utilidad agronómica demostrada; ver limitaciones en la sección 9. **Revisión 2 (corrige la Revisión 1):** la Revisión 1 usaba la idempotencia de `POST .../forecasts` como si fuera el mecanismo de reproducción histórica — no lo es (una idempotencia de emisión no es un contexto de reproducción: no separa preparación de navegación, no desambigua por fecha de emisión frente a `POST`s futuros, y evalúa "reviewable" contra el reloj real). Esa revisión agregó las rutas de solo lectura `/historical/...` para resolver eso. **Revisión 3:** implementa la UI de productor del ensamble (pantallas Mi cultivo / Historial / Datos, sin Ajustes) sobre esas rutas, y agrega un parámetro `revealed_through` a `GET .../historical/{as_of_date}/forecasts` para que la UI pueda separar la emisión seleccionada del punto hasta el que avanzó el recorrido sin simular esa elegibilidad del lado del cliente — ver sección 8b. **Revisión 4:** la Revisión 3 emitía una tanda operativa automáticamente al montar "Mi cultivo" (una idempotencia de emisión sigue siendo una escritura, no una consulta), compartía un único contexto de revisión entre el flujo operativo y el histórico, no invalidaba respuestas obsoletas al vaciar la selección, calculaba `last_reading_date`/`data_age_days` sobre todo el archivo en vez de sobre lo admisible por el reloj histórico, y guardaba el feedback histórico en el mismo documento que las revisiones operativas. Corregido — ver sección 8c. **Revisión 5 (esta, corrige la Revisión 4):** `reviewed()` en `HistoricalWalkthrough.tsx` solo comparaba `forecast_id`, sin distinguir el reloj efectivo del recorrido — si cambiaba `revealed_through` conservando la misma emisión, una respuesta tardía de una revisión iniciada bajo un reloj anterior podía sobrescribir la tarjeta con el `reviewable` de ese reloj viejo. Corregido vinculando cada operación a la generación del contexto vigente (sensor + emisión + reloj efectivo) — ver sección 8e.

## 0. Origen

- Contrato técnico del ensamble (Hito 1): PR #217, `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`.
- Ejecución real (Hito 2): PR #218 (ejecutor), PR #219 (`docs/design/ensemble-real-execution-report-2026-09-26.md`, SHA `67eed9d`).
- Recorrido histórico real (con las rutas de reproducción de esta revisión): `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md`.
- Procedencia externa: soporte de `external_reanalysis` end-to-end.

## 1. Rutas y campos que consumirá la UI

Todas bajo el prefijo `/api/v2` (`backend/app/routers/producer_v2.py`).

**Preparación (ya ejecutada; la UI de reproducción no la necesita):**

| Ruta | Método | Uso |
| --- | --- | --- |
| `/sensors/{sensor_id}/forecasts` | POST | Emisión idempotente. Ya ejecutada una vez por día para la ventana verificada (sección 3). **Nunca** se usa para "navegar" el recorrido histórico. |

**Contexto operativo (en vivo, reloj real — sin cambios, no forma parte de este contrato de demostración):**

| Ruta | Método |
| --- | --- |
| `/sensors/{sensor_id}/readings?days=N&end=<date>` | GET |
| `/sensors/{sensor_id}/forecasts?...` / `/forecasts/{forecast_id}` | GET |
| `/sensors/{sensor_id}/forecasts/{forecast_id}/reviews` | POST |

**Contexto histórico (nuevo, esta revisión — reproducción real para la UI):**

| Ruta | Método | Uso previsto en UI |
| --- | --- | --- |
| `/sensors/{sensor_id}/historical/{as_of_date}/readings?days=N` | GET | Observaciones reveladas exactamente hasta `as_of_date` — nunca un `end` distinto; nunca dispara inferencia. |
| `/sensors/{sensor_id}/historical/{as_of_date}/forecasts?revealed_through=<date>` | GET | Búsqueda **inequívoca por fecha de emisión** (nunca `target_date`, nunca "la más reciente"). `404 batch_not_prepared` si esa fecha nunca se emitió — nunca infiere. `revealed_through` (opcional, ≥ `as_of_date`; si no, `422 invalid_reveal_window`) avanza solo el reloj usado para `review.reviewable`/`review_open_at`, sin cambiar qué emisión se seleccionó. |
| `/sensors/{sensor_id}/historical/{as_of_date}/forecasts/{forecast_id}/reviews` | POST | Feedback gateado por el **reloj simulado** (`as_of_date`, fin de ese día), nunca por el reloj real. Rechaza (`404 forecast_not_visible_at_this_historical_date`) revisar una emisión posterior a `as_of_date`. |

Campos relevantes de `ForecastResponse`/`AvailableForecastSlot` que la UI debe consumir sin reinterpretar:

- `alert: bool` — decisión binaria de nivel superior, siempre igual a `ensemble.combined_alert` cuando hay ensamble (verificado, sección 5).
- `ensemble.combined_probability`, `ensemble.combined_alert`, `ensemble.positive_votes`, `ensemble.agreement_category` — **conceptos separados, nunca conflacionados**.
- `ensemble.components[].{family, score, alert, model_reference, calibrated_through}` — detalle por familia, siempre 3.
- `ensemble.weights` — pesos uniformes 1/3 (política `ensemble_agreement_v1`).
- `score_kind`, `display_probability: null`, `probability_status: "not_qualified"` — **la UI nunca debe mostrar un porcentaje de probabilidad** para el ensamble.
- `ReadingRow.origin` / `ReadingsResponse.provenance` — ver sección 2.

## 2. Origen externo y etiqueta prevista

Sin cambios respecto de la revisión anterior — reconocido de extremo a extremo, retrocompatible:

- Valor crudo: `external_reanalysis_era5_nasa_power` (`src/data_ingestion/history.py::EXTERNAL_REANALYSIS_RAW_VALUE`).
- Valor clasificado/expuesto: `"external_reanalysis"`.
- Etiqueta visible prevista: *"Datos externos de ERA5-Land y NASA POWER"*.
- `real`/`sintetico`/`synthetic`/`unknown` sin cambios; no reconocido → `unknown`; lote mixto → `mixed`.

## 3. Fechas disponibles y límites del reloj — reloj de lectura y de pronóstico, separados

- Ventana real preparada: **2023-06-13 a 2023-06-17** (una emisión POST por día, ya ejecutada), más el punto único **2023-06-15** (verificación real original). Cualquier otro día de 2023 requeriría repetir la preparación — no está persistido hoy.
- Primera fecha admisible de inferencia para los 9 componentes reales: **2022-12-31** (`calibrated_through`).
- **Reloj de lectura** (`GET .../historical/{as_of_date}/readings`): revela observaciones exactamente hasta `as_of_date` — nunca una fila posterior. `as_of_date` fija también la "hoy" simulada para la antigüedad presentada (`server_today=as_of_date`, no el reloj real).
- **Reloj de pronóstico** (`GET .../historical/{as_of_date}/forecasts`): búsqueda determinística por fecha de emisión — la misma consulta para la misma `as_of_date` devuelve exactamente el mismo resultado sin importar qué otras fechas se hayan emitido o consultado entretanto (navegación A→B→A verificada, `backend/tests/test_pergamino_ensemble_historical_reproduction.py`). Nunca ejecuta modelos — verificado bloqueando la función de inferencia y confirmando que nunca se invoca durante la navegación (no solo "los hashes no cambiaron", que no prueba ausencia de inferencia).
- Una `as_of_date` nunca preparada responde `404 batch_not_prepared` — nunca una respuesta vacía ambigua ni un error genérico.

## 4. Resultados almacenados y observaciones revelables

- 9 modelos + 9 calibradores reales, inmutables. Verificado sin cambios de hash **antes y después** de toda la navegación histórica (incluido el feedback de la sección 5).
- Por cada uno de los 5 días preparados: 3 pronósticos persistidos (+1/+2/+3), cada uno con `forecast_id` propio.
- Revelación extendida hasta **2023-06-20** verificada: permite contrastar el objetivo +3 de la emisión del 2023-06-17 (target 2023-06-20) contra la observación ya existente de esa fecha — comparación por `target_date`, unidad y umbral del evento (`event_threshold`), sin generar ninguna predicción nueva y sin exponer ninguna observación posterior a 2023-06-20.

## 5. Semántica de alertas, votos y feedback histórico

- `alert` y `ensemble.combined_alert` son la misma decisión binaria, siempre coherentes.
- `ensemble.agreement_category` es información adicional sobre el grado de acuerdo — nunca sustituye la decisión combinada.
- Feedback histórico (`POST .../historical/{as_of_date}/forecasts/{forecast_id}/reviews`):
  - `observed_label` se deriva de la decisión combinada, nunca de la categoría de votos.
  - **Gateado por el reloj simulado, no por el real:** una revisión cuyo `target_date` el reloj simulado todavía no alcanzó responde `409 review_not_open` — verificado explícitamente que el reloj *real* (2026+) no habilita esto de forma indebida.
  - **Nunca expone una emisión posterior como visible desde una fecha anterior:** revisar el `forecast_id` de una emisión de `B` mientras se navega `A` (con `A < B`) responde `404 forecast_not_visible_at_this_historical_date`.
  - **Nunca recalibra ni modifica los 9 bundles** — verificado por hash de archivo, y estructuralmente aislado: el directorio de datos de esta demostración (`data_dir` del sensor) es explícito y distinto del `DEFAULT_DATA_DIR` operativo; ningún proceso de reentrenamiento/recalibración de este repositorio escanea directorios — todos requieren un `sensor_id`+`data_dir` explícitos.
  - Cualquier registro usado solo para verificar el flujo debe marcarse en `comment` como prueba técnica — esa marca es **complementaria**, nunca el único mecanismo de aislamiento (el aislamiento real es estructural, punto anterior).

## 6. Configuración para acceder a los bundles y datos persistentes

- `PRODUCER_V2_ENABLED=true`.
- `PRODUCER_BUNDLE_ROOT=<ruta>` — para el ensamble real: `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z`, fuera del repositorio.
- El directorio de datos del sensor debe ser un espacio de demostración separado del `data/` real — nunca compartido con `replay_packages/` ni `base-seed4`.
- `sensor_id` de demostración: `pergamino-ensemble-demo` (nunca prefijo `demo-`).
- `historical_replay` (`HISTORICAL_REPLAY_ENABLED`) es **independiente** y no interviene aquí — investigado y descartado como mecanismo de reproducción (sección 8): su contrato es de un solo escalar `y_pred`/`y_true`, sin `alert`/`ensemble`/votos, y adaptarlo exigiría un rediseño de esquema, no un cambio mínimo.

## 7. Entorno requerido para cargar los artefactos

Sin cambios: Python 3.13.14, `scikit-learn 1.9.0`, `pandas 2.3.3`, `numpy 2.5.1`, `pyarrow 19.0.1`, `joblib 1.6.0` — `load_operational_bundle` exige igualdad exacta de `capture_environment()`.

## 8. Qué cambió en esta revisión (implementado vs. pendiente)

**Implementado y verificado en esta revisión** (`backend/tests/test_pergamino_ensemble_historical_reproduction.py`, 7 pruebas; producción: `OperationalRepository.get_batch_by_as_of_date` + 3 rutas nuevas `/historical/...` en `producer_v2.py`):

1. Separación preparación/reproducción: la reproducción nunca hace `POST` de emisión ni modifica el snapshot; verificado bloqueando la función de inferencia durante la navegación (no solo por hashes).
2. Selección inequívoca por `as_of_date` (nunca `target_date`); navegación A→B→A verificada byte a byte.
3. Reloj simulado alineado: observaciones (`server_today=as_of_date`) y apertura de revisión (`review_open_at` contra el reloj simulado, no el real) — verificado que el reloj real no autoriza indebidamente. El contexto operativo (rutas sin `/historical/`) no se tocó: sigue usando el reloj real.
4. Aislamiento del feedback histórico verificado estructuralmente (directorio explícito, no auto-descubierto), no solo por el comentario "prueba técnica".
5. Revelación hasta 2023-06-20 verificada, contrastando el objetivo +3 del 2023-06-17 contra una observación ya existente, sin generar predicciones nuevas.

## 8b. UI de productor del ensamble (Revisión 3)

Implementada sobre la fachada v2 existente, dentro de `frontend/src/features/producer/`, como pestañas internas de la
pantalla "Mi cultivo" (`ProducerTabs`) — nunca como rutas nuevas del `App.tsx` general, que sigue sirviendo el flujo
de un solo modelo (`prediccion`/`calidad`/`linaje`) sin cambios:

- **Mi cultivo** (`ProducerView` + `EmissionPanel`): consulta automática (idempotente, sin repetir inferencia) al
  entrar; procedencia (`provenance`); 3 tarjetas de horizonte con `combined_alert` y acuerdo entre modelos
  (`ForecastCard`, sección de acuerdo nueva); mensaje "No hay información suficiente..." cuando los 3 horizontes
  están indisponibles; gráfico y tabla de mediciones (`ProducerHistoryPanel`, sin cambios).
- **Historial** (`ProducerHistoryScreen`): lista persistida de emisiones con sus 3 horizontes y revisión
  (`ForecastsSection`, sin cambios) más `HistoricalWalkthrough`, que separa explícitamente la **emisión
  seleccionada** (`as_of_date`, vía `/historical/{as_of_date}/forecasts`) del **recorrido avanzado hasta**
  (`revealed_through`, vía el mismo parámetro nuevo y vía `/historical/{revealed_through}/readings`), con revisión
  histórica (`submitHistoricalReview`) gateada por ese reloj del recorrido y no por el de la emisión. Descarta
  respuestas obsoletas por número de secuencia (no solo por clave), cubriendo A→B→A.
- **Datos** (`ProducerDataScreen`): variables, unidad, procedencia, cobertura por variable (`variable_coverage`) y
  anomalías por día (`quality_flags`) tal como las emite el backend — nunca se inventa una anomalía sin ese respaldo,
  y un hueco nunca se muestra como cero.
- **Sin pestaña "Ajustes":** este ensamble no tiene una capacidad real de ajustar los próximos pronósticos a partir
  de observaciones. La capacidad existente de ese tipo (`RecalibrationPanel`, ruta `linaje`) pertenece al flujo de un
  solo modelo y se conserva sin cambios en su propia ruta, sin exponerse en la navegación del productor del ensamble.

Pruebas dirigidas nuevas (frontend, `vitest`): agregado del campo `ensemble` y su presentación separada de la alerta
combinada; `revealed_through` reenviado como parámetro propio; descarte de respuestas obsoletas en A→B→A por
secuencia; revisión histórica dirigida al reloj del recorrido, no al de la emisión; anomalías mostradas solo cuando
`quality_flags` las respalda. Backend: 2 pruebas dirigidas nuevas para `revealed_through`
(`test_pergamino_ensemble_historical_reproduction.py`), además de las 7 ya existentes.

**Pendiente (fuera de alcance de esta revisión, no implementado):**

- Un mecanismo de "recorrido continuo" que muestre 2023 completo — solo la ventana 2023-06-13..17 (+ el punto 2023-06-15) está preparada; la UI depende de que el productor conozca esas fechas (errores `batch_not_prepared` para el resto).
- Cualquier extensión de `historical_replay/replay_packages/` — deliberadamente descartada, no un pendiente a resolver ahí.
- Autenticación/autorización de quién puede navegar el contexto histórico — las rutas `/historical/...` heredan únicamente el gate `PRODUCER_V2_ENABLED` existente, sin un control de acceso propio adicional.

## 8c. Correcciones de PR #221 (Revisión 4)

1. **Sin emisiones automáticas durante la navegación.** `EmissionPanel` ya no llama a `emitForecasts()` al montarse ni al cambiar de pestaña/sensor — solo ante un clic explícito ("Consultar próximos tres días"). Cambiar de sensor limpia el lote anterior sin emitir nada. El recorrido histórico nunca usó ni usa `POST` de emisión (sección 3). Verificado: `EmissionPanel.test.tsx` (ningún llamado a `emitForecasts` tras montar/cambiar sensor sin clic) y `ProducerView.test.tsx` (entrar a "Mi cultivo", cambiar a Historial/Datos y volver, sin clic, nunca invoca `emitForecasts`).
2. **Contextos operativo e histórico separados de verdad, no solo por componentes.** `ProducerHistoryScreen` ya no envuelve `ForecastsSection` (operativo) y `HistoricalWalkthrough` (histórico) en el mismo `ForecastReviewsProvider`: cada uno tiene su propio alcance, así que una tarjeta histórica nunca puede terminar mostrando una revisión operativa compartida por `forecast_id` (o viceversa) solo porque llegó con una revisión igual o mayor. En el backend, el feedback histórico se persiste en `HistoricalReviewStore` (`src/human_feedback/historical_review_store.py`), un documento propio bajo `historical_feedback/<sensor_id>.json` — nunca `ui_metadata/operational_v2__<sensor_id>.json` de `OperationalRepository`. `get_historical_forecasts` reemplaza el campo `review` de cada slot disponible por el estado de ese store aislado, nunca por el embebido en la tanda operativa. Verificado: `test_operational_review_never_changes_a_historical_cards_review_state` (backend) confirma una revisión real por la ruta en vivo sin afectar la tarjeta histórica del mismo `forecast_id`, y viceversa; `ProducerHistoryScreen.test.tsx` (frontend) confirma lo mismo a nivel de React.
3. **Respuestas obsoletas invalidadas en todos los casos, no solo A→B→A.** `HistoricalWalkthrough` ahora incrementa su contador de secuencia también al vaciar la fecha de emisión (antes solo lo hacía al elegir una fecha, dejando pasar una respuesta tardía de la selección anterior aun con el campo vacío) y resetea ambas fechas al cambiar de sensor. La actualización tras una revisión (`reviewed()`) verifica además que el `forecast_id` todavía pertenezca al lote actualmente mostrado antes de aplicar el parche — cubre navegar a otra emisión mientras una revisión sigue en curso. Verificado con 6 pruebas dirigidas en `HistoricalWalkthrough.test.tsx`: A→B→A, fecha→vacío con respuesta tardía, cambio de sensor con petición en curso, y una revisión que resuelve después de que el usuario ya navegó a otra emisión.
4. **Contrato temporal corregido.** `GET .../historical/{as_of_date}/forecasts` ahora refleja `server_today` con `revealed_through` cuando existe (antes siempre devolvía `as_of_date`, sin importar el parámetro). `query_readings` (`src/data_ingestion/history.py`) calcula `last_reading_date`/`data_age_days` sobre las lecturas admisibles hasta el reloj efectivo (escaneando el archivo completo, no solo la ventana mostrada, porque la última lectura admisible puede ser anterior al inicio de esa ventana) — nunca sobre el archivo completo sin filtrar por el reloj, y nunca clampeando una antigüedad negativa a cero. Un archivo con datos pero ninguno admisible bajo el reloj responde `status: "no_readings"`, coherente con esa ausencia. El comportamiento operativo (sin `end`/`server_today` explícitos) queda preservado porque sigue usando el reloj real sin filtrar nada adicional. Verificado con 2 pruebas unitarias nuevas en `tests/test_history.py` y 3 pruebas de integración nuevas en `test_pergamino_ensemble_historical_reproduction.py`, incluida la regresión exacta pedida: lecturas del 13 y 20/06, consultar al 13/06 nunca devuelve última lectura 20/06 ni antigüedad −7.
5. **Arranque real reproducible, documentado.** `scripts/run_producer_preview_backend.py` + `docs/design/producer-ui-local-preview-2026-09-26.md`: toma `PRODUCER_DATA_DIR`/`PRODUCER_BUNDLE_ROOT` por variable de entorno (nunca hardcodeados), valida que contengan lecturas/emisiones/manifiestos reales antes de arrancar y falla con un diagnóstico concreto si falta algo — nunca sustituye por fixtures. El frontend usa `frontend/.env.development.local` (gitignorado) con `VITE_API_BASE_URL`. Documenta explícitamente que no reemplaza ni se apoya en `docker-compose.producer-preview.yml` (ese flujo, si existe, prepara datos sintéticos) como evidencia del recorrido real.
6. **Verificación en navegador — parcial, ver Revisión 5.** En esta revisión no se pudo conectar un navegador; en la Revisión 5 sí se conectó y se verificó en escritorio real contra el backend levantado con `run_producer_preview_backend.py` (ver sección 8e). Móvil (390px) sigue sin verificarse: `resize_window` no logró achicar la ventana de Chrome en ese entorno.

## 8d. Verificación de la política del ensamble (a pedido, sin cambios de código)

Se verificó — sin modificar nada — qué regla determina `combined_alert`: es **promedio** de las 3 probabilidades comparado contra el umbral (`src/predictive_modeling/ensemble_bundle.py`), nunca mayoría de votos (`positive_votes >= 2`). El esquema HTTP (`backend/app/schemas_v2.py`, `EnsembleDetail.validate_coherence`) impone activamente esta regla de promedio. Puede contradecir `agreement_category` en casos de 2 votos positivos con probabilidades bajas (combinación que muestra "posible alerta, acuerdo parcial" junto con `combined_alert=false`). No se encontró ninguna implementación de mayoría pendiente en otras ramas, worktrees, stashes o diffs sin commitear. No se implementó ni publicó ningún cambio de política — queda documentado como hallazgo, a decidir en un cambio aparte.

## 8e. Corrección de la Revisión 5: generación del contexto en `HistoricalWalkthrough`

`reviewed()` solo comparaba `forecast_id` contra el lote visible, sin distinguir el reloj efectivo del recorrido (`revealed_through`). Si el usuario avanzaba el reloj (p. ej. a 20/06), enviaba una revisión, y retrocedía el reloj sobre la **misma emisión** (p. ej. a 13/06) antes de que la respuesta llegara, esa respuesta tardía podía sobrescribir la tarjeta con el `reviewable` calculado bajo el reloj anterior — comparar solo `forecast_id` (o los valores de las fechas) no distingue este caso, en particular A→B→A sobre `revealed_through` con la misma emisión.

Corrección: `renderGeneration` captura `batchSeq.current` (el mismo contador que ya invalida el lote ante cualquier cambio de sensor, emisión o reloj de recorrido, incluida la selección vacía) en el mismo render que crea `reviewed`/`submitReviewFn`/`refetchFn`. `reviewed()` descarta el resultado si `batchSeq.current` ya no coincide con esa generación — sin revertir nada ya persistido en el backend, solo decide qué se muestra. El mismo punto de entrada cubre tanto una confirmación exitosa como la recuperación tras un conflicto de revisión y un error tardío, porque ambos llegan a través del mismo `onChanged`.

Verificado con 3 pruebas dirigidas nuevas (envío pendiente bajo un reloj → retroceso sobre la misma emisión → respuesta tardía no sobrescribe; A→B→A cambiando solo el reloj de recorrido; error y recuperación de conflicto tardíos de un contexto anterior no alteran el nuevo), más las pruebas existentes de cambio de emisión/sensor/selección vacía (9/9 en el archivo). Verificado también en navegador real contra el backend real: retroceder el reloj de 20/06 a 13/06 sobre la misma emisión bloquea correctamente la posibilidad de reeditar la revisión ya confirmada. No se pudo forzar la condición de carrera exacta contra el backend real (resuelve más rápido que cualquier interacción manual); esa condición queda cubierta por las pruebas con promesas controladas, no por la observación en vivo.

## 9. Limitaciones — no declarar

- **No** hay validación científica confirmatoria de HU7/HU8 en ningún artefacto de este contrato.
- **No** hay utilidad agronómica demostrada.
- Los resultados de la ventana **no se fuerzan a diferir** entre familias ni horizontes: si las 3 familias coinciden (como ocurrió en la ventana verificada), la UI debe mostrar exactamente eso.
- La ventana preparada cubre 5 días (+ 1 punto), no la totalidad de 2023.
