# Tareas — add-experiment-automation

Subconjunto de las tareas técnicas de HU7 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Segundo de tres *changes* en que se dividió HU7.

- [x] Implementar el procedimiento automatizado de experimentación. `src/experiment_runner/runner.py::run_configuration` (ejecuta el orquestador de HU6 por semilla, con aumento sintético opcional). Tests: `tests/test_experiment_runner.py`. Verificado sobre el dataset real: configuración base, 3 semillas, 3 filas de métricas (F1 0.400-0.500).
- [x] Configurar el registro de parámetros, versiones y resultados. `src/experiment_runner/mlflow_logging.py::log_configuration_results` (run padre con métricas agregadas + run hijo anidado por semilla). Tests: `tests/test_mlflow_logging.py`. `mlflow` agregado como dependencia del proyecto (`mlflow>=2.14,<3`, mismo rango que el servidor de ADR-0004). Verificado sobre los resultados reales anteriores: run padre con `f1_mean=0.449`, `f1_std=0.050`, y 3 runs hijos anidados (uno por semilla) recuperables por `tags.mlflow.parentRunId`.
