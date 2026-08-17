# Spec delta: predictive-modeling

## ADDED Requirements

### Requirement: Modelo de referencia por persistencia

El sistema DEBE poder predecir la variable objetivo mediante un modelo de referencia (baseline) que no requiere entrenamiento: predice estrés futuro si el valor actual de humedad de suelo ya está por debajo del umbral de estrés.

#### Scenario: Predicción de referencia sobre un valor actual bajo

- **GIVEN** una fila cuyo valor actual de humedad de suelo está por debajo del umbral de estrés configurado
- **WHEN** se aplica el modelo de referencia a esa fila
- **THEN** la predicción es estrés (1)

### Requirement: Entrenamiento de modelos candidatos

El sistema DEBE poder entrenar modelos candidatos (regresión logística y Random Forest) sobre un conjunto de entrenamiento con variables predictoras y la variable objetivo.

#### Scenario: Entrenamiento de ambos candidatos sobre el mismo conjunto

- **GIVEN** un conjunto de entrenamiento con variables predictoras y la variable objetivo, sin valores faltantes
- **WHEN** se entrenan los modelos candidatos sobre ese conjunto
- **THEN** ambos modelos quedan entrenados y pueden generar predicciones sobre datos nuevos con las mismas columnas

### Requirement: Ajuste de hiperparámetros con validación temporal

El sistema DEBE poder ajustar los hiperparámetros de un modelo candidato usando validación cruzada que respete el orden temporal (cada fold de validación posterior a su fold de entrenamiento correspondiente).

#### Scenario: Ajuste de hiperparámetros sin mezclar fechas entre folds

- **GIVEN** un conjunto de entrenamiento ordenado cronológicamente y una grilla de hiperparámetros para un modelo candidato
- **WHEN** se ajustan los hiperparámetros con validación cruzada temporal
- **THEN** en cada fold de validación cruzada, todas las fechas del fold de validación son posteriores a todas las fechas del fold de entrenamiento correspondiente

### Requirement: Comparación de desempeño, estabilidad y complejidad

El sistema DEBE poder comparar el modelo de referencia y los modelos candidatos entrenados, reportando para cada uno: métricas de desempeño de la clase de estrés (precisión, recall, F1, ROC-AUC), estabilidad (desvío de la métrica entre folds de validación cruzada) y un indicador de complejidad del modelo.

#### Scenario: Comparación de tres modelos sobre el mismo conjunto de evaluación

- **GIVEN** el modelo de referencia y dos modelos candidatos ya entrenados, y un conjunto de evaluación común
- **WHEN** se comparan los tres modelos
- **THEN** se obtiene, para cada uno, sus métricas de desempeño, su estabilidad y su indicador de complejidad, en una tabla comparable
