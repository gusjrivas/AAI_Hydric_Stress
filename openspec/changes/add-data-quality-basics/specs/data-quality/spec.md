# Spec delta: data-quality

## ADDED Requirements

### Requirement: Reporte de distribuciones por variable

El sistema DEBE generar, para cada columna del esquema presente en un dataset, un reporte con tipo de dato, valor mínimo, máximo, media y desvío estándar.

#### Scenario: Distribuciones de un dataset con variables numéricas

- **GIVEN** un dataset normalizado al esquema con columnas obligatorias y opcionales
- **WHEN** se genera el reporte de distribuciones
- **THEN** el reporte incluye, para cada columna numérica presente, su tipo, mínimo, máximo, media y desvío estándar

### Requirement: Rangos físicos/climáticos plausibles por variable

El sistema DEBE definir, para cada columna obligatoria del esquema, un rango físico o climático plausible (mínimo y máximo genéricos, no específicos de un cultivo en particular), documentado con su justificación.

#### Scenario: Consulta del rango plausible de una variable

- **GIVEN** el esquema de columnas obligatorias definido en `data_ingestion.schema`
- **WHEN** se consulta el rango plausible de la variable "temperatura"
- **THEN** se obtiene un rango numérico (mínimo, máximo) documentado, sin necesidad de ejecutar ningún análisis de datos

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

### Requirement: Tratamiento de valores faltantes por interpolación temporal

El sistema DEBE poder imputar valores faltantes en una serie temporal mediante interpolación lineal entre el valor anterior y posterior válidos, preservando de forma explícita qué filas fueron imputadas (no deben quedar indistinguibles de los valores originales).

#### Scenario: Imputación de un valor faltante entre dos valores válidos

- **GIVEN** una serie temporal diaria con un valor faltante entre dos valores válidos consecutivos en el tiempo
- **WHEN** se aplica la interpolación de valores faltantes
- **THEN** el valor faltante se reemplaza por un valor interpolado linealmente entre los dos valores válidos, y la fila queda marcada como imputada

### Requirement: Estandarización numérica reversible para modelado

El sistema DEBE poder estandarizar (media cero, desvío uno) las columnas numéricas de un dataset, conservando los parámetros de la transformación (media y desvío por columna) de forma que la transformación pueda invertirse.

#### Scenario: Estandarización y reversión de una columna

- **GIVEN** un dataset con una columna numérica de media y desvío conocidos
- **WHEN** se estandariza esa columna y luego se revierte la transformación usando los parámetros guardados
- **THEN** los valores revertidos coinciden con los valores originales

### Requirement: Partición entrenamiento/evaluación sin fuga temporal

El sistema DEBE poder particionar un dataset en un conjunto de entrenamiento y uno de evaluación mediante un corte cronológico simple, de forma que ninguna fecha del conjunto de evaluación sea anterior a ninguna fecha del conjunto de entrenamiento.

#### Scenario: Partición de una serie temporal por fecha de corte

- **GIVEN** un dataset con una columna de timestamp que cubre un año completo
- **WHEN** se particiona el dataset con una fecha de corte dada
- **THEN** el conjunto de entrenamiento contiene únicamente fechas anteriores a la fecha de corte y el conjunto de evaluación únicamente fechas posteriores o iguales a esa fecha
