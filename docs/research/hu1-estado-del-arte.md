# HU1 — Estado del arte y marco conceptual

Tarea de origen: "Redactar el estado del arte y el marco conceptual" (HU1, sección 9 del plan de tesis).

Este documento consolida, en un único entregable, los insumos relevados en `docs/research/hu1-variables-y-antecedentes.md` y `docs/research/hu1-retroalimentacion-humana.md`. Constituye el estado del arte disponible a la fecha para los tres ejes de HU1: modelado predictivo de estrés hídrico, detección de anomalías y datos sintéticos, y retroalimentación humana con recalibración de modelos.

> **Nota de alcance metodológico.** El corpus que sustenta este documento proviene de una búsqueda dirigida acotada, no de la ejecución del protocolo sistemático definido en `docs/research/hu1-protocolo-revision-bibliografica.md`. Las búsquedas en Scopus, Web of Science e IEEE Xplore permanecen bloqueadas por falta de acceso institucional. Por este motivo, el presente documento se considera una versión preliminar del estado del arte, sujeta a validación y ampliación una vez ejecutado el protocolo completo.

## 1. Introducción y alcance

El estrés hídrico en cultivos hortícolas de pequeña y mediana escala constituye el fenómeno central de este trabajo de tesis. El objetivo de esta revisión consiste en la caracterización del estado actual del conocimiento respecto de tres problemas interrelacionados: la predicción del estrés hídrico a partir de variables agronómicas y climáticas, la detección de anomalías en datos de sensores con el consecuente uso de datos sintéticos ante su escasez, y la incorporación de retroalimentación humana para la recalibración de modelos predictivos. La delimitación temporal del corpus corresponde al período 2019-2026, con la excepción de referencias seminales de vigencia metodológica sostenida (sección 5 del protocolo de revisión).

## 2. Marco conceptual

### 2.1. Estrés hídrico y sus variables asociadas

El estrés hídrico se define, en la literatura relevada, como la condición fisiológica derivada de un déficit de agua disponible para el cultivo, con efectos medibles tanto en variables fisiológicas directas (potencial hídrico foliar, conductancia estomática) como en variables proxy no destructivas (humedad de suelo, temperatura de canopia, índices de vegetación). La adopción de proxies no destructivos responde al costo y la naturaleza destructiva de la medición directa, lo cual motiva su preferencia en esquemas de monitoreo continuo de bajo costo.

Las variables climáticas estándar (temperatura, humedad relativa, precipitación, radiación solar, velocidad del viento) constituyen el insumo habitual del cálculo de evapotranspiración de referencia (ET0) mediante el método de Penman-Monteith, variable derivada de uso extendido en los modelos de manejo hídrico agrícola relevados. La tabla 1 detalla estas variables, su tipo y su prioridad para el esquema de datos de HU2.

**Tabla 1 — Variables predictoras de estrés hídrico**

| Variable | Tipo | Prioridad | Referencia |
|---|---|---|---|
| Humedad de suelo (SMC) | Agronómica | Obligatoria | Zhang et al., 2024 (*Sensors*) |
| Temperatura de canopia / foliar | Agronómica | Opcional | *ScienceDirect*, 2024 |
| Índices de vegetación (NDVI y derivados) | Agronómica | Opcional | Zhang et al., 2024 (*Sensors*) |
| Conductancia estomática / potencial hídrico foliar | Agronómica | Opcional (referencia) | Zhang et al., 2024 (*Sensors*) |
| Temperatura ambiente | Climática | Obligatoria | *J. Hydroinformatics* |
| Humedad relativa | Climática | Obligatoria | *J. Hydroinformatics* |
| Precipitación | Climática | Obligatoria | *J. Hydroinformatics* |
| Radiación solar | Climática | Obligatoria | *J. Hydroinformatics* |
| Velocidad del viento | Climática | Obligatoria | *J. Hydroinformatics* |
| Evapotranspiración de referencia (ET0) | Climática (derivada) | Obligatoria | *J. Hydroinformatics* |
| Marca temporal / frecuencia de muestreo | Temporal | Obligatoria | Requisito transversal |

