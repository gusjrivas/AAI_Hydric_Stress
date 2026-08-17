# Spec: data-ingestion

Capacidad implementada (Épica 1, HU2). Origen: `openspec/changes/add-data-ingestion/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

## Requirements

### Requirement: Contrato de acceso a datos estable

El sistema DEBE exponer una interfaz de acceso a datos (`load_dataset()` / `save_dataset()`) que devuelva y reciba estructuras tabulares estándar, de forma que ningún módulo de las capas de calidad, modelado o retroalimentación humana dependa del formato de almacenamiento subyacente (ADR-0002).

#### Scenario: Un módulo de otra capa lee datos ingeridos

- **GIVEN** un dataset ya ingerido y almacenado en el backend local (Parquet/CSV)
- **WHEN** un módulo de la capa de calidad (`data-quality`, HU3) invoca `load_dataset()` para ese dataset
- **THEN** recibe una estructura tabular estándar sin conocer ni depender del formato de archivo subyacente

Implementado en `src/data_ingestion/storage.py` (`load_dataset`, `save_dataset`), testeado en `tests/test_storage.py`.

### Requirement: Esquema con columnas obligatorias y opcionales

El sistema DEBE distinguir explícitamente, en el esquema de cada dataset ingerido, entre columnas obligatorias (humedad de suelo, temperatura, humedad relativa, precipitación, radiación solar, velocidad del viento, evapotranspiración de referencia derivada, marca temporal) y columnas opcionales (temperatura de canopia, índices de vegetación, conductancia estomática o potencial hídrico foliar).

#### Scenario: Ingesta de una fuente que no reporta todas las variables opcionales

- **GIVEN** una fuente de datos que solo reporta humedad de suelo y variables climáticas obligatorias
- **WHEN** se ingesta esa fuente
- **THEN** el dataset resultante es válido para modelado (cumple las columnas obligatorias) y las columnas opcionales quedan ausentes o nulas sin invalidar el dataset

Implementado en `src/data_ingestion/schema.py` (`REQUIRED_COLUMNS`, `OPTIONAL_COLUMNS`, `normalize_to_schema`), testeado en `tests/test_schema.py`. Verificado con datos reales: NASA POWER no reporta humedad de suelo, ESA CCI Soil Moisture no reporta variables climáticas, y ambos datasets son válidos individualmente.

### Requirement: Flag de procedencia real/sintético desde la ingesta

El sistema DEBE registrar, para cada fila ingerida, un campo de procedencia con valor `real`, fijado en el momento de la ingesta y no como un atributo agregado posteriormente por otro componente.

#### Scenario: Ingesta de una fuente de datos real

- **GIVEN** una fuente de datos pública o de campo
- **WHEN** se ingesta esa fuente mediante esta capacidad
- **THEN** cada fila del dataset resultante queda marcada con procedencia `real`

Implementado en `src/data_ingestion/schema.py` (`normalize_to_schema`, columna `origen`), testeado en `tests/test_schema.py`. Confirmado con datos reales de NASA POWER y ESA CCI (`origen: real` en ambos datasets).

### Requirement: Preservación de la resolución temporal nativa junto a una vista diaria

El sistema DEBE conservar la serie en su resolución temporal nativa y, adicionalmente, DEBE exponer una vista agregada a granularidad diaria, para que fuentes de campo de alta frecuencia y fuentes públicas de granularidad diaria (SMN, NASA POWER, Copernicus) sean comparables.

#### Scenario: Ingesta de una fuente de campo de alta frecuencia

- **GIVEN** una fuente de sensores de campo que reporta cada 15 minutos
- **WHEN** se ingesta esa fuente
- **THEN** el dataset conserva la serie a 15 minutos y además queda disponible una vista agregada diaria derivada de esa serie

Implementado en `src/data_ingestion/aggregation.py` (`to_daily`), testeado en `tests/test_aggregation.py`. Las fuentes reales incorporadas hasta ahora (NASA POWER, ESA CCI) ya son diarias en origen; el mecanismo de agregación no fue ejercitado todavía con una fuente de campo de mayor frecuencia real.

### Requirement: Reporte de cobertura por columna obligatoria

El sistema DEBE generar, para cada dataset ingerido, un reporte de cobertura que indique el rango temporal cubierto y el porcentaje de completitud de cada columna obligatoria.

#### Scenario: Ingesta con datos faltantes en una variable obligatoria

- **GIVEN** una fuente de datos con valores faltantes en la columna de precipitación durante parte del período cubierto
- **WHEN** se genera el reporte de cobertura del dataset ingerido
- **THEN** el reporte indica el porcentaje de completitud de la columna de precipitación y el rango temporal afectado

Implementado en `src/data_ingestion/coverage.py` (`coverage_report`), testeado en `tests/test_coverage.py`. Verificado con datos reales: el dataset consolidado de Melchor Romero 2024 reporta 100% de completitud en variables climáticas y 75.96% en humedad de suelo (gaps reales del producto satelital).

### Requirement: Diccionario de datos versionado por fuente

El sistema DEBE producir, para cada fuente ingerida, un diccionario de datos que documente procedencia, licencia, restricciones de uso y limitaciones conocidas, versionado junto con el dataset correspondiente.

#### Scenario: Se agrega una nueva fuente de datos al conjunto experimental

- **GIVEN** una nueva fuente de datos seleccionada para el conjunto experimental
- **WHEN** se ejecuta el procedimiento de ingesta para esa fuente
- **THEN** se genera un diccionario de datos versionado que documenta su procedencia, licencia y limitaciones, reproducible a partir de esa documentación

Implementado en `src/data_ingestion/dictionary.py` (`write_data_dictionary`), testeado en `tests/test_dictionary.py`. Diccionarios reales generados para NASA POWER y ESA CCI Soil Moisture (`data/dictionaries/`, gitignorado por diseño — ver ADR-0002).

### Requirement: Consolidación multi-fuente por timestamp

El sistema DEBE poder combinar varios datasets ya normalizados al esquema en un único conjunto experimental, indexado por timestamp, sin perder los valores no nulos que cada fuente aporte a columnas distintas.

#### Scenario: Dos fuentes complementarias se consolidan en un conjunto único

- **GIVEN** un dataset de variables climáticas (sin humedad de suelo) y un dataset de humedad de suelo (sin variables climáticas), ambos con la misma columna de timestamp
- **WHEN** se consolidan ambos datasets
- **THEN** el dataset resultante contiene, para cada timestamp común, tanto las variables climáticas como la humedad de suelo

Implementado en `src/data_ingestion/consolidate.py` (`consolidate_sources`), testeado en `tests/test_consolidate.py`. Verificado con datos reales: `data/melchor_romero_2024_consolidado.parquet` combina NASA POWER y ESA CCI Soil Moisture para 366 días. Este requisito no formaba parte de la propuesta original del *change* (que solo mencionaba homogeneización dentro de una fuente); se agregó aquí porque es el objetivo explícito de la tarea "Implementar procedimiento reproducible de ingestión y consolidación" del plan de tesis (HU2), y la propuesta original lo dejaba implícito sin un requisito propio.

## Limitaciones conocidas

- Ejecutado y verificado con datos reales para dos fuentes (NASA POWER, ESA CCI Soil Moisture), un único punto geográfico (Melchor Romero, Partido de La Plata) y un único año (2024). No se validó con múltiples ubicaciones ni múltiples años.
- SMN (bloqueado por acceso técnico) y Copernicus (bloqueado por falta de registro) no están incorporados como fuentes reales — ver `docs/research/hu2-fuentes-datos-acceso.md`.
- No hay criterios explícitos de calidad/relevancia agronómica para seleccionar o descartar fuentes candidatas (tarea de HU2 aparte, todavía sin cerrar — ver `docs/seguimiento-tareas.md`).
- ET0 (evapotranspiración de referencia) es una columna obligatoria del esquema pero se deriva en preprocesamiento, no se ingiere directamente de ninguna fuente todavía.
