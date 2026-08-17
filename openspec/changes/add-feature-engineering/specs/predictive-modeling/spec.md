# Spec delta: predictive-modeling

## ADDED Requirements

### Requirement: Variable objetivo de estrés hídrico por umbral relativo

El sistema DEBE poder etiquetar cada fila de un dataset con una variable objetivo binaria: si la humedad de suelo cae por debajo de un umbral (percentil de la distribución histórica observada de esa misma variable) dentro de un horizonte de anticipación dado, medido en días.

#### Scenario: Etiquetado de una serie con un evento de estrés futuro

- **GIVEN** una serie temporal de humedad de suelo donde el valor de un día, `horizonte` días después del día actual, cae por debajo del percentil de umbral configurado
- **WHEN** se etiqueta esa serie con el horizonte y percentil configurados
- **THEN** el día actual queda etiquetado como estrés (1)

#### Scenario: Días sin información futura suficiente no se etiquetan

- **GIVEN** una serie temporal cuyos últimos `horizonte` días no tienen datos posteriores suficientes para conocer el valor futuro
- **WHEN** se etiqueta esa serie
- **THEN** esos últimos días quedan sin etiqueta (no se inventa un valor)

### Requirement: Variables predictoras con retardos y ventanas móviles sin fuga temporal

El sistema DEBE poder construir variables predictoras de retardo (*lag*) y ventana móvil (*rolling*) a partir de las columnas numéricas del esquema, usando únicamente información disponible hasta el día de la predicción (inclusive), nunca información de días posteriores.

#### Scenario: Una variable de retardo no contiene información futura

- **GIVEN** una serie temporal con variables climáticas y de humedad de suelo
- **WHEN** se construyen variables de retardo y ventana móvil para el día `t`
- **THEN** todas esas variables se calculan exclusivamente con datos de días `t` o anteriores

### Requirement: Evaluación de relevancia de variables

El sistema DEBE poder reportar la relevancia de cada variable predictora respecto de la variable objetivo (correlación), para orientar la selección de variables antes del modelado.

#### Scenario: Reporte de relevancia sobre una matriz de variables ya construida

- **GIVEN** una matriz de variables predictoras y su variable objetivo correspondiente
- **WHEN** se genera el reporte de relevancia
- **THEN** se obtiene, para cada variable predictora, su correlación con la variable objetivo
