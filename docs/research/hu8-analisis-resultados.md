# HU8 — Análisis de resultados experimentales

Épica 4, HU8 (sin capacidad de código, igual que HU1 — ver `openspec/project.md`). Primer sub-proyecto: consolidación y análisis de los resultados reales registrados en MLflow durante HU7 (`openspec/specs/experiment-runner/spec.md`).

**Alcance de la evidencia disponible**: un único dataset real (`melchor_romero_2024_consolidado.parquet`, Partido de La Plata, año calendario 2024, 366 filas antes de limpieza, 357 tras imputación/ingeniería de variables), 4 configuraciones experimentales (base, +sintéticos, +anomalías, completa), 5 semillas cada una, modelo Random Forest. Este análisis es honesto respecto de esa limitación de escala: un solo punto geográfico, un solo año, un dataset chico.

## 1. Consolidación de los resultados de todas las ejecuciones experimentales

Registrados en el servidor MLflow real (`http://localhost:5000`, experimento `hu7-epica4`), verificados en `openspec/changes/add-experiment-execution/`:

| Configuración | Semillas | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión (media) | Recall (media) |
|---|---|---|---|---|---|
| Base | 1-5 | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 1-5 | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 1-5 | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| Completa | 1-5 | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |

Más una prueba piloto (`piloto-base`, semillas 1-2) usada solo para validar el mecanismo contra el servidor real, no incluida en esta tabla de resultados.

## 2. Ejecuciones incompletas o inconsistentes

Las 4 configuraciones × 5 semillas (20 corridas) completaron sin errores, con las 4 métricas (precisión, recall, F1, ROC-AUC) registradas en cada run hijo del servidor MLflow real. No hay ejecuciones incompletas que descartar.

**Inconsistencia real detectada** (no un fallo de ejecución, sino un hallazgo sobre el propio diseño): `+Anomalías` produjo métricas *idénticas* a `Base`, y `Completa` idénticas a `+Sintéticos` — ver sección 5.

## 3. Métricas agregadas y medidas de dispersión

Ya incluidas en la tabla de la sección 1 (media ± desvío entre las 5 semillas, por configuración). El desvío estándar de F1 es más alto en las configuraciones con datos sintéticos (0.086 vs. 0.042 en las que no los usan) — la variabilidad entre semillas aumenta al introducir aumento sintético, no solo el valor medio empeora.

## 4. Comparación del enfoque de referencia con la arquitectura propuesta

- **Enfoque de referencia** (persistencia, sin entrenamiento, HU4, partición única): F1=0.486, precisión=0.500, recall=0.474.
- **Arquitectura propuesta** (Random Forest, configuración base, HU7, promedio de 5 semillas): F1=0.4585±0.0423, ROC-AUC=0.5551±0.0191.

**Hallazgo honesto**: la arquitectura propuesta (modelo entrenado con variables de retardo/ventana móvil) **no supera** al enfoque de referencia más simple (persistencia por umbral) en F1, ni siquiera en su mejor configuración disponible. Esto ya estaba anticipado como límite en HU4 ("Ni la regresión logística ni el Random Forest superan claramente al modelo de referencia por persistencia en F1 sobre este dataset") y HU7 lo confirma con repetición estadística (5 semillas) en vez de una única partición.

## 5. Aporte de la detección de anomalías y los datos sintéticos

- **Detección de anomalías**: sin efecto medible. `+Anomalías` = `Base` exactamente, en las 4 métricas, en las 5 semillas. Causa raíz: `is_anomaly` (la columna que agrega `data_quality.anomaly_detection.detect_anomalies`) nunca se incluye entre las variables predictoras (`feature_columns`) que recibe el modelo en `architecture_integration.pipeline.run_end_to_end_pipeline` (HU6) — la detección corre y marca filas, pero esa marca no llega a influir la predicción. **No es evidencia de que la detección de anomalías no aporte**; es evidencia de que el orquestador actual no la conecta con el modelo.
- **Datos sintéticos**: efecto medible y negativo. `+Sintéticos` tiene F1 0.3123 frente a 0.4585 de `Base` (recall cae de 0.373 a 0.232, la caída más marcada). Causa probable: `experiment_runner.synthetic_augmentation.add_synthetic_rows` muestrea una normal multivariada sobre el espacio de variables ya construidas (retardos/ventanas móviles + etiqueta), que no preserva relaciones no lineales ni la estructura de autocorrelación temporal real entre esas variables — genera filas sintéticas estadísticamente plausibles en media/covarianza pero que diluyen la señal predictiva real, en vez de reforzarla.

