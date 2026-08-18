# Change: Add experiment execution capability

## Trazabilidad

- **Épica:** 4. Evaluación experimental.
- **Historia de usuario:** HU7 — Diseño y ejecución del plan experimental (tercer y último sub-proyecto: ejecución real de los experimentos). Cierra HU7.
- **Fase de CRISP-DM:** Evaluación.
- **Insumo de diseño:** [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) (procedimiento automatizado, registro en MLflow), [ADR-0004](../../../docs/adr/0004-orquestacion-experimentos-mlflow-minio.md) (servidor MLflow real).

## Why

El procedimiento automatizado y el registro en MLflow (`add-experiment-automation`) están implementados y probados, pero solo se verificaron contra un tracking store de archivo local — nunca se ejecutaron contra el servidor MLflow real de docker-compose, ni se corrieron las 4 configuraciones completas de la Épica 4 sobre el dataset real.

## What Changes

- **Prueba piloto**: se ejecuta la configuración base con 2 semillas contra el servidor MLflow real (`http://localhost:5000`, Postgres + MinIO, ADR-0004) para validar que el procedimiento completo funciona de punta a punta con la infraestructura real, antes de correr las 4 configuraciones completas.
- **Experimentos con modelos de referencia**: se ejecutan las configuraciones sin mecanismos de robustez integrados — base y +sintéticos — con las 5 semillas del diseño experimental, registradas en MLflow.
- **Experimentos con mecanismos de robustez integrados**: se ejecutan las configuraciones que sí incluyen detección de anomalías — +anomalías y completa — con las 5 semillas, registradas en MLflow.
- **Verificación de integridad y reproducibilidad**: se re-ejecuta la configuración base con las mismas 5 semillas y se comparan las métricas resultantes contra la primera corrida — deben ser idénticas, confirmando que las semillas fijan completamente el resultado (sin fuentes ocultas de no-determinismo).

## Impact

- **Specs afectadas:** `experiment-runner` (extiende el spec existente, cierra los 3 sub-proyectos de HU7).
- **Specs futuras que dependen de esta:** HU8 (análisis de resultados) consume las métricas registradas en MLflow de las 4 configuraciones para contrastar la hipótesis de investigación.
- **Código afectado:** ninguno nuevo — este *change* es de ejecución y documentación, reutiliza `experiment_runner.runner`/`mlflow_logging` sin modificarlos.
- **Fuera de alcance de este change:** análisis/interpretación de los resultados (HU8); cualquier ajuste a los modelos o al pipeline motivado por los resultados observados (quedaría como un *change* nuevo si corresponde).

## Alternativas consideradas

- **Piloto con las 4 configuraciones a la vez**: se descarta porque mezclaría la validación del mecanismo (¿corre bien contra el servidor real?) con la primera pasada de resultados, dificultando distinguir un problema de infraestructura de un resultado experimental genuino.
- **Verificar reproducibilidad solo revisando que los runs tengan parámetros completos**: se descarta porque no prueba nada sobre el determinismo real de las semillas — dos corridas podrían tener parámetros completos y sin embargo producir métricas distintas si hay una fuente de aleatoriedad no fijada por semilla.

## Estado: implementado

Ver [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) para los requisitos vigentes, los resultados de las 4 configuraciones y un hallazgo real importante (la detección de anomalías no tiene efecto medible en el pipeline actual). Con esta *change* se completan los tres sub-proyectos de HU7.
