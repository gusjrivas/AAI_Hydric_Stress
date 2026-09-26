# Contrato disponible para la integración de UI del ensamble (Hito 2)

**Estado:** documenta el contrato **realmente disponible y verificado** hasta esta fecha, incluida la UI de productor ya implementada sobre él. No declara validación científica ni utilidad agronómica demostrada; ver limitaciones en la sección 9. **Revisión 2 (corrige la Revisión 1):** la Revisión 1 usaba la idempotencia de `POST .../forecasts` como si fuera el mecanismo de reproducción histórica — no lo es (una idempotencia de emisión no es un contexto de reproducción: no separa preparación de navegación, no desambigua por fecha de emisión frente a `POST`s futuros, y evalúa "reviewable" contra el reloj real). Esa revisión agregó las rutas de solo lectura `/historical/...` para resolver eso. **Revisión 3 (esta):** implementa la UI de productor del ensamble (pantallas Mi cultivo / Historial / Datos, sin Ajustes) sobre esas rutas, y agrega un parámetro `revealed_through` a `GET .../historical/{as_of_date}/forecasts` para que la UI pueda separar la emisión seleccionada del punto hasta el que avanzó el recorrido sin simular esa elegibilidad del lado del cliente — ver sección 8b.

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
- Revisión visual real en navegador (escritorio y móvil): no se realizó en esta revisión por no contar con un navegador disponible en el entorno de ejecución. Verificado en su lugar mediante pruebas de componente (`vitest`) y build de producción (`tsc` + `vite build`); no debe interpretarse como una revisión visual ni una integración end-to-end reales.

## 9. Limitaciones — no declarar

- **No** hay validación científica confirmatoria de HU7/HU8 en ningún artefacto de este contrato.
- **No** hay utilidad agronómica demostrada.
- Los resultados de la ventana **no se fuerzan a diferir** entre familias ni horizontes: si las 3 familias coinciden (como ocurrió en la ventana verificada), la UI debe mostrar exactamente eso.
- La ventana preparada cubre 5 días (+ 1 punto), no la totalidad de 2023.
