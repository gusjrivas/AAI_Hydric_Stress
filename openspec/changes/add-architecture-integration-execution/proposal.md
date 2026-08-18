# Change: Add architecture integration execution capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historia de usuario:** HU6 — Integración de la arquitectura experimental (segundo y último sub-proyecto: configuración de la ejecución completa, pruebas funcionales de integración, y ajustes/documentación de incidencias). Cierra HU6.
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) (orquestador `run_end_to_end_pipeline`).

## Why

El orquestador de punta a punta (`add-architecture-integration-pipeline`) ya existe y está probado con tests unitarios sobre datos sintéticos simples, pero no hay todavía una forma configurable de ejecutarlo con parámetros reales (dataset, columnas, fecha de corte, modelo, umbral) ni pruebas funcionales más amplias que ejerciten el flujo completo bajo escenarios más realistas (valores faltantes que requieren interpolación, distintas combinaciones de detección de anomalías).

## What Changes

- **Configuración de la ejecución completa**: script `scripts/run_end_to_end_pipeline.py`, con la misma convención que `scripts/run_data_quality_pipeline.py` (argumentos de línea de comandos: dataset, columnas, fecha de corte, modelo, umbral de alerta, detección de anomalías), que ejecuta `run_end_to_end_pipeline` sobre un dataset real y reporta un resumen.
- **Pruebas funcionales de integración**: `tests/test_architecture_integration_functional.py`, con escenarios sintéticos más realistas que los tests unitarios existentes (valores faltantes intercalados que requieren interpolación antes del etiquetado, y verificación de que desactivar la detección de anomalías efectivamente omite la columna `is_anomaly`).
- **Ajustes de integración**: se documentan en el spec y en `tasks.md` cualquier incidencia encontrada al construir el script o las pruebas funcionales, con la corrección aplicada.

## Impact

- **Specs afectadas:** `architecture-integration` (extiende el spec existente, cierra los 2 sub-proyectos de HU6).
- **Specs futuras que dependen de esta:** `experiment-runner` (HU7) reutilizará el mismo orquestador y probablemente el mismo patrón de script parametrizado para correr las 4 configuraciones experimentales.
- **Código afectado:** nuevo `scripts/run_end_to_end_pipeline.py`; nuevo `tests/test_architecture_integration_functional.py`.
- **Fuera de alcance de este change:** ejecución programada/automática (scheduler); las 4 configuraciones experimentales de la Épica 4 en simultáneo (eso es HU7).

## Alternativas consideradas

- **No agregar un script de ejecución, solo llamar la función directamente en cada uso**: se descarta por inconsistencia con el patrón ya establecido en el repo (`scripts/run_data_quality_pipeline.py`, `scripts/consolidate_datasets.py`), que da una forma reproducible y documentada de correr cada flujo desde línea de comandos.
- **Pruebas funcionales sobre el dataset real dentro del suite de pytest**: se descarta porque el dataset real está en `.gitignore` (ADR-0002) y no está disponible en CI; se sigue el mismo criterio ya usado en todo el repo (verificación real vía script ad-hoc, documentada con números concretos en el spec, y pruebas automatizadas con datos sintéticos).

## Estado: implementado

Ver [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) para los requisitos vigentes y la verificación con datos reales. Con esta *change* se completan los dos sub-proyectos de HU6.
