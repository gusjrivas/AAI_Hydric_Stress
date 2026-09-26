# Reporte de ejecución real — demostración técnica retrospectiva del ensamble (Hito 2)

**Estado:** ejecución real completada. Esto es una **demostración técnica retrospectiva**, no una nueva validación confirmatoria ni una reparación de la campaña científica `controlled_daily_v4_external_pergamino` (cerrada con `FAIL` de gobernanza, `openspec/scientific-closure/decisions.md` GD-38/GD-40). No modifica, reejecuta ni reabre esa campaña, su ledger, su evidencia histórica ni `replay_packages/`.

## 0. Autorización

Autorizado explícitamente por Gustavo Julián Rivas, responsable del Trabajo Final, el 2026-09-26T03:39:51Z, sobre el código revisado en PR #218 (SHA de cabecera `7b4dc727060d5d825e35e9206a4f7c52367af257`, mergeado como `67eed9d0d3b9657ae43f267e258af549f8c3a9a8`). El alcance autorizado comprendió explícitamente: ajuste nuevo de las tres familias (`logistic_regression`, `random_forest`, `hist_gradient_boosting_classifier`) para +1/+2/+3, calibración sigmoid con partición separada, exportación/carga/inferencia de los bundles, y verificación por la API v2 en un entorno aislado — resolviendo así, con esta autorización, las dos decisiones metodológicas que `docs/design/ensemble-real-enablement-plan.md` (secciones 6.1/6.2) dejaba pendientes del responsable.

## 1. Verificación previa (antes de ejecutar)

- PR #218: `MERGED` el 2026-09-26T03:39:51Z, merge commit `67eed9d0d3b9657ae43f267e258af549f8c3a9a8`.
- CI en el SHA autorizado (`7b4dc72`): `backend-quality` PASS (2m51s), `experiment-v4-container` PASS (8m59s), `frontend-quality` PASS (28s), `python-quality` PASS (14m42s) — los cuatro en verde.
- `origin/main` coincidía exactamente con el merge commit (no había avanzado más).
- Checkout nuevo (rama `feat/ensemble-real-execution-report`) creado directamente desde `67eed9d`; `git diff --stat` contra el head autorizado del PR: vacío (árbol idéntico).
- Identidad de código verificada en el propio checkout: `commit=67eed9d0d3b9657ae43f267e258af549f8c3a9a8`, `dirty=false`.

## 2. Entradas verificadas

| Archivo | Ruta | SHA-256 verificado | Coincide con el autorizado |
| --- | --- | --- | --- |
| ERA5-Land horario | `C:\Repo\AAI_Hydric_Stress_external_data\raw\pergamino_era5land_soil_hourly_2015_2025.csv` | `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` | Sí |
| NASA POWER diario | `C:\Repo\AAI_Hydric_Stress_external_data\raw\pergamino_nasa_power_daily_2015_2025.csv` | `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` | Sí |

## 3. Entorno utilizado

Host Windows de esta sesión (no la imagen Docker `experiment-v4-scientific-closure:latest` de la campaña cerrada, que no contiene el ejecutor nuevo): Python `3.13.14`, `scikit-learn 1.9.0`, `pandas 2.3.3`, `numpy 2.5.1`, `pyarrow 19.0.1`, `joblib 1.6.0`. Registrado tal cual, sin falsear metadatos, tanto en el registro de ejecución (`execution_record.json`) como dentro de cada `bundle.json` real (`capture_environment()`, sin modificar).

## 4. Comando ejecutado (una sola vez)

```
PYTHONPATH=C:\Repo\AAI_Hydric_Stress_ensemble_integration\src \
python -m experiment_runner.pergamino_ensemble_demo_runner \
  --era5-csv "C:/Repo/AAI_Hydric_Stress_external_data/raw/pergamino_era5land_soil_hourly_2015_2025.csv" \
  --nasa-power-csv "C:/Repo/AAI_Hydric_Stress_external_data/raw/pergamino_nasa_power_daily_2015_2025.csv" \
  --output-dir "C:/Repo/AAI_Hydric_Stress_ensemble_demo_runtime/pergamino-ensemble-demo-2026-09-26T034114Z" \
  --sensor-id pergamino-ensemble-demo \
  --horizons 1 2 3 \
  --input-mode scientific
```

Directorio de trabajo: `C:\Repo\AAI_Hydric_Stress_ensemble_integration` (checkout de `67eed9d`). Intérprete: `C:\tcnenv\Scripts\python.exe`. Código de salida: `0`. `stderr` vacío. Ningún hiperparámetro, familia, variable, ventana, política ni partición se modificó respecto del código revisado para lograr que la corrida terminara.

