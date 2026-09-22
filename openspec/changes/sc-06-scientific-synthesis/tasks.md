# Tareas de sc-06-scientific-synthesis

`IN_PROGRESS` desde el 2026-09-22, sobre entregables reconciliados de dos
líneas de trabajo. Marcar una tarea **no** acredita suficiencia científica:
ningún PASS estructural equivale a cierre científico. `CLOSE` queda sin marcar
hasta el veredicto de la auditoría independiente única.

- [x] T08 (SC-GOV-008) Revisión independiente. Comprobar: Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor. Evidencia: audit.json.
- [x] T16 (SC-GOV-016) Interpretación científica. Comprobar: Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte. Evidencia: claim-evidence-review.json.
- [ ] T25 (SC-GOV-025) Cierre científico. Comprobar: Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado. Evidencia: scientific-closure-audit.json.
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.

Notas, para que las casillas no digan más de lo que ocurrió:

- **T08** se cumple por la cadena de revisión independiente ya acreditada en
  RB-03 (crítico + auditor, sesiones separadas, `openspec/changes/sc-0{7,9,10}-*/reviews/`)
  y por las dos rondas de auditoría de `f355272`, preservadas verbatim en
  `reviews/`. No hay `audit.json` propio de `sc-06`: la evidencia vive
  distribuida en esas rutas.
- **T16** se cumple documentalmente: la síntesis
  (`docs/research/scientific-closure-synthesis-2026-09-22.md`) y la
  «Clasificación final de afirmaciones» de `claims.md` se contrastaron frase a
  frase contra las métricas ya recomputadas en las auditorías preservadas. No
  hay `claim-evidence-review.json` separado en esta reconciliación.
- **T25 queda deliberadamente sin marcar.** Las dos rondas de auditoría
  requisito por requisito sobre el snapshot de `f355272` terminaron en
  veredicto formal `FAIL`; ninguna tercera ronda verificó la corrección final,
  y esta reconciliación **no** trata la renuncia del auditor a esa tercera
  ronda como un `PASS`. T25 se marcará únicamente con el veredicto de la
  auditoría independiente única sobre el snapshot reconciliado.
- REVIEW-1 y REVIEW-2 los ejecutó el orquestador (sin rol separado, declarado
  en `reconciliation-2026-09-22/session-identity.json`). REVIEW-3 y REVIEW-4 no
  corrieron como pasadas separadas en ninguna de las dos ramas de origen.
  REVIEW-5 corrió **dos veces** en `f355272` (`FAIL`, `FAIL`) y correrá **una
  vez más** aquí, sobre el snapshot reconciliado.
- CLOSE exige `PASS`, que no existe todavía.
