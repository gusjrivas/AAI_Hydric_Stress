# HU8 — Resultados, discusión y conclusiones

Épica 4, HU8 (sin capacidad de código, igual que HU1). Segundo y último sub-proyecto: contrastación con la hipótesis de investigación, limitaciones y amenazas a la validez, redacción de resultados/discusión/conclusiones, y consolidación final de evidencias. Se apoya en `docs/research/hu8-analisis-resultados.md` (primer sub-proyecto) y en las specs vigentes de `data-quality`, `predictive-modeling`, `human-feedback`, `architecture-integration` y `experiment-runner`.

## 1. Resultados experimentales

Sobre el conjunto experimental disponible (Melchor Romero, Partido de La Plata, año calendario 2024, 357 filas tras limpieza e ingeniería de variables), se evaluaron 4 configuraciones de la Épica 4, cada una con 5 semillas aleatorias, mediante un modelo Random Forest entrenado sobre variables de retardo y ventana móvil (HU4):

| Configuración | F1 (media ± desvío) | ROC-AUC (media ± desvío) | Precisión | Recall |
|---|---|---|---|---|
| Base | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| +Sintéticos | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |
| +Anomalías | 0.4585 ± 0.0423 | 0.5551 ± 0.0191 | 0.5967 | 0.3730 |
| Completa | 0.3123 ± 0.0862 | 0.5083 ± 0.0439 | 0.5091 | 0.2324 |

El modelo de referencia por persistencia, sin entrenamiento, alcanzó F1=0.486 sobre la misma partición temporal (HU4). Ninguna configuración de la arquitectura propuesta superó a ese modelo de referencia en F1. La detección de anomalías no modificó ninguna métrica respecto de la configuración sin ella (`+Anomalías` = `Base`, `Completa` = `+Sintéticos`, exactamente); el aumento con datos sintéticos redujo el desempeño frente a no usarlos, tanto en valor medio como en estabilidad entre semillas.

El mecanismo de retroalimentación humana y recalibración supervisada (HU5) se verificó funcionalmente: una corrección humana sobre una fecha del conjunto de entrenamiento modifica la predicción del modelo recalibrado en esa misma fecha, de forma consistente con la corrección indicada. No se dispone de una evaluación agregada de su efecto sobre el desempeño general del modelo, por el volumen mínimo de retroalimentación humana real acumulada durante el desarrollo del prototipo.

## 2. Contrastación con la hipótesis de investigación

La hipótesis de investigación (ADR-0001, plan de tesis) sostiene que *"la combinación de generación de datos sintéticos, detección de anomalías, modelado predictivo y retroalimentación humana mejora la detección temprana de estrés hídrico frente a enfoques tradicionales, en contextos de disponibilidad limitada, ruido y alta variabilidad de datos"*.

La evidencia experimental reunida en este prototipo **no confirma** esa hipótesis en su forma general, y en dos de sus cuatro componentes apunta en la dirección contraria:

- **Modelado predictivo**: el componente central de la arquitectura (Random Forest sobre variables de retardo/ventana móvil) no superó al enfoque tradicional más simple evaluado (persistencia por umbral) en la métrica principal (F1). No hay evidencia, con este dataset, de que el modelado predictivo propuesto mejore la detección temprana frente a un enfoque de referencia.
- **Detección de anomalías**: no se observó ningún efecto, positivo o negativo, sobre el desempeño. La causa identificada (`docs/research/hu8-analisis-resultados.md`, sección 5) es una limitación de integración del orquestador (HU6), no una medición válida del aporte real de la técnica. La hipótesis respecto de este componente queda **sin evaluar**, no refutada.
- **Datos sintéticos**: se observó un efecto medible y **negativo** sobre el desempeño y la estabilidad. Con el método de generación sintética disponible (muestreo por normal multivariada sobre el espacio de variables ya construidas), la hipótesis de que los datos sintéticos mejoran la detección **se rechaza** para este dataset y este método.
- **Retroalimentación humana**: el mecanismo de recalibración funciona como está diseñado (cambia predicciones ante correcciones humanas), pero no hay evidencia agregada de que mejore el desempeño general, por falta de volumen de retroalimentación real. La hipótesis respecto de este componente también queda **sin evaluar**.

En síntesis: de los cuatro componentes que la hipótesis combina, uno (modelado predictivo) fue evaluado y no mostró mejora frente a un enfoque tradicional; otro (datos sintéticos) fue evaluado y mostró un efecto contrario al esperado; y dos (detección de anomalías, retroalimentación humana) no pudieron evaluarse de forma concluyente con la evidencia disponible, por limitaciones de integración y de escala respectivamente, no por ausencia de aporte demostrado.

## 3. Limitaciones y amenazas a la validez

**Amenazas a la validez interna** (¿miden los experimentos lo que dicen medir?):

- La detección de anomalías nunca influye en la predicción del modelo, porque `is_anomaly` no forma parte de las variables predictoras en `architecture_integration.pipeline.run_end_to_end_pipeline` (HU6). Cualquier conclusión sobre "el aporte de la detección de anomalías" a partir de estos experimentos es inválida hasta corregir esa integración y repetir la medición.
- El umbral de alerta (0.5) y el umbral de estrés (percentil 20 de la distribución observada) son ambos elecciones no calibradas contra un criterio agronómico o de validación externa (`openspec/specs/predictive-modeling/spec.md`). Las métricas de precisión/recall reportadas dependen de esos umbrales, no son propiedades intrínsecas del modelo.
- El método de generación de datos sintéticos (normal multivariada sobre variables ya construidas) es una elección deliberadamente simple (`openspec/changes/add-experiment-design/proposal.md`); su efecto negativo observado no permite concluir que los datos sintéticos en general no aportan, solo que este método concreto no aportó con este dataset.

