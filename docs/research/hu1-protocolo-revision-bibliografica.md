# HU1 — Protocolo de revisión bibliográfica

Este documento define originalmente 3 tareas de HU1 (Estado del arte y comprensión del dominio), ya completas según `docs/seguimiento-tareas.md`:

- Definir el protocolo de revisión bibliográfica.
- Definir términos, sinónimos y cadenas de búsqueda (ES/EN).
- Definir criterios de inclusión, exclusión y período de análisis.

**Estado de ejecución (actualizado 2026-09-06):** las búsquedas en Scopus e IEEE Xplore ya se ejecutaron para los 4 ejes y están registradas en `docs/research/hu1-registro-busquedas.csv`, con exports reales en `docs/research/exports/scopus/` y `docs/research/exports/ieee/`, consolidados en `docs/research/hu1-corpus-final.csv`. Web of Science no pudo ejecutarse (acceso institucional sin Document Search/Core Collection, ver nota más abajo). Se incorporaron además fuentes abiertas complementarias (Crossref, OpenAlex, DOAJ). Este trabajo se caracteriza como una **revisión bibliográfica estructurada y dirigida, con criterios explícitos de búsqueda, inclusión, exclusión, trazabilidad y verificación** — no como una revisión sistemática exhaustiva: quedan pendientes Web of Science y AGRIS/SciELO/Horticultura Argentina de forma automatizada. La cola de revisión humana (`docs/research/hu1-cola-revision-humana.csv`) ya se resolvió (29 incluir, 30 excluir, 12 indeterminado); ver `docs/research/hu1-matriz-comparativa-final.md` y `docs/research/hu1-estado-del-arte.md` para los entregables consolidados definitivos.

## 1. Objetivo y alcance

Sistematizar la búsqueda de antecedentes para los 4 ejes de HU1 identificados en el plan de tesis. Los ejes 2 y 3 (detección de anomalías; generación de datos sintéticos) corresponden a dos técnicas de IA metodológicamente distintas — con literatura, términos y objetivos de búsqueda propios — y se tratan como ejes independientes para que cada uno quede trazable por separado, aunque el plan de tesis los agrupe en una misma tarea de análisis (`docs/seguimiento-tareas.md`):

1. **Modelado predictivo de estrés hídrico** — ya tiene un borrador preliminar no sistemático en `docs/research/hu1-variables-y-antecedentes.md` (secciones 1 y 2), que debe validarse/ampliarse con este protocolo.
2. **Detección de anomalías** — mismo borrador preliminar (parte de la sección 2 de ese documento), a validar/ampliar.
3. **Generación de datos sintéticos** — mismo borrador preliminar (parte de la sección 2 de ese documento), a validar/ampliar.
4. **Retroalimentación humana y recalibración** — ya cuenta con una primera matriz de antecedentes (búsqueda dirigida acotada, no sistemática) en `docs/research/hu1-retroalimentacion-humana.md`, con el mismo alcance preliminar que los otros ejes; debe validarse/ampliarse aplicando este protocolo de forma sistemática.

El resultado de aplicar este protocolo a los 4 ejes es el insumo para "Redactar el estado del arte y el marco conceptual" (tarea aún pendiente de HU1).

## 2. Términos y sinónimos (ES/EN)

| Eje | Términos ES | Términos EN |
|---|---|---|
| Estrés hídrico / cultivo | estrés hídrico, déficit hídrico, riego, humedad de suelo, cultivo hortícola, agricultura de precisión | water stress, drought stress, crop water stress, irrigation, soil moisture, horticultural crop, precision agriculture |
| Modelado predictivo | predicción, modelo predictivo, aprendizaje automático, aprendizaje profundo, series temporales | prediction, predictive model, machine learning, deep learning, time series forecasting |
| Detección de anomalías | detección de anomalías, datos atípicos, control de calidad de datos, sensor defectuoso | anomaly detection, outlier detection, data quality control, faulty sensor, rogue sensor |
| Datos sintéticos | datos sintéticos, generación de datos, aumento de datos, escasez de datos | synthetic data, data generation, data augmentation, data scarcity, few-shot |
| Retroalimentación humana | retroalimentación humana, humano en el circuito, recalibración, aprendizaje activo, supervisión humana | human feedback, human-in-the-loop, model recalibration, active learning, human oversight |

Estos términos se combinan entre columnas (un término de "Estrés hídrico / cultivo" AND un término del eje correspondiente) para armar las cadenas de búsqueda.

## 3. Cadenas de búsqueda por base

Sintaxis booleana estándar (`AND`/`OR`), con comillas para frases exactas. Estructura general: `(términos de cultivo/estrés hídrico) AND (términos del eje)`.

### Scopus / Web of Science (sintaxis con campos de título-resumen-palabras clave)

- **Eje 1 — Modelado predictivo:**
  `TITLE-ABS-KEY(("water stress" OR "drought stress" OR "soil moisture") AND ("machine learning" OR "deep learning" OR "predictive model" OR "time series forecasting") AND ("crop" OR "horticultur*" OR "irrigation"))`
