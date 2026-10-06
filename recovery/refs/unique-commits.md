# Commits únicos preservados por referencia

Fecha: 2026-10-06. `origin/main` al momento del backup: `4c1cd6c8a909c8faeed3f3732c2efa1eeffd5377`.

Cada commit se conserva sin modificar, sin rebase y sin cherry-pick, mediante una rama remota `backup/recovery-*` que apunta exactamente a su SHA.

## 1. chore/rehearsal-producer-reset

| Campo | Valor |
|---|---|
| Rama original | `chore/rehearsal-producer-reset` (solo local; worktree `.worktrees/sensor-closure`) |
| SHA completo | `4c734f981b1355c14124261b73a288d6af69552b` |
| Parent | `b56b97a267045147648c507d68e3ce976f20d946` (merge del PR #230) |
| Autor / fecha | gusjrivas, 2026-09-29 22:37:22 -0300 |
| Mensaje | `chore(alerting-ui): script to regenerate the verified producer copy for the Docker rehearsal` |
| Rama de recuperación | `backup/recovery-rehearsal-producer-reset` (exactamente `4c734f9`) |

Archivos (2 agregados, 176 líneas):

- `docker/defense-rehearsal/producer-package.sha256` (84 líneas)
- `docker/defense-rehearsal/reset-producer-copy.ps1` (92 líneas)

Diferencia respecto de main: ninguno de los dos archivos existe en `origin/main` (`docker/defense-rehearsal/` solo contiene `compose.yml`). El commit se apoya en `b56b97a`, que está 19 commits detrás de `origin/main`; el diff directo contra `origin/main` incluye además el efecto del avance de main (por ejemplo, `scripts/demo_reset.ps1` figura como eliminado solo porque `b56b97a` es anterior). Se trata de tooling de ensayo Docker; no contiene resultados científicos. Patch-id: `3fa3edb363ca`.

Pendiente de decisión, fuera de esta tarea: portar o no el commit a main antes del freeze.

## 2. feat/replay-ui-guided-experience

| Campo | Valor |
|---|---|
| Rama original | `feat/replay-ui-guided-experience` (upstream `origin/...: gone`; worktree `.claude/worktrees/agent-aa8267105b82d075e`) |
| Base común | `f17fe658bad4726202fe13784bb716c06468af9a` (merge del PR #214) |
| Rama de recuperación | `backup/recovery-replay-ui-guided-experience` (exactamente `cdbf71c74e0c2272c9279bf32f46dbec61a7f3fa`) |

Commits únicos (2):

1. `5ab46aa26b9af628c02292ee7778d5b312f00ecf`, 2026-09-23 22:41:43 -0300, `feat(historical-replay): guided walkthrough for the replay exploration UI` (patch-id `5d4d74e2f61f`).
2. `cdbf71c74e0c2272c9279bf32f46dbec61a7f3fa`, 2026-09-23 23:01:43 -0300, `fix(historical-replay-ui): evitar solapamiento entre etiqueta de banda y fecha del eje` (1 archivo, `MoistureHistoryChart.tsx`; patch-id `9baac30c3679`).

PR #215 fue cerrado sin merge por decisión consciente. No debe recuperarse salvo investigación histórica.

## 3. docs/forecast-evidence-assessment

| Campo | Valor |
|---|---|
| Rama original | `docs/forecast-evidence-assessment` (solo local; worktree `AAI_Hydric_Stress_forecast_evidence_assessment`) |
| SHA completo | `9aaabe2545cd6cb0ec8734db9dea616dcf821abd` |
| Parent | `44f8ad21ad9d301868f123500845c52e932faa3c` |
| Autor / fecha | gusjrivas, 2026-09-27 02:06:07 -0300 |
| Mensaje | `docs: assess forecast evidence for defense` |
| Rama de recuperación | `backup/recovery-forecast-evidence-assessment` (exactamente `9aaabe2`) |

Archivo: `docs/research/forecast-evidence-assessment.md` (199 líneas).

Equivalencia en main: comprobada. `origin/main` contiene `96f59a1132e5e7ef5204b54edbeb418f79a7a4c5` (`docs: assess forecast evidence for defense`, 2026-09-27 02:16:35 -0300) con el mismo patch-id estable (`70f25862b04f`) y el archivo es idéntico (`git diff --quiet` entre ambos blobs). El contenido ya está en main.
