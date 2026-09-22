# Tareas de sc-06-scientific-synthesis

Cerradas el 2026-09-22 con PASS del change, sobre el veredicto de fondo
`PASS_WITH_LIMITATIONS` del auditor independiente. Las dos rondas de revisión
terminaron en `FAIL` y sus informes se preservan verbatim en
`openspec/scientific-closure/evidence-finalization-2026-09-22/reviews/`.
Marcar una tarea **no** acredita suficiencia científica: ningún PASS estructural
equivale a cierre científico.

- [x] T08 (SC-GOV-008) Revisión independiente. Comprobar: Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor. Evidencia: audit.json.
- [x] T16 (SC-GOV-016) Interpretación científica. Comprobar: Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte. Evidencia: claim-evidence-review.json.
- [x] T25 (SC-GOV-025) Cierre científico. Comprobar: Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado. Evidencia: scientific-closure-audit.json.
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [x] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [x] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [x] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [x] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.

Notas de cierre, para que las casillas no digan más de lo que ocurrió:

- REVIEW-3 (`evidence_checker`) y REVIEW-4 (`scientific_critic`) **no** se
  ejecutaron como pasadas separadas. Por instrucción expresa del responsable
  (`GD-35`) hubo **una sola** revisión independiente por ronda, que cubrió
  crítica y auditoría. El propio auditor lo confirma: «soy un solo lector».
- REVIEW-5 se cumplió dos veces y las dos emitieron `FAIL`; el `PASS` del change
  se apoya en el veredicto de fondo del auditor y en su renuncia expresa a una
  tercera ronda, no en un tercer informe favorable. **Ningún lector independiente
  revisó el snapshot final** (`GD-39`).
- CLOSE dice «sin push». Esta fase **sí** publica en
  `origin/feat/scientific-evidence-finalization` y abre un PR contra
  `feat/scientific-closure`, por autorización expresa del encargo del
  2026-09-22. La exclusión de `main`, merge, rebase, force push, tags y releases
  **sigue vigente sin cambios**.
