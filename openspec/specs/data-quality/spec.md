# Spec: data-quality

Capacidad implementada (Épica 2, HU3). Origen: `openspec/changes/add-data-quality-basics/` (calidad/limpieza básica), `openspec/changes/add-anomaly-detection/` (detección de anomalías), `openspec/changes/add-synthetic-data-generation/` (generación de datos sintéticos) y `openspec/changes/add-data-quality-integration/` (flujo integrado). Este documento es la fuente de verdad vigente de la capacidad; los *changes* que la originaron quedan como registro histórico de cada decisión, no se actualizan en paralelo a este archivo.

**HU3 queda completa con este documento**: los tres sub-proyectos y su integración están implementados y verificados con datos reales. Este spec, junto con la sección "Limitaciones conocidas" al final, cumple también la tarea de cierre "Documentar decisiones, parámetros y limitaciones del componente".

## Requirements

### Requirement: Reporte de distribuciones por variable

El sistema DEBE generar, para cada columna del esquema presente en un dataset, un reporte con tipo de dato, valor mínimo, máximo, media y desvío estándar.

#### Scenario: Distribuciones de un dataset con variables numéricas

- **GIVEN** un dataset normalizado al esquema con columnas obligatorias y opcionales
- **WHEN** se genera el reporte de distribuciones
- **THEN** el reporte incluye, para cada columna numérica presente, su tipo, mínimo, máximo, media y desvío estándar

Implementado en `src/data_quality/distributions.py` (`describe_variables`), testeado en `tests/test_distributions.py`. Verificado sobre `data/melchor_romero_2024_consolidado.parquet`: humedad de suelo 0.27–0.42 m³/m³, temperatura 1.6–31.8°C, valores plausibles para el punto/año evaluados.

### Requirement: Rangos físicos/climáticos plausibles por variable

El sistema DEBE definir, para cada columna obligatoria del esquema, un rango físico o climático plausible (mínimo y máximo genéricos, no específicos de un cultivo en particular), documentado con su justificación.

#### Scenario: Consulta del rango plausible de una variable

- **GIVEN** el esquema de columnas obligatorias definido en `data_ingestion.schema`
- **WHEN** se consulta el rango plausible de la variable "temperatura"
- **THEN** se obtiene un rango numérico (mínimo, máximo) documentado, sin necesidad de ejecutar ningún análisis de datos

Implementado en `src/data_quality/rules.py` (`AGRONOMIC_RANGES`, `get_range`), testeado en `tests/test_rules.py`. Cubre las 7 columnas obligatorias numéricas del esquema.

### Requirement: Reporte de calidad (faltantes, duplicados, atípicos)

El sistema DEBE generar, para un dataset dado, un reporte que identifique el porcentaje de valores faltantes por columna, los timestamps duplicados, y los valores fuera del rango físico/climático plausible definido para cada variable. La detección de atípicos de este reporte se basa en reglas de rango explícitas, no en modelos de aprendizaje automático.

#### Scenario: Dataset con un valor fuera de rango físico

- **GIVEN** un dataset con un valor de temperatura de 80°C en una fila (fuera del rango físico plausible)
- **WHEN** se genera el reporte de calidad
- **THEN** el reporte identifica esa fila como atípica para la columna de temperatura

#### Scenario: Dataset con timestamps duplicados

- **GIVEN** un dataset con dos filas que comparten el mismo timestamp
- **WHEN** se genera el reporte de calidad
- **THEN** el reporte identifica ese timestamp como duplicado

Implementado en `src/data_quality/quality_report.py` (`quality_report`), testeado en `tests/test_quality_report.py`. Verificado sobre el dataset real consolidado: 24.04% de faltantes en humedad de suelo, 100% en ET0 (esperado, no se ingiere directamente), 0 timestamps duplicados, 0 valores fuera de rango en ninguna columna.

### Requirement: Tratamiento de valores faltantes por interpolación temporal

El sistema DEBE poder imputar valores faltantes en una serie temporal mediante interpolación lineal entre el valor anterior y posterior válidos, preservando de forma explícita qué filas fueron imputadas (no deben quedar indistinguibles de los valores originales).

#### Scenario: Imputación de un valor faltante entre dos valores válidos

- **GIVEN** una serie temporal diaria con un valor faltante entre dos valores válidos consecutivos en el tiempo
- **WHEN** se aplica la interpolación de valores faltantes
- **THEN** el valor faltante se reemplaza por un valor interpolado linealmente entre los dos valores válidos, y la fila queda marcada como imputada