- **Eje 2 — Detección de anomalías:**
  `TITLE-ABS-KEY(("soil moisture" OR "crop" OR "agricultur*") AND ("anomaly detection" OR "outlier detection" OR "faulty sensor" OR "rogue sensor") AND ("sensor" OR "time series"))`
- **Eje 3 — Datos sintéticos:**
  `TITLE-ABS-KEY(("soil moisture" OR "crop" OR "agricultur*") AND ("synthetic data" OR "data augmentation" OR "data generation") AND ("sensor" OR "time series" OR "data scarcity"))`
- **Eje 4 — Retroalimentación humana:**
  `TITLE-ABS-KEY(("human feedback" OR "human-in-the-loop" OR "active learning" OR "model recalibration") AND ("machine learning" OR "predictive model") AND ("agricultur*" OR "environmental monitoring" OR "sensor"))`

> **Bloqueo de acceso institucional — Web of Science (2026-09-05):** se intentó ejecutar estas cadenas en Web of Science Core Collection y no fue posible: la cuenta institucional disponible permite búsqueda de perfiles de investigadores, pero no Document Search/Core Collection (que es el módulo que ejecuta estas cadenas). A diferencia del bloqueo de AGRIS (limitación de herramienta), esto es una limitación de nivel de suscripción/acceso institucional. Estado: no ejecutada.

### IEEE Xplore (sintaxis de "Command Search")

Misma lógica, adaptada al operador de campo de IEEE Xplore (`"Full Text & Metadata"`):
- **Eje 1:** `("Full Text & Metadata":"water stress" OR "Full Text & Metadata":"soil moisture") AND ("Full Text & Metadata":"machine learning" OR "Full Text & Metadata":"deep learning") AND ("Full Text & Metadata":"crop" OR "Full Text & Metadata":"irrigation")`
- **Eje 2:** `("Full Text & Metadata":"soil moisture" OR "Full Text & Metadata":"agriculture") AND ("Full Text & Metadata":"anomaly detection" OR "Full Text & Metadata":"faulty sensor")`
- **Eje 3:** `("Full Text & Metadata":"soil moisture" OR "Full Text & Metadata":"agriculture") AND ("Full Text & Metadata":"synthetic data" OR "Full Text & Metadata":"data augmentation")`
- **Eje 4:** `("Full Text & Metadata":"human-in-the-loop" OR "Full Text & Metadata":"human feedback" OR "Full Text & Metadata":"active learning") AND ("Full Text & Metadata":"machine learning")`

### AGRIS, SciELO, Horticultura Argentina

Estas bases tienen buscadores más simples (sin operadores de campo compuestos ni siempre con `AND`/`OR` explícito). Se usan búsquedas de frase simplificadas, ejecutadas una por una y combinando resultados manualmente:

- Eje 1: `estrés hídrico cultivo hortícola predicción` / `crop water stress machine learning`
- Eje 2: `detección de anomalías sensores agrícolas` / `anomaly detection agricultural sensors`
- Eje 3: `datos sintéticos agricultura` / `synthetic data agriculture`
- Eje 4: `retroalimentación humana modelo agrícola` / `human-in-the-loop agriculture`

> **Bloqueo de automatización (2026-08-16):** se intentó ejecutar estas cadenas de forma automatizada en AGRIS (`agris.fao.org`) y no fue posible: la interfaz de búsqueda es una SPA que renderiza resultados por JavaScript (`curl` devuelve la página vacía, HTTP 200 sin resultados), un fetch automatizado recibe HTTP 403, y no se pudo verificar con navegador real (extensión Claude in Chrome no disponible en el intento). A diferencia de SMN (bloqueo técnico del lado del servidor), esto es una limitación de herramienta: la ejecución de estas cadenas en AGRIS requiere navegación manual en un navegador, no scripting. SciELO y Horticultura Argentina sí se ejecutaron sin este problema (ver `docs/research/hu1-antecedentes-argentina.md`).

## 4. Criterios de inclusión y exclusión

**Inclusión:**
- Publicado en revista revisada por pares, congreso indexado, o reporte técnico de un organismo reconocido (INTA, FAO, SMN, NASA, Copernicus).
- Idioma español o inglés.
- Aborda al menos uno de los 4 ejes aplicado a: agricultura/horticultura, monitoreo ambiental con sensores, o series temporales con escasez de datos (si el eje es detección de anomalías, datos sintéticos o retroalimentación humana y el dominio no es agrícola pero la técnica es directamente transferible, se incluye marcado como "dominio distinto").
- Texto completo accesible (open access o vía acceso institucional disponible).

**Exclusión:**
- Duplicados entre bases (se eliminan tras consolidar, quedándose con la versión de mayor detalle bibliográfico).
- Resúmenes de congreso sin texto completo disponible.
- Trabajos que solo mencionan el tema tangencialmente en el título/resumen sin desarrollarlo (se filtra en la etapa de "evaluar títulos y resúmenes", tarea siguiente a este protocolo).
- Divulgación no académica (blogs, notas de prensa) — excepto documentación técnica oficial de INTA/FAO/SMN, que se admite como fuente secundaria de contexto, no como antecedente científico.