**Amenazas a la validez externa** (¿generalizan los resultados más allá de este experimento?):

- Un único punto geográfico (Melchor Romero, Partido de La Plata) y un único año calendario (2024). No hay evidencia de que los resultados se repitan en otro sitio, cultivo o período.
- El dataset consolidado tiene 357 filas tras limpieza — pequeño para un modelo de ensamble como Random Forest; el desvío estándar entre semillas (0.042-0.086 en F1) ya sugiere sensibilidad del resultado al tamaño de muestra.
- Los escenarios de escasez y ruido de datos, parte explícita de la hipótesis ("contextos de disponibilidad limitada, ruido y alta variabilidad de datos"), no se ejecutaron: no hay una fuente real que caracterice el ruido de sensor esperado más allá de los gaps ya documentados en ESA CCI Soil Moisture (HU2), y el procedimiento automatizado no implementó todavía un escenario de escasez controlada. La hipótesis se formula explícitamente para esos contextos, y este prototipo no los evaluó.
- La retroalimentación humana real acumulada durante el desarrollo (1-2 casos) es demasiado pequeña para generalizar cualquier conclusión sobre su efecto en producción.

## 4. Discusión y conclusiones

Los resultados de este prototipo no respaldan, con la evidencia reunida, la hipótesis de que la combinación de los cuatro componentes propuestos mejora la detección temprana de estrés hídrico frente a un enfoque tradicional. Esto no invalida necesariamente el enfoque arquitectónico (ADR-0001): dos de los cuatro componentes (detección de anomalías, retroalimentación humana) no llegaron a evaluarse en condiciones que permitan una conclusión válida, por una limitación de integración identificada y corregible, y por una limitación de escala de la retroalimentación real disponible, respectivamente.

El hallazgo más claro y con mayor validez interna es que, en este dataset, un modelo de referencia sin entrenamiento (persistencia) es al menos tan bueno como el modelo entrenado propuesto — un resultado consistente con la literatura de pronóstico de series temporales de corto plazo, donde la persistencia suele ser un baseline difícil de superar cuando la variable objetivo tiene alta autocorrelación y el conjunto de entrenamiento es pequeño (como es el caso aquí, un solo año de datos).

El segundo hallazgo claro es que el método de generación de datos sintéticos elegido (normal multivariada) perjudica el desempeño en vez de mejorarlo. Esto es consistente con la limitación ya documentada de que ese método no captura relaciones no lineales ni la estructura de autocorrelación temporal real entre las variables — el mismo motivo, documentado desde HU3, por el que se descartó explícitamente un modelo generativo más complejo (GAN/VAE) *"para cuando haya más datos reales"*. Los resultados de HU7-HU8 son consistentes con esa decisión original: con los datos disponibles hoy, ni el dataset ni el método de síntesis alcanzan para que los datos sintéticos aporten valor.

**Recomendaciones para trabajo futuro**, en orden de impacto esperado sobre la validez de una repetición de este experimento:

1. Corregir la integración de la detección de anomalías (incluir `is_anomaly`, o una variable derivada, entre las variables predictoras del modelo) antes de volver a medir su aporte — la conclusión actual sobre este componente no es válida.
2. Ampliar el conjunto de datos real a más de un año y/o más de un punto geográfico, dado que el tamaño de muestra actual (357 filas) es la limitación más probable detrás de que ni el modelo entrenado ni el aumento sintético superen a la persistencia.
3. Ejecutar los escenarios de escasez y ruido explícitos en la hipótesis de investigación, una vez que se disponga de una caracterización real de esas condiciones (o de datos sintéticos suficientemente fieles para simularlas de forma justificada).
4. Acumular retroalimentación humana real en un volumen que permita evaluar el efecto agregado de la recalibración, no solo su corrección mecánica en casos puntuales.
5. Calibrar el umbral de alerta y el umbral de estrés contra un criterio externo (agronómico o de retroalimentación humana), en vez de mantenerlos como valores por defecto no ajustados.

## 5. Consolidación de tablas, figuras, referencias y evidencias

**Fuentes de evidencia primaria** (todas verificadas con datos reales, no sintéticos de test, salvo donde se indica):

| Evidencia | Fuente |
|---|---|
| Resultados de las 4 configuraciones × 5 semillas | Servidor MLflow real (`http://localhost:5000`), experimento `hu7-epica4`; `openspec/changes/add-experiment-execution/` |
| Modelo de referencia por persistencia | `openspec/specs/predictive-modeling/spec.md`, requirement "Modelo de referencia por persistencia" |
| Comparación de modelos candidatos (partición única) | `openspec/specs/predictive-modeling/spec.md`, requirement "Comparación de desempeño, estabilidad y complejidad" |
| Falsos positivos/negativos con fechas | `openspec/specs/predictive-modeling/spec.md`, requirement "Análisis de errores de predicción por fecha" |
| Mecanismo de recalibración verificado | `openspec/specs/human-feedback/spec.md`, requirement "Recalibración supervisada de un modelo candidato" |
| Limitación de integración de `is_anomaly` | `openspec/specs/architecture-integration/spec.md`, "Limitaciones conocidas" |
| Diseño experimental (preguntas, factores, configuraciones) | `openspec/specs/experiment-runner/spec.md` |
| Análisis consolidado (secciones 1-10, HU8 primer sub-proyecto) | `docs/research/hu8-analisis-resultados.md` |
| Hipótesis de investigación (texto citado) | `docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md` |

No se generaron figuras (gráficos) en este sub-proyecto: las tablas anteriores y las de `docs/research/hu8-analisis-resultados.md` consolidan la evidencia cuantitativa disponible. La generación de figuras específicas para el documento final de tesis queda como tarea de redacción del documento completo, fuera del alcance de este repositorio de código.
