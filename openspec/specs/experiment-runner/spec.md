# Spec: experiment-runner

Capacidad implementada (Épica 4, HU7 — primer sub-proyecto: diseño experimental). Origen: `openspec/changes/add-experiment-design/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

Los otros dos sub-proyectos de HU7 (procedimiento automatizado con registro en MLflow; ejecución real de los experimentos) todavía no comenzaron y se documentarán como *changes* independientes que extienden esta spec.

## Requirements

### Requirement: Aumento sintético del conjunto de entrenamiento sobre variables ya construidas

El sistema DEBE poder generar filas sintéticas adicionales para el conjunto de entrenamiento muestreando conjuntamente las variables predictoras ya construidas (retardos, ventanas móviles) y la variable objetivo, sin requerir una fecha ni continuidad temporal real.

#### Scenario: Las filas sintéticas quedan marcadas y con etiqueta binaria válida

- **GIVEN** un conjunto de entrenamiento con variables predictoras ya construidas y su variable objetivo binaria
- **WHEN** se generan filas sintéticas adicionales a partir de ese conjunto
- **THEN** las filas resultantes quedan marcadas con procedencia `sintetico`, y su variable objetivo toma únicamente los valores 0 o 1

Implementado en `src/experiment_runner/synthetic_augmentation.py` (`add_synthetic_rows`), testeado en `tests/test_synthetic_augmentation.py`. Resuelve el bloqueo documentado en `openspec/specs/architecture-integration/spec.md` (HU6): a diferencia de `data_quality.synthetic_data.generate_synthetic` (que muestrea columnas físicas crudas y no puede usarse junto con las variables de retardo/ventana móvil sin inventar una fecha), esta función muestrea directamente sobre el espacio de variables ya construidas por `predictive_modeling.feature_engineering`, evitando el problema por completo.

Verificado sobre el dataset real (Melchor Romero 2024): partiendo de un conjunto de entrenamiento de 286 filas, se agregaron 100 filas sintéticas sin valores faltantes en las variables predictoras, con etiqueta binaria válida (0/1), y un modelo Random Forest reentrenado sobre el conjunto aumentado predijo sin error sobre las 71 filas del conjunto de evaluación.

### Requirement: Configuraciones comparativas de la Épica 4

El sistema DEBE poder identificar las 4 configuraciones experimentales resultantes de cruzar detección de anomalías (on/off) y aumento sintético (on/off): base, +sintéticos, +anomalías, completa.

#### Scenario: Las 4 configuraciones quedan documentadas con su combinación de factores

- **GIVEN** los dos factores de evaluación (detección de anomalías, aumento sintético)
- **WHEN** se documentan las configuraciones comparativas
- **THEN** existen exactamente 4 configuraciones, cada una con una combinación distinta de ambos factores

Documentado en `proposal.md`. Las 4 configuraciones:

| Configuración | Detección de anomalías | Aumento sintético |
|---|---|---|
| Base | No | No |
| +Sintéticos | No | Sí |
| +Anomalías | Sí | No |
| Completa | Sí | Sí |

## Diseño experimental

- **Preguntas experimentales**: ¿la detección de anomalías (HU3) mejora el desempeño del modelo predictivo (HU4) frente a la configuración base? ¿aportan los datos sintéticos (HU3) valor predictivo cuando se combinan con las variables de retardo/ventana móvil ya diseñadas (HU4)?
- **Escenarios de escasez y variabilidad**: escasez de datos se aproxima reduciendo el tamaño del conjunto de entrenamiento real (subconjunto de las filas más recientes antes del corte); variabilidad se aproxima ejecutando cada configuración con 5 semillas aleatorias distintas y reportando media/desvío de cada métrica entre corridas. No se inyecta ruido sintético artificial: no hay una caracterización real del ruido de sensor esperado más allá de los gaps ya observados y documentados en ESA CCI Soil Moisture (HU2).
- **Métricas y criterios de evaluación**: se reutilizan sin cambios las de `predictive_modeling.evaluation` (precisión, recall, F1 y ROC-AUC de la clase de estrés), más estabilidad (desvío entre repeticiones) y complejidad del modelo — mismos criterios ya usados para comparar los modelos candidatos en HU4.
- **Particiones, semillas y repeticiones**: partición temporal simple (`data_quality.splitting.temporal_train_test_split`, ya verificada sin fuga en HU3); 5 semillas aleatorias por configuración experimental.

## Limitaciones conocidas

- El escenario de "ruido" queda sin implementar por falta de una fuente real que lo caracterice; se reevaluará si surge una necesidad concreta durante la ejecución de los experimentos.
- El escenario de "escasez" y la "variabilidad" (semillas) todavía no tienen una implementación de código en este *change* — son parte del diseño; su ejecución concreta corresponde al procedimiento automatizado (segundo *change* de HU7).
- El aumento sintético sobre variables ya construidas es estadísticamente equivalente al de HU3 (normal multivariada), con las mismas limitaciones: no captura relaciones no lineales entre variables que un modelo generativo más complejo (GAN/VAE) sí podría, y no fue validado con similitud estadística/utilidad predictiva formal como se hizo en HU3 para los datos sintéticos crudos — queda como trabajo futuro si esta configuración resulta relevante en los resultados experimentales.