## 5. Período de análisis

**2019–2026** (últimos ~7 años), por el ritmo de avance de las técnicas de ML/DL aplicadas a agricultura de precisión y detección de anomalías, donde trabajos de más de 7 años suelen estar desactualizados en cuanto a arquitecturas y disponibilidad de datos.

Excepción: se admiten trabajos seminales anteriores a 2019 si son citados recurrentemente como base metodológica por los trabajos del período (ej. formulación original de Penman-Monteith para ET0, o papers fundacionales de una técnica de detección de anomalías todavía vigente), marcándolos explícitamente como "referencia seminal fuera de período".

## 6. Procedimiento de registro

Cada búsqueda ejecutada se registra en una tabla con estas columnas, una fila por resultado antes de la etapa de cribado:

| Base | Cadena de búsqueda usada | Fecha de ejecución | Título | Año | Autores | Eje | Duplicado de (si aplica) | Decisión (incluir/excluir) | Motivo de exclusión (si aplica) |
|---|---|---|---|---|---|---|---|---|---|

La deduplicación se hace por título normalizado (minúsculas, sin puntuación) + año; ante coincidencia, se conserva la entrada con más metadatos (DOI, texto completo accesible).

Esta tabla conceptual se implementa en dos artefactos de trabajo separados:

- `docs/research/hu1-registro-busquedas.csv` (columnas: `base,cadena,fecha_ejecucion,eje,cantidad_resultados,observaciones`): una fila por cada ejecución de una cadena de búsqueda en una base, antes de revisar resultados individuales.
- `docs/research/hu1-corpus-final.csv` (columnas: `id,titulo,autores,anio,doi,url,base,eje,tipo_publicacion,incluido,motivo_exclusion,duplicado_de,referencia_seminal`): una fila por referencia individual evaluada, tras el cribado de títulos/resúmenes.

En ambos archivos, `eje` admite un único valor (`1`, `2`, `3` o `4`, según la numeración de la sección 1) o varios separados por `;` (p. ej. `2;3`) cuando el trabajo aborda más de un eje. `referencia_seminal` en `hu1-corpus-final.csv` se completa solo para trabajos admitidos por la excepción de la sección 5 (referencia seminal fuera de período).

**Estado real (actualizado 2026-09-06):** ambos archivos ya contienen datos reales, no solo encabezados. `hu1-registro-busquedas.csv` tiene 27 filas: 4 ejecuciones de Scopus, 4 de IEEE Xplore, 1 fila de Web of Science (no ejecutada), 12 filas de Crossref/OpenAlex/DOAJ (ejecutadas como descubrimiento complementario), 5 filas de fuentes no ejecutadas o bloqueadas (Semantic Scholar, CORE, AGRIS, SciELO, Horticultura Argentina) y 1 fila de referencia a FAO/INTA como fuente de verificación. `hu1-corpus-final.csv` tiene 450 registros consolidados y deduplicados: 180 incluidos, 256 excluidos y 14 indeterminados (metadatos insuficientes o no verificables), tras cribado semántico y resolución completa de la cola de revisión humana (`docs/research/hu1-cola-revision-humana.csv`). Selección representativa validada: 25 referencias (`docs/research/hu1-referencias-representativas-validadas.csv`), sintetizadas en `docs/research/hu1-matriz-comparativa-final.md`.

Distinción de estado por fuente:

a) **Protocolo planificado** (esta sección y la 3): cadenas y criterios definidos para las 5 bases originales (Scopus, WoS, IEEE Xplore, AGRIS, SciELO/Horticultura Argentina).
b) **Búsquedas efectivamente ejecutadas**: Scopus (4 ejes), IEEE Xplore (4 ejes) — exports reales en `docs/research/exports/`; la cadena literalmente tipeada en cada interfaz no quedó preservada como log/captura, por lo que `hu1-registro-busquedas.csv` la documenta como "cadena exacta ejecutada no preservada", sin asumir identidad con la cadena de referencia de esta sección.
c) **Fuentes no ejecutadas o bloqueadas**: Web of Science (Document Search/Core Collection sin acceso institucional), AGRIS (bloqueo de herramienta, SPA/JS), SciELO y Horticultura Argentina (sin API de búsqueda libre automatizable), Semantic Scholar y CORE (requieren API key no disponible en este entorno).
d) **Fuentes complementarias utilizadas**: Crossref, OpenAlex y DOAJ, consultadas vía API pública como descubrimiento adicional (no sustituyen la ejecución sistemática en Scopus/WoS/IEEE Xplore para las bases donde falta).

Los ejes 1, 2 y 3 contaban además con un borrador preliminar de búsqueda dirigida previo a esta ejecución (en `docs/research/hu1-variables-y-antecedentes.md`) y el eje 4 en `docs/research/hu1-retroalimentacion-humana.md`; ese borrador quedó incorporado/superado por la consolidación real descrita arriba, no reemplaza por sí solo la verificación científica final pendiente (cola de revisión humana, matriz comparativa, revalidación de vacancias).
