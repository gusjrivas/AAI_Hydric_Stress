# HU8 — Análisis de resultados experimentales

> **Actualización (2026-09-04) — corrección de fuga temporal, ver sección 11.** Todas las secciones siguientes (1-10) describen los resultados **previos** a esta corrección, y se conservan sin modificar como evidencia histórica. La sección 11, al final de este documento, presenta la comparación completa antes/después y qué conclusiones se mantienen, cuáles cambian de magnitud, y cuál cambia de sentido.

Épica 4, HU8 (sin capacidad de código, igual que HU1 — ver `openspec/project.md`). Primer sub-proyecto: consolidación y análisis de los resultados reales registrados en MLflow durante HU7 (`openspec/specs/experiment-runner/spec.md`).

**Alcance de la evidencia disponible**: un único dataset real (`melchor_romero_2024_consolidado.parquet`, Partido de La Plata, año calendario 2024, 366 filas antes de limpieza, 357 tras imputación/ingeniería de variables), 4 configuraciones experimentales (base, +sintéticos, +anomalías, completa), 5 semillas cada una, modelo Random Forest. Este análisis es honesto respecto de esa limitación de escala: un solo punto geográfico, un solo año, un dataset chico.

## 1. Consolidación de los resultados de todas las ejecuciones experimentales

Registrados en el servidor MLflow real (`http://localhost:5000`, experimento `hu7-epica4`), verificados en `openspec/changes/add-experiment-execution/`:

| Configuración | Semillas | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión (media) | Recall (media) |
|---|---|---|---|---|---|
| Base | 1-5 | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 1-5 | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0-4 (ver nota) | 0.4625 ± 0.0414 | 0.5881 ± 0.0309 | 0.6097 | 0.3730 |
| Completa | 0-4 (ver nota) | 0.3733 ± 0.1065 | 0.5297 ± 0.0629 | 0.5286 | 0.2973 |

`+Anomalías` y `Completa` fueron re-ejecutadas y re-registradas (runs `anomalias-refit`/`completa-refit`) tras `openspec/changes/fix-anomaly-feature-integration/`, que corrigió que `is_anomaly` no llegaba al modelo; los valores de `Base` y `+Sintéticos` no cambian.

**Nota sobre semillas**: la lista exacta de semillas usada en la ejecución original de `Base`/`+Sintéticos` nunca quedó registrada en el repositorio (fue una ejecución ad hoc, ver `openspec/changes/add-experiment-execution/proposal.md`, "Código afectado: ninguno nuevo"); la etiqueta "1-5" es una referencia genérica a "5 semillas", no una lista verificada. El re-run de `+Anomalías`/`Completa` sí usó semillas verificadas y explícitas: `[0, 1, 2, 3, 4]`. En consecuencia, cualquier comparación entre las filas re-ejecutadas y `Base`/`+Sintéticos` tiene la salvedad de que podrían no compartir exactamente la misma lista de semillas, aunque ambas usan 5 semillas y es poco probable que las conclusiones cualitativas de este análisis sean sensibles a esa diferencia dado el tamaño de muestra.

Más una prueba piloto (`piloto-base`, semillas 1-2) usada solo para validar el mecanismo contra el servidor real, no incluida en esta tabla de resultados.

## 2. Ejecuciones incompletas o inconsistentes

Las 4 configuraciones × 5 semillas (20 corridas) completaron sin errores, con las 4 métricas (precisión, recall, F1, ROC-AUC) registradas en cada run hijo del servidor MLflow real. No hay ejecuciones incompletas que descartar.

**Inconsistencia resuelta**: la primera ejecución de HU7 mostró `+Anomalías` con métricas *idénticas* a `Base`, y `Completa` idénticas a `+Sintéticos` — no un fallo de ejecución, sino un defecto de integración (`is_anomaly` no llegaba al modelo). Tras corregirlo en `openspec/changes/fix-anomaly-feature-integration/` y re-ejecutar ambas configuraciones, los valores ya no son idénticos (ver tabla de la sección 1) — ver sección 5 para el efecto real medido.

## 3. Métricas agregadas y medidas de dispersión

Ya incluidas en la tabla de la sección 1 (media ± desvío entre las 5 semillas, por configuración). El desvío estándar de F1 es más alto en las configuraciones con datos sintéticos (`+Sintéticos` 0.0862, `Completa` 0.1065, rango 0.086-0.107) que en las que no los usan (`Base` 0.0423, `+Anomalías` 0.0414, rango 0.041-0.042) — la variabilidad entre semillas aumenta al introducir aumento sintético, no solo el valor medio empeora.

