# Spec delta: predictive-modeling

## ADDED Requirements

### Requirement: Generación de alertas tempranas por umbral de probabilidad

El sistema DEBE poder convertir la probabilidad predicha de estrés de un modelo entrenado en una alerta binaria, usando un umbral de decisión configurable.

#### Scenario: Emisión de alerta cuando la probabilidad supera el umbral

- **GIVEN** un modelo entrenado con `predict_proba` y un conjunto de datos con variables predictoras
- **WHEN** se generan alertas con un umbral de decisión configurado
- **THEN** cada fila con probabilidad de estrés mayor o igual al umbral queda marcada con alerta (1), y el resto sin alerta (0)

### Requirement: Análisis de errores de predicción por fecha

El sistema DEBE poder identificar, sobre un conjunto de evaluación con fechas, las fechas concretas de falsos positivos (alerta sin estrés real) y falsos negativos (estrés real sin alerta).

#### Scenario: Identificación de una alerta incorrecta puntual

- **GIVEN** un conjunto de evaluación con fecha, etiqueta real y alerta generada, donde una fila tiene alerta pero la etiqueta real es "sin estrés"
- **WHEN** se analiza los errores de predicción
- **THEN** la fecha de esa fila aparece listada como falso positivo
