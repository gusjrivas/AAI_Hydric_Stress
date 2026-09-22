# Tareas de sc-02-runtime-readiness

Todas pendientes; la especificación no acredita ejecución.

- [ ] T02 (SC-GOV-002) Autoridad y autorización. Comprobar: Revisión de autorización contra instrucciones de sesión, protocolo y ADR-0011; registrar discrepancias sin resolverlas unilateralmente. Evidencia: authorizations.json.
- [ ] T06 (SC-GOV-006) Separación de roles. Comprobar: python -m unittest discover -s tests -p test_scientific_closure_governance.py; verificar carga efectiva y permisos en Codex. Evidencia: agent-capabilities.json.
- [ ] T07 (SC-GOV-007) Cambios y dependencias. Comprobar: Inspección del DAG, registro de asignaciones y manifiestos de revisión por SHA. Evidencia: workflow-events.jsonl.
- [ ] T09 (SC-GOV-009) Identidad reproducible. Comprobar: tests/test_controlled_daily_v4_reproducibility_artifacts.py; tests/test_controlled_daily_v4_environment_validation.py; docker inspect y pip check. Evidencia: execution-manifest.json.
- [ ] T17 (SC-GOV-017) Procedencia desconocida. Comprobar: Revisar manifiesto v4, ADR-0011 y evidencia documental aportada por responsable; no consultar valores reservados. Evidencia: provenance-assessment.json.
- [ ] T18 (SC-GOV-018) Backup y recuperación. Comprobar: Ensayo sintético de backup/restauración más tests/test_controlled_daily_v4_stage_c_recovery.py; revisión de rutas por responsable. Evidencia: recovery-rehearsal.json.
- [ ] T19 (SC-GOV-019) Checkpoints. Comprobar: git diff --check; git diff --cached; git log; registro de checkpoints y estado. Evidencia: checkpoints.json.
- [ ] T20 (SC-GOV-020) Validación de especificaciones. Comprobar: OpenSpec 1.13.1 validate; python -m unittest discover -s tests -p test_scientific_closure_governance.py. Evidencia: structural-validation.json.
- [ ] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [ ] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.
