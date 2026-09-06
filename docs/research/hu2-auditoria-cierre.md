# HU2 — Auditoría de cierre

Este documento mapea los criterios de aceptación de la Épica 1 · HU2 (issue #11) y el estado de los issues hijos (#34 a #43) contra la evidencia documental y técnica disponible. Los issues #35, #36, #37 y #11 fueron cerrados en GitHub con el comentario de trazabilidad correspondiente, referenciando este documento y el PR #174; el detalle queda registrado a continuación.

## 1. Alcance

HU2 corresponde a la preparación e ingestión del conjunto experimental de datos: identificación de fuentes, definición del esquema, descarga, homogeneización, consolidación multi-fuente, análisis de cobertura y documentación de procedencia/licencias. No corresponde a HU2 la limpieza, imputación, detección de anomalías ni generación de datos sintéticos, que son responsabilidad de HU3 (`data-quality`). En particular, la existencia de gaps de humedad de suelo en el dataset consolidado es un hallazgo que HU2 debe medir y documentar, no resolver; su tratamiento (imputación) corresponde a HU3 y ya está implementado allí.

## 2. Criterios de aceptación

### CA1 — Fuentes seleccionadas identificadas y documentadas

**Estado: CUMPLE**

**Evidencia:** NASA POWER (variables climáticas) y ESA CCI Soil Moisture (humedad de suelo) fueron identificadas, evaluadas y documentadas en `docs/research/hu2-fuentes-datos-acceso.md`, con criterios explícitos de selección/descarte (sección "Criterios de selección y descarte de fuentes de datos"), procedencia, licencia y diccionarios de datos versionados (`data/dictionaries/`).

SMN y Copernicus fueron relevados y documentados en el mismo checklist, pero su incorporación no era obligatoria para satisfacer este criterio: CA1 exige identificar y documentar las fuentes seleccionadas, no incorporar todas las fuentes candidatas relevadas.

### CA2 — Proceso de preparación definido y documentado

**Estado: CUMPLE**

**Evidencia:** `openspec/specs/data-ingestion/spec.md` define 8 requirements formales (contrato de acceso a datos, esquema obligatorio/opcional, flag de procedencia, resolución temporal nativa + vista diaria, reporte de cobertura, diccionario de datos versionado, consolidación multi-fuente, huella de dataset/fingerprint), cada uno con implementación real en `src/data_ingestion/` y test asociado (`tests/test_storage.py`, `test_schema.py`, `test_aggregation.py`, `test_coverage.py`, `test_dictionary.py`, `test_consolidate.py`).

### CA3 — Conjunto experimental apto para desarrollo y evaluación

**Estado: CUMPLE**

**Evidencia principal:** `data/melchor_romero_2024_consolidado.parquet`.

- Ubicación: Melchor Romero, Partido de La Plata (-34.95, -58.05), Cinturón Hortícola Platense.
- Período: año calendario 2024 completo (366 registros diarios).
- Fuentes: NASA POWER para variables climáticas (temperatura, humedad relativa, precipitación, radiación solar, viento); ESA CCI Soil Moisture para humedad de suelo.
- Cobertura: 100% en las variables climáticas obligatorias; 75.96% en humedad de suelo (gap real del producto satelital, cuantificado en `data/melchor_romero_2024_consolidado_coverage.csv`); 0% en ET0 (ver sección 4).
- Procedencia: `origen: real` en ambas fuentes, fijado desde la ingesta.
- Utilización posterior efectiva: el dataset fue consumido real y extensamente por HU3 (calidad, anomalías, datos sintéticos), HU4 (modelado predictivo), HU5 (retroalimentación humana), HU6 (integración de arquitectura) y HU7/HU8 (experimentación, incluido el protocolo experimental formal vigente de HU7/HU8, con la re-ejecución posterior a la corrección de fuga temporal).

**Aclaración explícita:** "apto para desarrollo y evaluación del prototipo experimental" no equivale a "suficiente para generalización científica externa". Esta segunda afirmación no es un requisito de HU2 y la limitación de un único sitio/año ya está documentada como amenaza a la validez externa en HU8, no como un incumplimiento de HU2.

### CA4 — Procedimiento reproducible

**Estado: CUMPLE**

**Evidencia:** scripts parametrizados por ubicación/período (`scripts/ingest_nasa_power.py`, `scripts/ingest_esa_cci_soil_moisture.py`, `scripts/consolidate_datasets.py`), conectores (`src/data_ingestion/sources/`), normalización al esquema (`schema.py`), persistencia (`storage.py`), consolidación (`consolidate.py`), cobertura (`coverage.py`) y diccionarios (`dictionary.py`), todos con tests asociados. Datasets y diccionarios quedan versionados en git. El procedimiento es reproducible mediante los scripts versionados sin requerir credenciales ni cuentas para las dos fuentes seleccionadas (NASA POWER, ESA CCI), sujeto a la disponibilidad de los servicios y productos públicos externos correspondientes.

## 3. Fuentes seleccionadas

**Fuentes seleccionadas para el conjunto experimental real:**

- NASA POWER
- ESA CCI Soil Moisture

**Fuentes candidatas relevadas pero no incorporadas** (no descriptas como trabajo pendiente obligatorio):

- SMN: bloqueo técnico documentado (dataset de `datos.gob.ar` removido, `smn.gob.ar` con protección anti-bot).
- Copernicus CDS: requiere registro/cuenta personal gratuita no gestionada (registro, token personal y aceptación de licencia del dataset); estado "pendiente", no descarte definitivo.
- NASA SMAP, ISMN, INTA RIAN, MAGyP y otras fuentes del checklist: relevadas, sin necesidad de incorporación adicional dado que ESA CCI ya cubre humedad de suelo con completitud suficiente y NASA POWER ya cubre las variables climáticas obligatorias.

## 4. Estado de ET0

- ET0 (evapotranspiración de referencia) es una columna obligatoria del esquema (`src/data_ingestion/schema.py`).
- El dataset histórico Melchor Romero 2024 **no tiene ET0 poblada** (0% de cobertura, confirmado en `data/melchor_romero_2024_consolidado_coverage.csv`).
- PR #162 incorporó un cálculo de referencia de ET0 (FAO-56 Penman-Monteith simplificado, `src/data_quality/reference_et.py::estimate_et0`) exclusivamente para el flujo de sensor mock/en vivo (`src/data_ingestion/mock_sensor.py`, capacidad `alerting-ui`), un dataset distinto y no relacionado con el conjunto experimental histórico.
- Ese mecanismo **no modificó retrospectivamente** el dataset histórico de HU7/HU8.
- `openspec/specs/predictive-modeling/spec.md` confirma que HU7/HU8 no utilizan ET0 como predictor.
- Esta situación es una **limitación documentada, no un bloqueo para el cierre de HU2**: ET0 es una variable agronómicamente relevante y una columna derivada del esquema, sin ser un predictor obligatorio de HU7/HU8.

No se afirma que ET0 histórica "se derive en preprocesamiento": ningún paso de preprocesamiento real deriva ET0 para el conjunto experimental histórico.

## 5. Limitaciones

Se preservan explícitamente, aunque HU2 se cierre:

- Un único sitio geográfico (Melchor Romero).
- Un único año (2024).
- Humedad de suelo con 75.96% de cobertura (el tratamiento de este faltante corresponde a HU3, no a HU2).
- SMN no incorporado por bloqueo técnico documentado.
- Copernicus no incorporado por requerimiento de registro/cuenta personal gratuita no gestionada.
- ET0 histórica no poblada, no utilizada como predictor de HU7/HU8.
- Generalización científica externa no demostrada (fuera de alcance de HU2).

## 6. Auditoría de issues hijos

| Issue | Estado final |
|---|---|
| #34 — Definir variables agronómicas, climáticas y temporales requeridas | CLOSED / completed |
| #35 — Identificar conjuntos de datos asociados a publicaciones científicas | CLOSED / not_planned |
| #36 — Relevar datos disponibles en SMN, NASA POWER y Copernicus | CLOSED / completed, con limitación documentada |
| #37 — Evaluar metadatos, licencias, procedencia y restricciones de uso | CLOSED / completed |
| #38 — Descargar y organizar muestras representativas de las fuentes candidatas | CLOSED / completed |
| #39 — Homogeneizar formatos, unidades, frecuencias y zonas horarias | CLOSED / completed |
| #40 — Analizar cobertura temporal, granularidad e integridad de las fuentes | CLOSED / completed |
| #41 — Definir criterios de selección y descarte de fuentes de datos | CLOSED / completed |
| #42 — Implementar el procedimiento reproducible de ingestión y consolidación | CLOSED / completed |
| #43 — Documentar el diccionario de datos, procedencia y limitaciones | CLOSED / completed |
| #11 — Épica 1 · HU2: Preparación del conjunto experimental de datos | CLOSED / completed |

### #35 — Identificar conjuntos de datos asociados a publicaciones científicas

La identificación de datasets asociados a publicaciones científicas era una estrategia posible para obtener datos, pero no constituía un criterio de aceptación independiente de HU2. HU2 obtuvo un conjunto experimental real, reproducible y utilizado por las HUs posteriores mediante fuentes públicas alternativas (NASA POWER, ESA CCI). Por ello no se justificó ejecutar una nueva búsqueda únicamente para completar esta tarea, y el issue fue cerrado como `not_planned`.

### #36 — Relevar datos disponibles en SMN, NASA POWER y Copernicus

NASA POWER fue relevado e incorporado. SMN fue relevado y su bloqueo técnico documentado con fecha y motivo concreto. Copernicus fue relevado y quedó fuera por requerimiento de registro/cuenta personal gratuita no gestionada (cuenta, token personal y aceptación de licencia del dataset), no por descarte definitivo. "Relevar" no implica incorporar obligatoriamente las tres fuentes: las tres fueron investigadas con evidencia concreta y disposición clara, por lo que el issue fue cerrado como `completed` con esta limitación documentada.

### #37 — Evaluar metadatos, licencias, procedencia y restricciones de uso

Metadatos, licencias, procedencia, restricciones y limitaciones están documentados con el nivel necesario para las fuentes finalmente seleccionadas (NASA POWER, ESA CCI), mediante diccionarios de datos reales versionados. No se exige el mismo nivel de documentación para fuentes descartadas o bloqueadas (SMN, Copernicus), ya que el criterio de aceptación no lo requiere. El issue fue cerrado como `completed`.

## 7. Conclusión de auditoría

HU2 cumple sus cuatro criterios de aceptación (CA1-CA4: CUMPLE). El cierre de HU2 y de sus issues hijos no modificó hipótesis, propósito, alcance, arquitectura, HU3-HU8 ni resultados experimentales: solo formalizó documentalmente un estado que HU3-HU8 ya asumían como dado, dado que el conjunto experimental ya había sido consumido y experimentado extensamente por esas historias de usuario.

## 8. Estado administrativo final

HU2 quedó formalmente cerrada en GitHub luego del merge del PR #174 y del cierre trazable de los issues #35, #36 y #37. Los issues #34 y #38-#43 ya se encontraban cerrados previamente. Una vez verificado el cierre de todos los issues hijos, el issue principal #11 fue cerrado como `completed`. Los cuatro criterios de aceptación permanecen en estado CUMPLE.
