
# HU1 — Subconjunto prerequisito de HU2: variables y antecedentes

Este documento cubre únicamente las 3 tareas de HU1 (Estado del arte y comprensión del dominio) identificadas en `openspec/project.md` como prerequisito duro del primer *change* de HU2 (`data-ingestion`). El resto de HU1 (antecedentes sobre detección de anomalías, datos sintéticos y retroalimentación humana) se documentará por separado y no bloquea el arranque de HU2.

Estado general: **borrador preliminar**.

> **Nota de alcance metodológico.** Las tres secciones siguientes se completaron con una búsqueda dirigida acotada (Google/motores generales), **no** con el protocolo sistemático completo que HU1 define en otras tareas (cadenas de búsqueda en Scopus, Web of Science e IEEE Xplore, criterios de inclusión/exclusión, período de análisis). Este borrador alcanza para desbloquear el diseño del esquema de datos de HU2, pero antes de redactar el estado del arte final (entregable completo de HU1) debe validarse y ampliarse ejecutando el protocolo sistemático definido en el plan de tesis. Cada fila indica el título exacto y el enlace para que la referencia sea verificable.

## 1. Variables predictoras de estrés hídrico

Tarea de origen: "Analizar trabajos sobre modelado predictivo de estrés hídrico".

Objetivo: identificar qué variables agronómicas, climáticas y temporales utiliza la literatura para predecir o caracterizar estrés hídrico en cultivos hortícolas, para fijar el esquema de datos de HU2.

Estado: borrador preliminar (a validar con el protocolo sistemático de HU1).

