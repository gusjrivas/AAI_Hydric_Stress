# Spec delta: architecture-integration

## ADDED Requirements

### Requirement: Orquestación de punta a punta de las capacidades del núcleo de IA

El sistema DEBE poder ejecutar, con una única función, el flujo completo desde un dataset consolidado ya imputable hasta un registro de retroalimentación inicializado: imputación, etiquetado, ingeniería de variables, partición temporal, entrenamiento de un modelo, generación de alertas e inicialización del registro de retroalimentación.

#### Scenario: Ejecución completa produce todos los artefactos esperados

- **GIVEN** un dataset consolidado con columnas climáticas y de humedad de suelo, una fecha de corte para la partición temporal, y un modelo candidato sin entrenar
- **WHEN** se ejecuta el orquestador de punta a punta sobre ese dataset
- **THEN** el resultado incluye el reporte de calidad, las particiones de entrenamiento y evaluación con variables predictoras, el modelo entrenado, las alertas generadas sobre la partición de evaluación, y un registro de retroalimentación inicializado con esas alertas

### Requirement: Orden de etapas sin fuga temporal entre calidad y modelado

El sistema DEBE calcular las variables de retardo y ventana móvil sobre la serie completa imputada, antes de partir en entrenamiento/evaluación, para que los primeros días de la partición de evaluación tengan historia disponible.

#### Scenario: Las variables de los primeros días de evaluación no quedan vacías por la partición

- **GIVEN** un dataset consolidado cuya partición de evaluación comienza inmediatamente después de la de entrenamiento
- **WHEN** se ejecuta el orquestador de punta a punta
- **THEN** las variables de retardo y ventana móvil de los primeros días de la partición de evaluación se calculan con datos de la partición de entrenamiento, sin quedar en NaN por la partición
