# Change: Add feedback registry integration capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historia de usuario:** HU5 — Mecanismo de retroalimentación humana (segundo sub-proyecto: registro persistente de validaciones/correcciones e integración con los registros de predicción, de tres en que se divide HU5).
- **Fase de CRISP-DM:** Despliegue / Evaluación continua.
- **Insumo de diseño:** [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) (esquema y actualización en memoria del registro de retroalimentación), [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (alertas y probabilidades predichas).

## Why

El primer sub-proyecto de HU5 (`add-feedback-data-model`) define el esquema y las funciones de actualización en memoria, pero no hay todavía forma de persistirlo a disco, de reconciliar un registro existente con alertas nuevas sin perder validaciones humanas ya hechas, ni de juntar la retroalimentación con la probabilidad predicha por el modelo — insumo necesario para la recalibración del tercer sub-proyecto.

## What Changes

- **Persistencia**: se reutiliza el contrato `load_dataset`/`save_dataset` de `data-ingestion` (Parquet local, ADR-0002) para guardar y recuperar el registro de retroalimentación — sin funciones de storage nuevas ni dependencias adicionales.
- **Actualización (*upsert*) por fecha**: al regenerar alertas (ej. nuevos días de datos), las fechas nuevas se agregan al registro existente en estado `pendiente`; las fechas ya presentes conservan su `estado_validacion`, `etiqueta_corregida` y `observacion` sin importar el nuevo valor de `alerta_generada` — evita que una re-ejecución del pipeline borre validaciones humanas ya hechas.
- **Integración con registros de predicción**: función que junta, por fecha, el registro de retroalimentación con la probabilidad predicha (`y_proba`) y la etiqueta real (`stress_label`) de ese mismo día — permite ver, para cada corrección humana, cuán confiado estaba el modelo cuando se equivocó.

## Impact

- **Specs afectadas:** `human-feedback` (extiende el spec existente).
- **Specs futuras que dependen de esta:** el tercer *change* de HU5 (recalibración supervisada) usa la tabla integrada (feedback + probabilidad + etiqueta real) para seleccionar observaciones de recalibración.
- **Código afectado:** `src/human_feedback/registry.py` (nuevo módulo).
- **Fuera de alcance de este change:** reglas de selección de observaciones de recalibración y la prueba de recalibración supervisada (tercer *change*); interfaz de usuario (HU6).

## Alternativas consideradas

- **Reemplazar todo el registro en cada regeneración de alertas**: se descarta porque borraría cualquier validación humana ya hecha, contradiciendo el propósito mismo de HU5 (que la retroalimentación se acumule con el tiempo).
- **Funciones de storage propias en `human_feedback`**: se descarta por duplicar código ya existente en `data-ingestion` sin ninguna necesidad concreta distinta (el registro de retroalimentación es un dataset tabular más, no requiere ningún tratamiento especial de storage).

## Estado: implementado

Ver [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) para los requisitos vigentes y la verificación con datos reales.
