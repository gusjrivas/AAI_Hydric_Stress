# Contrato disponible para la integración de UI del ensamble (Hito 2)

**Estado:** documenta el contrato **realmente disponible y verificado** hasta esta fecha — no una propuesta de diseño de pantallas. No declara validación científica ni utilidad agronómica demostrada; ver limitaciones en la sección 8.

## 0. Origen

- Contrato técnico del ensamble (Hito 1): PR #217, `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`.
- Ejecución real (Hito 2): PR #218 (ejecutor), PR #219 (`docs/design/ensemble-real-execution-report-2026-09-26.md`, SHA `67eed9d`).
- Recorrido histórico real: `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md`.
- Procedencia externa (esta rama): soporte de `external_reanalysis` end-to-end.

## 1. Rutas y campos que consumirá la UI

Todas bajo el prefijo `/api/v2`, backend FastAPI ya existente (`backend/app/routers/producer_v2.py`), sin rutas nuevas:

| Ruta | Método | Uso previsto en UI |
| --- | --- | --- |
| `/sensors/{sensor_id}/readings?days=N&end=<date>` | GET | Observaciones reveladas hasta la fecha simulada del reloj. |
| `/sensors/{sensor_id}/forecasts?target_from&target_to&horizon_days` | GET | Listado de pronósticos ya persistidos (nunca recalcula). |
| `/sensors/{sensor_id}/forecasts/{forecast_id}` | GET | Detalle de un pronóstico individual, incluido `ensemble`. |
| `/sensors/{sensor_id}/forecasts` | POST | Emisión (idempotente vía `Idempotency-Key`) — en el recorrido histórico, ya ejecutada una vez por día; la UI solo necesita leer, no volver a emitir. |
| `/sensors/{sensor_id}/forecasts/{forecast_id}/reviews` | POST | Feedback (confirmar/rechazar) sobre la decisión combinada. |

Campos relevantes de `ForecastResponse`/`AvailableForecastSlot` (`backend/app/schemas_v2.py`) que la UI debe consumir sin reinterpretar:

- `alert: bool` — decisión binaria de nivel superior, siempre igual a `ensemble.combined_alert` cuando hay ensamble (verificado, sección 4).
- `ensemble.combined_probability`, `ensemble.combined_alert`, `ensemble.positive_votes`, `ensemble.agreement_category` — **conceptos separados, nunca conflacionados**: la UI no debe derivar la alerta de la categoría de votos ni viceversa.
- `ensemble.components[].{family, score, alert, model_reference, calibrated_through}` — detalle por familia, siempre 3.
- `ensemble.weights` — pesos uniformes 1/3 (política `ensemble_agreement_v1`).
- `score_kind: "ensemble_mean_of_calibrated_components"`, `display_probability: null`, `probability_status: "not_qualified"`, `probability_reason_code: "incompatible_assessment"` — **la UI nunca debe mostrar un porcentaje de probabilidad** para el ensamble; solo la decisión binaria y el detalle de votos.
- `ReadingRow.origin` / `ReadingsResponse.provenance` — ver sección 2.

## 2. Origen externo y etiqueta prevista

Nuevo valor reconocido de extremo a extremo (almacenamiento → esquema → HTTP → tipo de frontend), retrocompatible:

- Valor crudo persistido en la columna `origen`: `external_reanalysis_era5_nasa_power` (`src/data_ingestion/history.py::EXTERNAL_REANALYSIS_RAW_VALUE`).
- Valor clasificado (`_origin`) y expuesto por la API: `"external_reanalysis"`.
- **Etiqueta visible prevista (frontend, `readingsApi.ts`):** *"Datos externos de ERA5-Land y NASA POWER"* — nunca "Fuente real" (no es un sensor físico propio) ni "Simulado" (no es sintético).
- `real`/`sintetico`/`synthetic`/`unknown` siguen funcionando exactamente igual que antes; cualquier valor no reconocido sigue siendo `unknown`. Reducción por lote (`provenance`) sin cambios: un lote con orígenes mixtos sigue reduciendo a `"mixed"`.
- Pruebas: `tests/test_history.py` (persistencia), `backend/tests/test_pergamino_ensemble_historical_walkthrough.py` (respuesta HTTP).

## 3. Fechas disponibles y límites del reloj

- Ventana real ya verificada: **2023-06-13 a 2023-06-17** (recorrido histórico), más el punto único **2023-06-15** (ejecución real original). Cualquier otro día de 2023 requeriría repetir la preparación (sección 5) — no está persistido hoy.
- Primera fecha admisible de inferencia para los 9 componentes reales: **2022-12-31** (`calibrated_through`; `predict_operational_bundle` rechaza estrictamente antes de esa fecha).
- El reloj de **lectura** (`GET .../readings?end=`) puede moverse a cualquier fecha ≤ la última observación persistida en el snapshot del sensor — nunca revela una fila posterior a `end` (verificado).
- El reloj de **pronóstico** no es un parámetro de consulta: cada día ya "vivido" requiere su propia emisión POST (ya hecha, una vez, para los 5+1 días de arriba); mover el reloj hacia un día ya emitido devuelve el resultado ya persistido, nunca reejecuta modelos (verificado, idempotencia + hashes de archivo sin cambios).