El detalle de justificación por variable, con enlaces a cada referencia, se encuentra en `docs/research/hu1-variables-y-antecedentes.md`, sección 1.

### 2.2. Detección de anomalías y datos sintéticos

La literatura sobre detección de anomalías en sensores de humedad de suelo distingue dos enfoques predominantes: el control de calidad automático orientado a la identificación de fallas de sensor (DeepQC), y la detección autosupervisada que prescinde de etiquetas previas de anomalía. Este segundo enfoque resulta pertinente para el escenario de esta tesis, en el cual no existe un corpus etiquetado de anomalías disponible de antemano.

En paralelo, la generación de datos sintéticos surge como estrategia frente a la escasez de datos históricos, con dos líneas metodológicas principales: la generación condicionada por tarea y los modelos generativos (VAE, GAN) revisados en el ámbito de la agricultura de precisión. Ninguna de las referencias relevadas aborda de manera específica la generación de datos sintéticos para series temporales cortas de estrés hídrico en horticultura, lo cual constituye una vacancia de la literatura (sección 4).

### 2.3. Retroalimentación humana y recalibración

El concepto de *human-in-the-loop* (HITL) refiere, según la revisión sistemática de Entropy (2026), a la intervención humana en distintos puntos del ciclo de vida de un modelo de inteligencia artificial: el etiquetado de datos, la validación de salidas, la corrección de errores y la decisión de re-entrenamiento. La revisión de alcance sobre agricultura de precisión (Basnayake y Gajendrasinghe, 2026) concluye que los sistemas HITL presentan mayor robustez que los sistemas completamente automatizados en entornos de agricultura inteligente, aun cuando estos últimos alcancen mayor precisión en condiciones simuladas.

El marco de HILAD (2024) propone un ciclo bidireccional entre el modelo y el operador humano para la detección de anomalías en series temporales, en el cual la validación humana retroalimenta al modelo de forma iterativa. Este patrón constituye la referencia metodológica más cercana al mecanismo de retroalimentación previsto para HU5 y HU6 de este trabajo, aunque su dominio de aplicación no corresponde a sensores agrícolas ni a estrés hídrico específicamente. El detalle completo de esta matriz, con las seis referencias relevadas, se encuentra en `docs/research/hu1-retroalimentacion-humana.md`.

## 3. Síntesis comparativa de antecedentes

La matriz comparativa completa (catorce trabajos, con técnica de IA, fuente de datos, resultado principal y limitación) se distribuye entre `docs/research/hu1-variables-y-antecedentes.md` (sección 2, ocho trabajos sobre modelado predictivo, anomalías y datos sintéticos) y `docs/research/hu1-retroalimentacion-humana.md` (seis trabajos sobre retroalimentación humana y recalibración). No se reproduce aquí en su totalidad para evitar duplicación; este documento remite a ambas fuentes como corpus de referencia.

De la síntesis se desprenden tres observaciones transversales:

1. La mayoría de los trabajos aborda cada uno de los tres ejes (predicción, anomalías/datos sintéticos, retroalimentación humana) de forma aislada. Ningún trabajo relevado integra los tres componentes en una arquitectura única aplicada a estrés hídrico en horticultura.
2. Los trabajos de detección de anomalías que prescinden de etiquetas previas (DeepQC, detección autosupervisada) resultan compatibles con el escenario de datos sin etiquetar de esta tesis, a diferencia de enfoques supervisados que exigen un corpus previamente validado.
3. Los antecedentes de retroalimentación humana provienen, en su mayoría, de dominios distintos al agrícola (series temporales genéricas, sistemas de recomendación de manejo agrícola general). Su aporte es de tipo metodológico y conceptual, no de dominio.

