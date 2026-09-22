# Tareas de sc-06-scientific-synthesis

**`FAIL` desde el 2026-09-22** (`changes.json`: `REVIEW → FAIL`). Cerrado
administrativamente con no conformidad declarada, no con `PASS`
(`decisions.md` GD-40). Marcar una tarea **no** acredita suficiencia
científica: ningún PASS estructural equivale a cierre científico.

**Corrección 2026-09-22 (hallazgo material M-02 de la auditoría Codex RB-05,
`openspec/scientific-closure/rb05-audit-preparation-2026-09-22/reviews/review-audit-codex-round1-FAIL.md`):**
se preparó un dossier RB-05 (`openspec/scientific-closure/rb05-audit-preparation-2026-09-22/`)
sobre el snapshot `88ced62` para la auditoría requisito por requisito que T25
exige. Esa auditoría corrió y terminó en **`FAIL`** — hallazgos M-01..M-04,
el más severo una contradicción cronológica comprobada contra fuentes
primarias en la secuencia de gates A→B→C (ver `decisions.md` GD-38 y
`risks.md` RK-20). **T08 se desmarca**: la cadena de revisión independiente
que debía acreditarlo no cubre esta contradicción y el propio informe FAIL la
identifica como afectando a SC-GOV-007/012/014, de los que T08 depende
indirectamente vía `operations.md`.

- [ ] T08 (SC-GOV-008) Revisión independiente. Comprobar: Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor. Evidencia: audit.json. **Desmarcada 2026-09-22 (M-02):** la auditoría Codex RB-05 round 1 sobre `88ced62` encontró que el registro de cambios (`changes.json`) acredita, para sc-04 y sc-05, autorizaciones basadas en un PASS de la etapa previa fechado *después* de esas autorizaciones — ver `decisions.md` GD-38. Mientras ese hallazgo no se resuelva, T08 no puede darse por cumplida
- [x] T16 (SC-GOV-016) Interpretación científica. Comprobar: Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte. Evidencia: claim-evidence-review.json. *(evidencia distribuida; no hay `claim-evidence-review.json` propio, declarado en las notas)*
- [x] T25 (SC-GOV-025) Cierre científico. Comprobar: Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado. Evidencia: scientific-closure-audit.json. **Completada con veredicto `FAIL`, 2026-09-22.** La auditoría requisito por requisito sobre los 25 SC-GOV corrió sobre el dossier RB-05 (`88ced62`) y terminó en `FAIL` (M-01..M-04, `openspec/changes/sc-06-scientific-synthesis/reviews/review-audit-rb05-codex-FAIL.md`). El hallazgo M-01 fue confirmado, declarado incumplimiento histórico no reparable documentalmente (`decisions.md` GD-38) y aceptado administrativamente por el responsable como desviación permanente (`decisions.md` GD-40). Marcada `[x]` porque la tarea —ejecutar la auditoría y registrar su veredicto— **se hizo**; el veredicto es negativo, no está pendiente
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico. **No corrió** como pasada separada; declarado en `session-identity.json` (OBS-03 del auditor)
- [x] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir. Corrió sobre el dossier RB-05 (no sobre la síntesis completa de `sc-06`): un hallazgo material (M-01 de esa ronda, cita mal atribuida), corregido el 2026-09-22. Ver `rb05-audit-preparation-2026-09-22/rb05-dossier.md` §2
- [x] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot. Corrió dos veces: (a) `PASS` sobre el alcance de seis ítems de la reconciliación (`reviews/review-audit-reconciliation.md`); (b) `FAIL` sobre los 25 requisitos, snapshot `88ced62` (`rb05-audit-preparation-2026-09-22/reviews/review-audit-codex-round1-FAIL.md`). La (b) es la auditoría que T25 exige y su veredicto es `FAIL`, no `PASS`
- [x] CLOSE Registrar SHA, evidencia, alcance y checkpoint. **Cerrado administrativamente con no conformidad declarada, 2026-09-22 (`decisions.md` GD-40), no con `PASS`.** El texto original de esta tarea («Solo con PASS... ») describe el cierre confirmatorio, que **no se alcanzó**; el cierre que sí ocurrió es distinto y se registra como tal: `change` en `FAIL`, `SC-GOV-025` y `GF` en `FAIL`, B y C reclasificados como evidencia retrospectiva exploratoria. No hay tareas experimentales pendientes dentro de esta campaña — una confirmación futura es una campaña nueva sobre datos no utilizados, no una reparación de ésta

Notas de cierre parcial, para que las casillas no digan más de lo que ocurrió:

- **T08** se apoya en la cadena de revisión independiente de RB-03 (crítico +
  auditor, sesiones separadas, `openspec/changes/sc-0{7,9,10}-*/reviews/`), en
  las dos rondas de auditoría de `f355272` (preservadas como historia) y en la
  auditoría de esta reconciliación. No hay `audit.json` propio de `sc-06`.
- **T16** se cumple documentalmente contra las métricas ya recomputadas en las
  auditorías preservadas; no hay `claim-evidence-review.json` propio.
- **T25 es la tarea que falta.** El camino más corto, según el propio auditor
  de la reconciliación: crítica independiente (`scientific_critic`) sobre el
  snapshot corregido con `F-01`, y luego una auditoría final **requisito por
  requisito sobre los 25 requisitos**. Ninguno de los dos pasos exige reabrir
  el holdout ni reejecutar A, B, C, H, R, N o S.
- REVIEW-1 y REVIEW-2 los ejecutó el orquestador, sin rol separado, declarado.
- REVIEW-5 corrió una vez en esta reconciliación (`PASS` acotado). En
  `f355272` corrió dos veces sobre el snapshot de esa rama (`FAIL`, `FAIL`),
  preservado en `reviews/review-audit-final-round{1,2}-FAIL.md`; ninguna
  tercera ronda verificó la corrección final de esa rama, y esta reconciliación
  no la trata como un `PASS`.
