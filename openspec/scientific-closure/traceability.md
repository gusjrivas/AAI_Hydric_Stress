# Matriz requisito → tarea → prueba → evidencia

Fuente estructurada: requirements.json. Criterios completos: spec científica.
Cada fila tiene estado PENDING; no atribuir resultados a artefactos esperados.
R/H/N/S solo aplican si el análisis de afirmaciones los marca REQUIRED.

| Requisito | Change / tarea | Comprobación | Evidencia esperada |
| --- | --- | --- | --- |
| SC-GOV-001 | sc-01-evidence-scope / T01 | git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --porcelain=v1 --untracked-files=all | session-identity.json |
| SC-GOV-002 | sc-02-runtime-readiness / T02 | Revisión de autorización contra instrucciones de sesión, protocolo y ADR-0011; registrar discrepancias sin resolverlas unilateralmente. | authorizations.json |
| SC-GOV-003 | sc-01-evidence-scope / T03 | git diff --name-status BASE..HEAD; comparar hashes de archivos históricos sin analizar sus resultados. | preservation.json |
| SC-GOV-004 | sc-01-evidence-scope / T04 | Contrastar inventario con rutas y documentación permitidas; jamás llenar resultados por inferencia. | inventory.json |
| SC-GOV-005 | sc-01-evidence-scope / T05 | Auditoría de claims.md contra project.md, ADR-0009/0010/0011 y decisiones de cierre. | claims-assessment.json |
| SC-GOV-006 | sc-02-runtime-readiness / T06 | python -m unittest discover -s tests -p test_scientific_closure_governance.py; verificar carga efectiva y permisos en Codex. | agent-capabilities.json |
| SC-GOV-007 | sc-02-runtime-readiness / T07 | Inspección del DAG, registro de asignaciones y manifiestos de revisión por SHA. | workflow-events.jsonl |
| SC-GOV-008 | sc-06-scientific-synthesis / T08 | Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor. | audit.json |
| SC-GOV-009 | sc-02-runtime-readiness / T09 | tests/test_controlled_daily_v4_reproducibility_artifacts.py; tests/test_controlled_daily_v4_environment_validation.py; docker inspect y pip check. | execution-manifest.json |
| SC-GOV-010 | sc-03-stage-a / T10 | tests/test_controlled_daily_v4_stage_window.py; tests/test_controlled_daily_v4_splits.py; tests/test_controlled_daily_v4_features.py. | temporal-contract-check.json |
| SC-GOV-011 | sc-03-stage-a / T11 | tests/test_controlled_daily_v4_selection.py; tests/test_controlled_daily_v4_freezing.py; tests/test_controlled_daily_v4_stage_a_integration.py; auditar frozen_config.json. | A/gate-review.json |
| SC-GOV-012 | sc-04-stage-b / T12 | tests/test_controlled_daily_v4_stage_b_runner.py; tests/test_controlled_daily_v4_stage_b_integration.py; contrastar decision.json. | B/gate-review.json |
| SC-GOV-013 | sc-04-stage-b / T13 | tests/test_controlled_daily_v4_scientific_closure.py: custodia, concurrencia, reserva antes de validación y recuperación. | B/custody-review.json |
| SC-GOV-014 | sc-05-stage-c / T14 | tests/test_controlled_daily_v4_stage_c_admissibility.py; tests/test_controlled_daily_v4_holdout_ledger.py; tests/test_controlled_daily_v4_stage_c_recovery.py. | C/holdout-review.json |
| SC-GOV-015 | sc-03-stage-a / T15 | tests/test_controlled_daily_v4_bootstrap.py; tests/test_controlled_daily_v4_metrics.py; tests/test_controlled_daily_v4_scientific_closure.py. | statistical-review.json |
| SC-GOV-016 | sc-06-scientific-synthesis / T16 | Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte. | claim-evidence-review.json |
| SC-GOV-017 | sc-02-runtime-readiness / T17 | Revisar manifiesto v4, ADR-0011 y evidencia documental aportada por responsable; no consultar valores reservados. | provenance-assessment.json |
| SC-GOV-018 | sc-02-runtime-readiness / T18 | Ensayo sintético de backup/restauración más tests/test_controlled_daily_v4_stage_c_recovery.py; revisión de rutas por responsable. | recovery-rehearsal.json |
| SC-GOV-019 | sc-02-runtime-readiness / T19 | git diff --check; git diff --cached; git log; registro de checkpoints y estado. | checkpoints.json |
| SC-GOV-020 | sc-02-runtime-readiness / T20 | OpenSpec 1.13.1 validate; python -m unittest discover -s tests -p test_scientific_closure_governance.py. | structural-validation.json |
| SC-GOV-021 | sc-07-aux-regression / T21 | Revisión claims-assessment y fixtures específicos del diseño auxiliary_soil_regression_v1 antes de cualquier ejecución. | auxiliary/R/review.json |
| SC-GOV-022 | sc-08-aux-hitl / T22 | Revisión de fechas de feedback, separación de refit/correcciones, fixtures del diseño auxiliary_hitl_v1. | auxiliary/H/review.json |
| SC-GOV-023 | sc-09-aux-anomalies / T23 | Fixtures de inyección, fit/reserva y matriz de confusión del diseño auxiliary_anomalies_v1. | auxiliary/N/review.json |
| SC-GOV-024 | sc-10-aux-robustness / T24 | Fixtures de grilla causal, perturbaciones y fechas comunes del diseño auxiliary_robustness_v1. | auxiliary/S/review.json |
| SC-GOV-025 | sc-06-scientific-synthesis / T25 | Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado. | scientific-closure-audit.json |

Las comprobaciones de contenido científico son revisiones sustantivas además
de tests: un archivo presente no demuestra que su resultado sea válido.
La ausencia de artefacto produce PENDING/BLOCKED según el momento del gate.
