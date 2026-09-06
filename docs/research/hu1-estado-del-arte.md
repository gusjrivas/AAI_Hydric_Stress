# HU1 — Estado del arte y marco conceptual

Tarea de origen: "Redactar el estado del arte y el marco conceptual" (HU1, issue #32; criterios de aceptación de la Épica 1, issue #10).

Este documento constituye la versión definitiva del estado del arte de HU1. Reemplaza las versiones preliminares anteriores, redactadas antes de la consolidación y validación científica del corpus bibliográfico.

## 1. Introducción y alcance

El propósito de HU1 consiste en fundamentar, mediante una revisión bibliográfica, las decisiones de diseño de la arquitectura propuesta para la detección temprana de estrés hídrico en cultivos hortícolas de pequeña y mediana escala. La revisión se caracteriza como una **revisión bibliográfica estructurada y dirigida, con criterios explícitos de búsqueda, inclusión, exclusión, trazabilidad y verificación**, y no como una revisión sistemática exhaustiva bajo un protocolo tipo PRISMA.

El período de análisis corresponde a 2019-2026, con la excepción explícita de referencias seminales de vigencia metodológica sostenida (`docs/research/hu1-protocolo-revision-bibliografica.md`, sección 5); ninguna de las 25 referencias representativas validadas invocó esta excepción.

Las fuentes efectivamente utilizadas fueron Scopus e IEEE Xplore, ejecutadas y registradas para los cuatro ejes (`docs/research/hu1-registro-busquedas.csv`, exports reales en `docs/research/exports/`), complementadas con búsquedas automatizadas vía API pública en Crossref, OpenAlex y DOAJ. Web of Science no pudo ejecutarse: la cuenta institucional disponible permite búsqueda de perfiles de investigadores, pero no Document Search/Core Collection. AGRIS no pudo completarse bajo el protocolo previsto por una limitación de herramienta (interfaz de búsqueda no automatizable). Ambas limitaciones quedan documentadas y no se presentan como si invalidaran el corpus consolidado.

El corpus final consolida 450 registros, de los cuales 180 quedaron incluidos, 256 excluidos y 14 indeterminados por metadatos insuficientes o no verificables (`docs/research/hu1-corpus-final.csv`, `docs/research/hu1-cola-revision-humana.csv`). A partir de este corpus se validó una selección representativa de 25 referencias (`docs/research/hu1-referencias-representativas-validadas.csv`), verificadas por DOI/Crossref, con cobertura de los cuatro ejes (eje 1: 6, eje 2: 5, eje 3: 9, eje 4: 5). Estos números describen el alcance de una revisión dirigida y verificada, no los resultados de una revisión sistemática bajo un protocolo tipo PRISMA.

## 2. Marco conceptual

### 2.1. Estrés hídrico y variables de monitoreo

El estrés hídrico se define, en la literatura relevada, como la condición fisiológica derivada de un déficit de agua disponible para el cultivo, con efectos medibles tanto en variables fisiológicas directas (potencial hídrico foliar, conductancia estomática) como en variables proxy no destructivas (humedad de suelo, temperatura de canopia, índices de vegetación). La adopción de proxies no destructivos responde al costo y a la naturaleza destructiva de la medición directa, lo cual motiva su preferencia en esquemas de monitoreo continuo de bajo costo.

Las variables climáticas estándar (temperatura, humedad relativa, precipitación, radiación solar, velocidad del viento) constituyen el insumo habitual del cálculo de evapotranspiración de referencia (ET0) mediante el método de Penman-Monteith. La tabla 1 detalla estas variables, su tipo y su prioridad en el esquema de ingesta de datos definido en `openspec/specs/data-ingestion/spec.md`.

**Tabla 1 — Variables de monitoreo del esquema de datos**

| Variable | Tipo | Prioridad en el esquema de ingesta | Referencia |
|---|---|---|---|
| Humedad de suelo (SMC) | Agronómica | Obligatoria | Cho et al., 2024 ([*Sensors*](https://www.mdpi.com/1424-8220/24/19/6313)) |
| Temperatura de canopia / foliar | Agronómica | Opcional | [*ScienceDirect*, 2024](https://www.sciencedirect.com/science/article/pii/S0378377424003949) |
| Índices de vegetación (NDVI y derivados) | Agronómica | Opcional | Cho et al., 2024 ([*Sensors*](https://www.mdpi.com/1424-8220/24/19/6313)) |
| Conductancia estomática / potencial hídrico foliar | Agronómica | Opcional (referencia) | Cho et al., 2024 ([*Sensors*](https://www.mdpi.com/1424-8220/24/19/6313)) |
| Temperatura ambiente | Climática | Obligatoria | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Humedad relativa | Climática | Obligatoria | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Precipitación | Climática | Obligatoria | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Radiación solar | Climática | Obligatoria | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Velocidad del viento | Climática | Obligatoria | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Evapotranspiración de referencia (ET0) | Climática (derivada) | Obligatoria en el esquema de ingesta | [*J. Hydroinformatics*](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) |
| Marca temporal / frecuencia de muestreo | Temporal | Obligatoria | Requisito transversal |

La obligatoriedad de ET0 indicada en la tabla corresponde exclusivamente al esquema de ingesta de datos (`openspec/specs/data-ingestion/spec.md`), donde se declara como columna obligatoria aunque derivada en preprocesamiento, no ingerida directamente de ninguna fuente. Esta obligatoriedad no se extiende al modelado predictivo: `openspec/specs/predictive-modeling/spec.md` documenta explícitamente que ET0 no es una variable predictora en ningún experimento de HU7/HU8, dado que el dataset experimental real no registra valores no nulos para esa columna. ET0 puede utilizarse como variable derivada o en análisis posteriores, pero no se declara predictor obligatorio, y este documento no modifica esa decisión formal.

El detalle de justificación por variable, con enlaces a cada referencia, se encuentra en `docs/research/hu1-variables-y-antecedentes.md`, sección 1.

### 2.2. Modelado predictivo

La literatura relevada aborda la predicción de estrés hídrico y humedad de suelo mediante modelos de complejidad baja a media (Random Forest, SVR, ANN superficiales) y, cuando la tarea exige un horizonte temporal explícito de forecasting, mediante modelos recurrentes (LSTM, Bi-GRU). La elección de técnica está condicionada por el volumen y la calidad de los datos disponibles, no por una preferencia metodológica hacia la complejidad del modelo. El detalle comparativo se encuentra en `docs/research/hu1-matriz-comparativa-final.md`, eje 1.

### 2.3. Detección de anomalías

La literatura sobre detección de anomalías en sensores de humedad de suelo distingue dos enfoques predominantes: el control de calidad basado en reglas y estadística clásica, y la detección no supervisada mediante aprendizaje automático (Isolation Forest, One-Class SVM), que prescinde de etiquetas previas de anomalía. Este segundo enfoque resulta pertinente para el escenario de esta tesis, en el cual no existe un corpus etiquetado de anomalías disponible de antemano. El detalle comparativo se encuentra en `docs/research/hu1-matriz-comparativa-final.md`, eje 2.

### 2.4. Generación de datos sintéticos

La generación de datos sintéticos surge como estrategia frente a la escasez de datos históricos, mediante modelos generativos (redes generativas adversarias, autoencoders variacionales, modelos de difusión, TimeGAN) o mediante simulación restringida por conocimiento físico del dominio. En el corpus analizado no se identificó un antecedente que aplique estos métodos de forma específica a series temporales cortas de estrés hídrico en horticultura. El detalle comparativo se encuentra en `docs/research/hu1-matriz-comparativa-final.md`, eje 3.

### 2.5. Retroalimentación humana y recalibración

El concepto de intervención humana en el ciclo de vida de un modelo de inteligencia artificial (validación de salidas, corrección de errores, decisión de reentrenamiento) se documenta principalmente en dominios distintos del agrícola. En el corpus analizado no se identificó un antecedente que evalúe la intervención humana aplicada específicamente a un sistema de alertas de estrés hídrico. El detalle comparativo se encuentra en `docs/research/hu1-matriz-comparativa-final.md`, eje 4.

En los cinco apartados anteriores, los sensores y la infraestructura de Internet de las Cosas aparecen únicamente como fuente de datos y como contexto experimental de los antecedentes relevados, no como la contribución central de esta tesis.

## 3. Síntesis comparativa

La matriz comparativa definitiva se encuentra en `docs/research/hu1-matriz-comparativa-final.md`. Se construyó a partir de la selección representativa validada de 25 referencias (`docs/research/hu1-referencias-representativas-validadas.csv`), verificadas por DOI/Crossref sobre el corpus consolidado de 450 registros, y reemplaza las matrices preliminares anteriores (de 8 y de 14 trabajos) citadas en versiones previas de este documento.

La síntesis por eje, con patrones observados, limitaciones comunes e implicancias de diseño, se encuentra en cada bloque de `docs/research/hu1-matriz-comparativa-final.md`. En términos generales: el modelado predictivo no exige aprendizaje profundo como requisito (eje 1); la detección de anomalías se orienta hacia métodos no supervisados compatibles con la ausencia de etiquetas (eje 2); la generación de datos sintéticos se valida mayoritariamente contra un único modelo downstream, sin evaluación sistemática de fidelidad estadística (eje 3); y la retroalimentación humana se documenta como mecanismo de validación y corrección, sin evidencia de que mejore necesariamente la confianza del usuario (eje 4).

## 4. Vacancia identificada

En el corpus analizado no se identificó un enfoque que evaluara de manera conjunta y controlada el aporte individual y conjunto del modelado predictivo, la detección de anomalías, la generación de datos sintéticos y la retroalimentación humana para la detección temprana de estrés hídrico en horticultura, bajo escenarios explícitos de escasez, ruido y variabilidad temporal de los datos.

Esta vacancia distingue varios planos, detallados en `docs/research/hu1-matriz-comparativa-final.md`, sección "Síntesis de vacancia":

- **Vacancia de integración controlada.** Los antecedentes que combinan más de un componente lo hacen de a pares (generación de datos sintéticos con modelado predictivo, o detección de anomalías con un componente de predicción o de automatización), no con los cuatro componentes evaluados conjuntamente.
- **Escasez y variabilidad de datos.** Los antecedentes de modelado predictivo y de generación de datos sintéticos abordan la escasez de datos de forma parcial, generalmente en un único cultivo o localización, sin escenarios explícitos y simultáneos de escasez, ruido y variabilidad temporal.
- **Transferencia de técnicas desde otros dominios.** Una parte sustancial de los antecedentes de detección de anomalías y de retroalimentación humana proviene de dominios distintos del agrícola, con transferibilidad metodológica directa pero sin validación previa en el dominio de esta tesis.
- **Necesidad de evaluación individual y conjunta.** La contribución que se busca no depende de demostrar la novedad absoluta de cada componente por separado, sino de evaluar su aporte individual y combinado bajo un protocolo experimental común.

Esta formulación se sostiene con la evidencia disponible, sujeta a la limitación explícita de que Web of Science y AGRIS no pudieron consultarse bajo el protocolo previsto (sección 7).

## 5. Criterios derivados para la selección de técnicas

Esta sección responde al criterio de aceptación "se justificó la selección de las técnicas que serán evaluadas" (issue #10) y a la tarea correspondiente. La justificación se mantiene coherente con la propuesta de tesis aprobada, con la arquitectura definida en `docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md` y con las especificaciones formales vigentes (`openspec/specs/`).

Reglas permanentes que se mantienen en esta sección:

- El aprendizaje profundo no es obligatorio. Las técnicas se seleccionan según las características, el volumen, la calidad y la disponibilidad de los datos, no según una preferencia metodológica hacia la complejidad.
- Los sensores y la infraestructura de Internet de las Cosas constituyen fuentes de datos y contexto experimental, no la contribución central de esta tesis.
- El núcleo técnico de la tesis está compuesto por cuatro componentes: modelado predictivo, generación de datos sintéticos, detección de anomalías y retroalimentación humana para recalibración progresiva.

Para cada componente se distingue entre: (a) técnicas candidatas justificadas por la literatura relevada; (b) técnicas efectivamente adoptadas por las especificaciones formales actuales; y (c) técnicas que permanecen como alternativas experimentales. Esta sección no modifica ninguna decisión formal ya adoptada por HU7 o HU8; cuando existe una diferencia entre lo sugerido por la literatura y lo implementado, se explica como una decisión metodológica documentada, no se corrige silenciosamente.

### 5.1. Modelado predictivo

La literatura relevada (`docs/research/hu1-matriz-comparativa-final.md`, eje 1) justifica la comparación de modelos de complejidad creciente según la disponibilidad de datos: desde regresión logística y Random Forest hasta modelos recurrentes (LSTM, Bi-GRU) cuando el volumen de datos y la necesidad de un horizonte temporal explícito lo justifiquen. `openspec/specs/predictive-modeling/spec.md` adopta formalmente regresión logística y Random Forest como modelos candidatos, comparados mediante validación cruzada temporal. En la configuración experimental vigente, el procedimiento formal de selección basado en desempeño de validación temporal selecciona Random Forest. Esta selección corresponde al dataset y al protocolo experimental actuales y no constituye un requisito arquitectónico permanente: un volumen o una calidad de datos distintos podrían derivar en la selección de otro modelo candidato dentro del mismo mecanismo de comparación. Ningún antecedente ni ninguna especificación formal establece una técnica de aprendizaje profundo como requisito; permanece como alternativa experimental a evaluar si el volumen de datos disponible lo justifica, conforme a `docs/adr/0002-stack-tecnico-poc.md`.

### 5.2. Detección de anomalías

La literatura relevada (`docs/research/hu1-matriz-comparativa-final.md`, eje 2) justifica enfoques compatibles con la ausencia o escasez de etiquetas de anomalía, con ruido y con fallas de sensor, preservando los datos reales sin descartarlos. `openspec/specs/data-quality/spec.md` adopta formalmente Isolation Forest como método no supervisado, evaluado mediante inyección de anomalías sintéticas conocidas, dado que no existen anomalías reales etiquetadas contra las cuales evaluar. Métodos estadísticos más simples (Z-score, rango intercuartílico) permanecen como línea de base complementaria, no como sustituto.

### 5.3. Generación de datos sintéticos

La literatura relevada (`docs/research/hu1-matriz-comparativa-final.md`, eje 3) justifica explorar la generación de datos sintéticos como estrategia frente a la escasez de datos agrícolas, mediante modelos generativos (GAN, VAE, TimeGAN, modelos de difusión) o simulación restringida por conocimiento físico, sin imponer una técnica única. El mecanismo de referencia actualmente implementado (`openspec/specs/data-quality/spec.md`) utiliza un método estadístico basado en una distribución normal multivariada; un modelo generativo profundo (GAN o VAE) permanece documentado en la especificación como alternativa metodológica a evaluar cuando exista mayor volumen de datos reales disponibles. Se mantienen, como reglas permanentes: los datos sintéticos no sustituyen la validación con datos reales; deben distinguirse de la augmentation convencional (recorte, rotación, escalado, deformación temporal), que no constituye generación de datos sintéticos propiamente dicha; debe preservarse la trazabilidad del origen real o sintético de cada registro desde la ingesta; y su aporte debe evaluarse experimentalmente, no asumirse por diseño.

### 5.4. Retroalimentación humana

La literatura relevada (`docs/research/hu1-matriz-comparativa-final.md`, eje 4) justifica la intervención humana como mecanismo conceptual de confirmación, corrección o descarte de alertas, con posible recalibración progresiva del modelo. `openspec/specs/human-feedback/spec.md` implementa este mecanismo mediante un contrato técnico con terminología propia, distinta de la descripción conceptual anterior: cada alerta queda representada con un estado de validación (`pendiente`, `confirmada` o `rechazada`), una etiqueta corregida opcional y una observación opcional. La recalibración supervisada reentrena el modelo únicamente sobre las observaciones en estado `rechazada` que tienen una etiqueta corregida asociada; las observaciones `confirmada` se excluyen deliberadamente de la recalibración, dado que no corrigen ningún error. No se afirma que toda retroalimentación produzca automáticamente un reentrenamiento: la recalibración tiene un disparo manual (`docs/adr/0006-recalibracion-disparada-desde-la-ui.md`), no se ejecuta en cada evento de retroalimentación individual.

## 6. Antecedentes regionales y contexto argentino

Esta sección integra únicamente la evidencia ya verificada en `docs/research/hu1-antecedentes-argentina.md`, sin agregar antecedentes nuevos. Se distinguen tres categorías:

**Antecedentes territoriales y agronómicos regionales.** Un estudio sobre estimación de estrés hídrico mediante el índice TVDI en la región pampeana (cultivos extensivos, no hortícolas); un ensayo fisiológico sobre estrés salino y estrés hídrico combinado en cultivares de tomate; y un resumen de congreso sobre restricción hídrica programada según evapotranspiración del cultivo en tomate. Ninguno de estos tres antecedentes emplea técnicas de inteligencia artificial; constituyen contexto agronómico regional, no antecedentes de IA.

**Fuentes instrumentales de datos.** El sensor de humedad de suelo multiprofundidad desarrollado por INTA (B01) constituye evidencia de instrumentación de bajo costo disponible en el país, compatible con la variable obligatoria de humedad de suelo. INTA RIAN, por su parte, se relevó como fuente de datos para HU2 (`docs/research/hu2-fuentes-datos-acceso.md`), no como antecedente bibliográfico. Ninguna de estas dos fuentes constituye, por sí misma, un antecedente de inteligencia artificial: ambas corresponden a instrumentación y a acceso a datos, no a una técnica de modelado, detección o generación evaluada.

**Antecedentes de inteligencia artificial.** El relevamiento regional disponible no aportó antecedentes de inteligencia artificial aplicada a los cuatro ejes de esta tesis; los antecedentes de IA provienen de la selección representativa internacional (`docs/research/hu1-matriz-comparativa-final.md`).

## 7. Limitaciones de la revisión

- Web of Science no pudo ejecutarse por falta de acceso institucional a Document Search/Core Collection; la cuenta disponible solo permite búsqueda de perfiles de investigadores.
- AGRIS no pudo completarse bajo el protocolo previsto: su interfaz de búsqueda no es automatizable con las herramientas disponibles en este entorno.
- El corpus es producto de una revisión dirigida y verificada, no de una revisión sistemática exhaustiva bajo un protocolo tipo PRISMA.
- Existe heterogeneidad de dominio entre los ejes 2, 3 y 4: una parte sustancial de sus antecedentes proviene de dominios distintos del agrícola (sensores ambientales genéricos, robótica industrial, detección de objetos), con transferibilidad metodológica justificada caso por caso, no antecedentes agrícolas directos.
- Persisten 14 registros del corpus clasificados como indeterminados, por metadatos bibliográficos insuficientes o no verificables (`docs/research/hu1-cola-revision-humana.csv`); no se incluyeron como evidencia central.
- El corpus consolidado ya fue validado científicamente (deduplicación, cribado semántico por título y abstract, verificación de la selección representativa); no se encuentra pendiente de validación.

## 8. Conclusión

La revisión bibliográfica realizada permite caracterizar el estado actual del conocimiento sobre los cuatro componentes técnicos de esta tesis y fundamenta la pertinencia del problema de investigación planteado en el plan de tesis: no se identificó, en el corpus revisado, una integración controlada y evaluada de los cuatro componentes aplicada a la detección temprana de estrés hídrico en horticultura bajo escenarios explícitos de escasez, ruido y variabilidad temporal de los datos. Esta vacancia fundamenta las decisiones de diseño de la arquitectura (`docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md`) y la selección de familias metodológicas descrita en la sección 5.

Esta revisión no demuestra la hipótesis de investigación. La contrastación de la hipótesis corresponde a los ensayos experimentales y al análisis de resultados de HU7 y HU8, y al capítulo de ensayos y resultados de la memoria técnica.
