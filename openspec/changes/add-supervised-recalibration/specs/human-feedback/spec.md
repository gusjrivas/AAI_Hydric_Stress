# Spec delta: human-feedback

## ADDED Requirements

### Requirement: Selección de observaciones para recalibración

El sistema DEBE poder seleccionar, de un registro de retroalimentación integrado con predicciones, únicamente las observaciones rechazadas que tienen una etiqueta corregida.

#### Scenario: Selección excluye confirmaciones y rechazos sin corrección

- **GIVEN** un registro integrado con una fila `confirmada`, una fila `rechazada` con etiqueta corregida, y una fila `rechazada` sin etiqueta corregida
- **WHEN** se seleccionan las observaciones de recalibración
- **THEN** solo la fila `rechazada` con etiqueta corregida queda seleccionada

### Requirement: Recalibración supervisada de un modelo candidato

El sistema DEBE poder reentrenar un modelo candidato sobre un conjunto de entrenamiento donde las etiquetas de las fechas seleccionadas para recalibración fueron reemplazadas por su etiqueta corregida.

#### Scenario: El modelo recalibrado predice distinto en las fechas corregidas

- **GIVEN** un modelo entrenado sobre un conjunto original y un conjunto de observaciones de recalibración que corrige la etiqueta de al menos una fecha presente en ese conjunto
- **WHEN** se recalibra el modelo con esas correcciones
- **THEN** el conjunto de entrenamiento usado para el modelo recalibrado tiene, en esas fechas, la etiqueta corregida en lugar de la original