## 5. Destinos

- **Artefactos:** `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z\` — directorio nuevo, vacío antes de la corrida, fuera del repositorio y de cualquier ruta de la campaña cerrada (`evidence/A|B|C`, `ledger/`, `openspec/scientific-closure/`).
- **Logs/registro:** `...-logs\` (sibling): `execution_record.json` (registro completo pre/post-ejecución), `stdout.log`, `stderr.log`, `exit_code.log`, `http_verification_report.json`.
- **Respaldo:** copia completa en `D:\AAI_Hydric_Stress_ensemble_demo_backup\` (disco físicamente separado). Verificado con `sha256sum` de cada archivo en ambos árboles: **idéntico byte a byte**.

## 6. Resultado por familia/horizonte

`run_manifest.json` (`status: "completado"`):

- **Frame permitido:** SHA-256 `491cedeebd7e66e78e2a00be256caed628c014b60ea9b51931a09332ca605312`.
- **Umbral físico común (P20, solo sobre entrenamiento 2015-01-01..2021-12-31):** `0.3130583333333333`, idéntico para las 3 familias y los 3 horizontes.
- **9 modelos + 9 calibradores reales**, exportados y con hash de archivo verificado contra `bundle.json["files"]` (coincide en los 27 archivos: 9 `model.joblib` + 9 `calibrator.joblib` + 9 `contract.json`).
- **3 `ensemble_manifest.json`** (uno por horizonte): `policy_version=ensemble_agreement_v1`, pesos uniformes 1/3 verificados.
- **Contratos:** `trained_through=2021-12-31`, `calibrated_through=2022-12-31` en los 9 componentes; `decision_threshold=0.5` en los 9.

### Conteos efectivos — dos conceptos distinguidos (nunca mezclados)

**Purga temporal** (contención de fecha objetivo dentro de la misma partición, ya aplicada dentro de `partition_labeled_horizon` antes de cualquier conteo posterior) — última fecha efectivamente usada:

| Horizonte | Último día de entrenamiento usado | Último día de calibración usado |
| --- | --- | --- |
| +1 | 2021-12-30 | 2022-12-30 |
| +2 | 2021-12-29 | 2022-12-29 |
| +3 | 2021-12-28 | 2022-12-28 |

**Purga por features faltantes** (`*_rows_excluded_by_purge` de `run_manifest.json`, exclusivamente el `dropna` posterior a la purga temporal anterior — nunca el total de la purga temporal):

| Horizonte | `train_rows_used` | `train_rows_excluded_by_purge` | `calibration_rows_used` | `calibration_rows_excluded_by_purge` |
| --- | --- | --- | --- | --- |
| +1 | 2550 | 6 | 364 | 0 |
| +2 | 2549 | 6 | 363 | 0 |
| +3 | 2548 | 6 | 362 | 0 |

Los 6 días excluidos por features faltantes en entrenamiento corresponden al inicio de la ventana de ingesta (2015-01-01 en adelante, sin *lookback* de 7 días todavía disponible) — independiente del horizonte, como se esperaba. Calibración no tuvo purga por features faltantes en ningún horizonte.

## 7. Carga e inferencia real (sin datos sintéticos)

`load_ensemble_bundle`/`predict_ensemble_bundle` (sin modificar) cargaron e infirieron correctamente para los 3 horizontes, sobre el frame real permitido, con `as_of_date=2023-06-15`.

**Regla de selección de la fecha de demostración** (registrada antes de observar cualquier predicción): punto medio del calendario 2023 — lejos del límite de calibración (2022-12-31) y del borde de fin de año, con *lookback* completo de 7 días disponible. Nunca elegida por convenir a un resultado.

Fechas objetivo resultantes (las tres en 2023, como exige la autorización): +1 → 2023-06-16, +2 → 2023-06-17, +3 → 2023-06-18.

## 8. Verificación HTTP real (entorno aislado)

Directorio de datos y `bundle_root` exclusivos de esta corrida (nunca compartidos con otro sensor ni con la campaña cerrada). Snapshot de observaciones recortado hasta 2023-06-15 exactamente (cargar todo 2023 habría desplazado la emisión al 2023-12-31). Procedencia (`origen`) registrada como `external_reanalysis_era5_nasa_power` — datos reales externos, nunca marcados como `sintetico`, y nunca presentados como medición de un sensor físico propio (`"real"` en el esquema de `data_ingestion.history._origin` significaría exactamente eso); el esquema solo reconoce `real`/`sintetico`, así que esta etiqueta se clasifica honestamente como `unknown`.

- `POST /api/v2/sensors/pergamino-ensemble-demo/forecasts` (`json={}`, `Idempotency-Key` explícita): **201**.
- Repetición con la misma clave: **201**, respuesta idéntica a la original (idempotencia verificada).
- `GET` de cada pronóstico individual (+1/+2/+3): **200** los tres.
- `GET` del listado del sensor: **200**.
- Los tres *slots* (+1/+2/+3): `status=available`, fecha objetivo en 2023, `ensemble.policy_version=ensemble_agreement_v1`, `ensemble.weights` uniforme 1/3, 3 componentes con `score`/`alert`/`model_reference`/`calibrated_through` coherentes, `positive_votes=0`, `agreement_category=sin_alerta_por_unanimidad`, `combined_alert=False` (coherente con `alert` de nivel superior en los tres).
- `combined_probability` (+1) = `0.01657426242378581`, verificado igual al promedio exacto de los 3 `score` de componente.
- `display_probability=null` y `probability_status=not_qualified` en los tres — nunca habilitada la probabilidad de presentación.

Reporte HTTP completo: `http_verification_report.json` (en logs y respaldo).

## 9. Qué se reutiliza y qué es enteramente nuevo

- **Reutilizado:** el rango de fechas de las particiones (2015-2021/2022/2023, ya definido en el ejecutor revisado); la *elección* de hiperparámetros de `logistic_regression` (idéntica a la ganadora real de la Etapa A, según el manifiesto versionado en git) — **nunca el artefacto ajustado de esa campaña**, que no existe serializado.
- **Enteramente nuevo, sin antecedente en la campaña cerrada:**
  - Los 9 modelos y 9 calibradores ajustados en esta corrida (incluida la propia `logistic_regression`, reajustada sobre una ventana 2015-2021 distinta y más angosta que la Etapa A real, 2015-2022).
  - `random_forest`/`hist_gradient_boosting_classifier`: nunca tuvieron un artefacto congelado en la campaña real; sus hiperparámetros son un punto fijo dentro de la grilla ya declarada por el protocolo, elegido sin leer ninguna métrica (real o sintética) de ninguna corrida.
  - La calibración de las 3 familias: el protocolo real nunca calibró nada; esta corrida introduce `CalibratedClassifierCV(FrozenEstimator(...), sigmoid)` como parte del empaquetado operativo, explícitamente autorizado ahora por el responsable.
  - Los horizontes +1 y +2 en su totalidad: sin ningún antecedente real de `controlled_daily_v4` (que solo corrió +3).
- **Ausencia de nueva evidencia confirmatoria:** esta corrida no constituye, ni pretende constituir, una validación científica de HU7/HU8. No se abrió el holdout 2024-2025, no se tocó la campaña cerrada, y no se recalculó ni se leyó ninguna métrica del período excluido.

## 10. Limitaciones y fallos

- Ninguna falla durante la ejecución (código de salida 0, `run_manifest.json` en `completado`).
- El umbral físico, la calibración y los 9 modelos provienen de una única corrida sobre una única partición temporal fija — no hay repetición con semillas alternativas ni validación cruzada adicional en esta demostración.
- La demostración usa `as_of_date=2023-06-15` únicamente; no se generó un recorrido día por día de todo 2023.
- Advertencias de `scikit-learn` sobre nombres de features (`X has/does not have valid feature names`) aparecieron en `stderr` de las verificaciones de carga/inferencia — no son errores, son el mismo comportamiento ya documentado en Hito 1 para estimadores ajustados por array con `feature_names_in_` restituido por `attach_feature_names`.

## 11. Trazabilidad

- **HU:** HU7 (`experiment-runner`) + `predictive-modeling` (Hito 1, PR #217) + Hito 2 (PR #218).
- **Impacto en configuración experimental:** ninguno sobre `controlled_daily_v3`/`controlled_daily_v4` congelados. Esta corrida es un empaquetado operativo nuevo, con su propia identidad (commit `67eed9d`, hashes propios), nunca una modificación de resultados históricos.
- **Impacto en hipótesis/alcance/arquitectura:** ninguno. No se reejecutó A/B/C, no se abrió el holdout, no se alteró `replay_packages/` ni la evidencia de la campaña cerrada.
- **Autorización:** registrada en la sección 0 y en `execution_record.json`; resuelve explícitamente las decisiones metodológicas de `ensemble-real-enablement-plan.md` secciones 6.1/6.2 para el alcance de esta demostración.
- **Artefactos y logs:** `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z\` (+ `-logs`), con respaldo verificado en `D:\AAI_Hydric_Stress_ensemble_demo_backup\`. Ninguno de estos árboles se sube a git (datasets/binarios/logs fuera de convenciones existentes).
