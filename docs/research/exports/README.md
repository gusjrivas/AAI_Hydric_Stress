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

Todas las subcarpetas están vacías (solo `.gitkeep`) al momento de crear esta estructura — ninguna búsqueda fue ejecutada todavía.