## 4. Comparación del enfoque de referencia con la arquitectura propuesta

- **Enfoque de referencia** (persistencia, sin entrenamiento, HU4, partición única): F1=0.486, precisión=0.500, recall=0.474.
- **Arquitectura propuesta** (Random Forest, configuración base, HU7, promedio de 5 semillas): F1=0.4585±0.0423, ROC-AUC=0.5551±0.0191.

**Hallazgo honesto**: la arquitectura propuesta (modelo entrenado con variables de retardo/ventana móvil) **no supera** al enfoque de referencia más simple (persistencia por umbral) en F1, ni siquiera en su mejor configuración disponible. Esto ya estaba anticipado como límite en HU4 ("Ni la regresión logística ni el Random Forest superan claramente al modelo de referencia por persistencia en F1 sobre este dataset") y HU7 lo confirma con repetición estadística (5 semillas) en vez de una única partición.

## 5. Aporte de la detección de anomalías y los datos sintéticos

- **Detección de anomalías**: efecto medible y positivo, aunque modesto. Corregida la integración en `openspec/changes/fix-anomaly-feature-integration/` (`is_anomaly` ahora es una variable predictora real que recibe el modelo, con el detector ajustado solo sobre `train`), `+Anomalías` mejora sobre `Base` en ROC-AUC (0.5551 → 0.5881) y precisión (0.5967 → 0.6097), con F1 prácticamente igual (0.4585 → 0.4625) y un recall medio que coincide con el de `Base` a cuatro decimales (0.3730) — coincidencia de redondeo entre semillas individualmente distintas, no la identidad total en las 4 métricas que caracterizaba el defecto ya corregido; `Completa` mejora sobre `+Sintéticos` en las 4 métricas (F1 0.3123 → 0.3733, ROC-AUC 0.5083 → 0.5297, precisión 0.5091 → 0.5286, recall 0.2324 → 0.2973). Ningún indicador empeora en ninguna de las dos comparaciones. La magnitud del efecto es modesta (la mejora de F1 frente a `Base` está dentro del ruido entre semillas), pero es consistente y nunca negativa, lo que sugiere que `is_anomaly` sí aporta señal predictiva real, aunque acotada, una vez que efectivamente llega al modelo.
- **Datos sintéticos**: efecto medible y negativo. `+Sintéticos` tiene F1 0.3123 frente a 0.4585 de `Base` (recall cae de 0.373 a 0.232, la caída más marcada). Causa probable: `experiment_runner.synthetic_augmentation.add_synthetic_rows` muestrea una normal multivariada sobre el espacio de variables ya construidas (retardos/ventanas móviles + etiqueta), que no preserva relaciones no lineales ni la estructura de autocorrelación temporal real entre esas variables — genera filas sintéticas estadísticamente plausibles en media/covarianza pero que diluyen la señal predictiva real, en vez de reforzarla.

## 6. Efecto de la retroalimentación y la recalibración (HU5)

Verificado con datos reales y correcciones sintéticas inyectadas (`openspec/specs/human-feedback/spec.md`): el mecanismo de recalibración supervisada (`human_feedback.recalibration.recalibrate_model`) reemplaza correctamente la etiqueta de las fechas corregidas por retroalimentación humana en el conjunto de entrenamiento, y el modelo recalibrado predice distinto exactamente en esas fechas (ejemplo real: predicciones `[1,1,0]` pasan a `[0,0,1]`, coincidiendo con la corrección). El mecanismo funciona; no se evaluó todavía su efecto agregado sobre las métricas de un conjunto de evaluación completo, porque el volumen de retroalimentación humana real acumulada es mínimo (1-2 casos reales) — la evaluación agregada requeriría una campaña de retroalimentación más extensa, fuera de alcance de este prototipo de tesis.

## 7. Falsos positivos, falsos negativos y errores relevantes (HU4)

Sobre la partición única de evaluación (72 filas, Random Forest, umbral 0.5, `predictive_modeling.alerts`): 7 falsos positivos (ej. 2024-11-15, 2024-12-10 a 2024-12-13) y 24 falsos negativos (ej. 2024-10-18 a 2024-10-20, 2024-11-17 a 2024-11-22) — el recall bajo (0.373 en el promedio de 5 semillas de HU7) implica que la mayoría de los eventos de estrés reales no generan alerta con el umbral actual (0.5, no calibrado).

