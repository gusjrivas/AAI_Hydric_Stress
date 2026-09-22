# Tareas de sc-06-scientific-synthesis

`IN_PROGRESS` desde el 2026-09-22, sobre entregables reconciliados de dos
líneas de trabajo, con auditoría independiente de alcance acotado ya recibida
(`reviews/review-audit-reconciliation.md`, `PASS` sobre seis ítems, un hallazgo
material `F-01` corregido). Marcar una tarea **no** acredita suficiencia
científica: ningún PASS estructural equivale a cierre científico. `CLOSE` queda
sin marcar: **`T25` sigue sin marcar y el auditor fue explícito en que su
`PASS` no la descarga.**

- [x] T08 (SC-GOV-008) Revisión independiente. Comprobar: Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor. Evidencia: audit.json. *(evidencia distribuida en `reviews/`; no hay `audit.json` propio de `sc-06`, declarado en las notas)*
- [x] T16 (SC-GOV-016) Interpretación científica. Comprobar: Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte. Evidencia: claim-evidence-review.json. *(evidencia distribuida; no hay `claim-evidence-review.json` propio, declarado en las notas)*
- [ ] T25 (SC-GOV-025) Cierre científico. Comprobar: Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado. Evidencia: scientific-closure-audit.json. **Sin marcar.** La auditoría recibida tuvo alcance acotado a seis ítems de la reconciliación, no a los 25 requisitos; el propio auditor lo declara como límite decisivo de su informe
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico. **No corrió** como pasada separada; declarado en `session-identity.json` (OBS-03 del auditor)
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir. **No corrió** sobre este snapshot antes de la auditoría (OBS-03 del auditor: «el snapshot reconciliado no pasó por una crítica adversarial independiente»)
- [x] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot. Corrió: `PASS` sobre el alcance de seis ítems fijado por el responsable (`reviews/review-audit-reconciliation.md`), con hallazgo material `F-01` corregido en el mismo commit que preserva su informe. **No** es la auditoría requisito por requisito que T25 exige
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push. **No aplica todavía:** no hay `PASS` de change

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
