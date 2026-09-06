# Exports bibliográficos — HU1

Carpeta para depositar los archivos exportados tal cual entrega cada base al ejecutar las cadenas de `docs/research/hu1-instrucciones-ejecucion-busquedas.md` (CSV, BibTeX o RIS de Scopus, Web of Science, IEEE Xplore, AGRIS o SciELO/Horticultura Argentina).

No editar estos archivos a mano: son el original exportado, insumo para consolidar en `docs/research/hu1-corpus-final.csv` y `docs/research/hu1-registro-busquedas.csv` (ver protocolo, sección 6).

Una subcarpeta por base:

```
exports/
├── scopus/
├── wos/
├── ieee/
├── agris/
├── scielo/
└── horticultura_argentina/
```

Dentro de cada una, un archivo por eje y fecha de ejecución, p. ej. `exports/scopus/eje1_2026-09-05.csv`.

## Estado real (2026-09-06)

- **Scopus:** exports reales para los 4 ejes (`scopus/eje1_modelado_predictivo.csv` … `eje4_feedback_recalibracion.csv`), consolidados en `docs/research/hu1-corpus-final.csv`.
- **IEEE Xplore:** exports reales para los 4 ejes (`ieee/eje1_modelado_predictivo.csv` … `eje4_feedback_recalibracion.csv`), ídem.
- **Web of Science:** no se pudo ejecutar — la cuenta institucional disponible permite búsqueda de perfiles de investigadores, pero no Document Search/Core Collection (ver `docs/research/hu1-protocolo-revision-bibliografica.md`, sección 3). Carpeta `wos/` sin exports, solo `.gitkeep`.
- **AGRIS, SciELO, Horticultura Argentina:** sin exports — no ejecutadas de forma automatizada (bloqueos de herramienta/scraping, ver `docs/research/hu1-registro-busquedas.csv`). Carpetas sin exports, solo `.gitkeep`.
- **Fuentes complementarias** (Crossref, OpenAlex, DOAJ) no usan esta carpeta de exports manuales: se consultaron vía API y su estado/cadena real están documentados directamente en `docs/research/hu1-registro-busquedas.csv`.

No afirmar que una fuente fue ejecutada si no hay un export real (o, para las APIs, una fila con resultado real) que lo respalde.
