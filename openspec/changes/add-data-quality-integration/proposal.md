# Change: Integrate data-quality sub-projects into a reproducible pipeline

> **Estado: implementado.** Ver `openspec/specs/data-quality/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU3 — Componente de calidad y robustez de datos (tareas de cierre: integración y documentación final).
- **Fase de CRISP-DM:** Preparación de los datos.
- **Configuración experimental afectada:** las 4 configuraciones de la Épica 4 (base, +sintéticos, +anomalías, completa) — esta capacidad es justamente la que las hace seleccionables sin reescribir código.
- **Insumo de diseño:** [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (los tres sub-proyectos ya implementados: calidad básica, detección de anomalías, datos sintéticos).

## Why

Los tres sub-proyectos de HU3 (calidad básica, detección de anomalías, datos sintéticos) existen como módulos independientes, pero no hay todavía un procedimiento único que los combine en el orden correcto y de forma reproducible. Sin esto, cada configuración experimental de la Épica 4 requeriría ensamblar manualmente los módulos cada vez, con riesgo de inconsistencias (ej. olvidar ajustar la estandarización solo sobre el conjunto de entrenamiento).

## What Changes

- Se agrega `run_quality_pipeline`, que orquesta: reporte de calidad sobre los datos crudos → imputación de faltantes → partición entrenamiento/evaluación → detección de anomalías (opcional) → estandarización (ajustada solo sobre entrenamiento, aplicada también a evaluación) → generación de datos sintéticos (opcional, agregados al entrenamiento ya estandarizado).
- Los pasos opcionales se controlan con dos banderas booleanas simples (`include_anomaly_detection`, `include_synthetic`), no con una herramienta de feature flags: la Épica 4 necesita seleccionar una de 4 configuraciones conocidas de antemano al lanzar una corrida, no alternar comportamiento en tiempo de ejecución para usuarios/entornos — una herramienta de flags sería infraestructura que este alcance no requiere (mismo criterio que ADR-0002 aplicó a otras decisiones de este proyecto).
- Se agrega `apply_standardization` a `data_quality.scaling`, para aplicar parámetros de escalado ya ajustados (sobre el conjunto de entrenamiento) al conjunto de evaluación y a los datos sintéticos, sin recalcularlos — cerrando la fuga de información señalada como limitación conocida en el spec de `data-quality-basics`.
- Se agrega `scripts/run_data_quality_pipeline.py` como CLI reproducible sobre un dataset ya consolidado.

## Impact

- **Specs afectadas:** `data-quality` (extiende el spec existente con el requirement de flujo integrado).
- **Specs futuras que dependen de esta:** `predictive-modeling` (HU4) y `experiment-runner` (HU7) consumirán directamente `run_quality_pipeline` para cada configuración experimental.
- **Código afectado:** nuevo módulo `src/data_quality/pipeline.py`; extensión de `src/data_quality/scaling.py` (`apply_standardization`); nuevo script `scripts/run_data_quality_pipeline.py`.
- **Fuera de alcance de este change:** el modelo predictivo en sí (HU4, no iniciada); la ejecución sistemática de las 4 configuraciones sobre múltiples repeticiones/semillas (HU7, no iniciada).
