# Tareas de sc-01-evidence-scope

Todas pendientes; la especificación no acredita ejecución.

- [ ] T01 (SC-GOV-001) Identidad y aislamiento. Comprobar: git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --porcelain=v1 --untracked-files=all Evidencia: session-identity.json.
- [ ] T03 (SC-GOV-003) Preservación. Comprobar: git diff --name-status BASE..HEAD; comparar hashes de archivos históricos sin analizar sus resultados. Evidencia: preservation.json.
- [ ] T04 (SC-GOV-004) Inventario con procedencia. Comprobar: Contrastar inventario con rutas y documentación permitidas; jamás llenar resultados por inferencia. Evidencia: inventory.json.
- [ ] T05 (SC-GOV-005) Alcance de afirmaciones. Comprobar: Auditoría de claims.md contra project.md, ADR-0009/0010/0011 y decisiones de cierre. Evidencia: claims-assessment.json.
- [ ] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [ ] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [ ] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [ ] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [ ] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [ ] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.
