# Inventario inicial de evidencia y faltantes

Fecha de inspección: 2026-09-18. Base documental:
ba539bd2f17f8a05da41f6ffff32d730a0152f07.
No se han abierto datasets ni valores reservados. La evidencia histórica aquí
referenciada conserva su fuente y no se reinterpreta.

| ID | Ubicación | Estado y procedencia | Uso / faltante |
| --- | --- | --- | --- |
| EV-01 | docs/research/reference-v3-formal-results.json y reference-v3-formal-table.md | Referenciadas por spec HU7 y protocolo v3; contenido no reanalizado | CL-04, histórica inmutable; verificar hashes sin recalcular |
| EV-02 | docs/research/scientific-closure-preexecution-audit.md | Leída; auditoría previa, no validación realizada en esta sesión | Reporta 483 passed/3 skipped y 53 aceptación; evidencia técnica |
| EV-03 | docs/research/scientific-closure-decisions.md | Leída, diseños congelados y corrección matemática MCC | A/B/C y diseños R/H/N/S; no resultados |
| EV-04 | src/experiment_runner/controlled_daily_v4/ | Runners/CLI/custodia inspeccionados por código y símbolos | Implementación disponible; eficacia real pendiente |
| EV-05 | tests/test_controlled_daily_v4_*.py | Suite inventariada, tests de cierre inspeccionados | Fixtures, no datos científicos |
| EV-06 | docker/experiment-v4/constraints.txt y build.ps1 | Leídos; imagen local 55bc923efac0 listada | Identidad completa de imagen reportada por auditoría previa; recontrastar en readiness |
| EV-07 | C:\Repo\AAI_Hydric_Stress_scientific_runtime\evidence | Directorio listado vacío en esta sesión | A/B/C y gobernanza científica faltantes |
| EV-08 | C:\Repo\AAI_Hydric_Stress_scientific_runtime\ledger | Directorio listado vacío en esta sesión | No inicializar todavía; ausencia observada no certifica actividad de terceros |
| EV-09 | C:\Repo\AAI_Hydric_Stress_scientific_runtime\validation | Existencia del directorio observada; archivos referenciados por EV-02 | Logs técnicos previos no revalidados |
| EV-10 | docs/research/controlled-daily-v4-external-pergamino-manifest.yaml | Leído en esta sesión; plantilla PROTOCOL_ONLY, sin resultados; procedencia histórica pendiente | Adquisición efectiva/versiones/licencia NASA pendientes según EV-02 |
| EV-11 | docs/research/scientific-closure-execution.template.json | Leída; plantilla NOT_AUTHORIZED_NOT_EXECUTED | Identidad y autorización futuras; no manifiesto ejecutado |
| EV-12 | C:\Repo\AAI_Hydric_Stress_external_data\raw | Ubicación referenciada, datos no abiertos ni hasheados aquí | Fuentes/hashes esperados en manifiesto; verificación solo al autorizar |
| EV-13 | R/H/N/S en scientific-closure-decisions.md | Diseño disponible, runners/evidencia pendientes según EV-02 | Necesidad condicional por CL-05..08 |
| EV-14 | Backups independientes | No acreditados; solo existe directorio local backups | Ensayo con fixtures y segunda copia pendientes |
| EV-15 | openspec/project.md y spec experiment-runner | Leídas | Alcance y límites HU7/HU8; suficiencia global pendiente |

No certificar apertura histórica solo por directorios vacíos. Ante registro
faltante, movido o contradicción de custodia durante campaña, tratar período como
posiblemente abierto y bloquear; no crear otra raíz para aparentar primer intento.
