# Spec delta: data-ingestion

## ADDED Requirements

### Requirement: Contrato de acceso a datos estable

El sistema DEBE exponer una interfaz de acceso a datos (`load_dataset()` / `save_dataset()`) que devuelva y reciba estructuras tabulares estándar, de forma que ningún módulo de las capas de calidad, modelado o retroalimentación humana dependa del formato de almacenamiento subyacente (ADR-0002).

#### Scenario: Un módulo de otra capa lee datos ingeridos

- **GIVEN** un dataset ya ingerido y almacenado en el backend local (Parquet/CSV)
- **WHEN** un módulo de la capa de calidad (`data-quality`, HU3) invoca `load_dataset()` para ese dataset
- **THEN** recibe una estructura tabular estándar sin conocer ni depender del formato de archivo subyacente

### Requirement: Esquema con columnas obligatorias y opcionales

El sistema DEBE distinguir explícitamente, en el esquema de cada dataset ingerido, entre columnas obligatorias (humedad de suelo, temperatura, humedad relativa, precipitación, radiación solar, velocidad del viento, evapotranspiración de referencia derivada, marca temporal) y columnas opcionales (temperatura de canopia, índices de vegetación, conductancia estomática o potencial hídrico foliar).

#### Scenario: Ingesta de una fuente que no reporta todas las variables opcionales

- **GIVEN** una fuente de datos que solo reporta humedad de suelo y variables climáticas obligatorias
- **WHEN** se ingesta esa fuente
- **THEN** el dataset resultante es válido para modelado (cumple las columnas obligatorias) y las columnas opcionales quedan ausentes o nulas sin invalidar el dataset

### Requirement: Flag de procedencia real/sintético desde la ingesta

El sistema DEBE registrar, para cada fila ingerida, un campo de procedencia con valor `real`, fijado en el momento de la ingesta y no como un atributo agregado posteriormente por otro componente.

#### Scenario: Ingesta de una fuente de datos real

- **GIVEN** una fuente de datos pública o de campo
- **WHEN** se ingesta esa fuente mediante esta capacidad
- **THEN** cada fila del dataset resultante queda marcada con procedencia `real`

### Requirement: Preservación de la resolución temporal nativa junto a una vista diaria

El sistema DEBE conservar la serie en su resolución temporal nativa y, adicionalmente, DEBE exponer una vista agregada a granularidad diaria, para que fuentes de campo de alta frecuencia y fuentes públicas de granularidad diaria (SMN, NASA POWER, Copernicus) sean comparables.

#### Scenario: Ingesta de una fuente de campo de alta frecuencia

- **GIVEN** una fuente de sensores de campo que reporta cada 15 minutos
- **WHEN** se ingesta esa fuente
- **THEN** el dataset conserva la serie a 15 minutos y además queda disponible una vista agregada diaria derivada de esa serie

### Requirement: Reporte de cobertura por columna obligatoria

El sistema DEBE generar, para cada dataset ingerido, un reporte de cobertura que indique el rango temporal cubierto y el porcentaje de completitud de cada columna obligatoria.

#### Scenario: Ingesta con datos faltantes en una variable obligatoria

- **GIVEN** una fuente de datos con valores faltantes en la columna de precipitación durante parte del período cubierto
- **WHEN** se genera el reporte de cobertura del dataset ingerido
- **THEN** el reporte indica el porcentaje de completitud de la columna de precipitación y el rango temporal afectado

### Requirement: Diccionario de datos versionado por fuente

El sistema DEBE producir, para cada fuente ingerida, un diccionario de datos que documente procedencia, licencia, restricciones de uso y limitaciones conocidas, versionado junto con el dataset correspondiente.

#### Scenario: Se agrega una nueva fuente de datos al conjunto experimental

- **GIVEN** una nueva fuente de datos seleccionada para el conjunto experimental
- **WHEN** se ejecuta el procedimiento de ingesta para esa fuente
- **THEN** se genera un diccionario de datos versionado que documenta su procedencia, licencia y limitaciones, reproducible a partir de esa documentación
