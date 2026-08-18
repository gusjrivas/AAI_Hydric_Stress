# Change: Add experiment scenarios capability

## Trazabilidad

- **Épica:** 4. Evaluación experimental.
- **Historia de usuario:** HU8 — Análisis de resultados y contrastación de la hipótesis (cierre de las tareas "Analizar el desempeño bajo escenarios de escasez de datos" y "...de ruido y variabilidad de datos", que HU7 había dejado documentadas como limitación, sin ejecutar).
- **Fase de CRISP-DM:** Evaluación.
- **Insumo de diseño:** [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) (procedimiento automatizado), [`docs/research/hu8-analisis-resultados.md`](../../../docs/research/hu8-analisis-resultados.md) (limitación documentada).

## Why

El análisis de resultados de HU8 documentó honestamente que los escenarios de escasez y ruido de datos —parte explícita de la hipótesis de investigación ("contextos de disponibilidad limitada, ruido y alta variabilidad de datos")— no se habían ejecutado por falta de una implementación concreta (escasez) o de una fuente real que caracterice el ruido (ruido). Se decide cerrar ambos cabos: implementar y ejecutar el escenario de escasez con datos reales, e implementar una inyección de ruido gaussiano simple (documentando explícitamente que no está calibrada contra una caracterización real de ruido de sensor) para tener evidencia concreta que reportar.

## What Changes

- **Escenario de escasez**: `subsample_training_period` conserva solo una fracción configurable del período de entrenamiento (las fechas más recientes antes del corte), sin tocar el período de evaluación — aproxima "menos datos disponibles" de forma simple y auditable.
- **Escenario de ruido**: `inject_gaussian_noise` agrega ruido gaussiano de media cero a las variables predictoras, con desvío proporcional al desvío observado de cada variable — una aproximación deliberadamente simple, no calibrada contra una fuente real de ruido de sensor (documentado como limitación).
- **Integración con el procedimiento automatizado**: `run_configuration` acepta `train_fraction` y `noise_std_ratio` como parámetros opcionales (por defecto, sin cambios respecto del comportamiento actual), aplicando el escenario correspondiente antes de ejecutar el orquestador de punta a punta, con una semilla de ruido distinta por repetición.

## Impact

- **Specs afectadas:** `experiment-runner` (extiende el spec existente).
- **Código afectado:** nuevo `src/experiment_runner/scenarios.py`; `src/experiment_runner/runner.py` (parámetros nuevos, retrocompatibles).
- **Fuera de alcance de este change:** calibrar el ruido inyectado contra una caracterización real de sensor (no existe todavía); escenarios combinados de escasez + ruido simultáneos.

## Alternativas consideradas

- **Dejar ambos escenarios sin ejecutar, solo documentados como limitación**: se descarta por decisión explícita del usuario de cerrar estos cabos con evidencia real en vez de dejarlos como limitación permanente.
- **Inyectar ruido no gaussiano o con una distribución más realista**: se descarta por ahora por falta de una caracterización real que justifique una distribución distinta; el ruido gaussiano proporcional al desvío es la aproximación más simple y transparente disponible, documentada explícitamente como no calibrada.

## Estado: implementado

Ver [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) para los requisitos vigentes y la verificación con datos reales. Hallazgo real: la escasez de datos (mitad más reciente del entrenamiento) mejoró el desempeño (F1 0.622 vs. 0.459 de base); el ruido lo empeoró (F1 0.319), como se esperaba.
