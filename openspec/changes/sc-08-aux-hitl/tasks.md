# Tareas de sc-08-aux-hitl

Cerradas el 2026-09-21 con PASS del auditor independiente sobre el snapshot
`5aec15d4`. El detalle está en `reviews/` y en
`evidence/governance/hitl-complement-2026-09-21/`.

- [x] T22 (SC-GOV-022) HITL condicional. Comprobar: Revisión de fechas de feedback, separación de refit/correcciones, fixtures del diseño auxiliary_hitl_v1. Evidencia: auxiliary/H/review.json.
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [x] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [x] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [x] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [x] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.

Notas de cierre, para que las casillas no se lean como más de lo que son:

- REVIEW-3 lo cumplió el propio auditor final al recomputar hashes, manifiestos y métricas
  por su cuenta; no hubo un `evidence_checker` separado.
- REVIEW-4 se ejecutó cuatro veces: tres sobre el paquete, antes de la intervención humana
  (dos `NO_APTO` y una `APTO`), y una sobre la ejecución (un hallazgo material). Los cuatro
  informes están preservados verbatim en `reviews/`.
- CLOSE registra el SHA, la evidencia y el alcance. **Sí hubo push y PR**, a diferencia de
  la redacción original de esta tarea: la instrucción vigente del responsable los ordena
  expresamente hacia `origin/feat/scientific-closure-hitl-complement` y un PR contra
  `feat/scientific-closure`, nunca contra `main`.
