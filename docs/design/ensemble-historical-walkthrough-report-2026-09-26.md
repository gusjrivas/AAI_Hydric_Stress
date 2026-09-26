# Reporte: recorrido histórico real sobre el ensamble ya generado (Hito 2)

**Estado:** verificación real completada, sin entrenar, recalibrar ni tocar los contratos/hashes/entorno de los 9 modelos y 9 calibradores producidos en la ejecución real anterior (`docs/design/ensemble-real-execution-report-2026-09-26.md`, SHA `67eed9d`).

## 0. Alcance

Este recorrido reutiliza exclusivamente los bundles reales ya existentes en `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z\`. No es un segundo sistema de reproducción: **reutiliza el propio mecanismo de idempotencia/inmutabilidad de la API v2 operativa** (`OperationalRepository.emit_snapshot`/`record_batch`), ya verificado en la ejecución real anterior. El sistema `historical_replay`/`replay_packages/` existente es arquitectónicamente incompatible con el contrato del ensamble (contrato de un solo escalar `y_pred`/`y_true`, sin `alert`/`ensemble`/votos — ver sección 3 de este documento) y **no se modifica ni se usa** aquí; construir un adaptador equivalente exigiría un rediseño de esquema, no un "cambio mínimo", así que se descarta explícitamente esa vía.

## 1. Verificación previa (antes de consultar cualquier predicción)

- Hash de los 27 archivos reales (9 `model.joblib` + 9 `calibrator.joblib` + 9 `contract.json`) verificado contra `run_manifest.json` antes de usarlos: **sin cambios**.
- Ventana registrada de antemano: **2023-06-13 a 2023-06-17** (5 días consecutivos), centrada en 2023-06-15 (la fecha usada en la verificación real anterior) — elegida únicamente por disponibilidad de entradas/observaciones (lookback completo, lejos de ambos bordes de 2023), nunca por obtener alertas, desacuerdos o resultados favorables.

## 2. Preparación de predicciones (una emisión real por día, con los bundles existentes)

Para cada uno de los 5 días, una entrada real (Pergamino, recortada causalmente hasta ese día) se envió a `POST /api/v2/sensors/pergamino-ensemble-demo/forecasts` con una `Idempotency-Key` propia por día. Resultado — los 5 días, los 3 horizontes:

| Día emisión | `provenance` | `as_of_date` | +1 objetivo | +2 objetivo | +3 objetivo |
| --- | --- | --- | --- | --- | --- |
| 2023-06-13 | `external_reanalysis` | 2023-06-13 | 2023-06-14 | 2023-06-15 | 2023-06-16 |
| 2023-06-14 | `external_reanalysis` | 2023-06-14 | 2023-06-15 | 2023-06-16 | 2023-06-17 |
| 2023-06-15 | `external_reanalysis` | 2023-06-15 | 2023-06-16 | 2023-06-17 | 2023-06-18 |
| 2023-06-16 | `external_reanalysis` | 2023-06-16 | 2023-06-17 | 2023-06-18 | 2023-06-19 |
| 2023-06-17 | `external_reanalysis` | 2023-06-17 | 2023-06-18 | 2023-06-19 | 2023-06-20 |

Las 15 fechas objetivo (5 días × 3 horizontes) quedan dentro de 2023. Los 15 `slots` resultaron `status=available`, `alert == ensemble.combined_alert` (coherente), `agreement_category=sin_alerta_por_unanimidad`, `display_probability=null`, `probability_status=not_qualified` — nunca se declaró una probabilidad de presentación habilitada.

## 3. Mover el reloj: predicciones almacenadas, nunca reejecutadas

Cada día se emitió **dos veces** con la misma `Idempotency-Key`: la segunda respuesta fue **idéntica** a la primera (código `201` ambas veces), y los hashes de los 27 archivos de los bundles reales se verificaron sin cambios **antes y después** de todo el recorrido (incluida la emisión de los 5 días y el feedback de la sección 5). Ningún modelo se reajustó para "mover el reloj".

## 4. Revelación progresiva de observaciones

`GET /api/v2/sensors/pergamino-ensemble-demo/readings?days=10&end=<día>` para cada día de la ventana: la fecha máxima de fila revelada nunca superó `end`, y aumentó monótonamente al avanzar el reloj día por día. `origin`/`provenance` de cada fila: `external_reanalysis` — nunca `real` (no es un sensor físico propio) ni `sintetico`.

## 5. Feedback en contexto histórico

Se registró una revisión de prueba técnica sobre el pronóstico +1 del primer día (2023-06-13), explícitamente marcada en el campo `comment` como prueba técnica ("no es feedback real de un productor ni de un experto"). El `observed_label` persistido coincidió con la **decisión combinada** (`ensemble.combined_alert`), nunca con la categoría de votos — verificado directamente contra el documento persistido. Los hashes de los 27 archivos de los bundles reales no cambiaron tras esta revisión: el feedback histórico no recalibra ni modifica modelos.

## 6. Espacio de demostración

Datos y bundles: `bundle_root` reutilizado sin modificar (`pergamino-ensemble-demo-2026-09-26T034114Z`); datos/estado de esta corrida en un directorio nuevo y separado, `pergamino-walkthrough-2023-06-13_17` (+ `-logs`), fuera del repositorio. No se tocó `replay_packages/`, `base-seed4` ni ningún resultado histórico custodiado.

## 7. Limitaciones

- Recorrido de 5 días, no de todo 2023.
- No constituye validación científica ni utilidad agronómica demostrada — es una demostración técnica retrospectiva, igual que la ejecución real que la origina.
- El espacio de esta corrida (`pergamino-walkthrough-2023-06-13_17`) no se respaldó en un disco separado (a diferencia del `bundle_root` real, que sí tiene respaldo verificado) — sus predicciones son reproducibles determinísticamente a partir de los bundles reales ya respaldados, así que no se consideró evidencia primaria irremplazable.

## 8. Trazabilidad

Reporte completo (JSON) de esta corrida: `pergamino-walkthrough-2023-06-13_17-logs/walkthrough_report.json` (fuera del repositorio). Prueba equivalente, con datos sintéticos, para CI: `backend/tests/test_pergamino_ensemble_historical_walkthrough.py`.
