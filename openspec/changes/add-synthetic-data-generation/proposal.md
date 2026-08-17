# Change: Add synthetic-data-generation capability

> **Estado: implementado.** Ver `openspec/specs/data-quality/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU3 — Componente de calidad y robustez de datos (subconjunto: generación de datos sintéticos, tercero de tres sub-proyectos en que se dividió HU3).
- **Fase de CRISP-DM:** Modelado.
- **Configuración experimental afectada:** base+sintéticos y completa (Épica 4) — este componente es uno de los que se activa/desactiva para comparar configuraciones.
- **Insumo de diseño:** [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (distribuciones y rangos reales), [`docs/research/hu1-variables-y-antecedentes.md`](../../../docs/research/hu1-variables-y-antecedentes.md) (antecedentes de generación de datos sintéticos en agricultura).

## Why

El criterio ético del plan de tesis (sección 12.2) exige separar y marcar explícitamente los datos sintéticos desde la ingesta — ya resuelto por el flag `origen` de `data-ingestion` (HU2). Falta el componente que genere esos datos sintéticos. El dataset real disponible hoy (`data/melchor_romero_2024_consolidado.parquet`, 366 filas) es pequeño para entrenar un modelo generativo profundo (GAN/VAE, mencionados en los antecedentes de HU1) de forma confiable; se decide un prototipo con un método estadístico más simple ahora, dejando el generativo profundo para cuando haya más datos reales disponibles (ver "Alternativas consideradas").

## What Changes

- Se agrega la generación de datos sintéticos al componente `data-quality`.
- **Técnica candidata seleccionada:** muestreo de una distribución normal multivariada ajustada a la media y matriz de covarianza de las variables reales — preserva las correlaciones entre variables sin requerir aprendizaje profundo, apropiado para el tamaño de dataset disponible hoy.
- Se implementa el prototipo: ajuste de la distribución a un dataset real y generación de N filas sintéticas, marcadas con `origen: sintético` (esquema ya definido en `data-ingestion`).
- Se evalúa similitud estadística (medias, desvíos y correlaciones entre variables) comparando el dataset real contra el sintético generado.
- Se evalúa utilidad predictiva: se entrena un modelo simple de regresión (predicción de humedad de suelo a partir de variables climáticas) sobre datos reales y, por separado, sobre datos sintéticos, y se comparan ambos contra el mismo conjunto de evaluación real — sin que esto constituya el modelo de `predictive-modeling` (HU4, no iniciada), solo una métrica de utilidad para este *change*.

## Impact

- **Specs afectadas:** `data-quality` (extiende el spec existente con requirements nuevos).
- **Specs futuras que dependen de esta:** `predictive-modeling` (HU4) podrá usar datos sintéticos para complementar escenarios de escasez de datos, según el criterio ético de mantenerlos siempre identificables.
- **Código afectado:** nuevo módulo `src/data_quality/synthetic_data.py`, sin modificar los módulos ya existentes de `data_quality` ni `data_ingestion`.
- **Fuera de alcance de este change:** un modelo generativo profundo (GAN/VAE); la integración final de los tres sub-proyectos de HU3 en un flujo reproducible (tarea aparte de HU3, todavía pendiente).

## Alternativas consideradas

- **GAN o VAE (PyTorch)**: se descarta para este prototipo, no de forma definitiva, porque 366 filas es un dataset pequeño para entrenar un modelo generativo profundo de forma confiable; ADR-0002 ya habilita PyTorch para cuando el estado del arte o los resultados experimentales lo justifiquen. Queda como candidato a reevaluar cuando haya más datos reales disponibles (más fuentes, más años, o la incorporación de SMN/Copernicus).
- **Bootstrap/perturbación simple de filas reales**: se descarta porque no genera variabilidad genuinamente nueva más allá de las filas ya observadas, a diferencia de muestrear de una distribución ajustada.
