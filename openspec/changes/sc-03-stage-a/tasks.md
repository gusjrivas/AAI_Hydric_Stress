# Tareas de sc-03-stage-a

Todas pendientes; la especificación no acredita ejecución.

- [ ] T10 (SC-GOV-010) Causalidad temporal. Comprobar: tests/test_controlled_daily_v4_stage_window.py; tests/test_controlled_daily_v4_splits.py; tests/test_controlled_daily_v4_features.py. Evidencia: temporal-contract-check.json.
- [ ] T11 (SC-GOV-011) Gate A. Comprobar: tests/test_controlled_daily_v4_selection.py; tests/test_controlled_daily_v4_freezing.py; tests/test_controlled_daily_v4_stage_a_integration.py; auditar frozen_config.json. Evidencia: A/gate-review.json.
- [ ] T15 (SC-GOV-015) Estadística y soporte. Comprobar: tests/test_controlled_daily_v4_bootstrap.py; tests/test_controlled_daily_v4_metrics.py; tests/test_controlled_daily_v4_scientific_closure.py. Evidencia: statistical-review.json.
- [ ] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [ ] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.
