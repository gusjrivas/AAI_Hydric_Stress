# stash@{0}

- Origen: `On docs/thesis-defense-normalization: !!GitHub_Desktop<docs/thesis-defense-normalization>`
- Commit del stash: `5bc4746f1067f009ec676f9fe84a373f8b6d48c1`
- Base: `96bb80606c9646b0946ff3bab1a5e19b2ebbf43b` (`docs: precisar runner H y elegibilidad de reviews`, 2026-09-27 00:48:27 -0300; ancestro de `origin/main`)
- Fecha del stash: 2026-09-27 20:42:24 -0300

## Contenido

| Estado | Archivo | Copia en esta rama |
|---|---|---|
| M | `.codebase-memory/artifact.json` | no copiado (índice derivado; ver nota) |
| M | `.codebase-memory/graph.db.zst` | no copiado (binario derivado, ver nota) |
| A | `docs/design/plan-robustez-tecnica-defensa-2026-09-27.md` | `files/docs/design/...` |
| A | `revision-documental-3ebb004.patch` | `files/revision-documental-3ebb004.patch` |

Archivos de apoyo: `stash-0.patch` (patch completo con `--binary`, excluidos los dos archivos de `.codebase-memory`), `files.txt` (listado), `description.txt`, `stash-commit.txt`, `base-commit.txt`, `codebase-memory-blobs.txt` (SHA de los blobs de `.codebase-memory`).

El stash no tiene tercer padre: los archivos nuevos están dentro del árbol del propio commit del stash, de donde se extrajeron con `git show`. No se ejecutó ningún archivo.

Nota: `.codebase-memory/graph.db.zst` es el índice de grafo regenerable (7 MB); se registra solo el SHA del blob.

## Relevancia aparente

- `plan-robustez-tecnica-defensa-2026-09-27.md`: plan de ejecución para Codex; se declara explícitamente no autorizante de HU7/HU8 A/B/C.
- `revision-documental-3ebb004.patch`: patch de revisión documental referido al commit `3ebb004`.
- Cambios de `.codebase-memory`: ruido de reindexación.

## Equivalente en main

No. Ni el plan ni el patch existen en `origin/main` (verificado con `git cat-file -e`). No se buscó equivalencia semántica con otros documentos.

## Decisión provisional

Contenido documental único, de relevancia moderada. Preservado aquí; la decisión de incorporarlo o descartarlo queda para una etapa posterior. No se incorpora a main.
