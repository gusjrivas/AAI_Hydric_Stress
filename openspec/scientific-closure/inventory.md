# Inventario de evidencia y faltantes

Inspección Linux: 2026-09-19. Commit documental de entrada:
`a70022d3dd84495421c35186ec91abf765828e6c`. Inventario histórico inicial:
2026-09-18 sobre `ba539bd2f17f8a05da41f6ffff32d730a0152f07`.
No se abrieron datasets, holdouts ni valores reservados; no se accedió a `/mnt/c`.
Las referencias Windows se conservan como historia documental, no como estado
revalidado desde Linux.

| ID | Ubicación | Estado, procedencia e inspección | Uso / faltante |
| --- | --- | --- | --- |
| EV-01 | `docs/research/reference-v3-formal-results.json`; `reference-v3-formal-table.md` | `REFERENCED`; existen, 1.561.988/819 bytes, SHA-256 `b876d21c…b45a` / `29639c48…d47c`; hash verificado sin reanalizar resultados | CL-04 y límites CL-08; evidencia histórica inmutable, no resultado nuevo |
| EV-02 | `docs/research/scientific-closure-preexecution-audit.md` | `INSPECTED_DOCUMENT`; 20.855 bytes, SHA-256 `1f42f040…c944`; auditoría previa | Evidencia técnica referenciada; sus conteos no se reejecutan aquí |
| EV-03 | `docs/research/scientific-closure-decisions.md` | `INSPECTED_DOCUMENT`; 11.254 bytes, SHA-256 `92dc7ae4…74b0`; diseños congelados A/B/C y R/H/N/S | Diseños preejecución, no resultados |
| EV-04 | `src/experiment_runner/controlled_daily_v4/` | `METADATA_HASHED`; 28 archivos públicos; digest del listado ordenado de SHA-256 `1353ac16…0fed` | Implementación disponible; eficacia real `PENDING` |
| EV-05 | `tests/test_controlled_daily_v4_*.py` | `METADATA_HASHED`; 33 archivos; digest del listado ordenado de SHA-256 `8562c5df…fc4d` | Fixtures y evidencia técnica, nunca científica |
| EV-06 | `docker/experiment-v4/constraints.txt`; `build.ps1` | `REFERENCED`; identidad histórica de imagen en auditoría previa; existencia local de imagen no revalidada | Imagen ejecutable futura debe verificarse en readiness |
| EV-07 | `C:\Repo\AAI_Hydric_Stress_scientific_runtime\evidence` | `HISTORICAL_REFERENCE_NOT_ACCESSED`; el inventario 2026-09-18 la reportó vacía | No prueba estado actual ni custodia desde Linux |
| EV-08 | `C:\Repo\AAI_Hydric_Stress_scientific_runtime\ledger` | `HISTORICAL_REFERENCE_NOT_ACCESSED`; el inventario 2026-09-18 la reportó vacía | Ledger definitivo no inicializado en esta preparación |
| EV-09 | `C:\Repo\AAI_Hydric_Stress_scientific_runtime\validation` | `HISTORICAL_REFERENCE_NOT_ACCESSED`; existencia histórica referenciada | Logs técnicos previos no revalidados |
| EV-10 | `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` | `INSPECTED_DOCUMENT`; 17.983 bytes, SHA-256 `c07a9175…a83`; plantilla `PROTOCOL_ONLY` | Adquisición efectiva/versiones y licencia NASA siguen pendientes; no inferidas |
| EV-11 | `docs/research/scientific-closure-execution.template.json` | `REFERENCED`; plantilla `NOT_AUTHORIZED_NOT_EXECUTED` | No es manifiesto ejecutado ni identidad de campaña |
| EV-12 | `C:\Repo\AAI_Hydric_Stress_external_data\raw` | `HISTORICAL_REFERENCE_NOT_ACCESSED`; datos no abiertos ni hasheados | Fuentes/hashes efectivos siguen faltantes |
| EV-13 | R/H/N/S en decisiones preejecución | `REFERENCED`; diseños preservados, sin resultados nuevos | R/N/S `NOT_REQUIRED` bajo límites aprobados; H `REQUIRED` y científico `PENDING` |
| EV-14 | Backups independientes | `MISSING`; no acreditados | Segunda copia y ensayo con fixtures pendientes |
| EV-15 | `openspec/project.md`; spec `scientific-closure` | `INSPECTED_DOCUMENT`; 6.663/26.615 bytes, SHA-256 `34e40dbf…1fb0` / `37716bc0…f57` | Alcance, requisitos y límites HU7/HU8 |
| EV-16 | `/home/gus/work/AAI_Hydric_Stress_scientific_runtime` | `ABSENT`; comprobación de existencia Linux 2026-09-19, sin crear directorios | Runtime, evidence, ledger y backups originales no disponibles aquí |
| EV-17 | `/home/gus/work/AAI_Hydric_Stress_external_data/raw` | `ABSENT`; comprobación de existencia Linux 2026-09-19 | Raw original no disponible; no sustituir por descargas nuevas |
| EV-18 | `openspec/scientific-closure/readiness-linux-2026-09-19/scope-exploration.json` | `INSPECTED_DOCUMENT`; informe exacto del explorador y advisory crítico | Fuente de evaluación CL-01..10; no auditoría ni PASS |

Los SHA abreviados se expanden en `openspec/changes/sc-01-evidence-scope/inventory.json`.
La ausencia Linux no demuestra inexistencia histórica y no se completa por
inferencia. Ante registro faltante, movido o contradicción de custodia durante
una campaña, el período se trata como posiblemente abierto y se bloquea; no se
crea otra raíz para aparentar primer intento.