Implementado en `src/data_quality/imputation.py` (`interpolate_missing`), testeado en `tests/test_imputation.py`. Verificado sobre el dataset real: imputó 88 de 366 filas de humedad de suelo (los gaps del producto satelital ESA CCI), dejando 0 valores faltantes.

### Requirement: Estandarización numérica reversible para modelado

El sistema DEBE poder estandarizar (media cero, desvío uno) las columnas numéricas de un dataset, conservando los parámetros de la transformación (media y desvío por columna) de forma que la transformación pueda invertirse.

#### Scenario: Estandarización y reversión de una columna

- **GIVEN** un dataset con una columna numérica de media y desvío conocidos
- **WHEN** se estandariza esa columna y luego se revierte la transformación usando los parámetros guardados
- **THEN** los valores revertidos coinciden con los valores originales

Implementado en `src/data_quality/scaling.py` (`standardize`, `inverse_standardize`, y `apply_standardization` — agregada en `add-data-quality-integration` para aplicar parámetros ya ajustados sin recalcularlos, evitando fuga de información hacia el conjunto de evaluación), testeado en `tests/test_scaling.py` y `tests/test_scaling_apply.py`. Verificado con roundtrip exacto sobre el dataset real (temperatura, humedad de suelo imputada).

### Requirement: Partición entrenamiento/evaluación sin fuga temporal

El sistema DEBE poder particionar un dataset en un conjunto de entrenamiento y uno de evaluación mediante un corte cronológico simple, de forma que ninguna fecha del conjunto de evaluación sea anterior a ninguna fecha del conjunto de entrenamiento.

#### Scenario: Partición de una serie temporal por fecha de corte

- **GIVEN** un dataset con una columna de timestamp que cubre un año completo
- **WHEN** se particiona el dataset con una fecha de corte dada
- **THEN** el conjunto de entrenamiento contiene únicamente fechas anteriores a la fecha de corte y el conjunto de evaluación únicamente fechas posteriores o iguales a esa fecha

Implementado en `src/data_quality/splitting.py` (`temporal_train_test_split`), testeado en `tests/test_splitting.py`. Verificado sobre el dataset real: corte en 2024-10-01 produce 274 filas de entrenamiento (hasta 2024-09-30) y 92 de evaluación (desde 2024-10-01), sin fechas mezcladas.

### Requirement: Detección de anomalías no supervisada

El sistema DEBE poder marcar filas anómalas en un dataset sin requerir etiquetas de anomalía previas, usando un método no supervisado (Isolation Forest) sobre las columnas numéricas del esquema.

#### Scenario: Detección sobre un dataset sin anomalías etiquetadas

- **GIVEN** un dataset normalizado al esquema, sin ninguna columna de etiqueta de anomalía
- **WHEN** se ejecuta la detección de anomalías sobre sus columnas numéricas
- **THEN** el dataset resultante incluye una columna que marca cada fila como anómala o no, sin haber requerido ninguna etiqueta previa

Implementado en `src/data_quality/anomaly_detection.py` (`detect_anomalies`), testeado en `tests/test_anomaly_detection.py`. Verificado sobre el dataset real: marcó 19 de 366 filas (~5.2%, consistente con `contamination=0.05`), correspondientes a una ola de calor (fines de enero/inicio de febrero de 2024) y eventos de lluvia intensa (febrero-marzo de 2024) — ninguna de esas filas violaba el rango físico de `data_quality.rules`, lo que confirma que este requirement detecta un tipo de anomalía distinto y complementario al del reporte de calidad basado en reglas. Desde `openspec/changes/fix-anomaly-feature-integration/`, también existen `fit_anomaly_detector`/`apply_anomaly_detector` (fit/transform separados) para el caso donde `is_anomaly` se usa como variable predictora de un modelo (`architecture-integration`, HU6) y hace falta evitar que el conjunto de evaluación influya en su propia marca de anomalía.

### Requirement: Evaluación del detector mediante anomalías sintéticas inyectadas

El sistema DEBE poder evaluar la capacidad de detección del método base inyectando anomalías sintéticas conocidas sobre una copia de un dataset real y midiendo qué proporción de esas anomalías inyectadas el detector marca correctamente, dado que no existen anomalías reales etiquetadas contra las cuales evaluar.

