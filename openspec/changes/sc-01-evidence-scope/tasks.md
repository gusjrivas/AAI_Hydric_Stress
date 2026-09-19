# Tareas de sc-01-evidence-scope

Cierre documental con PASS independiente sobre snapshot `a0d8bf7412bbb68448cf3bcec262097cd1571ab3`.
Evidencia: [dictamen](../../scientific-closure/readiness-linux-2026-09-19/audit-final.json).
SC-GOV-001/003/004/005 quedan satisfechos solo dentro de sc-01; readiness integral BLOCKED.
Los casilleros acreditan este alcance documental, no ejecución científica ni aislamiento efectivo de roles.

- [x] T01 (SC-GOV-001) Identidad y aislamiento. Comprobar: git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --porcelain=v1 --untracked-files=all Evidencia: session-identity.json.
- [x] T03 (SC-GOV-003) Preservación. Comprobar: git diff --name-status BASE..HEAD; comparar hashes de archivos históricos sin analizar sus resultados. Evidencia: preservation.json.
- [x] T04 (SC-GOV-004) Inventario con procedencia. Comprobar: Contrastar inventario con rutas y documentación permitidas; jamás llenar resultados por inferencia. Evidencia: inventory.json.
- [x] T05 (SC-GOV-005) Alcance de afirmaciones. Comprobar: Auditoría de claims.md contra project.md, ADR-0009/0010/0011 y decisiones de cierre. Evidencia: claims-assessment.json.
- [x] REVIEW-1 Explorador reúne evidencia antes de implementar; registrar snapshot.
- [x] REVIEW-2 Implementador acotado ejecuta checks y conserva evidencia.
- [x] REVIEW-3 evidence_checker contrasta integridad y formatos, sin juicio científico.
- [x] REVIEW-4 scientific_critic intenta refutar cada criterio; corregir hallazgos y repetir.
- [x] REVIEW-5 scientific_auditor independiente emite PASS/FAIL/BLOCKED sobre snapshot.
- [x] CLOSE Solo con PASS, registrar SHA, evidencia, alcance y checkpoint; sin push.
