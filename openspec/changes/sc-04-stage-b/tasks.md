# Tareas de sc-04-stage-b

Todas pendientes; la especificación no acredita ejecución.

- [ ] T12 (SC-GOV-012) Gate B. Comprobar: tests/test_controlled_daily_v4_stage_b_runner.py; tests/test_controlled_daily_v4_stage_b_integration.py; contrastar decision.json. Evidencia: B/gate-review.json.
- [ ] T13 (SC-GOV-013) Custodia de B. Comprobar: tests/test_controlled_daily_v4_scientific_closure.py: custodia, concurrencia, reserva antes de validación y recuperación. Evidencia: B/custody-review.json.
- [ ] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [ ] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.