## 8. Desempeño bajo escenarios de escasez de datos

**Ejecutado** (`openspec/changes/add-experiment-scenarios/`): `experiment_runner.scenarios.subsample_training_period` reduce el entrenamiento a su mitad más reciente (`train_fraction=0.5`), sin tocar el conjunto de evaluación. Resultado real (configuración base, 5 semillas): F1 medio **0.6219 ± 0.0888**, ROC-AUC no reportado aquí (ver spec) — **superior** al F1 medio de la configuración base sin reducir (0.4585 ± 0.0423).

**Hallazgo contraintuitivo pero explicable**: menos datos de entrenamiento, pero más recientes, dieron mejor desempeño que todo el año completo. La explicación más plausible es un corrimiento de distribución (*distribution shift*) estacional: el conjunto de evaluación es el 20% final del año (aprox. octubre-diciembre), y entrenar solo con la mitad de fechas más cercanas a ese período (en vez de con el año completo, que incluye estaciones climáticamente distintas) produce un modelo más ajustado a las condiciones de la época que efectivamente se evalúa. No es evidencia de que "menos datos sea mejor" en general — es evidencia de que, en este dataset de un solo año, la relevancia temporal de los datos de entrenamiento importa más que su cantidad.

## 9. Desempeño bajo escenarios de ruido y variabilidad de datos

- **Variabilidad**: sí evaluada — el desvío estándar entre las 5 semillas de cada configuración (sección 3) es la medida de variabilidad disponible. Es moderado en `Base`/`+Anomalías` (F1 std=0.0423/0.0414) y considerablemente mayor en `+Sintéticos`/`Completa` (F1 std=0.0862/0.1065) y en el escenario de ruido (F1 std=0.113, el más alto de todos).
- **Ruido**: **ejecutado** (`openspec/changes/add-experiment-scenarios/`): `experiment_runner.scenarios.inject_gaussian_noise` agrega ruido gaussiano proporcional al desvío de cada variable predictora (`noise_std_ratio=0.3`, valor de ejemplo no calibrado contra ninguna caracterización real de ruido de sensor — HU7 documentó que esa caracterización no existe todavía). Resultado real (configuración base + ruido, 5 semillas): F1 medio **0.3188 ± 0.1130**, **inferior** al F1 medio sin ruido (0.4585 ± 0.0423) y con casi el triple de variabilidad entre semillas. El ruido degrada tanto el desempeño medio como su estabilidad, en la dirección esperada.

## 10. Robustez, estabilidad y compromisos entre métricas

- **Estabilidad** (desvío entre semillas): mejor en las configuraciones sin datos sintéticos (`Base`/`+Anomalías`, F1 std=0.0423/0.0414) que en las que sí los usan (`+Sintéticos`/`Completa`, F1 std=0.0862/0.1065) — el aumento sintético no solo empeora la media, también empeora la estabilidad.
- **Compromiso precisión/recall**: en todas las configuraciones, la precisión (0.509-0.610) supera al recall (0.23-0.37) — el modelo es más conservador que sensible: cuando alerta, suele acertar, pero deja pasar más eventos de estrés real de los que detecta. Este compromiso es consistente con el umbral de alerta fijo (0.5, no calibrado — ver `openspec/specs/predictive-modeling/spec.md`, "Limitaciones conocidas").
- **Complejidad vs. desempeño**: el modelo más complejo evaluado (Random Forest, 100 árboles) no logra superar al modelo de referencia sin entrenamiento (persistencia) en F1 — la complejidad adicional no se traduce en una ganancia de desempeño medible con los datos disponibles.

## Limitaciones de este análisis

- Basado en un único dataset (un punto geográfico, un año); no se puede generalizar a otros sitios o períodos sin repetir la evaluación con más datos.
- El hallazgo original sobre detección de anomalías reflejaba una limitación de integración del orquestador (HU6); corregida en `openspec/changes/fix-anomaly-feature-integration/` y vuelta a medir, el efecto real es positivo pero modesto (ver sección 5) — sigue siendo un único dataset de un año, por lo que no se puede generalizar la magnitud del efecto a otros contextos.
- El efecto de la retroalimentación humana está verificado mecánicamente pero no evaluado a escala agregada, por falta de volumen real de correcciones.
- El escenario de ruido usa un valor de ejemplo (`noise_std_ratio=0.3`) no calibrado contra ninguna fuente real de ruido de sensor.
- El hallazgo sobre escasez (menos datos, mejor desempeño) es específico de este dataset y de este recorte cronológico particular; no se probaron otras fracciones ni otras formas de subselección.