#### Scenario: Evaluación con anomalías inyectadas conocidas

- **GIVEN** una copia de un dataset real con un conjunto conocido de filas modificadas a valores extremos (anomalías sintéticas inyectadas)
- **WHEN** se evalúa el detector sobre ese dataset modificado
- **THEN** se obtiene la proporción de las filas inyectadas que el detector efectivamente marcó como anómalas

Implementado en `src/data_quality/anomaly_detection.py` (`evaluate_with_injected_anomalies`), testeado en `tests/test_anomaly_detection.py`. Verificado sobre el dataset real: 100% de detección de 10 anomalías sintéticas inyectadas (valores extremos a 20 desvíos estándar de la media de cada columna).

### Requirement: Generación de datos sintéticos por muestreo estadístico

El sistema DEBE poder generar filas sintéticas ajustando una distribución normal multivariada a la media y matriz de covarianza de un conjunto de variables reales, y muestreando de esa distribución. Cada fila generada DEBE quedar marcada con procedencia `sintético`, conforme al esquema definido en `data-ingestion`.

#### Scenario: Generación de N filas sintéticas a partir de datos reales

- **GIVEN** un dataset real con un conjunto de variables numéricas correlacionadas entre sí
- **WHEN** se genera un número N de filas sintéticas a partir de ese dataset
- **THEN** el resultado tiene N filas, con procedencia `sintético` en cada una, y las mismas columnas que el dataset real

Implementado en `src/data_quality/synthetic_data.py` (`generate_synthetic`), testeado en `tests/test_synthetic_data.py`. Verificado sobre el dataset real: 366 filas sintéticas generadas, todas con `origen: sintetico`, mismas columnas que el dataset original.

### Requirement: Similitud estadística entre datos reales y sintéticos

El sistema DEBE poder comparar un dataset real y uno sintético generado a partir de él, reportando la diferencia entre sus medias, desvíos estándar y matriz de correlación entre variables.

#### Scenario: Comparación de un dataset sintético contra el real que lo originó

- **GIVEN** un dataset real y un dataset sintético generado a partir de sus estadísticos
- **WHEN** se evalúa la similitud estadística entre ambos
- **THEN** se obtiene, para cada variable, la diferencia de media y desvío, y la diferencia de la matriz de correlación entre variables

Implementado en `src/data_quality/synthetic_data.py` (`statistical_similarity`), testeado en `tests/test_synthetic_data.py`. Verificado sobre el dataset real: diferencia de correlación promedio de 0.023 entre el dataset real y 366 filas sintéticas generadas a partir de él.

### Requirement: Utilidad predictiva de los datos sintéticos

El sistema DEBE poder comparar la utilidad predictiva de datos reales contra datos sintéticos, entrenando un modelo simple sobre cada conjunto y evaluando ambos modelos contra un mismo conjunto de evaluación real.

#### Scenario: Comparación de utilidad predictiva real vs. sintético

- **GIVEN** un conjunto de entrenamiento real, su versión sintética generada, y un conjunto de evaluación real separado
- **WHEN** se entrena un modelo simple sobre el conjunto real y, por separado, sobre el sintético, y se evalúan ambos contra el conjunto de evaluación real
- **THEN** se obtiene una métrica de error comparable para el modelo entrenado con datos reales y para el entrenado con datos sintéticos

Implementado en `src/data_quality/synthetic_data.py` (`evaluate_predictive_utility`), testeado en `tests/test_synthetic_data.py`. Verificado sobre el dataset real: un modelo de regresión lineal que predice humedad de suelo a partir de variables climáticas, evaluado sobre el mismo conjunto de test real, obtuvo MAE 0.02312 entrenado con datos reales y MAE 0.02323 entrenado con datos sintéticos — utilidad predictiva casi idéntica en este caso.

### Requirement: Flujo integrado y parametrizable por configuración experimental

El sistema DEBE poder ejecutar, en un único procedimiento reproducible, el reporte de calidad, la imputación de faltantes, la partición entrenamiento/evaluación, la detección de anomalías (opcional) y la generación de datos sintéticos (opcional), de forma que las 4 configuraciones experimentales de la Épica 4 (base, +sintéticos, +anomalías, completa) se puedan seleccionar sin reescribir código. Los parámetros de estandarización DEBEN ajustarse únicamente sobre el conjunto de entrenamiento y aplicarse, sin recalcular, al conjunto de evaluación y a los datos sintéticos.

