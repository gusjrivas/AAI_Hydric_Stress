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

### Requirement: Calificación directa con incertidumbre y alcance limitado
El sistema MUST aplicar el manifiesto y la regla de presentación de design.md:
tolerancias previas, soporte por clase e intervalo, cobertura, estabilidad y
límites de error con incertidumbre temporal. MUST NOT acreditar calibración
usando únicamente Brier/log-loss, una diagonal dentro de una banda amplia o
repeticiones de semillas. MUST evaluar el proxy observado por horizonte sin
reemplazar targets por opiniones humanas ni datos sintéticos.

#### Scenario: Métricas globales mejoran pero calibración directa falla
- **GIVEN** soporte suficiente y mejor Brier/log-loss que las referencias
- **WHEN** un límite de error supera la tolerancia predeclarada
- **THEN** assessment_result=failed y display_probability=null.

#### Scenario: Plan no completado antes del ajuste
- **WHEN** faltan tolerancias numéricas, soporte o método de incertidumbre congelados
- **THEN** se bloquea la calificación con incomplete_assessment_plan, sin defaults favorables.

#### Scenario: Incertidumbre o cobertura insuficientes
- **WHEN** faltan bloques temporales o coverage no alcanza el mínimo
- **THEN** assessment_result=insufficient_evidence y no se publica porcentaje.

#### Scenario: Banda amplia compatible con calibración perfecta
- **WHEN** la banda incluye error cero pero su límite superior excede epsilon_bin
- **THEN** no se califica ese horizonte por ausencia de evidencia de precisión suficiente.

#### Scenario: Probabilidad en un intervalo no respaldado
- **GIVEN** un horizonte aprobado con cobertura parcial declarada
- **WHEN** una inferencia cae en un intervalo sin soporte exigido
- **THEN** display_probability=null con unsupported_probability_range.

#### Scenario: Varias semillas sobre los mismos días
- **WHEN** se agregan los resultados de las cinco semillas
- **THEN** se informa sensibilidad sin multiplicar el tamaño de la muestra observada.

#### Scenario: Evaluación solo con datos sintéticos o ya explorados
- **WHEN** se genera el informe de calibración
- **THEN** se declara ese alcance y no se acredita validación independiente en condiciones reales.
