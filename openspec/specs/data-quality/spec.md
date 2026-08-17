# Spec: data-quality

Capacidad implementada (Épica 2, HU3 — primer sub-proyecto: calidad/limpieza básica). Origen: `openspec/changes/add-data-quality-basics/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

Los otros dos sub-proyectos de HU3 (detección de anomalías, generación de datos sintéticos) todavía no comenzaron y se documentarán como *changes* independientes que extienden esta spec.

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

Implementado en `src/data_quality/scaling.py` (`standardize`, `inverse_standardize`), testeado en `tests/test_scaling.py`. Verificado con roundtrip exacto sobre el dataset real (temperatura, humedad de suelo imputada).

### Requirement: Partición entrenamiento/evaluación sin fuga temporal

El sistema DEBE poder particionar un dataset en un conjunto de entrenamiento y uno de evaluación mediante un corte cronológico simple, de forma que ninguna fecha del conjunto de evaluación sea anterior a ninguna fecha del conjunto de entrenamiento.

#### Scenario: Partición de una serie temporal por fecha de corte

- **GIVEN** un dataset con una columna de timestamp que cubre un año completo
- **WHEN** se particiona el dataset con una fecha de corte dada
- **THEN** el conjunto de entrenamiento contiene únicamente fechas anteriores a la fecha de corte y el conjunto de evaluación únicamente fechas posteriores o iguales a esa fecha

Implementado en `src/data_quality/splitting.py` (`temporal_train_test_split`), testeado en `tests/test_splitting.py`. Verificado sobre el dataset real: corte en 2024-10-01 produce 274 filas de entrenamiento (hasta 2024-09-30) y 92 de evaluación (desde 2024-10-01), sin fechas mezcladas.

## Limitaciones conocidas

- Verificado con un único dataset real (Melchor Romero 2024, consolidado de NASA POWER + ESA CCI). No se validó con datos de otros puntos geográficos o años.
- Los rangos agronómicos son genéricos (físicos/climáticos plausibles), no específicos de un cultivo hortícola en particular — una iteración futura podría acotarlos por cultivo si se justifica.
- La detección de atípicos de este *change* es puramente basada en reglas de rango; no reemplaza la detección de anomalías por aprendizaje automático (sub-proyecto separado de HU3, todavía no iniciado).
- La estandarización usa media/desvío del propio dataset (no de un conjunto de referencia externo); si se aplica por separado a train y test, cada partición tendría sus propios parámetros — al usar esta función en HU4, se recomienda ajustar los parámetros solo sobre el conjunto de entrenamiento y aplicarlos también al de evaluación, para evitar fuga de información.