## 6. Efecto de la retroalimentación y la recalibración (HU5)

Verificado con datos reales y correcciones sintéticas inyectadas (`openspec/specs/human-feedback/spec.md`): el mecanismo de recalibración supervisada (`human_feedback.recalibration.recalibrate_model`) reemplaza correctamente la etiqueta de las fechas corregidas por retroalimentación humana en el conjunto de entrenamiento, y el modelo recalibrado predice distinto exactamente en esas fechas (ejemplo real: predicciones `[1,1,0]` pasan a `[0,0,1]`, coincidiendo con la corrección). El mecanismo funciona; no se evaluó todavía su efecto agregado sobre las métricas de un conjunto de evaluación completo, porque el volumen de retroalimentación humana real acumulada es mínimo (1-2 casos reales) — la evaluación agregada requeriría una campaña de retroalimentación más extensa, fuera de alcance de este prototipo de tesis.

## 7. Falsos positivos, falsos negativos y errores relevantes (HU4)

Sobre la partición única de evaluación (72 filas, Random Forest, umbral 0.5, `predictive_modeling.alerts`): 7 falsos positivos (ej. 2024-11-15, 2024-12-10 a 2024-12-13) y 24 falsos negativos (ej. 2024-10-18 a 2024-10-20, 2024-11-17 a 2024-11-22) — el recall bajo (0.373 en el promedio de 5 semillas de HU7) implica que la mayoría de los eventos de estrés reales no generan alerta con el umbral actual (0.5, no calibrado).

## 8. Desempeño bajo escenarios de escasez de datos

**No ejecutado.** HU7 documentó el escenario de escasez (subconjunto del entrenamiento real) como parte del diseño experimental, pero el procedimiento automatizado (`experiment_runner.runner.run_configuration`) no llegó a implementar un parámetro de tamaño de muestra reducido, y no se corrió sobre datos reales. No hay evidencia real para reportar sobre este escenario — se documenta como limitación abierta, no se inventa un resultado.

## 9. Desempeño bajo escenarios de ruido y variabilidad de datos

- **Variabilidad**: sí evaluada — el desvío estándar entre las 5 semillas de cada configuración (sección 3) es la medida de variabilidad disponible. Es moderado en `Base`/`+Anomalías` (F1 std=0.042) y considerablemente mayor en `+Sintéticos`/`Completa` (F1 std=0.086).
- **Ruido**: **no ejecutado.** HU7 documentó explícitamente que no hay una caracterización real del ruido de sensor esperado más allá de los gaps ya observados y documentados en ESA CCI Soil Moisture (HU2, 75.96% de completitud en humedad de suelo) — no se inyectó ruido sintético artificial. Se documenta como limitación abierta.

## 10. Robustez, estabilidad y compromisos entre métricas

- **Estabilidad** (desvío entre semillas): mejor en las configuraciones sin datos sintéticos (`Base`/`+Anomalías`, F1 std=0.042) que en las que sí los usan (`+Sintéticos`/`Completa`, F1 std=0.086) — el aumento sintético no solo empeora la media, también empeora la estabilidad.
- **Compromiso precisión/recall**: en todas las configuraciones, la precisión (0.51-0.60) supera al recall (0.23-0.37) — el modelo es más conservador que sensible: cuando alerta, suele acertar, pero deja pasar más eventos de estrés real de los que detecta. Este compromiso es consistente con el umbral de alerta fijo (0.5, no calibrado — ver `openspec/specs/predictive-modeling/spec.md`, "Limitaciones conocidas").
- **Complejidad vs. desempeño**: el modelo más complejo evaluado (Random Forest, 100 árboles) no logra superar al modelo de referencia sin entrenamiento (persistencia) en F1 — la complejidad adicional no se traduce en una ganancia de desempeño medible con los datos disponibles.

## Limitaciones de este análisis

- Basado en un único dataset (un punto geográfico, un año); no se puede generalizar a otros sitios o períodos sin repetir la evaluación con más datos.
- Los escenarios de escasez y ruido no tienen evidencia real — quedan como trabajo futuro explícito, no como resultados asumidos.
- El hallazgo sobre detección de anomalías refleja una limitación de integración del orquestador (HU6), no necesariamente que la técnica en sí no aporte — requeriría corregir esa integración y volver a medir antes de concluir lo contrario.
- El efecto de la retroalimentación humana está verificado mecánicamente pero no evaluado a escala agregada, por falta de volumen real de correcciones.
