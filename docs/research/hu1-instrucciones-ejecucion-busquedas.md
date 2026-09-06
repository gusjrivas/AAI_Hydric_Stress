# HU1 — Instrucciones de ejecución de búsquedas (listas para copiar y pegar)

Este documento empaqueta, en formato listo para copiar y pegar, las cadenas de búsqueda ya definidas en `docs/research/hu1-protocolo-revision-bibliografica.md` (secciones 2 y 3), para los 4 ejes de HU1:

1. Modelado predictivo de estrés hídrico
2. Detección de anomalías
3. Generación de datos sintéticos
4. Retroalimentación humana y recalibración

**No se ejecutó ninguna búsqueda todavía.** Scopus, Web of Science e IEEE Xplore siguen bloqueadas por falta de acceso institucional; AGRIS sigue bloqueada por herramienta (ver nota en el protocolo, sección 3). Este documento no reemplaza el protocolo — solo lo empaqueta para ejecución mecánica el día que haya acceso.

## Cómo usar este documento

1. Copiar la cadena de la base y el eje correspondiente.
2. Pegarla en el buscador avanzado de la base (no en el buscador simple/básico).
3. Aplicar el filtro de período 2019–2026 que ofrezca la base (protocolo, sección 5), salvo para referencias seminales evaluadas caso a caso.
4. Registrar la ejecución en `docs/research/hu1-registro-busquedas.csv` (una fila por cadena ejecutada).
5. Exportar los resultados y registrar cada referencia individual en `docs/research/hu1-corpus-final.csv` tras el cribado de títulos/resúmenes.

## Campos a exportar de cada base

Al exportar resultados de una búsqueda, priorizar el formato que incluya, como mínimo:

- Título
- Autores
- Año
- DOI (si existe)
- URL / enlace persistente
- Resumen (abstract) — necesario para la etapa de cribado, no se carga en el CSV de corpus
- Tipo de publicación (artículo de revista, congreso, reporte técnico)

## Formato de exportación recomendado

- **Scopus / Web of Science:** exportar en formato CSV o BibTeX (ambas bases lo ofrecen desde la lista de resultados); preferir CSV si se va a volcar directo a `hu1-corpus-final.csv`.
- **IEEE Xplore:** exportar en formato CSV desde "Export Results" (incluye DOI y abstract).
- **AGRIS:** exportar en formato RIS o CSV si la interfaz lo permite tras navegación manual (ver bloqueo de automatización, protocolo sección 3); si no lo permite, transcribir manualmente los campos mínimos.
- **SciELO / Horticultura Argentina:** no siempre ofrecen exportación estructurada; transcribir manualmente los campos mínimos a `hu1-corpus-final.csv`.

## Cómo registrar fecha de ejecución

Formato ISO 8601 (`YYYY-MM-DD`), fecha real del día en que se ejecuta la cadena en la base — no la fecha de publicación del trabajo. Va en la columna `fecha_ejecucion` de `hu1-registro-busquedas.csv` y en la columna `fecha_ejecucion` de la tabla conceptual del protocolo (sección 6).

## Cómo registrar cantidad de resultados

Número entero devuelto por la base para esa cadena exacta, antes de cualquier cribado manual (columna `cantidad_resultados` de `hu1-registro-busquedas.csv`). Si la base pagina resultados, es el total reportado por la interfaz (p. ej. "1–20 de 137 resultados" → `137`), no la cantidad de la página visible.

## Cómo asociar cada búsqueda con su eje

Usar el número de eje según la numeración de la sección 1 del protocolo: `1` (modelado predictivo), `2` (detección de anomalías), `3` (datos sintéticos), `4` (retroalimentación humana). Va en la columna `eje` de ambos CSV. Un resultado que aborde más de un eje se marca con los números separados por `;` (p. ej. `2;3`), según la convención ya definida en el protocolo, sección 6.

---

## Eje 1 — Modelado predictivo de estrés hídrico

### Scopus

```
TITLE-ABS-KEY(("water stress" OR "drought stress" OR "soil moisture") AND ("machine learning" OR "deep learning" OR "predictive model" OR "time series forecasting") AND ("crop" OR "horticultur*" OR "irrigation"))
```

### Web of Science

Misma cadena booleana del protocolo, traducida al operador de campo de tópico de Web of Science (`TS=`, equivalente a título+resumen+palabras clave):

```
TS=(("water stress" OR "drought stress" OR "soil moisture") AND ("machine learning" OR "deep learning" OR "predictive model" OR "time series forecasting") AND ("crop" OR "horticultur*" OR "irrigation"))
```

### IEEE Xplore (Command Search)

