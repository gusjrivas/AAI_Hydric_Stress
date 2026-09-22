# Tareas de sc-10-aux-robustness

Todas pendientes; la especificación no acredita ejecución. **Y siguen pendientes, deliberadamente**: ver la nota de cierre al pie.

- [ ] T24 (SC-GOV-024) Robustez condicional. Comprobar: Fixtures de grilla causal, perturbaciones y fechas comunes del diseño auxiliary_robustness_v1. Evidencia: auxiliary/S/review.json.
- [ ] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [ ] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.

## Nota de cierre documental — 2026-09-22

**Las casillas quedan sin marcar a propósito.** Este change **no se cerró**: sigue
`BLOCKED` en `changes.json` y su `extra_gate` exige la condición `REQUIRED`, que
no se cumple y no se cumplirá. Lo que ocurrió el 2026-09-22 es otra cosa, y
conviene no confundirlas.

**Qué sí ocurrió.** La decisión de suficiencia GD-12 clasificó **S como
`NOT_REQUIRED`**, se sometió a **crítica independiente** (confirma la
clasificación; 7 hallazgos materiales, todos remediados) y a **auditoría final
independiente** (**`PASS`** sobre el bloqueo RB-03, con 4 hallazgos propios y 5
condiciones documentales, todas aplicadas). Los dos informes están preservados
verbatim en `reviews/`. El artefacto `auxiliary/S/review.json` existe y vive en
`openspec/scientific-closure/sufficiency-review-2026-09-22/`.

**Consecuencia sobre cada casilla:**

- **T24 (SC-GOV-024)** — el requisito pasó a **`NOT_APPLICABLE`** en
  `traceability.md`, con sus límites permanentes declarados. La tarea no se marca
  porque su enunciado describe la rama **`REQUIRED`** («fixtures … antes de
  cualquier ejecución»), que no se tomó. La rama efectivamente recorrida es la
  otra que el criterio de aceptación prevé: «Si `NOT_REQUIRED`: solo decisión
  motivada, sin implementación».
- **REVIEW-1, REVIEW-2, REVIEW-3** — no corrieron como roles separados. No hubo
  explorador ni `evidence_checker` independientes, y el implementador no es
  independiente del orquestador. Declarado en `session-identity.json`.
- **REVIEW-4 y REVIEW-5** — sí corrieron, en sesiones de contexto separado y de
  solo lectura **instruida, no forzada por el harness**. Sus informes están en
  `reviews/`.
- **CLOSE** — no aplica: no hay `PASS` de change que registrar. Hubo commits, sin
  push, sin PR y sin merge.

**Lo que este expediente NO acredita:** ninguna ejecución de S, ningún
resultado sobre robustez, ningún desbloqueo de
`SC-GOV-025` ni del gate `GF`. `RB-04`, `RB-05` y `RB-06` siguen abiertos.
