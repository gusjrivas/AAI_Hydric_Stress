# Change: Add feedback data model capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historia de usuario:** HU5 — Mecanismo de retroalimentación humana (primer sub-proyecto: casos de uso, estados de validación, modelo de datos y flujo de interacción, de tres en que se divide HU5).
- **Fase de CRISP-DM:** Despliegue / Evaluación continua.
- **Insumo de diseño:** [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (alertas generadas por `generate_alerts`), [`openspec/specs/data-ingestion/spec.md`](../../specs/data-ingestion/spec.md) (contrato `load_dataset`/`save_dataset`, reutilizado sin cambios).

## Why

HU4 deja las alertas generadas, pero no hay ningún mecanismo para que un usuario humano las valide, las corrija, o dispare una recalibración del modelo con esas correcciones — el objetivo central de HU5 y de la capa 5 de la arquitectura (ADR-0001).

## What Changes

- **Casos de uso y estados de validación**: por cada alerta generada, el usuario puede dejarla `pendiente` (todavía no revisada), `confirmada` (la alerta era correcta) o `rechazada` (falsa alarma). Al rechazar, puede opcionalmente indicar la etiqueta correcta (`etiqueta_corregida`) y una observación textual libre.
- **Modelo de datos**: esquema tabular (fecha, alerta generada, estado de validación, etiqueta corregida opcional, observación opcional, timestamp de la retroalimentación), análogo en estilo al esquema de `data-ingestion` (`schema.py` con columnas tipadas y una función de inicialización).
- **Flujo de interacción**: un registro de retroalimentación se inicializa en estado `pendiente` para cada alerta generada; el usuario actualiza el estado (y opcionalmente la corrección/observación) de una alerta puntual identificada por fecha. No hay una interfaz de usuario todavía (HU6/frontend) — este *change* cubre solo el modelo de datos y las funciones de actualización que esa interfaz consumirá.
- **Almacenamiento**: se reutiliza el contrato `load_dataset`/`save_dataset` de `data-ingestion` (Parquet local, ADR-0002) sin ninguna extensión — el registro de retroalimentación es un dataset más bajo ese mismo contrato, evitando acoplar esta capacidad a la infraestructura de MLflow/Postgres (ADR-0004), que tiene otro propósito (tracking de experimentos).

## Impact

- **Specs afectadas:** nueva capacidad `human-feedback`.
- **Specs futuras que dependen de esta:** el *change* siguiente de HU5 (registro de validaciones/correcciones e integración con predicciones) construye sobre este esquema; el tercero (recalibración supervisada) consume los registros ya validados.
- **Código afectado:** nuevo paquete `src/human_feedback/` con `schema.py`.
- **Fuera de alcance de este change:** funciones de registro/actualización persistente sobre archivos reales (segundo *change*); lógica de recalibración (tercer *change*); interfaz de usuario (HU6).

## Alternativas consideradas

- **Postgres (la misma base que usa MLflow, ADR-0004)**: se descarta para mantener la retroalimentación desacoplada de la infraestructura de tracking de experimentos, que tiene otro propósito; y por consistencia con el resto del prototipo, que usa Parquet local como contrato de acceso a datos.
- **Escala de confianza granular (ej. 1-5) en vez de 3 estados simples**: se descarta para esta primera versión por agregar complejidad sin un caso de uso concreto todavía que la justifique en un prototipo de tesis; los 3 estados (confirmada/rechazada/pendiente) ya permiten disparar una recalibración supervisada.

## Estado: implementado

Ver [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) para los requisitos vigentes y la verificación con datos reales.
