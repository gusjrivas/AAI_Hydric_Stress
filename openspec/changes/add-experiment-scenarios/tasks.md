# Tareas — add-experiment-scenarios

Cierra las tareas de HU8 "Analizar el desempeño bajo escenarios de escasez de datos" y "...de ruido y variabilidad de datos" (issues #104 y #105), que HU7 había dejado sin ejecutar.

- [x] Implementar y ejecutar el escenario de escasez de datos. `src/experiment_runner/scenarios.py::subsample_training_period`, integrado en `run_configuration` (`train_fraction`). Tests: `tests/test_scenarios.py`, `tests/test_experiment_runner.py`. Verificado sobre el dataset real: `train_fraction=0.5`, F1 medio 0.6219±0.0888 (mejor que la configuración base sin reducir, 0.4585±0.0423).
- [x] Implementar y ejecutar el escenario de ruido de datos. `src/experiment_runner/scenarios.py::inject_gaussian_noise`, integrado en `run_configuration` (`noise_std_ratio`). Tests: `tests/test_scenarios.py`, `tests/test_experiment_runner.py`. Verificado sobre el dataset real: `noise_std_ratio=0.3`, F1 medio 0.3188±0.1130 (peor que base, y más variable entre semillas).