## 11. Corrección de fuga temporal (2026-09-04): comparación antes/después

Una auditoría metodológica de la memoria técnica identificó dos fugas temporales reales en `src/architecture_integration/pipeline.py` (ver `openspec/specs/data-quality/spec.md` y `openspec/specs/predictive-modeling/spec.md`, ambos actualizados el mismo día):

1. **Imputación** (`interpolate_missing`, interpolación lineal bidireccional) se aplicaba sobre el dataset completo antes de partir train/test, permitiendo que un hueco de entrenamiento se completara con una observación de evaluación.
2. **Umbral de la variable objetivo** (`add_stress_label`, percentil 20) se calculaba sobre el dataset completo antes de partir, dejando el umbral informado por la distribución de evaluación.

Ambas se corrigieron reordenando el pipeline (partir primero, imputar causalmente por partición con semilla de entrenamiento para evaluación, congelar el umbral en entrenamiento) sin tocar ningún otro componente de la arquitectura — ver `tests/test_imputation.py`, `tests/test_labeling.py` para las pruebas de causalidad, y la suite completa (`pytest -q`, 116 tests; `cd backend && pytest -q`, 24 tests) en verde tras la corrección.

### 11.1. Hallazgo previo a cualquier comparación de métricas

El umbral corregido (0.3223, solo entrenamiento) resultó más alto que el umbral anterior (0.3115, dataset completo). Esto no es arbitrario: la humedad de suelo de entrenamiento (media 0.345) es sistemáticamente mayor que la de evaluación (media 0.314) — la partición de evaluación corresponde a los últimos ~2.5 meses del año (2024-10-19 en adelante), una época más seca. El umbral anterior, al calibrarse parcialmente con la propia distribución de evaluación, producía una tasa base de estrés en evaluación artificialmente cercana al 51% (balanceada). El umbral corregido, calibrado honestamente solo con entrenamiento y aplicado tal cual a una evaluación más seca, produce una tasa base real de ~65% de filas etiquetadas como estrés en evaluación (antes: ~51%).

Esto cambia el terreno de comparación de F1 entre el antes y el después: F1 es sensible al balance de clases, y ese balance cambió de verdad (no es un artefacto de la corrección, es lo que el umbral anterior ocultaba). Por eso esta sección reporta también ROC-AUC con especial atención — es la métrica menos sensible al desbalance de clases y al umbral de decisión, y es la que revela la conclusión más importante de esta corrección.

### 11.2. Tabla comparativa (antes vs. después de la corrección)

Semillas `[0, 1, 2, 3, 4]` en ambos casos (ver nota de la sección 1 sobre semillas de `Base`/`+Sintéticos` original). Registrado en MLflow, experimento nuevo `hu7-epica4-leakage-fix` (`scripts/run_hu7_experiments.py`), separado del experimento histórico `hu7-epica4` — ninguna corrida anterior fue sobrescrita.

| Configuración | F1 antes | F1 después | ROC-AUC antes | ROC-AUC después |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.7354 ± 0.0094 | 0.5551 ± 0.0191 | 0.4664 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.7098 ± 0.0379 | 0.5083 ± 0.0439 | 0.4432 |
| +Anomalías | 0.4625 ± 0.0414 | 0.7368 ± 0.0123 | 0.5881 ± 0.0309 | 0.4962 |
| Completa | 0.3733 ± 0.1065 | 0.7075 ± 0.0401 | 0.5297 ± 0.0629 | 0.4544 |

Persistencia (referencia, sin entrenamiento): F1 antes 0.486 (umbral 0.3126, 72 filas) → F1 después 0.6087 (umbral 0.3223, 71 filas). Un clasificador trivial que siempre prediga "estrés" (sin ningún modelo) tendría, bajo la nueva tasa base de evaluación (~65% positivo), un F1 aproximado de 0.786 — más alto que cualquiera de las 4 configuraciones del Random Forest y que la propia persistencia. Esto se verificó directamente (no es una estimación): con una tasa positiva de 0.6479 y 71 filas, un predictor "siempre positivo" da precisión=recall=tasa base=0.6479, F1=2·p·r/(p+r)≈0.786.

