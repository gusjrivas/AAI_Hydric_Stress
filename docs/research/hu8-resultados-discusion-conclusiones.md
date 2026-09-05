# HU8 — Resultados, discusión y conclusiones

> **Actualización (2026-09-04) — corrección de fuga temporal, ver sección 6.** Las secciones 1-5 describen los resultados y conclusiones **previos** a esta corrección (`fix: corrige fuga temporal en imputacion y umbral de estres`, PR #164) y se conservan sin modificar como evidencia histórica. La sección 6, al final, actualiza específicamente la contrastación de hipótesis (sección 2) y la discusión (sección 4) a la luz de los resultados corregidos — léela antes de citar cualquier conclusión de este documento en la memoria técnica.

Épica 4, HU8 (sin capacidad de código, igual que HU1). Segundo y último sub-proyecto: contrastación con la hipótesis de investigación, limitaciones y amenazas a la validez, redacción de resultados/discusión/conclusiones, y consolidación final de evidencias. Se apoya en `docs/research/hu8-analisis-resultados.md` (primer sub-proyecto) y en las specs vigentes de `data-quality`, `predictive-modeling`, `human-feedback`, `architecture-integration` y `experiment-runner`.

## 1. Resultados experimentales

Sobre el conjunto experimental disponible (Melchor Romero, Partido de La Plata, año calendario 2024, 357 filas tras limpieza e ingeniería de variables), se evaluaron 4 configuraciones de la Épica 4, cada una con 5 semillas aleatorias, mediante un modelo Random Forest entrenado sobre variables de retardo y ventana móvil (HU4):

| Configuración | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión | Recall |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0.4625 ± 0.0414 | 0.5881 ± 0.0309 | 0.6097 | 0.3730 |
| Completa | 0.3733 ± 0.1065 | 0.5297 ± 0.0629 | 0.5286 | 0.2973 |

(`+Anomalías`/`Completa` re-ejecutadas y actualizadas en `openspec/changes/fix-anomaly-feature-integration/`, que corrigió que `is_anomaly` no llegaba al modelo como variable predictora.)

El modelo de referencia por persistencia, sin entrenamiento, alcanzó F1=0.486 sobre la misma partición temporal (HU4). Ninguna configuración de la arquitectura propuesta superó a ese modelo de referencia en F1. La detección de anomalías, ya conectada al modelo tras la corrección mencionada, mejoró de forma modesta pero consistente el ROC-AUC y la precisión (`+Anomalías` vs. `Base`, `Completa` vs. `+Sintéticos`, sin empeorar ningún indicador); el aumento con datos sintéticos siguió reduciendo el desempeño frente a no usarlos, tanto en valor medio como en estabilidad entre semillas.

El mecanismo de retroalimentación humana y recalibración supervisada (HU5) se verificó funcionalmente: una corrección humana sobre una fecha del conjunto de entrenamiento modifica la predicción del modelo recalibrado en esa misma fecha, de forma consistente con la corrección indicada. No se dispone de una evaluación agregada de su efecto sobre el desempeño general del modelo, por el volumen mínimo de retroalimentación humana real acumulada durante el desarrollo del prototipo.

Adicionalmente, se ejecutaron los escenarios de escasez y ruido de datos explícitos en la hipótesis de investigación (`openspec/changes/add-experiment-scenarios/`), sobre la configuración base:

| Escenario | F1 (media ± desvío) | Comparación con base sin escenario (0.4585 ± 0.0423) |
|---|---|---|
| Escasez (entrenamiento reducido a la mitad más reciente) | 0.6219 ± 0.0888 | Mejor |
| Ruido (gaussiano, proporción 0.3 del desvío de cada variable) | 0.3188 ± 0.1130 | Peor, y más variable |

El escenario de ruido degradó el desempeño y aumentó la variabilidad, como se esperaba. El escenario de escasez, en cambio, **mejoró** el desempeño — un hallazgo contraintuitivo explicado en la sección 4.

## 2. Contrastación con la hipótesis de investigación

La hipótesis de investigación (ADR-0001, plan de tesis) sostiene que *"la combinación de generación de datos sintéticos, detección de anomalías, modelado predictivo y retroalimentación humana mejora la detección temprana de estrés hídrico frente a enfoques tradicionales, en contextos de disponibilidad limitada, ruido y alta variabilidad de datos"*.

La evidencia experimental reunida en este prototipo **no confirma** esa hipótesis en su forma general, y en dos de sus cuatro componentes apunta en la dirección contraria:

- **Modelado predictivo**: el componente central de la arquitectura (Random Forest sobre variables de retardo/ventana móvil) no superó al enfoque tradicional más simple evaluado (persistencia por umbral) en la métrica principal (F1). No hay evidencia, con este dataset, de que el modelado predictivo propuesto mejore la detección temprana frente a un enfoque de referencia.
- **Detección de anomalías**: tras corregir la integración del orquestador (`openspec/changes/fix-anomaly-feature-integration/`) e incluir `is_anomaly` como variable predictora real, se observó un efecto **positivo pero modesto** sobre el desempeño (ROC-AUC y precisión mejoran en las dos comparaciones disponibles, F1 mejora levemente o queda dentro del ruido entre semillas, y ningún indicador empeora). La hipótesis respecto de este componente queda **evaluada de forma válida**, con un resultado que apunta a favor, aunque de magnitud acotada y sobre un único dataset.
- **Datos sintéticos**: se observó un efecto medible y **negativo** sobre el desempeño y la estabilidad. Con el método de generación sintética disponible (muestreo por normal multivariada sobre el espacio de variables ya construidas), la hipótesis de que los datos sintéticos mejoran la detección **se rechaza** para este dataset y este método.
- **Retroalimentación humana**: el mecanismo de recalibración funciona como está diseñado (cambia predicciones ante correcciones humanas), pero no hay evidencia agregada de que mejore el desempeño general, por falta de volumen de retroalimentación real. La hipótesis respecto de este componente también queda **sin evaluar**.
- **Contextos de disponibilidad limitada y ruido** (explícitos en la hipótesis): el escenario de ruido confirma la parte esperable de la hipótesis en sentido inverso — más ruido, peor desempeño, sin que ningún componente lo compense en este experimento (el ruido se inyectó sobre la configuración base, sin anomalías ni sintéticos). El escenario de escasez, en cambio, **no confirma** que "menos datos" perjudique la detección: en este dataset, un entrenamiento más chico pero más reciente superó al año completo, por relevancia estacional más que por cantidad de datos.

En síntesis: de los cuatro componentes que la hipótesis combina, uno (modelado predictivo) fue evaluado y no mostró mejora frente a un enfoque tradicional; otro (datos sintéticos) fue evaluado y mostró un efecto contrario al esperado; otro (detección de anomalías) fue evaluado, tras corregir un defecto de integración (`openspec/changes/fix-anomaly-feature-integration/`), y mostró un efecto positivo pero modesto; y uno (retroalimentación humana) no pudo evaluarse de forma concluyente, por una limitación de escala en el volumen de correcciones reales disponibles, no por ausencia de aporte demostrado. De los dos contextos de evaluación mencionados explícitamente en la hipótesis (ruido, escasez), el ruido se comportó como se esperaba (perjudicial) y la escasez no (fue beneficiosa en este caso concreto), matizando la premisa de que "más variabilidad/menos datos" es siempre desfavorable.

## 3. Limitaciones y amenazas a la validez

**Amenazas a la validez interna** (¿miden los experimentos lo que dicen medir?):

- La detección de anomalías originalmente no influía en la predicción del modelo, porque `is_anomaly` no formaba parte de las variables predictoras en `architecture_integration.pipeline.run_end_to_end_pipeline` (HU6). Esa limitación quedó corregida en `openspec/changes/fix-anomaly-feature-integration/` y la medición se repitió sobre el dataset real (ver sección 1); la conclusión sobre este componente ya es válida, aunque sigue acotada a un único dataset de un año.
- El umbral de alerta (0.5) y el umbral de estrés (percentil 20 de la distribución observada) son ambos elecciones no calibradas contra un criterio agronómico o de validación externa (`openspec/specs/predictive-modeling/spec.md`). Las métricas de precisión/recall reportadas dependen de esos umbrales, no son propiedades intrínsecas del modelo.
- El método de generación de datos sintéticos (normal multivariada sobre variables ya construidas) es una elección deliberadamente simple (`openspec/changes/add-experiment-design/proposal.md`); su efecto negativo observado no permite concluir que los datos sintéticos en general no aportan, solo que este método concreto no aportó con este dataset.

**Amenazas a la validez externa** (¿generalizan los resultados más allá de este experimento?):

- Un único punto geográfico (Melchor Romero, Partido de La Plata) y un único año calendario (2024). No hay evidencia de que los resultados se repitan en otro sitio, cultivo o período.
- El dataset consolidado tiene 357 filas tras limpieza — pequeño para un modelo de ensamble como Random Forest; el desvío estándar entre semillas (0.041-0.107 en F1, más alto en las configuraciones con datos sintéticos) ya sugiere sensibilidad del resultado al tamaño de muestra.
- El escenario de ruido usa un valor de ejemplo (`noise_std_ratio=0.3`) no calibrado contra ninguna fuente real de ruido de sensor — no hay una caracterización real de ese ruido más allá de los gaps ya documentados en ESA CCI Soil Moisture (HU2). El resultado (ruido perjudica el desempeño) es cualitativamente esperable, pero la magnitud reportada no es representativa de un nivel de ruido real medido.
- El escenario de escasez solo probó una fracción (50%) y una única forma de recorte (las fechas más recientes del período de entrenamiento); no se puede generalizar a otras fracciones u otras formas de subselección (ej. muestreo aleatorio) sin repetir la medición.
- La retroalimentación humana real acumulada durante el desarrollo (1-2 casos) es demasiado pequeña para generalizar cualquier conclusión sobre su efecto en producción.

## 4. Discusión y conclusiones

Los resultados de este prototipo no respaldan, con la evidencia reunida, la hipótesis de que la combinación de los cuatro componentes propuestos mejora la detección temprana de estrés hídrico frente a un enfoque tradicional. Esto no invalida necesariamente el enfoque arquitectónico (ADR-0001): la detección de anomalías, tras corregir su integración (`openspec/changes/fix-anomaly-feature-integration/`), sí mostró un efecto positivo (aunque modesto); y la retroalimentación humana no llegó a evaluarse en condiciones que permitan una conclusión válida, por una limitación de escala de la retroalimentación real disponible.

El hallazgo más claro y con mayor validez interna es que, en este dataset, un modelo de referencia sin entrenamiento (persistencia) es al menos tan bueno como el modelo entrenado propuesto — un resultado consistente con la literatura de pronóstico de series temporales de corto plazo, donde la persistencia suele ser un baseline difícil de superar cuando la variable objetivo tiene alta autocorrelación y el conjunto de entrenamiento es pequeño (como es el caso aquí, un solo año de datos).

El segundo hallazgo claro es que el método de generación de datos sintéticos elegido (normal multivariada) perjudica el desempeño en vez de mejorarlo. Esto es consistente con la limitación ya documentada de que ese método no captura relaciones no lineales ni la estructura de autocorrelación temporal real entre las variables — el mismo motivo, documentado desde HU3, por el que se descartó explícitamente un modelo generativo más complejo (GAN/VAE) *"para cuando haya más datos reales"*. Los resultados de HU7-HU8 son consistentes con esa decisión original: con los datos disponibles hoy, ni el dataset ni el método de síntesis alcanzan para que los datos sintéticos aporten valor.

El tercer hallazgo, sobre los escenarios explícitos de la hipótesis (escasez, ruido), es mixto: el ruido se comportó como la hipótesis anticipa (contexto adverso, peor desempeño), pero la escasez no — un entrenamiento más chico y más reciente superó al año completo. Esto sugiere que, para este dataset de un solo año, la *relevancia temporal* de los datos de entrenamiento pesa más que su *cantidad*, un matiz que la hipótesis original (formulada en términos de "disponibilidad limitada" como una condición uniformemente adversa) no distingue.

**Recomendaciones para trabajo futuro**, en orden de impacto esperado sobre la validez de una repetición de este experimento:

1. ~~Corregir la integración de la detección de anomalías...~~ **Hecho**: resuelto en `openspec/changes/fix-anomaly-feature-integration/`, con la medición ya repetida sobre el dataset real (efecto positivo pero modesto, ver sección 1). Queda como trabajo futuro repetir esta medición con más datos, para ver si el efecto se mantiene o se amplifica.
2. Ampliar el conjunto de datos real a más de un año y/o más de un punto geográfico, dado que el tamaño de muestra actual (357 filas) es la limitación más probable detrás de que ni el modelo entrenado ni el aumento sintético superen a la persistencia.
3. Repetir el escenario de escasez con más fracciones y con datos de más de un año, para distinguir si el efecto observado (menos datos, mejor desempeño) es realmente sobre relevancia estacional o una particularidad de esta partición puntual.
4. Calibrar el escenario de ruido contra una caracterización real de ruido de sensor, en vez del valor de ejemplo usado (`noise_std_ratio=0.3`).
5. Acumular retroalimentación humana real en un volumen que permita evaluar el efecto agregado de la recalibración, no solo su corrección mecánica en casos puntuales.
6. Calibrar el umbral de alerta y el umbral de estrés contra un criterio externo (agronómico o de retroalimentación humana), en vez de mantenerlos como valores por defecto no ajustados.

## 5. Consolidación de tablas, figuras, referencias y evidencias

**Fuentes de evidencia primaria** (todas verificadas con datos reales, no sintéticos de test, salvo donde se indica):

| Evidencia | Fuente |
|---|---|
| Resultados de las 4 configuraciones × 5 semillas | Servidor MLflow real (`http://localhost:5000`), experimento `hu7-epica4`; `openspec/changes/add-experiment-execution/` |
| Modelo de referencia por persistencia | `openspec/specs/predictive-modeling/spec.md`, requirement "Modelo de referencia por persistencia" |
| Comparación de modelos candidatos (partición única) | `openspec/specs/predictive-modeling/spec.md`, requirement "Comparación de desempeño, estabilidad y complejidad" |
| Falsos positivos/negativos con fechas | `openspec/specs/predictive-modeling/spec.md`, requirement "Análisis de errores de predicción por fecha" |
| Mecanismo de recalibración verificado | `openspec/specs/human-feedback/spec.md`, requirement "Recalibración supervisada de un modelo candidato" |
| Corrección de integración de `is_anomaly` y resultados re-ejecutados | `openspec/changes/fix-anomaly-feature-integration/`; `openspec/specs/architecture-integration/spec.md` y `openspec/specs/experiment-runner/spec.md` |
| Diseño experimental (preguntas, factores, configuraciones) | `openspec/specs/experiment-runner/spec.md` |
| Escenarios de escasez y ruido (ejecutados) | `openspec/changes/add-experiment-scenarios/`; servidor MLflow real, experimento `hu8-escenarios` |
| Análisis consolidado (secciones 1-10, HU8 primer sub-proyecto) | `docs/research/hu8-analisis-resultados.md` |
| Hipótesis de investigación (texto citado) | `docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md` |

No se generaron figuras (gráficos) en este sub-proyecto: las tablas anteriores y las de `docs/research/hu8-analisis-resultados.md` consolidan la evidencia cuantitativa disponible. La generación de figuras específicas para el documento final de tesis queda como tarea de redacción del documento completo, fuera del alcance de este repositorio de código.

## 6. Actualización tras corrección de fuga temporal (2026-09-04)

Una auditoría metodológica detectó dos fugas temporales reales en `src/architecture_integration/pipeline.py`: la imputación de valores faltantes y el umbral de la variable objetivo (percentil 20) se calculaban sobre el dataset completo antes de partir train/test, permitiendo que ambas operaciones usaran información del período de evaluación. Corregido sin alterar la arquitectura (detalle completo, tabla de métricas antes/después y análisis de causa en `docs/research/hu8-analisis-resultados.md`, sección 11).

**Re-lectura de la sección 2 (contrastación de hipótesis) a la luz de los resultados corregidos:**

- La afirmación "ninguna configuración de la arquitectura propuesta superó al modelo de referencia en F1" (sección 1) **ya no es cierta en términos de F1** (con el pipeline corregido, las 4 configuraciones superan numéricamente a la persistencia: 0.71-0.74 vs. 0.6087), pero esa comparación de F1 quedó confundida por un cambio real en la proporción de casos de estrés en evaluación (de ~51% a ~65%), no por una mejora genuina del modelo. La lectura correcta usa ROC-AUC, insensible a ese desbalance: las 4 configuraciones (0.4432-0.4962) están en o por debajo de 0.5, el valor de un clasificador sin capacidad de discriminación. La conclusión correcta es **más débil** que la original, no más fuerte: ni el modelo entrenado ni la persistencia discriminan de forma confiable entre estrés y no-estrés en este dataset, una vez eliminada la fuga.
- **Detección de anomalías**: el efecto relativo (`+Anomalías` mejor que `Base`, `Completa` mejor que `+Sintéticos`, en F1 y ROC-AUC) se mantiene igual de consistente que antes de la corrección. Esta sigue siendo la conclusión más sólida de las cuatro, aunque ahora dentro de un contexto donde ninguna configuración discrimina bien en términos absolutos.
- **Datos sintéticos**: el efecto negativo se mantiene igual de consistente (`+Sintéticos` peor que `Base`, `Completa` peor que `+Anomalías`, en F1 y ROC-AUC). La conclusión de rechazo de la hipótesis para este componente no cambia.
- **Retroalimentación humana**: sin cambios — el mecanismo no se re-evaluó a escala agregada, misma limitación que antes.
- **Escenarios de escasez y ruido**: ambos direccionalmente iguales que antes (escasez mejora, ruido empeora, frente a su propia base recalculada), aunque con los mismos valores absolutos desplazados por el cambio de tasa base.

**Re-lectura de la sección 4 (discusión) a la luz de los resultados corregidos:**

El hallazgo más claro de la sección 4 original ("un modelo de referencia sin entrenamiento es al menos tan bueno como el modelo entrenado propuesto") queda **reemplazado por un hallazgo más severo**: ni el modelo entrenado ni la persistencia muestran capacidad de discriminación medible sobre este dataset, una vez corregida la fuga que inflaba artificialmente el F1 de ambos por igual (al balancear artificialmente la clase de estrés en evaluación). Esto no invalida el segundo hallazgo (datos sintéticos perjudican) ni el tercero (escasez/ruido), que se mantienen sin cambios cualitativos.

**Recomendación adicional para trabajo futuro**, a agregar a la lista de la sección 4: dado que el ROC-AUC post-corrección sugiere que las variables predictoras actuales (retardos y ventanas móviles de humedad de suelo, radiación solar, humedad relativa) no alcanzan para discriminar el estrés futuro en este dataset, valdría la pena reconsiderar qué variables se usan como predictoras (por ejemplo, incorporar variables adicionales del conjunto consolidado, o revisar el horizonte de anticipación) antes de invertir en modelos más complejos — la limitación parece estar más en la señal disponible que en el algoritmo elegido.

## 7. Actualización tras segunda auditoría metodológica (2026-09-04): purga de frontera de horizonte, consistencia del detector de anomalías y métricas robustas al desbalance

Una segunda auditoría encontró una fuga temporal residual (las últimas filas de entrenamiento recibían una etiqueta objetivo derivada de una fecha ya perteneciente al período de evaluación, por el desplazamiento hacia adelante del horizonte) y un error de diseño (el detector de anomalías de evaluación se ajustaba sobre la propia distribución de evaluación en vez de reusar el detector de entrenamiento). Ambos corregidos sin alterar la arquitectura; además se agregó `gap=horizon_days` a la validación cruzada temporal, se rediseñó el desempate de selección de modelo (ya no favorece Random Forest por nombre) y se incorporaron baselines de clase mayoritaria y "siempre estrés" junto a las métricas MCC, balanced accuracy y PR-AUC (detalle completo, tabla de métricas y análisis de causa en `docs/research/hu8-analisis-resultados.md`, sección 12).

**Re-lectura de la sección 6 (actualización anterior) a la luz de estos resultados:**

- La conclusión "la detección de anomalías sigue ayudando de forma consistente" **ya no se sostiene**. Con la purga de frontera de horizonte, `Base` (F1 0.7309, MCC 0.0743) supera a `+Anomalías` (F1 0.7278, MCC 0.0571) en ambas métricas — el orden se invirtió respecto de la sección 6. Un diagnóstico por semilla muestra diferencias de signo mixto (`[+0.0122, +0.0158, -0.0396, +0.0210, -0.0250]`), es decir, ruido, no un efecto real. La conclusión correcta es que **no hay evidencia de que la detección de anomalías tenga un efecto real, positivo o negativo, sobre el desempeño del modelo**.
- La conclusión sobre datos sintéticos (efecto negativo consistente) **se mantiene sin cambios** — `+Sintéticos` y `Completa` siguen por debajo de sus contrapartes sin sintéticos en F1, ROC-AUC y ahora también en MCC.
- **Hallazgo nuevo, más severo que cualquiera de la sección 6**: el escenario de escasez de datos (`train_fraction=0.5`), que la sección 6 (heredando la sección 11.3) reportaba como una mejora de F1 frente a la base, tiene el **MCC más negativo de todo el estudio** (-0.1103, peor incluso que persistencia). Es el ejemplo más claro producido por esta auditoría de por qué evaluar solo con F1 puede ocultar, en vez de revelar, el desempeño real de un modelo bajo desbalance de clases: la "mejora" de F1 bajo escasez de datos no refleja una mejor discriminación, sino un desplazamiento de las predicciones hacia la clase mayoritaria de evaluación, agravado por tener menos datos de entrenamiento para corregirlo. **La recomendación de la sección 6 y de la sección 4 original (reconsiderar qué variables se usan como predictoras) se refuerza con este hallazgo**: ni el volumen de datos de entrenamiento por sí solo, ni los componentes arquitectónicos evaluados (anomalías, sintéticos), muestran evidencia de mejorar la capacidad de discriminación real del modelo sobre este dataset.
- La validación cruzada temporal ahora incluye `gap=horizon_days` y reporta explícitamente cuándo un fold de validación carece de ejemplos positivos (`selection_warning`), en vez de ocultar esa limitación detrás de un promedio de F1 de validación cruzada. Esto no cambió la elección de modelo (Random Forest sigue siendo elegido, ahora por desempeño real y no por un desempate arbitrario hacia su nombre), pero deja documentada la incertidumbre de esa elección para trabajo futuro.
- Se confirmó (sin cambios de código, por instrucción explícita de la auditoría) que ET0 no es una variable predictiva de ningún experimento de HU7/HU8 — es una capacidad de generación de datos sintéticos de HU2 sin relación con el modelo evaluado aquí. La memoria técnica no debe presentar ET0 como parte del modelo experimental de HU7/HU8.

**Conclusión general de esta actualización**: la incorporación de MCC y de los baselines de clase mayoritaria/siempre-estrés (motivada por esta misma auditoría) fue la que permitió detectar que dos conclusiones previamente reportadas como "mejoras" (detección de anomalías, escasez de datos) no correspondían a una mejora real de la capacidad de discriminación del modelo, sino a artefactos del desbalance de clases y del ruido de muestreo. Ninguna de las dos conclusiones se "forzó" a mejorar — se reportan tal como quedaron, incluyendo el hallazgo negativo de la sección 12.3, por instrucción explícita de no optimizar artificialmente para superar los baselines.
