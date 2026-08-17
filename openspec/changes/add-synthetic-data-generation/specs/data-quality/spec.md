# Spec delta: data-quality

## ADDED Requirements

### Requirement: Generación de datos sintéticos por muestreo estadístico

El sistema DEBE poder generar filas sintéticas ajustando una distribución normal multivariada a la media y matriz de covarianza de un conjunto de variables reales, y muestreando de esa distribución. Cada fila generada DEBE quedar marcada con procedencia `sintético`, conforme al esquema definido en `data-ingestion`.

#### Scenario: Generación de N filas sintéticas a partir de datos reales

- **GIVEN** un dataset real con un conjunto de variables numéricas correlacionadas entre sí
- **WHEN** se genera un número N de filas sintéticas a partir de ese dataset
- **THEN** el resultado tiene N filas, con procedencia `sintético` en cada una, y las mismas columnas que el dataset real

### Requirement: Similitud estadística entre datos reales y sintéticos

El sistema DEBE poder comparar un dataset real y uno sintético generado a partir de él, reportando la diferencia entre sus medias, desvíos estándar y matriz de correlación entre variables.

#### Scenario: Comparación de un dataset sintético contra el real que lo originó

- **GIVEN** un dataset real y un dataset sintético generado a partir de sus estadísticos
- **WHEN** se evalúa la similitud estadística entre ambos
- **THEN** se obtiene, para cada variable, la diferencia de media y desvío, y la diferencia de la matriz de correlación entre variables

### Requirement: Utilidad predictiva de los datos sintéticos

El sistema DEBE poder comparar la utilidad predictiva de datos reales contra datos sintéticos, entrenando un modelo simple sobre cada conjunto y evaluando ambos modelos contra un mismo conjunto de evaluación real.

#### Scenario: Comparación de utilidad predictiva real vs. sintético

- **GIVEN** un conjunto de entrenamiento real, su versión sintética generada, y un conjunto de evaluación real separado
- **WHEN** se entrena un modelo simple sobre el conjunto real y, por separado, sobre el sintético, y se evalúan ambos contra el conjunto de evaluación real
- **THEN** se obtiene una métrica de error comparable para el modelo entrenado con datos reales y para el entrenado con datos sintéticos
