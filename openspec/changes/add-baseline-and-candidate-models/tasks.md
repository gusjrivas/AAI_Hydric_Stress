# Tareas — add-baseline-and-candidate-models

Subconjunto de las tareas técnicas de HU4 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Segundo de tres *changes* en que se dividió HU4.

- [x] Definir modelos de referencia y modelos candidatos. `src/predictive_modeling/models.py::build_candidate_models` (regresión logística + Random Forest, ADR-0002); `tests/test_models.py`.
- [x] Implementar el modelo de referencia. `src/predictive_modeling/models.py::predict_persistence_baseline`; verificado sobre datos reales: precisión 0.500, recall 0.474, F1 0.486 (72 filas de test, umbral 0.3126).
- [x] Implementar el flujo de entrenamiento para los modelos candidatos. `src/predictive_modeling/training.py::train_models`; `tests/test_training.py`.
- [x] Implementar el esquema de validación temporal o cruzada. `src/predictive_modeling/training.py::tune_hyperparameters` con `sklearn.model_selection.TimeSeriesSplit`.
- [x] Ejecutar el entrenamiento inicial de los modelos candidatos. Verificado sobre `data/melchor_romero_2024_consolidado.parquet` (285 filas de entrenamiento, 72 de test, tras ingeniería de variables e interpolación).
- [x] Ejecutar el ajuste de hiperparámetros. `tune_hyperparameters` con grillas `{"C": [0.1, 1.0, 10.0]}` (regresión logística) y `{"n_estimators": [100], "max_depth": [5, None]}` (Random Forest); mejores parámetros reales: `C=0.1` y `max_depth=5, n_estimators=100`.
- [x] Comparar desempeño, estabilidad y complejidad de los modelos. `src/predictive_modeling/evaluation.py::compare_models`; `tests/test_evaluation.py`. Resultado real (test set real, 72 filas, tasa positiva 52.8%): persistencia F1=0.486, regresión logística F1=0.406 (ROC-AUC 0.533), Random Forest F1=0.475 (ROC-AUC 0.554). Estabilidad (`cv_std_score`) de ambos candidatos ≈0.0 en la validación cruzada temporal interna — ver "Limitaciones conocidas" en el spec.
