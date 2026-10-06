# Manifiesto de recuperación

Rama: `backup/pre-freeze-recovery-2026-10-06` (huérfana; exclusivamente de archivo y recuperación; no mergear a `main`).

## Estado al momento del backup

| Campo | Valor |
|---|---|
| Fecha | 2026-10-06 |
| Repositorio | `gusjrivas/AAI_Hydric_Stress` |
| `origin/main` | `4c1cd6c8a909c8faeed3f3732c2efa1eeffd5377` (merge del PR #232; coincide con el esperado) |
| `main` local | `b56b97a267045147648c507d68e3ce976f20d946` (19 commits detrás de `origin/main`; no actualizado) |
| PR #215 | CLOSED, sin merge (decisión consciente) |
| PR #232 | MERGED (2026-10-06T02:03:17Z) |
| Estado científico canónico | RB-05 = FAIL; sc-06 = FAIL; SC-GOV-025 = FAIL; GF = FAIL |
| Experimentos / holdouts / A-B-C-H | no ejecutados, no abiertos |

`SHA256SUMS.txt` lista el SHA-256 de todos los archivos de la rama fuera de este directorio. `repo-state.txt` registra ramas, stashes y worktrees locales al momento del backup. Las columnas SHA/Hash muestran el SHA-256 completo del artefacto, o el SHA de commit de Git.

## Artefactos

| Artefacto | Origen | SHA/Hash | Backup | Estado | Recuperación |
|---|---|---|---|---|---|
| Commit `4c734f9` (script de reset de copia productor) | rama local `chore/rehearsal-producer-reset` | `4c734f981b1355c14124261b73a288d6af69552b` | rama `backup/recovery-rehearsal-producer-reset`; `recovery/refs/unique-commits.md` | único (no está en main) | `git fetch origin backup/recovery-rehearsal-producer-reset` |
| Commits `5ab46aa`, `cdbf71c` (PR #215) | rama `feat/replay-ui-guided-experience` (upstream eliminado) | `cdbf71c74e0c2272c9279bf32f46dbec61a7f3fa` | rama `backup/recovery-replay-ui-guided-experience` | únicos; PR cerrado sin merge | `git fetch origin backup/recovery-replay-ui-guided-experience` |
| Commit `9aaabe2` (evaluación de evidencia de pronóstico) | rama local `docs/forecast-evidence-assessment` | `9aaabe2545cd6cb0ec8734db9dea616dcf821abd` | rama `backup/recovery-forecast-evidence-assessment` | equivalente en main (`96f59a1`: mismo patch-id, archivo idéntico) | `git fetch origin backup/recovery-forecast-evidence-assessment` |
| checker dirty: `check_scientific_closure.py.patch` | worktree `AAI_Hydric_Stress_scientific_closure` (`feat/scientific-closure` @ `59612ab`) | `b76eb96ae60ea8aa4ad67f8f061109d4bd893c477ef103ac6ad8dc235a45d1e1` | `recovery/checker/check_scientific_closure.py.patch` | checkpoint interrumpido, probablemente superado por main | copiar desde la rama |
| checker dirty: `test_scientific_closure_checker.py.patch` | worktree `AAI_Hydric_Stress_scientific_closure` (`feat/scientific-closure` @ `59612ab`) | `c004323ac85602baca4f8037a6818248f3e361e6978c8f397ebfa629976605ed` | `recovery/checker/test_scientific_closure_checker.py.patch` | checkpoint interrumpido, probablemente superado por main | copiar desde la rama |
| checker dirty: `validation-read-only-probe.tmp` | worktree `AAI_Hydric_Stress_scientific_closure` (`feat/scientific-closure` @ `59612ab`) | `5f32a4bf1e4462d70cd8d17d805e297d88629a9745c2a6459d32e5ed9b548976` | `recovery/checker/validation-read-only-probe.tmp` | checkpoint interrumpido, probablemente superado por main | copiar desde la rama |
| stash@{0}: `stash-0.patch` | `git stash` local | `cfde7713d5b9b34fa54a8b8000e17273b886088533d71b78eeed6a9fbf52eec0` | `recovery/stashes/stash-0/stash-0.patch` | no aplicado | copiar desde la rama; ver README del stash |
| stash@{0}: `files.txt` | `git stash` local | `947d711b1b6f9be9e2fbf5b6af1b7e3ea055787ee959263d8704452014d1638a` | `recovery/stashes/stash-0/files.txt` | no aplicado | copiar desde la rama; ver README del stash |
| stash@{1}: `stash-1.patch` | `git stash` local | `1cf1d807fc2cb52b4d7cf5b8d770a3e795c0ddfe4c45f3fefc4c2b6254ae58e2` | `recovery/stashes/stash-1/stash-1.patch` | no aplicado | copiar desde la rama; ver README del stash |
| stash@{1}: `files.txt` | `git stash` local | `d2854e84aa830f8163ac8a98593733dabff33d1f41aeb346c99c8854886a0c67` | `recovery/stashes/stash-1/files.txt` | no aplicado | copiar desde la rama; ver README del stash |
| stash@{0}: 2 archivos extraídos | objeto stash `5bc4746` | ver `SHA256SUMS.txt` | `recovery/stashes/stash-0/files/` | únicos (ausentes en main) | copiar desde la rama |
| stash@{1}: 30 archivos extraídos | objeto stash `a78c25c` | ver `SHA256SUMS.txt` | `recovery/stashes/stash-1/files/` | no existen en main (salvo los modificados) | copiar desde la rama |
| stash@{0}/{1}: `.codebase-memory/*` | objeto stash | blobs en `codebase-memory-blobs.txt` de cada stash | no copiado (índice derivado regenerable) | descartable | n/a |
| untracked: `pergamino-worktree-referencias/Mi cultivo · rediseño UI.html` | `.worktrees/ui-defense-pergamino/referencias/` | `739029cd99cfbb9f6c4ac3aee66a61d9bd9ef2fb5b256f160b2becfbcc326f39` | `recovery/untracked/pergamino-worktree-referencias/Mi cultivo · rediseño UI.html` | único; copia idéntica en Descargas | copiar desde la rama |
| untracked: `ensemble-retrospective-evaluation-worktree/revision-evaluacion-2023.zip` | worktree `AAI_Hydric_Stress_ensemble_retrospective_evaluation` | `e4bde2e2bea578ad4a8e2f4367b352430a5e3649dec38d6a9f3c90ca484117cb` | `recovery/untracked/ensemble-retrospective-evaluation-worktree/revision-evaluacion-2023.zip` | único; ZIP no extraído (listado en `.listing.txt`) | copiar desde la rama |
| untracked: `build-identity/main-worktree/.build_identity.json` | raíz `AAI_Hydric_Stress` (ignorado) | `43bba0fdd0f994fcb8779fbdaf2c6463babb2995419305cd91148bea46a4479c` | `recovery/untracked/build-identity/main-worktree/.build_identity.json` | preservado | copiar desde la rama |
| untracked: `build-identity/repro-docs-worktree/.build_identity.json` | worktree `AAI_Hydric_Stress_repro-docs` (ignorado) | `a57c58491bfef4220f2792f2870e325b48a091710db74bbea95ca46920fe58f6` | `recovery/untracked/build-identity/repro-docs-worktree/.build_identity.json` | preservado | copiar desde la rama |
| untracked: `build-identity/scientific-closure-worktree/.build_identity.json` | worktree `AAI_Hydric_Stress_scientific_closure` (ignorado) | `b85a2aec0d108c6d0141e2725d38d9d9b94bf7a4fc8a820b62de6e92583ab8d1` | `recovery/untracked/build-identity/scientific-closure-worktree/.build_identity.json` | preservado | copiar desde la rama |
| untracked: `audit-step2-worktree-docs-design/backend-audit-step2-brief-2026-09-24.md` | worktree `AAI_Hydric_Stress_audit_step2` | `34314a2b6eb22f20f4c8e1fff7309791b5564e1cb8602d1ef7f17a476405aa55` | `recovery/untracked/audit-step2-worktree-docs-design/backend-audit-step2-brief-2026-09-24.md` | único | copiar desde la rama |
| untracked: `audit-step2-worktree-docs-design/backend-chapter3-preliminary-matrix-2026-09-24.md` | worktree `AAI_Hydric_Stress_audit_step2` | `ff04f580e028094b03221d82c211ea0b6ab9e99e95ec9cd3e5d048dee2009396` | `recovery/untracked/audit-step2-worktree-docs-design/backend-chapter3-preliminary-matrix-2026-09-24.md` | único | copiar desde la rama |
| untracked: `audit-step2-worktree-docs-design/backend-technical-survey-2026-09-24.md` | worktree `AAI_Hydric_Stress_audit_step2` | `3bf98cd86ae13f0a76db979d87e1656994db940ac8e49d9decfbdf6f28a4695e` | `recovery/untracked/audit-step2-worktree-docs-design/backend-technical-survey-2026-09-24.md` | único | copiar desde la rama |
| untracked: `hu7-v3-reference-worktree-docs-research/reference-v3-formal-results.json` | worktree `AAI_Hydric_Stress_hu7_v3_reference` | `b876d21cf655075cede4f9532696eb9abc4357fe43b9b7c29414cf6e1e83445a` | `recovery/untracked/hu7-v3-reference-worktree-docs-research/reference-v3-formal-results.json` | único | copiar desde la rama |
| untracked: `hu7-v3-reference-worktree-docs-research/reference-v3-formal-table.md` | worktree `AAI_Hydric_Stress_hu7_v3_reference` | `29639c4871033f5abb008258f47c4dfa4dd12c394d4a377fd365a1eda9c4d47c` | `recovery/untracked/hu7-v3-reference-worktree-docs-research/reference-v3-formal-table.md` | único | copiar desde la rama |
| untracked: `ignored-archives/mlruns-hu7-epica4-experiments.tar.gz` | ignorado `mlruns/` (2 experimentos hu7-epica4) | `82bfa3124ec6df3d0bd29eeaec317dfc7bc66f6b98be7855c1f05dd8383ca964` | `recovery/untracked/ignored-archives/mlruns-hu7-epica4-experiments.tar.gz` | archivo comprimido | copiar desde la rama |
| untracked: `ignored-archives/demo-sessions-and-ignored-data-parquets.tar.gz` | ignorados: `demo_sessions/`, `.demo_replay_sessions/`, parquets demo/lab de `data/` | `b51818c0e8845e16046a8245cc51acf3f57c0dfdcd3f5c4ed24d7fe936c288d6` | `recovery/untracked/ignored-archives/demo-sessions-and-ignored-data-parquets.tar.gz` | archivo comprimido | copiar desde la rama |

## Artefactos ignorados evaluados

| Conjunto | Tamaño / archivos | Clasificación | Justificación |
|---|---|---|---|
| `mlruns/` experimentos `265531178453459210` (hu7-epica4-purged-cv) y `338389283590227873` (hu7-epica4-leakage-fix) | 2,9 MB / 72 runs | RESPALDAR EN RAMA | Corridas históricas HU7 pequeñas; archivadas en `.tar.gz`. No se verificó reproducibilidad. |
| `mlruns/1`, `mlruns/2` (sin nombre) | 92 MB / ~1092 runs; `model.pkl` de ~552 KB cada uno | REQUIERE DECISIÓN | Máx. 552 KB por archivo (bajo el límite de 100 MB de GitHub) pero 92 MB y ~8,6 mil archivos; no se determinó si son reproducibles. No se agregaron. |
| `backend/mlruns/` | 99 MB / 2165 archivos (`alerting-ui`: 36 runs, 5,7 MB; `2`: 90 MB) | REQUIERE DECISIÓN | Runs generados por la API local; probablemente regenerables, no verificado. No se agregaron. |
| `demo_sessions/`, `.demo_replay_sessions/`, parquets `demo`/`lab`/`feedback_ui` de `data/` | ~0,4 MB / ~54 archivos | RESPALDAR EN RAMA | Estado de ejecuciones de demo; tamaño trivial. Archivados en `.tar.gz`. |
| `data/*.parquet`, `data/*.csv` y `data/dictionaries` versionados | 370 KB en `data/` | YA PRESERVADO | Versionados en git. |
| `data/.locks/` | 9 archivos de lock | NO NECESITA BACKUP | Archivos de bloqueo efímeros. |
| `frontend/dist/`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `src/*.egg-info` | 349 KB y cachés | NO NECESITA BACKUP | Derivados de build. |
| `.superpowers/`, `.claude/settings.local.json` | 45 KB y 4 KB | NO NECESITA BACKUP | Configuración local de herramientas. No se copió por posible contenido sensible. |
| `.codebase-memory/graph.db.zst` | 7,3 MB | NO NECESITA BACKUP | Índice de grafo regenerable (modificado sin commitear en main). |

## No encontrado

- `Diseño UI.html`: no existe en `C:\Repo` ni en las ubicaciones habituales del usuario. El archivo más cercano, `Mi cultivo · rediseño UI.html` (1 660 787 bytes), existe en `.worktrees/ui-defense-pergamino/referencias/` y como copia idéntica (mismo SHA-256) en Descargas; se preservó una copia.
