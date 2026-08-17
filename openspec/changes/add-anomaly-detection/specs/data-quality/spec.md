# Spec delta: data-quality

## ADDED Requirements

### Requirement: Detección de anomalías no supervisada

El sistema DEBE poder marcar filas anómalas en un dataset sin requerir etiquetas de anomalía previas, usando un método no supervisado (Isolation Forest) sobre las columnas numéricas del esquema.

#### Scenario: Detección sobre un dataset sin anomalías etiquetadas

- **GIVEN** un dataset normalizado al esquema, sin ninguna columna de etiqueta de anomalía
- **WHEN** se ejecuta la detección de anomalías sobre sus columnas numéricas
- **THEN** el dataset resultante incluye una columna que marca cada fila como anómala o no, sin haber requerido ninguna etiqueta previa

### Requirement: Evaluación del detector mediante anomalías sintéticas inyectadas

El sistema DEBE poder evaluar la capacidad de detección del método base inyectando anomalías sintéticas conocidas sobre una copia de un dataset real y midiendo qué proporción de esas anomalías inyectadas el detector marca correctamente, dado que no existen anomalías reales etiquetadas contra las cuales evaluar.

#### Scenario: Evaluación con anomalías inyectadas conocidas

- **GIVEN** una copia de un dataset real con un conjunto conocido de filas modificadas a valores extremos (anomalías sintéticas inyectadas)
- **WHEN** se evalúa el detector sobre ese dataset modificado
- **THEN** se obtiene la proporción de las filas inyectadas que el detector efectivamente marcó como anómalas
