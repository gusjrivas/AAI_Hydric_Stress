# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Disparo manual de recalibración desde la interfaz

El sistema DEBE poder recalibrar el modelo usado para pronosticar a partir de las alertas rechazadas con corrección presentes en el registro de retroalimentación, y registrar el resultado de forma versionada.

#### Scenario: Recalibrar con correcciones pendientes

- **GIVEN** un registro de retroalimentación con al menos una alerta en estado `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca el endpoint de recalibración
- **THEN** se reentrena el modelo incorporando esas correcciones, el resultado queda registrado con una nueva versión, y la respuesta indica la versión registrada y cuántas correcciones se aplicaron

#### Scenario: Recalibrar sin correcciones pendientes

- **GIVEN** un registro de retroalimentación sin ninguna alerta `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca el endpoint de recalibración
- **THEN** se devuelve un error explícito indicando que no hay correcciones pendientes de aplicar, sin registrar ninguna versión nueva

### Requirement: Uso del modelo recalibrado en el próximo pronóstico

El sistema DEBE usar la versión más reciente del modelo recalibrado (si existe alguna) al ejecutar un nuevo pronóstico, en vez de entrenar un modelo nuevo desde cero.

#### Scenario: Pronóstico posterior a una recalibración

- **GIVEN** un modelo recalibrado ya registrado
- **WHEN** se ejecuta el pronóstico
- **THEN** las predicciones se generan con ese modelo registrado, sin reentrenar uno nuevo

#### Scenario: Pronóstico sin ninguna recalibración previa

- **GIVEN** que todavía no se registró ningún modelo recalibrado
- **WHEN** se ejecuta el pronóstico
- **THEN** se entrena un modelo nuevo, igual que el comportamiento previo a este *change*