| Variable | Tipo (agronómica / climática / temporal) | Justificación y referencia | Prioridad (obligatoria / opcional) |
|----------|-------------------------------------------|------------------------------|--------------------------------------|
| Humedad de suelo (SMC) | Agronómica | Variable predictora central: a menor SMC, mayor severidad de estrés hídrico. Ver ["Recent Methods for Evaluating Crop Water Stress Using AI Techniques: A Review"](https://www.mdpi.com/1424-8220/24/19/6313) (Sensors, 2024) | Obligatoria |
| Temperatura de canopia / foliar (termal) | Agronómica | Usada junto a imágenes multiespectrales/térmicas para detección de estrés hídrico mediante UAV. Ver ["Crop water stress detection based on UAV remote sensing systems"](https://www.sciencedirect.com/science/article/pii/S0378377424003949) (ScienceDirect, 2024) | Opcional (depende de disponibilidad de sensores/UAV) |
| Índices de vegetación (NDVI y derivados) | Agronómica | Parámetro fisiológico no destructivo correlacionado con estrés hídrico, mencionado como alternativa a mediciones destructivas de potencial hídrico. Ver ["Recent Methods for Evaluating Crop Water Stress Using AI Techniques: A Review"](https://www.mdpi.com/1424-8220/24/19/6313) (Sensors, 2024) | Opcional |
| Conductancia estomática / potencial hídrico foliar | Agronómica | Parámetros fisiológicos de referencia, pero de medición destructiva/costosa — motivan el uso de proxies no destructivos (SMC, térmico, NDVI). Ver ["Recent Methods for Evaluating Crop Water Stress Using AI Techniques: A Review"](https://www.mdpi.com/1424-8220/24/19/6313) (Sensors, 2024) | Opcional (referencia/validación, no para ingesta rutinaria) |
| Temperatura ambiente | Climática | Variable meteorológica estándar en modelos de estrés hídrico y balance hídrico del cultivo. Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria |
| Humedad relativa | Climática | Variable meteorológica estándar, insumo directo de evapotranspiración de referencia (ET0). Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria |
| Precipitación | Climática | Determina aportes de agua al suelo; variable estándar en balance hídrico. Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria |
| Radiación solar | Climática | Insumo de ET0 (Penman-Monteith) y de estimación de demanda hídrica. Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria |
| Velocidad del viento | Climática | Insumo de ET0 (Penman-Monteith). Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria |
| Evapotranspiración de referencia (ET0) | Climática (derivada) | Síntesis de las variables meteorológicas anteriores; usada como variable derivada en modelos de manejo hídrico agrícola. Ver ["Advances in machine learning for agricultural water management"](https://iwaponline.com/jh/article/27/3/474/107443/Advances-in-machine-learning-for-agricultural) (J. Hydroinformatics) | Obligatoria (puede calcularse en preprocesamiento en lugar de ingerirse directamente) |
| Marca temporal / frecuencia de muestreo | Temporal | Necesaria para ingeniería de variables (ventanas, retardos) en HU4 y para detectar gaps/anomalías temporales en HU3. Requisito transversal, no de una referencia puntual | Obligatoria |

## 2. Matriz comparativa de antecedentes

Tarea de origen: "Elaborar la matriz comparativa de antecedentes".

Objetivo: comparar trabajos previos en cuanto a técnica de IA utilizada, fuente de datos y resultados, para identificar qué fuentes de datos son viables para el conjunto experimental de HU2.

Estado: borrador preliminar (a validar con el protocolo sistemático de HU1).

| Trabajo | Año | Técnica de IA usada | Fuente de datos | Resultado principal | Limitación |
|---------|-----|----------------------|------------------|----------------------|------------|
| ["Recent Methods for Evaluating Crop Water Stress Using AI Techniques: A Review"](https://www.mdpi.com/1424-8220/24/19/6313) | 2024 | Revisión de ML/DL (RF, ANN, SVM, CNN) aplicados a estrés hídrico | Sensores de suelo, UAV, satélite, mediciones fisiológicas | Consolida qué variables y técnicas predominan para evaluar estrés hídrico no destructivamente | Es una revisión, no aporta un modelo único evaluado; los métodos comparados varían mucho en madurez y escala |
| ["Crop water stress detection based on UAV remote sensing systems"](https://www.sciencedirect.com/science/article/pii/S0378377424003949) | 2024 | ML sobre imágenes multiespectrales/térmicas de UAV | Vuelos de UAV propios | Detección de estrés hídrico sin contacto a escala de parcela | Depende de vuelos UAV programados y condiciones climáticas; no aplicable a monitoreo continuo de bajo costo |
| ["A Machine Learning-Based High-Resolution Soil Moisture Mapping"](https://www.nass.usda.gov/Research_and_Science/Cropland/docs/Zhengwei_2024_High-Resolution_Soil_Moisture_Mapping.pdf) | 2024 | Quantile Random Forest | Sensores in situ + parámetros satelitales de superficie/terreno/suelo | Mapeo de humedad de suelo de alta resolución combinando fuentes in situ y satelitales | Enfocado en mapeo regional, no en alertas tempranas por parcela ni en escenarios de escasez de datos históricos |
| ["Task-Conditioned Synthetic Data Generation for Improving Machine Learning Performance in Agricultural Prediction Tasks"](https://arxiv.org/html/2607.09751v1) | 2026 | Generación de datos sintéticos condicionada por tarea | Datasets agrícolas de predicción (no específico de estrés hídrico) | Mejora el desempeño de modelos de predicción agrícola complementando datos reales escasos | No se centra en cultivos hortícolas ni en estrés hídrico específicamente; hay que evaluar transferibilidad |
| ["A comprehensive review of synthetic data generation in smart farming by using VAE and GAN"](https://www.sciencedirect.com/science/article/abs/pii/S0952197624000393) | 2024 | Revisión de VAE y GAN en agricultura de precisión | Diversas (según los trabajos revisados) | Consolida enfoques de generación de datos sintéticos aplicables a escenarios de escasez de datos | Revisión general de "smart farming", no específica de series temporales de humedad de suelo/estrés hídrico |
| ["DeepQC: A deep learning system for automatic quality control of in-situ soil moisture sensor time series data"](https://www.sciencedirect.com/science/article/pii/S2772375524001199) | 2024 | Deep learning (control de calidad automático) | Series temporales de sensores de humedad de suelo in situ | Detecta gaps y anomalías en datos de sensores de campo de forma automática | Orientado a control de calidad, no a generación de alertas de estrés hídrico en sí |
| ["Self-Supervised Anomaly Detection of Rogue Soil Moisture Sensors"](https://arxiv.org/pdf/2305.05495) | 2023 | Detección de anomalías autosupervisada | Redes de sensores de humedad de suelo en campo | Identifica sensores defectuosos/anómalos sin requerir etiquetas de anomalías previas | Relevante para HU3 (no depende de datos etiquetados), pero no aborda predicción ni alertas |
| ["SPADE: A Large Language Model Framework for Soil Moisture Pattern Recognition and Anomaly Detection"](https://arxiv.org/abs/2509.18123) | 2025 | LLM aplicado a reconocimiento de patrones y anomalías | Series temporales de humedad de suelo | Detecta simultáneamente patrones de riego y anomalías usando LLM | Enfoque emergente (LLM), aún sin evidencia extensa de robustez frente a escasez extrema de datos |

## 3. Vacancias y criterios de diseño

Tarea de origen: "Identificar vacancias y criterios para el diseño de la arquitectura".

Objetivo: registrar los huecos identificados en la literatura y los criterios concretos que debe cumplir el esquema de datos de HU2 (ej. granularidad temporal mínima, variables obligatorias vs. opcionales, cobertura geográfica/temporal esperada).

Estado: borrador preliminar (a validar con el protocolo sistemático de HU1).

- **Vacancia:** los trabajos relevados abordan por separado generación de datos sintéticos, detección de anomalías o modelado predictivo, pero no se encontró (en esta búsqueda acotada) una arquitectura integrada que combine los tres componentes junto con retroalimentación humana para recalibración, específicamente para estrés hídrico en cultivos hortícolas de pequeña/mediana escala — que es precisamente el aporte que persigue este trabajo de tesis.
  - **Implicancia para el esquema de datos de HU2:** el esquema debe soportar el flujo completo (datos crudos → detección de anomalías → datos sintéticos → modelado → alertas → retroalimentación), no solo un componente aislado; los identificadores de registro deben permitir trazar un dato desde su ingesta hasta la alerta y la retroalimentación asociada (ver HU5/HU6).
- **Vacancia:** la mayoría de los trabajos de detección de anomalías en sensores de suelo (DeepQC, self-supervised rogue sensors) asumen que no hay etiquetas de anomalías disponibles de antemano.
  - **Implicancia:** el esquema de datos de HU2 debe permitir marcar registros como "sin etiqueta de calidad conocida" en lugar de asumir un campo de calidad ya validado, para no imponer una precondición que HU3 (detección no supervisada) no puede garantizar.
- **Vacancia:** los trabajos de generación de datos sintéticos revisados no son específicos de estrés hídrico en horticultura ni de series temporales cortas y con escasez extrema (few-shot), que es el escenario real de esta tesis.
  - **Implicancia:** el esquema debe registrar explícitamente el origen de cada fila (`real` vs. `sintético`) desde la ingesta (HU2), no como un agregado posterior, para sostener la separación exigida por el criterio ético del plan (sección 12.2) y facilitar la comparación de configuraciones experimentales (Épica 4).
- **Criterio de granularidad temporal:** las variables climáticas obligatorias (temperatura, humedad relativa, precipitación, radiación, viento) y sus derivadas (ET0) requieren, como mínimo, granularidad diaria para ser comparables con las fuentes públicas identificadas (SMN, NASA POWER, Copernicus); si los sensores de campo reportan a mayor frecuencia, el esquema debe permitir agregación a esa granularidad sin perder la serie original.
  - **Implicancia:** el contrato de acceso a datos (ADR-0002) debe exponer tanto la resolución nativa como una vista agregada diaria, en lugar de forzar una única granularidad fija.
- **Criterio de cobertura de variables obligatorias:** un registro de ingesta solo se considera válido para modelado (HU4) si contiene, como mínimo, humedad de suelo y las variables climáticas obligatorias de la tabla 1; el resto (térmico, NDVI, fisiológicas) son enriquecimiento opcional.
  - **Implicancia:** el esquema de HU2 debe distinguir explícitamente entre columnas obligatorias y opcionales, y el componente de calidad (HU3) debe poder reportar cobertura por columna obligatoria.

## Uso de este documento

Este borrador ya es suficiente para redactar el `proposal.md` del primer *change* de OpenSpec para HU2 (`data-ingestion`), que debe referenciarlo como justificación del esquema de datos propuesto. Antes de cerrar el entregable final de HU1 (estado del arte completo), este borrador debe validarse y ampliarse ejecutando el protocolo sistemático de búsqueda (Scopus, Web of Science, IEEE Xplore) definido en las tareas restantes de HU1, dado que las referencias aquí provienen de una búsqueda acotada y no de ese protocolo.
