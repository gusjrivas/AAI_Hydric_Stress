## ADDED Requirements

### Requirement: Estimación directa por horizonte operativo
El contrato producer_daily_h123_v1 MUST producir predicciones independientes
para h=1,2,3 con un corte común de información y bundles compatibles.
MUST NOT repetir, interpolar o desplazar el score de t+3.

#### Scenario: Emisión con datos hasta una fecha
- **GIVEN** datos observados hasta t y modelos elegibles
- **WHEN** se infiere la tanda
- **THEN** cada horizonte tiene target_date=t+h e identidad de modelo propia.

#### Scenario: Un horizonte no es entrenable
- **GIVEN** h=2 sin ambas clases entrenables
- **WHEN** se consulta la tanda
- **THEN** h=2 queda unavailable con motivo y los otros no se inventan ni se ocultan.

### Requirement: Causalidad y separación de evidencia científica
Targets y transformaciones MUST respetar los cortes temporales. El desarrollo
MUST preservar protocolos y resultados formales y no acceder a sus holdouts.

#### Scenario: Target posterior al corte
- **WHEN** un ejemplo de entrenamiento tiene target_date en evaluación
- **THEN** se purga antes de ajustar el predictor.

### Requirement: Probabilidad con evidencia y límites explícitos
El sistema MUST publicar display_probability solo si supera el gate predeclarado
del diseño con evidencia compatible con ese bundle. Score bruto y calibración
MUST identificarse sin afirmar certeza ni diagnóstico fisiológico.

#### Scenario: Datos insuficientes para evaluar calibración
- **WHEN** no hay soporte por clase o el gate falla
- **THEN** display_probability es null y se conserva el motivo, sin ajustar usando test.

#### Scenario: Predictor recalibrado
- **WHEN** cambia el bundle mediante feedback
- **THEN** no hereda automáticamente la calificación probabilística del anterior.
