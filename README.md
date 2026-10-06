# Backup de recuperación previo al freeze

Esta rama contiene material preservado antes de la limpieza final del repositorio correspondiente al Trabajo Final de Maestría.

No representa código vigente.

No representa evidencia científica nueva.

No debe mergearse a main.

Su único propósito es permitir recuperación de artefactos locales, stashes, patches o referencias históricas que podrían eliminarse durante la limpieza final.

Estado científico canónico al momento del backup:

- RB-05 = FAIL
- sc-06 = FAIL
- SC-GOV-025 = FAIL
- GF = FAIL

Fecha de preservación: 2026-10-06.

## Contenido

Rama huérfana, sin historia común con `main`. Índice completo y hashes en `recovery/manifest/MANIFEST.md`.

- `recovery/manifest/`: manifiesto, hashes SHA-256 y estado del repositorio al momento del backup.
- `recovery/refs/`: registro de commits únicos conservados además como ramas `backup/recovery-*`.
- `recovery/checker/`: cambios sucios del checker científico estructural (patches).
- `recovery/stashes/`: snapshots de `stash@{0}` y `stash@{1}`.
- `recovery/untracked/`: archivos no versionados y archivos comprimidos de artefactos ignorados seleccionados.

Los archivos se conservan sin ejecutar y sin incorporar a `main`.