## 4. Resultados almacenados y observaciones revelables

- 9 modelos + 9 calibradores reales, inmutables, con procedencia documentada (`docs/design/ensemble-real-execution-report-2026-09-26.md`).
- Por cada uno de los 5 días de la ventana: 3 pronósticos persistidos (+1/+2/+3), cada uno con su `forecast_id` propio, disponibles vía `GET .../forecasts/{forecast_id}` o el listado.
- Repetir la emisión de un día ya emitido (`POST` con la misma `Idempotency-Key`) devuelve la respuesta original exacta — verificado para los 5 días.
- Observaciones: reveladas únicamente hasta la fecha `end` solicitada; dato original (`origin`) y procedencia agregada (`provenance`) se conservan en cada fila/respuesta.

## 5. Semántica de alertas, votos y feedback

- `alert` (nivel superior) y `ensemble.combined_alert` son **la misma decisión binaria**, siempre coherentes — la UI puede mostrar cualquiera de los dos indistintamente, nunca debe mostrarlos como si pudieran discrepar.
- `ensemble.agreement_category` (`alerta_por_unanimidad` / `posible_alerta_acuerdo_parcial` / `sin_alerta_por_mayoria_con_discrepancia` / `sin_alerta_por_unanimidad`) es información **adicional** sobre el grado de acuerdo entre las 3 familias — nunca sustituye ni reinterpreta la decisión combinada.
- Feedback (`POST .../reviews`, `action: confirm|reject`): el `observed_label` persistido se deriva de la **decisión combinada** (`alert`/`combined_alert`), nunca de la categoría de votos — verificado directamente.
- El feedback histórico (recorrido de 2023) **nunca** recalibra ni modifica los 9 modelos/calibradores — verificado por hash de archivo sin cambios antes/después de registrar una revisión.
- Cualquier registro de feedback usado únicamente para verificar el flujo debe marcarse explícitamente en `comment` como prueba técnica (p. ej. `"PRUEBA TECNICA..."`) — nunca presentado como opinión real de un productor o experto. La UI de demostración deberá exhibir esa marca si llega a mostrar el comentario.

## 6. Configuración para acceder a los bundles y datos persistentes

- `PRODUCER_V2_ENABLED=true` (feature flag; sin esto la ruta responde 404).
- `PRODUCER_BUNDLE_ROOT=<ruta>` (por defecto `<data_dir>/operational_bundles`; para el ensamble real: `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z`, fuera del repositorio).
- El directorio de datos del sensor (`get_dataset_data_dir`, overrideable) debe apuntar a un espacio de demostración separado del `data/` real del proyecto — nunca compartido con `replay_packages/` ni con el paquete `base-seed4` custodiado.
- `sensor_id` de demostración: `pergamino-ensemble-demo` (nunca un prefijo `demo-`, que activa el candado legado de `is_demo_reserved`).
- El sistema `historical_replay` (`HISTORICAL_REPLAY_ENABLED`, `HISTORICAL_REPLAY_PACKAGE_DIR`) es **independiente** y no interviene en este contrato — el recorrido histórico del ensamble usa la API v2 operativa, no `historical_replay`.

## 7. Entorno requerido para cargar los artefactos

Igual al usado para generar los bundles reales (`docs/design/ensemble-real-execution-report-2026-09-26.md`, sección 3): Python 3.13.14, `scikit-learn 1.9.0`, `pandas 2.3.3`, `numpy 2.5.1`, `pyarrow 19.0.1`, `joblib 1.6.0` — `load_operational_bundle` exige igualdad exacta de `capture_environment()` entre el entorno que generó el bundle y el que lo carga; un backend corriendo con otras versiones de estas dependencias rechazará los bundles reales (no los sintéticos de test, que se generan y cargan en el mismo proceso).

## 8. Limitaciones — no declarar

- **No** hay validación científica confirmatoria de HU7/HU8 en ningún artefacto de este contrato.
- **No** hay utilidad agronómica demostrada.
- Los resultados de los 5 días de la ventana **no se fuerzan a diferir** entre familias ni horizontes: si las 3 familias coinciden (como ocurrió en la ventana verificada — las 15 combinaciones día×horizonte resultaron `sin_alerta_por_unanimidad`), la UI debe mostrar exactamente eso, nunca inventar un desacuerdo.
- El recorrido cubre 5 días, no la totalidad de 2023; extenderlo requiere repetir la preparación (sección 3) sobre los mismos 9 bundles, sin reentrenar.