#### Scenario: Configuración base sin anomalías ni datos sintéticos

- **GIVEN** un dataset real con valores faltantes en alguna columna
- **WHEN** se ejecuta el flujo integrado con detección de anomalías y datos sintéticos desactivados
- **THEN** el conjunto de entrenamiento resultante no tiene valores faltantes, no tiene columna de anomalías, y todas sus filas tienen procedencia `real`

#### Scenario: Configuración completa con anomalías y datos sintéticos

- **GIVEN** el mismo dataset real
- **WHEN** se ejecuta el flujo integrado con detección de anomalías y datos sintéticos activados
- **THEN** el conjunto de entrenamiento resultante tiene una columna de anomalías y contiene tanto filas con procedencia `real` como filas con procedencia `sintético`

#### Scenario: Los parámetros de escalado no usan estadísticos del conjunto de evaluación

- **GIVEN** un dataset real particionado en entrenamiento y evaluación
- **WHEN** se ejecuta el flujo integrado
- **THEN** los parámetros de estandarización devueltos coinciden con la media y el desvío calculados únicamente sobre el conjunto de entrenamiento

Implementado en `src/data_quality/pipeline.py` (`run_quality_pipeline`) y `scripts/run_data_quality_pipeline.py`, testeado en `tests/test_pipeline.py`. Los flags `include_anomaly_detection`/`include_synthetic` son parámetros booleanos simples, no una herramienta de feature flags — decisión explícita (ver `openspec/changes/add-data-quality-integration/proposal.md`) dado que la Épica 4 solo necesita seleccionar 4 configuraciones conocidas de antemano al lanzar una corrida, no alternar comportamiento en tiempo de ejecución para usuarios/entornos. Verificado sobre el dataset real en las 4 configuraciones: base (274 train / 92 test, sin anomalías ni sintéticos), +sintéticos (374 train con 100 filas sintéticas agregadas), +anomalías (columna `is_anomaly` presente), completa (ambas). Los parámetros de escalado se confirmaron calculados solo sobre el conjunto de entrenamiento real.

## Limitaciones conocidas

- Verificado con un único dataset real (Melchor Romero 2024, consolidado de NASA POWER + ESA CCI). No se validó con datos de otros puntos geográficos o años.
- Los rangos agronómicos son genéricos (físicos/climáticos plausibles), no específicos de un cultivo hortícola en particular — una iteración futura podría acotarlos por cultivo si se justifica.
- La detección de atípicos basada en reglas de rango (`quality_report`) y la detección de anomalías no supervisada (`anomaly_detection`) son complementarias, no intercambiables: la primera detecta valores físicamente imposibles, la segunda detecta valores estadísticamente atípicos aunque sean físicamente plausibles (confirmado en la práctica: los eventos marcados por Isolation Forest en el dataset real no violaban ningún rango físico).
- El detector de anomalías se evaluó únicamente con anomalías sintéticas inyectadas (no hay anomalías reales etiquetadas en este dominio); no hay evidencia de su desempeño sobre fallas de sensor reales no evidentes a simple vista. En `run_quality_pipeline`, la detección de anomalías se ajusta por separado sobre entrenamiento y evaluación (cada partición fitea su propio Isolation Forest); a diferencia de la estandarización, esto no se corrigió para evitar fuga, porque el flag de anomalía no es un parámetro que se filtre hacia un modelo de la misma manera — queda documentado como simplificación deliberada, no como descuido.
- La generación de datos sintéticos asume una distribución normal multivariada; variables con distribuciones marcadamente distintas a la normal (ej. precipitación, con muchos ceros y cola derecha larga) se modelan de forma aproximada, no exacta. Un modelo generativo profundo (GAN/VAE) queda como candidato a evaluar cuando haya más datos reales disponibles (ver `openspec/changes/add-synthetic-data-generation/proposal.md`, "Alternativas consideradas").
- La utilidad predictiva se evaluó con un modelo de regresión lineal simple, no con el modelo que finalmente se use en `predictive-modeling` (HU4, no iniciada); el resultado (MAE similar entre real y sintético) es una señal favorable para este prototipo, no una garantía de que se sostenga con un modelo más complejo.
- El flujo integrado se verificó con una única semilla/corrida por configuración; la ejecución sistemática con múltiples repeticiones/semillas corresponde a `experiment-runner` (HU7, no iniciada).