```
("Full Text & Metadata":"water stress" OR "Full Text & Metadata":"soil moisture") AND ("Full Text & Metadata":"machine learning" OR "Full Text & Metadata":"deep learning") AND ("Full Text & Metadata":"crop" OR "Full Text & Metadata":"irrigation")
```

### AGRIS

```
estrés hídrico cultivo hortícola predicción
```
```
crop water stress machine learning
```
Bloqueada por herramienta (SPA con JS, ver protocolo sección 3) — requiere navegación manual en un navegador, no scripting automatizado.

### SciELO / Horticultura Argentina

```
estrés hídrico cultivo hortícola predicción
```
```
crop water stress machine learning
```

---

## Eje 2 — Detección de anomalías

### Scopus

```
TITLE-ABS-KEY(("soil moisture" OR "crop" OR "agricultur*") AND ("anomaly detection" OR "outlier detection" OR "faulty sensor" OR "rogue sensor") AND ("sensor" OR "time series"))
```

### Web of Science

```
TS=(("soil moisture" OR "crop" OR "agricultur*") AND ("anomaly detection" OR "outlier detection" OR "faulty sensor" OR "rogue sensor") AND ("sensor" OR "time series"))
```

### IEEE Xplore (Command Search)

```
("Full Text & Metadata":"soil moisture" OR "Full Text & Metadata":"agriculture") AND ("Full Text & Metadata":"anomaly detection" OR "Full Text & Metadata":"faulty sensor")
```

### AGRIS

```
detección de anomalías sensores agrícolas
```
```
anomaly detection agricultural sensors
```
Bloqueada por herramienta (SPA con JS, ver protocolo sección 3) — requiere navegación manual en un navegador, no scripting automatizado.

### SciELO / Horticultura Argentina

```
detección de anomalías sensores agrícolas
```
```
anomaly detection agricultural sensors
```

---

## Eje 3 — Generación de datos sintéticos

### Scopus

```
TITLE-ABS-KEY(("soil moisture" OR "crop" OR "agricultur*") AND ("synthetic data" OR "data augmentation" OR "data generation") AND ("sensor" OR "time series" OR "data scarcity"))
```

### Web of Science

```
TS=(("soil moisture" OR "crop" OR "agricultur*") AND ("synthetic data" OR "data augmentation" OR "data generation") AND ("sensor" OR "time series" OR "data scarcity"))
```

### IEEE Xplore (Command Search)

```
("Full Text & Metadata":"soil moisture" OR "Full Text & Metadata":"agriculture") AND ("Full Text & Metadata":"synthetic data" OR "Full Text & Metadata":"data augmentation")
```

### AGRIS

```
datos sintéticos agricultura
```
```
synthetic data agriculture
```
Bloqueada por herramienta (SPA con JS, ver protocolo sección 3) — requiere navegación manual en un navegador, no scripting automatizado.

### SciELO / Horticultura Argentina

```
datos sintéticos agricultura
```
```
synthetic data agriculture
```

---

## Eje 4 — Retroalimentación humana y recalibración

### Scopus

```
TITLE-ABS-KEY(("human feedback" OR "human-in-the-loop" OR "active learning" OR "model recalibration") AND ("machine learning" OR "predictive model") AND ("agricultur*" OR "environmental monitoring" OR "sensor"))
```

### Web of Science

```
TS=(("human feedback" OR "human-in-the-loop" OR "active learning" OR "model recalibration") AND ("machine learning" OR "predictive model") AND ("agricultur*" OR "environmental monitoring" OR "sensor"))
```

### IEEE Xplore (Command Search)

```
("Full Text & Metadata":"human-in-the-loop" OR "Full Text & Metadata":"human feedback" OR "Full Text & Metadata":"active learning") AND ("Full Text & Metadata":"machine learning")
```

### AGRIS

```
retroalimentación humana modelo agrícola
```
```
human-in-the-loop agriculture
```
Bloqueada por herramienta (SPA con JS, ver protocolo sección 3) — requiere navegación manual en un navegador, no scripting automatizado.

### SciELO / Horticultura Argentina

```
retroalimentación humana modelo agrícola
```
```
human-in-the-loop agriculture
```

---

## Estado de ejecución

Ninguna de las cadenas anteriores fue ejecutada. Este documento queda listo para que, en cuanto haya acceso institucional a Scopus/Web of Science/IEEE Xplore (y/o navegación manual disponible para AGRIS), la ejecución y el registro en `docs/research/hu1-registro-busquedas.csv` y `docs/research/hu1-corpus-final.csv` sean mecánicos y trazables por eje.