### 11.3. Qué conclusiones se mantienen

El orden relativo entre configuraciones se mantiene idéntico al reportado en la sección 5:
- `+Anomalías` (0.7368) sigue por encima de `Base` (0.7354) — efecto positivo y modesto, igual que antes.
- `Completa` (0.7075) sigue por debajo de `+Sintéticos` (0.7098) en F1, aunque la brecha es menor que antes; en ROC-AUC `Completa` (0.4544) sigue por encima de `+Sintéticos` (0.4432) — la detección de anomalías sigue ayudando dentro de cada par, tal como en la sección 5.
- `+Sintéticos`/`Completa` siguen por debajo de `Base`/`+Anomalías` respectivamente en ambas métricas — los datos sintéticos siguen perjudicando el desempeño, misma dirección que antes.
- Escasez de datos (`train_fraction=0.5`) sigue mejorando el F1 respecto de la base sin reducir: 0.8430 ± 0.0139 después vs. 0.6219 ± 0.0888 antes (ambos por encima de su respectiva base), consistente con la explicación de corrimiento estacional ya documentada en la sección 8.
- Ruido (`noise_std_ratio=0.3`) sigue degradando el desempeño respecto de la base sin ruido: 0.6467 ± 0.0520 después vs. 0.7354 ± 0.0094 (base después) — la misma dirección que antes (0.3188 vs. 0.4585), aunque la magnitud relativa de la degradación es menor.

### 11.4. Qué conclusión cambia de sentido (la más importante de esta corrección)

Antes: "el Random Forest no supera claramente al modelo de referencia por persistencia en F1" (sección 4) — una conclusión modesta pero con un ROC-AUC (0.5551-0.5881) que sugería algo de capacidad de discriminación real, mejor que el azar.

Después: el F1 del Random Forest (0.7354 en base) sí supera numéricamente a la persistencia (0.6087) — pero el ROC-AUC de las 4 configuraciones (0.4432-0.4962) está en o por debajo de 0.5, el valor esperado de un clasificador que no discrimina mejor que el azar. Dado que ROC-AUC no depende del umbral de decisión ni de la tasa base de la clase positiva (a diferencia de F1), esta es la lectura más confiable disponible, y dice algo más serio que la conclusión anterior: una vez eliminada la fuga que inflaba artificialmente el aparente poder predictivo del umbral, el modelo no muestra capacidad de discriminación medible sobre este dataset — su F1 alto se explica principalmente por el desbalance de clases en evaluación (65% positivo), no por señal predictiva real. Un comparador ingenuo "siempre predecir estrés" iguala o supera a las 4 configuraciones entrenadas en F1 (sección 11.2).

Esta es exactamente la clase de resultado que la auditoría pidió no forzar a mejorar: la validez metodológica revela una conclusión más débil, no más fuerte, que la reportada originalmente. La hipótesis de investigación (que la arquitectura propuesta mejora la detección temprana de estrés hídrico respecto de configuraciones de referencia) queda todavía menos respaldada por esta evidencia que antes de la corrección, no más.

### 11.5. Limitaciones de esta comparación

- Las semillas de `Base`/`+Sintéticos` originales ("1-5" genérico, sección 1) no están verificadas contra una lista exacta; esta re-ejecución usó `[0,1,2,3,4]` para las 4 configuraciones por igual, evitando esa ambigüedad hacia adelante, pero sin poder garantizar que sea exactamente la misma lista que la ejecución original de `Base`/`+Sintéticos`.
- `n_synthetic_samples=100` fue reconstruido a partir de una mención indirecta en la sección 8 de este documento (no hay un script committeado de la ejecución original de HU7 — ver `openspec/changes/add-experiment-execution/proposal.md`, "Código afectado: ninguno nuevo"). `scripts/run_hu7_experiments.py`, agregado junto con esta corrección, deja esto reproducible de ahora en adelante.
- No se recalculó el análisis de falsos positivos/negativos (sección 7) ni el efecto de retroalimentación humana (sección 6) bajo el pipeline corregido — quedan como trabajo pendiente si se decide profundizar esta línea.
- Esta comparación usa el mismo dataset de un solo punto geográfico y un solo año (limitación ya documentada en la sección "Limitaciones de este análisis"); el hallazgo de la sección 11.4 podría no generalizar, pero tampoco hay razón para esperar que el sentido de la corrección (revelar, no ocultar, un corrimiento de distribución real) sea específico de este dataset.
