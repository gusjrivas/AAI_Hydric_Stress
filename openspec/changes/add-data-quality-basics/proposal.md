# Change: Add data-quality-basics capability

> **Estado: implementado.** Ver `openspec/specs/data-quality/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU3 — Componente de calidad y robustez de datos (subconjunto: calidad/limpieza básica, primero de tres sub-proyectos en que se dividió HU3).
- **Fase de CRISP-DM:** Preparación de los datos.
- **Configuración experimental afectada:** ninguna directamente (esta capacidad prepara los datos para todas las configuraciones de la Épica 4; no es en sí misma una de las configuraciones comparadas).
- **Insumo de diseño:** [`openspec/specs/data-ingestion/spec.md`](../../specs/data-ingestion/spec.md) (esquema y datasets de origen), `data/melchor_romero_2024_consolidado.parquet` (primer conjunto experimental real).

## Why

HU3 tiene 14 tareas que cubren tres áreas distintas: calidad/limpieza básica, detección de anomalías, y generación de datos sintéticos. Se decidió dividir HU3 en tres *changes* independientes, empezando por calidad/limpieza básica porque es un prerequisito lógico de los otros dos: no tiene sentido detectar anomalías con criterio sin antes tener reglas de calidad explícitas, ni evaluar similitud estadística de datos sintéticos sin antes conocer las distribuciones reales de las variables.

Hoy el conjunto experimental de `data-ingestion` (HU2) tiene datos reales pero sin ningún análisis de calidad: no se conocen sus distribuciones ni rangos, no hay reglas de calidad agronómicas explícitas, los valores faltantes (ej. el 24% de huecos en humedad de suelo del dataset consolidado) no tienen tratamiento, y no existe un esquema de partición train/test que evite fuga de información temporal para el futuro modelado de HU4.

## What Changes

- Se agrega la capacidad `data-quality`, responsable de analizar, validar y preparar el conjunto experimental de datos para modelado (capa 2/3 del ADR-0001, previa a los módulos de IA propiamente dichos).
- Se define un reporte de distribuciones (tipo, rango, media, desvío) por columna del esquema.
- Se definen rangos físicos/climáticos plausibles por variable (rangos genéricos, no específicos de un cultivo hortícola en particular), con su justificación.
- Se define un reporte de calidad que identifica valores faltantes, timestamps duplicados y valores atípicos (fuera del rango físico plausible) — un método basado en reglas, explícitamente más simple que la detección de anomalías por aprendizaje automático que cubrirá el *change* siguiente de HU3.
- Se define el tratamiento de valores faltantes por interpolación temporal lineal, preservando trazabilidad de qué filas fueron imputadas.
- Se define la estandarización numérica de variables para preparación de modelado (HU4), con los parámetros de escalado guardados para poder invertir la transformación.
- Se define un esquema de partición entrenamiento/evaluación por corte cronológico simple, sin mezclar fechas entre ambos conjuntos, para evitar fuga de información temporal.

## Impact

- **Specs afectadas:** `data-quality` (nueva).
- **Specs futuras que dependen de esta:** el *change* siguiente de HU3 (detección de anomalías) consumirá el reporte de calidad y las reglas de rango; el de generación de datos sintéticos consumirá el reporte de distribuciones; `predictive-modeling` (HU4) consumirá la estandarización y la partición train/test.
- **Código afectado:** nuevo paquete `src/data_quality/`, sin modificar `src/data_ingestion/`.
- **Fuera de alcance de este change:** detección de anomalías por aprendizaje automático y generación de datos sintéticos (corresponden a los otros dos *changes* de HU3, todavía no iniciados).
