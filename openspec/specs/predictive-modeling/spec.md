# Spec: predictive-modeling

Capacidad implementada (Épica 2, HU4 — primer sub-proyecto: definición del problema e ingeniería de variables). Origen: `openspec/changes/add-feature-engineering/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

Los otros dos sub-proyectos de HU4 (modelos base/candidatos, alertas tempranas) todavía no comenzaron y se documentarán como *changes* independientes que extienden esta spec.

## Requirements

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

Implementado en `src/predictive_modeling/labeling.py` (`add_stress_label`), testeado en `tests/test_labeling.py`. Parámetros elegidos: horizonte de 3 días, percentil 20 (justificación en el *change* de origen: sin datos de capacidad de campo/punto de marchitez calibrados, un umbral agronómico absoluto no es calculable con rigor todavía — este es un proxy relativo, no una validación agronómica definitiva). Verificado sobre el dataset real: 363 de 366 filas etiquetadas (292 sin estrés, 71 con estrés, ~19.6%).

### Requirement: Variables predictoras con retardos y ventanas móviles sin fuga temporal

El sistema DEBE poder construir variables predictoras de retardo (*lag*) y ventana móvil (*rolling*) a partir de las columnas numéricas del esquema, usando únicamente información disponible hasta el día de la predicción (inclusive), nunca información de días posteriores.

#### Scenario: Una variable de retardo no contiene información futura

- **GIVEN** una serie temporal con variables climáticas y de humedad de suelo
- **WHEN** se construyen variables de retardo y ventana móvil para el día `t`
- **THEN** todas esas variables se calculan exclusivamente con datos de días `t` o anteriores

Implementado en `src/predictive_modeling/feature_engineering.py` (`add_lag_features`, `add_rolling_features`), testeado en `tests/test_feature_engineering.py`. Retardos usados: 1, 2, 3 días; ventanas móviles: 3, 7 días, sobre variables climáticas y humedad de suelo.

### Requirement: Evaluación de relevancia de variables

El sistema DEBE poder reportar la relevancia de cada variable predictora respecto de la variable objetivo (correlación), para orientar la selección de variables antes del modelado.

#### Scenario: Reporte de relevancia sobre una matriz de variables ya construida

- **GIVEN** una matriz de variables predictoras y su variable objetivo correspondiente
- **WHEN** se genera el reporte de relevancia
- **THEN** se obtiene, para cada variable predictora, su correlación con la variable objetivo

Implementado en `src/predictive_modeling/relevance.py` (`feature_relevance`), testeado en `tests/test_relevance.py`. Verificado sobre el dataset real: las variables más correlacionadas con el objetivo tienen sentido físico — radiación solar acumulada (ventanas de 3 y 7 días) correlacionada positivamente (~0.50, más sol implica más evapotranspiración y mayor probabilidad de estrés futuro), humedad relativa y humedad de suelo (ventanas móviles) correlacionadas negativamente (~-0.46 a -0.48).

Además, `tests/test_no_leakage.py` verifica explícitamente, de punta a punta (etiqueta + variables juntas), que modificar un valor futuro de humedad de suelo no altera ninguna variable de días anteriores.

## Limitaciones conocidas

- El umbral de estrés es relativo (percentil 20 de la distribución observada en un único punto/año), no un umbral agronómico validado con datos de capacidad de campo/punto de marchitez reales. Reevaluar si se consiguen esos datos.
- Verificado con un único dataset real (Melchor Romero 2024). No se validó con datos de otros puntos geográficos o años — el umbral relativo, en particular, cambiaría al incorporar más datos.
- El horizonte de anticipación (3 días) y los retardos/ventanas elegidos (1-3 días, 3-7 días) son una elección razonada pero no la única posible; no se comparó contra otros horizontes o ventanas todavía.
- La evaluación de relevancia usa correlación lineal simple; no captura relaciones no lineales entre variables y objetivo, que un modelo de los sub-proyectos siguientes de HU4 sí podría aprovechar.
