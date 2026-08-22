# Spec delta: predictive-modeling

## ADDED Requirements

### Requirement: Selección automática del mejor modelo candidato

El sistema DEBE poder elegir automáticamente, entre un conjunto de modelos candidatos, el de mejor desempeño de validación cruzada temporal, y devolver ese modelo ya ajustado junto con su nombre y su puntaje de validación.

#### Scenario: Selección entre candidatos con desempeño distinto

- **GIVEN** un conjunto de entrenamiento y un conjunto de modelos candidatos con sus grillas de hiperparámetros
- **WHEN** se ejecuta la selección automática
- **THEN** se devuelve el modelo candidato con mayor `cv_mean_score` (F1 medio entre folds de `TimeSeriesSplit`), ya ajustado sobre el conjunto de entrenamiento completo, junto con su nombre y su `cv_mean_score`/`cv_std_score`

#### Scenario: Selección usa los candidatos y grillas por defecto si no se especifican otros

- **GIVEN** solo un conjunto de entrenamiento, sin candidatos ni grillas explícitos
- **WHEN** se ejecuta la selección automática
- **THEN** se usan `build_candidate_models` y `DEFAULT_HYPERPARAMETER_GRIDS` (los mismos ya existentes de HU4) como candidatos y grillas por defecto
