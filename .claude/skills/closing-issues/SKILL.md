---
name: closing-issues
description: Use before closing any GitHub issue in this repo — verifies the task is genuinely done against docs/seguimiento-tareas.md and concrete evidence, then closes with a comment citing that evidence. Triggers on requests like "cerrá los issues que ya estén terminados", "revisá qué issues se pueden cerrar", before running `gh issue close`, or automatically after `gh pr merge` (ver hook `remind-close-issues-after-merge.sh`).
---

# Cerrar issues con evidencia verificable

Este repositorio tiene un issue por cada tarea técnica del plan de tesis (ver `openspec/project.md`, mapa HU → capacidad). Dos hooks sostienen esto automáticamente:

- `check-issue-close-evidence.sh` (PreToolUse) bloquea `gh issue close` sin un `--comment` que referencie evidencia concreta.
- `remind-close-issues-after-merge.sh` (PostToolUse) se dispara después de cada `gh pr merge` e inyecta un recordatorio para invocar esta skill — no depende de que el usuario lo pida ni de que el agente se acuerde por su cuenta.

Ambos hooks solo aplican heurísticas mecánicas (¿hay un `--comment`? ¿el comando fue `gh pr merge`?). Esta skill es el criterio real: qué cuenta como evidencia suficiente.

## Regla central

**Nunca cierres un issue por lo que decís haber hecho en la conversación — cerralo por lo que ya quedó escrito en el repo.** El mismo principio que sostiene `docs/seguimiento-tareas.md`: "artefacto creado" no es lo mismo que "tarea completada", y "lo mencioné en el chat" no es lo mismo que "hay evidencia versionada".

## Procedimiento

1. **Leé `docs/seguimiento-tareas.md` primero.** Ya audita cada tarea de HU1-HU8 contra evidencia real, con la leyenda ✅ (completado) / 🟡 (parcial) / ⬜ (no iniciado). Si la tarea del issue está marcada 🟡 o ⬜ ahí, **no la cierres**, aunque la conversación reciente haya avanzado sobre ese tema — 🟡 significa explícitamente que no cumple el criterio de aceptación completo.
2. **Si está marcada ✅**, confirmá que la evidencia citada en esa fila todavía existe (el archivo no fue borrado o renombrado desde entonces) antes de cerrar.
3. **Si el issue no tiene fila correspondiente en `docs/seguimiento-tareas.md`** (tareas de HU3-HU8, que hoy no tienen ninguna sección propia porque no arrancaron), buscá evidencia directa: un commit, un archivo, un test que pase, o un PR ya mergeado que implemente exactamente lo que pide el issue. Sin esa evidencia verificable, no lo cierres — decíselo al usuario en vez de asumir.
4. **Cerrá con `gh issue close <N> --comment "..."`**, citando la ruta exacta del archivo (o el número de PR) que demuestra el cierre — no un genérico "listo" o "hecho". El hook rechaza comentarios sin ese patrón, pero la vara real es más alta: el comentario debe permitir que alguien que no participó de esta conversación verifique la afirmación yendo directo a esa ruta.

## Qué NO hacer

- No cerrar un lote de issues "porque parecen relacionados" a un PR reciente sin verificar cada uno individualmente contra el seguimiento de tareas.
- No usar `SKIP_ISSUE_EVIDENCE=1` para saltear el hook salvo que el usuario lo pida explícitamente para un caso puntual (ej. un issue duplicado o creado por error, donde "evidencia de por qué está terminado" no aplica).
- No inferir que un issue está terminado solo porque su Épica/HU tiene *algún* PR mergeado — un PR puede cubrir una tarea de la HU sin cubrir todas.

## Ejemplo

```bash
gh issue close 18 --comment "Completado en docs/research/hu1-protocolo-revision-bibliografica.md (objetivo/alcance, secciones 1-6): protocolo formal con términos/sinónimos, cadenas de búsqueda por base, criterios de inclusión/exclusión y procedimiento de registro. Ver también docs/seguimiento-tareas.md (HU1, marcado ✅)."
```