## 4. Vacancias identificadas y criterios de diseño

Las vacancias que se detallan a continuación integran las identificadas en `docs/research/hu1-variables-y-antecedentes.md` (sección 3) y en `docs/research/hu1-retroalimentacion-humana.md`:

- **Vacancia de integración.** No se identifica, en el corpus relevado, una arquitectura que combine predicción de estrés hídrico, detección de anomalías, generación de datos sintéticos y retroalimentación humana para recalibración en un flujo único aplicado a horticultura de pequeña y mediana escala. Esta vacancia constituye el aporte diferencial que persigue el presente trabajo de tesis.
- **Vacancia de dominio en retroalimentación humana.** Los antecedentes de HITL más cercanos en mecanismo (HILAD) corresponden a dominios distintos del agrícola; la adaptación de ese patrón a alertas de estrés hídrico carece de precedente directo.
- **Vacancia de especificidad en datos sintéticos.** Los trabajos de generación de datos sintéticos revisados no atienden al caso de series temporales cortas y con escasez extrema de datos (*few-shot*) propio de este proyecto.

De estas vacancias se derivan los siguientes criterios de diseño, ya incorporados al esquema de datos de HU2 y pendientes de incorporación en el diseño de HU5/HU6:

- El esquema de datos debe permitir la trazabilidad de un registro desde su ingesta hasta la alerta y la retroalimentación asociada.
- El esquema debe admitir la ausencia de etiqueta de calidad conocida en lugar de presuponer un campo de calidad ya validado.
- El origen de cada registro (`real` o `sintético`) debe constar desde la ingesta, no como agregado posterior.
- La granularidad temporal mínima de las variables climáticas obligatorias corresponde al nivel diario, con preservación de la resolución nativa cuando esta sea mayor.
- Un registro se considera válido para el modelado únicamente si contiene humedad de suelo y las variables climáticas obligatorias de la tabla 1.
- El esquema de HU5/HU6 debe registrar, por cada alerta, la presencia y el tipo de retroalimentación humana recibida (confirmación, corrección o descarte), y si dicha retroalimentación derivó en una recalibración del modelo.
- El diseño de HU5/HU6 debe incorporar una medida de confianza o incertidumbre por alerta, con el fin de priorizar qué alertas se someten a validación humana, en lugar de requerir dicha validación de manera uniforme sobre el total de alertas generadas.

## 5. Limitaciones del presente estado del arte

El corpus relevado presenta tres limitaciones que condicionan el alcance de las conclusiones anteriores. En primer lugar, la búsqueda no siguió el protocolo sistemático definido para HU1, por lo cual no existe garantía de exhaustividad ni de ausencia de sesgo de selección. En segundo lugar, la consulta a fuentes agronómicas regionales se realizó de forma parcial: `docs/research/hu1-antecedentes-argentina.md` releva antecedentes en SciELO Argentina, Horticultura Argentina e INTA, pero AGRIS todavía no se consultó mediante su interfaz de búsqueda sistemática, lo cual limita la representación completa de antecedentes locales sobre horticultura en Argentina. En tercer lugar, la revisión de trabajos sobre modelado predictivo y detección de anomalías se sustenta, en su mayor parte, en una única referencia de síntesis (*Sensors*, 2024) para la caracterización de variables, lo cual reduce la triangulación de fuentes independientes.

## 6. Conclusión

El estado del arte disponible confirma la existencia de una vacancia de integración entre predicción de estrés hídrico, gestión de anomalías y datos sintéticos, y retroalimentación humana, aplicada específicamente a horticultura de pequeña y mediana escala. Dicha vacancia sustenta la pertinencia del problema de investigación planteado en el plan de tesis. La validación definitiva de esta conclusión requiere la ejecución del protocolo sistemático de revisión bibliográfica, pendiente de acceso institucional a Scopus y Web of Science, y la incorporación de fuentes agronómicas regionales todavía no consultadas.
