# Change: Add feature-engineering capability

> **Estado: implementado.** Ver `openspec/specs/predictive-modeling/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU4 — Componente de modelado predictivo (subconjunto: definición del problema e ingeniería de variables, primero de tres sub-proyectos en que se dividió HU4).
- **Fase de CRISP-DM:** Preparación de los datos / Modelado.
- **Configuración experimental afectada:** ninguna todavía (esta capacidad es previa a las 4 configuraciones comparadas en la Épica 4; sienta la base de la que dependen todas).
- **Insumo de diseño:** [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (conjunto experimental ya limpio, particionado y parametrizable), [`docs/research/hu1-variables-y-antecedentes.md`](../../../docs/research/hu1-variables-y-antecedentes.md) (humedad de suelo como variable predictora central de estrés hídrico).

## Why

`data-quality` (HU3) deja un conjunto experimental limpio, particionado y parametrizable por configuración, pero no define todavía qué se predice ni con qué anticipación — sin eso, no hay nada que entrenar en los sub-proyectos siguientes de HU4 (modelos base/candidatos, alertas).

No existen datos de capacidad de campo ni punto de marchitez calibrados para el suelo del punto evaluado (Melchor Romero), por lo que un umbral agronómico absoluto de estrés hídrico no es calculable con rigor todavía. Se decide un umbral relativo (percentil de la distribución observada) como proxy explícito, documentado como limitación, no como validación agronómica definitiva.

## What Changes

- Se agrega la capacidad `predictive-modeling`, responsable de transformar el conjunto experimental de `data-quality` en una matriz de variables (features) y una variable objetivo lista para modelado.
- **Variable objetivo:** clasificación binaria — si la humedad de suelo va a caer por debajo de un umbral en el horizonte de anticipación, sí o no. Se prefiere sobre una regresión del valor futuro porque encaja directo con el objetivo de "alerta temprana" (siguiente sub-proyecto de HU4) y es más simple de evaluar y comunicar.
- **Umbral de estrés:** percentil 20 de la distribución histórica de humedad de suelo observada en el propio punto/período (no un umbral agronómico absoluto, por falta de calibración de capacidad de campo/punto de marchitez).
- **Horizonte de anticipación:** 3 días.
- Se implementan variables predictoras con retardos (*lags*) y ventanas móviles (*rolling*) de las variables climáticas y de humedad de suelo, construidas exclusivamente con información disponible hasta el día de la predicción (sin mirar al futuro).
- Se evalúa relevancia de variables (correlación con el objetivo) y se verifica explícitamente, con un test, que ninguna variable predictora contiene información del período posterior al día de la predicción (fuga temporal).

## Impact

- **Specs afectadas:** `predictive-modeling` (nueva).
- **Specs futuras que dependen de esta:** el *change* siguiente de HU4 (modelos base/candidatos) consumirá directamente la matriz de variables y la variable objetivo definidas acá.
- **Código afectado:** nuevo paquete `src/predictive_modeling/`, sin modificar `src/data_quality/` ni `src/data_ingestion/`.
- **Fuera de alcance de este change:** entrenamiento de cualquier modelo (siguiente *change* de HU4); lógica de generación de alertas (tercer *change* de HU4).

## Alternativas consideradas

- **Regresión del valor futuro de humedad de suelo**: se descarta para este *change* (no definitivamente) por ser más compleja de evaluar; la clasificación binaria encaja más directo con el objetivo de alerta temprana del plan de tesis.
- **Umbral agronómico absoluto**: se descarta por ahora porque requeriría datos de capacidad de campo/punto de marchitez del suelo específico, que no están disponibles; el umbral relativo queda documentado como proxy explícito, reevaluable si se consiguen esos datos.
