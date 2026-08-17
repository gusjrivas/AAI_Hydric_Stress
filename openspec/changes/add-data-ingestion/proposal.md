# Change: Add data-ingestion capability

> **Estado: implementado.** Ver `openspec/specs/data-ingestion/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 1. Fundamentación científica y preparación de la información.
- **Historia de usuario:** HU2 — Preparación del conjunto experimental de datos.
- **Fase de CRISP-DM:** Comprensión de los datos / Preparación de los datos.
- **Configuración experimental afectada:** ninguna (esta capacidad es previa a las configuraciones comparadas en la Épica 4; toda configuración depende de ella).
- **Insumo de diseño:** [`docs/research/hu1-variables-y-antecedentes.md`](../../../docs/research/hu1-variables-y-antecedentes.md) (borrador preliminar de variables predictoras, antecedentes y criterios de diseño).

## Why

El resto de la arquitectura (calidad/robustez de datos, modelado predictivo, generación de alertas, retroalimentación humana) no puede construirse ni evaluarse sin un conjunto experimental de datos caracterizado, reproducible y con un esquema estable. Hoy no existe ninguna capacidad de ingesta: no hay forma de traer datos de humedad de suelo, variables climáticas o de riego al proyecto de forma trazable.

El borrador de HU1 (variables y antecedentes) ya identificó las variables obligatorias/opcionales y los criterios de diseño (granularidad, separación real/sintético, tolerancia a falta de etiquetas de calidad) que este esquema debe respetar. Sin fijarlos ahora en una capacidad concreta, cada componente posterior (HU3, HU4) tendría que inventar su propio esquema de datos, contradiciendo el contrato de acceso a datos versionado definido en el ADR-0002.

## What Changes

- Se agrega la capacidad `data-ingestion`, responsable de identificar, descargar, homogeneizar y documentar el conjunto experimental de datos (capa 2 del ADR-0001: almacenamiento y preprocesamiento).
- Se define el **contrato de acceso a datos** (`load_dataset()` / `save_dataset()`) exigido por el ADR-0002, con un esquema tabular que distingue columnas obligatorias (humedad de suelo, temperatura, humedad relativa, precipitación, radiación, viento, ET0 derivada, timestamp) de columnas opcionales (temperatura de canopia, NDVI, conductancia estomática/potencial hídrico).
- Se define el flag de procedencia (`origen: real | sintético`) desde la ingesta, en lugar de agregarlo posteriormente, conforme al criterio ético del plan de tesis (sección 12.2) y a la vacancia identificada en el borrador de HU1.
- Se define un mecanismo de agregación a granularidad diaria que conserva la serie nativa, para que las fuentes de campo (mayor frecuencia) y las fuentes públicas (SMN, NASA POWER, Copernicus — típicamente diarias) sean comparables sin perder resolución.
- Se define un reporte de cobertura por columna obligatoria (fecha de inicio/fin, % de completitud), consumible por la futura capacidad `data-quality` (HU3).
- Se define el diccionario de datos como artefacto versionado junto con cada fuente ingerida (procedencia, licencia, restricciones de uso), exigido por la gobernanza de datos (sección 12.1) y por el criterio de aceptación de HU2.

## Impact

- **Specs afectadas:** `data-ingestion` (nueva).
- **Specs futuras que dependen de esta:** `data-quality` (HU3) consumirá el reporte de cobertura y el flag de procedencia; `predictive-modeling` (HU4) consumirá el esquema agregado diario.
- **Código afectado:** aún no existe código en el repositorio; este change habilita la primera implementación.
- **Fuera de alcance de este change:** la limpieza/imputación de valores faltantes, la detección de anomalías y la generación de datos sintéticos (corresponden a `data-quality`, HU3).
