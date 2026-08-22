# Change: Fix anomaly detection integration into the predictive pipeline

## Trazabilidad

- **Épica:** 3. Integración y mejora (cambio de código) + 4. Evaluación experimental (re-ejecución de resultados afectados).
- **Historia de usuario:** HU6 (`architecture-integration`, corrige un defecto real de integración) — cierra una limitación que HU7 documentó y que HU8 heredó sin poder resolver ("La detección de anomalías no afecta actualmente el desempeño del modelo", `openspec/specs/experiment-runner/spec.md`, sección "Limitaciones conocidas").
- **Fase de CRISP-DM:** Modelado (integración) + Evaluación (re-ejecución de las configuraciones afectadas).
- **Insumo de diseño:** `openspec/specs/architecture-integration/spec.md`, `openspec/specs/data-quality/spec.md` (`detect_anomalies`), `openspec/specs/experiment-runner/spec.md` (hallazgo y limitación a resolver).

## Why

`run_end_to_end_pipeline` (HU6) llama a `detect_anomalies` y agrega la columna `is_anomaly` a `train`/`test`, pero `feature_cols` se calcula *antes* de esa llamada y nunca incluye `is_anomaly`. El resultado, confirmado con datos reales en HU7: las configuraciones experimentales `+anomalías` y `completa` producen métricas *idénticas* a `base`/`+sintéticos` — la detección de anomalías corre, marca filas, pero no influye en ninguna predicción. Esto no es un hallazgo científico sobre el valor de la detección de anomalías; es un defecto de integración que invalida esa comparación específica de la Épica 4 y, por lo tanto, la conclusión que HU8 pudo sacar sobre ese factor.

## What Changes

- **`src/data_quality/anomaly_detection.py`**: agrega `fit_anomaly_detector(df, columns, contamination, random_state) -> IsolationForest` y `apply_anomaly_detector(df, columns, detector) -> pd.DataFrame` (agrega `is_anomaly` usando un detector ya ajustado). `detect_anomalies` pasa a ser un atajo de ambas sobre el mismo `df` — comportamiento externo sin cambios, sigue usándose tal cual en `data_quality.pipeline.run_quality_pipeline` (HU3, fuera de alcance de este *change*).
- **`src/architecture_integration/pipeline.py`**: cuando `include_anomaly_detection=True`, ajusta el detector **solo sobre `train`** y lo aplica a `train` y a `test` (evita que `test` influya en su propia feature, igual que ya se hace con el modelo predictivo); agrega `"is_anomaly"` a `feature_cols`, que ahora se calcula después de la detección.
- **`src/experiment_runner/synthetic_augmentation.py`**: `add_synthetic_rows` redondea/recorta a `{0,1}` cualquier columna de `feature_columns`/`target_column` cuyo `dtype` en `train_df` sea `bool` (generaliza el tratamiento que hoy solo aplica a `target_column`), para que `is_anomaly` en filas sintéticas (configuración `completa`) sea un booleano válido y no un valor fraccionario sin sentido.
- **Re-ejecución de `+anomálias` y `completa`** (5 semillas, dataset real, contra el MLflow real de docker-compose) y actualización de los números/hallazgos en `openspec/specs/experiment-runner/spec.md`, `docs/research/hu8-analisis-resultados.md`, `docs/research/hu8-resultados-discusion-conclusiones.md`, `openspec/specs/architecture-integration/spec.md`, `openspec/specs/data-quality/spec.md` y `docs/seguimiento-tareas.md`. `base`/`+sintéticos` no cambian (no dependen de la detección de anomalías) y no se re-ejecutan.

## Impact

- **Specs afectadas:** `architecture-integration` (nuevo requirement, ver `specs/architecture-integration/spec.md` de este *change*), `data-quality` (nota de implementación actualizada sobre `detect_anomalies`, sin nuevo requirement), `experiment-runner` (tabla de resultados y limitación conocida corregidas, sin nuevo requirement).
- **Código afectado:** `src/data_quality/anomaly_detection.py`, `src/architecture_integration/pipeline.py`, `src/experiment_runner/synthetic_augmentation.py`, y sus tests (`tests/test_anomaly_detection.py`, `tests/test_architecture_integration_pipeline.py`, `tests/test_synthetic_augmentation.py`).
- **Resultados afectados:** las métricas ya registradas en MLflow para `+anomálias`/`completa` (HU7) quedan obsoletas frente al pipeline corregido; se re-ejecutan y se documentan como reemplazo, no como corrida adicional.
- **Fuera de alcance de este change:** filtrar filas anómalas del entrenamiento (alternativa descartada, ver abajo); cambiar `data_quality.pipeline.run_quality_pipeline` (HU3), que no consume `is_anomaly` como feature de ningún modelo y no tiene el defecto que motiva este *change*; calibrar `contamination` o evaluar si `is_anomaly` termina teniendo importancia real en el modelo entrenado (queda como observación para un análisis posterior, no como requisito de este *change*).

## Alternativas consideradas

- **Filtrar del entrenamiento las filas marcadas `is_anomaly=True` en vez de usarlas como feature**: se descarta porque reduciría aún más un conjunto de entrenamiento ya escaso (~285 filas, con folds de `TimeSeriesSplit` que ya quedan sin ejemplos positivos en HU4), y porque las anomalías detectadas no están validadas contra fallas de sensor reales (`openspec/specs/data-quality/spec.md`, "Limitaciones conocidas") — descartar datos reales por una señal no validada es más riesgoso que dejar que el modelo decida cuánto pesa la marca.
- **Ajustar el detector de anomalías sobre train+test combinados (como hace hoy `run_quality_pipeline` con train/test por separado, pero unificado)**: se descarta por ser una forma distinta de la misma fuga — el detector seguiría usando información de `test` para construir una feature de `test`. Ajustar solo en `train` y transformar `test` es consistente con cómo ya se entrena el modelo predictivo.
- **Dejar el resultado de HU7 como está y documentar la corrección solo como limitación resuelta a futuro**: se descarta por decisión explícita del usuario — la comparación entre configuraciones de la Épica 4 debe quedar metodológicamente válida, no solo señalada como pendiente.
