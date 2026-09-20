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

## Actualización 2026-09-20

Reconciliación posterior al traslado de entradas a Linux y a la campaña
`readiness-resolution-linux-2026-09-20`. Las filas históricas de arriba **no se
borran**: se indica cuáles quedan superadas y por qué. Ninguna entrada de esta
sección acredita ejecución científica; todas son verificaciones de identidad,
existencia y custodia.

Contexto verificado: rama `feat/scientific-closure`, HEAD documental
`dc0d3f5b4dbed235078c1bc93a3c863b6f65d3c6`, upstream
`origin/feat/scientific-closure`, `origin/main`
`9fcbfd9f4dd4860a07f7e99d5b16d849ac81c4af` (tras `git fetch` del 2026-09-20).

| ID | Estado 2026-09-20 | Hecho verificado | Efecto sobre la fila histórica |
| --- | --- | --- | --- |
| EV-12 | `SUPERSEDED_BY_MIGRATION` | Los dos CSV de Pergamino están disponibles en Linux, trasladados byte a byte desde `/mnt/c` (montado `ro`) y auditados en `input-migration-linux-2026-09-20/audit-final.json` (PASS limitado al paquete de traslado) | La fila histórica describía la ruta Windows no accedida; queda superada como estado, se conserva como origen documental |
| EV-17 | `SUPERSEDED_BY_MIGRATION` | Las entradas ya no están ausentes: residen en `/home/gus/scientific-closure-inputs/migration-20260920/AAI_Hydric_Stress_external_data/raw/` | `ABSENT` deja de describir el estado actual; la ruta `/home/gus/work/AAI_Hydric_Stress_external_data/raw` sigue sin existir |
| EV-14 | `PARTIALLY_SATISFIED` | Existe una copia lógica en `/home/gus/scientific-closure-backup/migration-20260920/...` con hashes idénticos y un ensayo de restauración con fixture técnico (exit 0). **No hay independencia física**: primaria, copia y ensayo comparten el dispositivo 2128 (`/dev/sdf`, ext4) | La fila histórica `MISSING` se matiza, no se cancela: el requisito de almacenamiento independiente sigue incumplido |
| EV-16 | `STILL_ABSENT` | `/home/gus/work/AAI_Hydric_Stress_scientific_runtime` no existe. Se creó una raíz **nueva y distinta**, `/home/gus/scientific-closure-runtime/` (`env/`, `evidence/`, `ledger/`, `backups/`, `logs/`), vacía de evidencia científica | La fila histórica sigue vigente. La raíz nueva no reemplaza ni acredita custodia del runtime original |
| EV-07 | `STILL_NOT_ACCESSED` | No se accedió a la ruta Windows de evidencia. La raíz Linux nueva tiene `evidence/` vacío | Sin cambio |
| EV-08 | `STILL_NOT_INITIALISED` | El ledger definitivo **no** está inicializado. `/home/gus/scientific-closure-runtime/ledger/` está vacío; el holdout 2024–2025 permanece cerrado y ningún valor reservado fue leído | Sin cambio sustantivo; se confirma desde Linux |
| EV-06 | `IMAGE_STILL_UNINSPECTED` | La imagen aprobada `sha256:55bc923e…b297af` no fue inspeccionada, exportada, importada ni reconstruida: el daemon Docker es inalcanzable (integración WSL deshabilitada; sockets de Docker Desktop deniegan `connect()` a uid 1000; `sudo` exige autenticación interactiva; no hay podman/nerdctl/buildah) | La fila histórica sigue vigente: la identidad de imagen permanece sin verificar |
| EV-10 | `PROVENANCE_VERIFIED_DATE_UNKNOWN` | Los hashes del manifiesto coinciden con los archivos trasladados y la validación de procedencia del runner terminó exit 0 (`Provenance OK`). Admisibilidad decidida como `ADMISSIBLE_WITH_EXPLICIT_LIMITATIONS` | La fila histórica queda parcialmente superada: la licencia se resolvió por decisión explícita; la fecha efectiva de adquisición y `downloaded_service_version` de NASA POWER siguen `DESCONOCIDO` y no se infieren |
| EV-11 | `STILL_TEMPLATE` | No existe manifiesto de campaña ejecutada. `readiness-resolution-linux-2026-09-20/execution-manifest.json` registra identidad *que se congelaría si hubiera autorización*, con `stage_A/B/C` vacíos y `ledger_initialised: false` | Sin cambio: sigue sin ser identidad de campaña |
| EV-04 | `IDENTITY_CONFIRMED` | `src/`, `docker/` y `pyproject.toml` en HEAD son byte-idénticos al commit ejecutable declarado `214735e42ee04f018156cd630591e798aadd8bf3` (`git diff --stat` vacío); entre ambos commits solo se agregaron `tests/test_scientific_closure_checker.py` y `tests/test_scientific_closure_governance.py` | Refuerza la fila histórica; la eficacia científica sigue `PENDING` |

Entradas nuevas de esta actualización:

| ID | Ubicación | Estado, procedencia e inspección | Uso / faltante |
| --- | --- | --- | --- |
| EV-19 | `/home/gus/scientific-closure-inputs/migration-20260920/AAI_Hydric_Stress_external_data/raw/` | `PRESENT_HASH_VERIFIED`; `pergamino_era5land_soil_hourly_2015_2025.csv` SHA-256 `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` (3.954.003 bytes); `pergamino_nasa_power_daily_2015_2025.csv` SHA-256 `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` (127.568 bytes) | Entradas primarias para una campaña futura autorizada; valores **no** analizados |
| EV-20 | `/home/gus/scientific-closure-backup/migration-20260920/AAI_Hydric_Stress_external_data/raw/` | `LOGICAL_SECOND_COPY_SAME_DEVICE`; hashes idénticos a EV-19, recalculados | Copia lógica; **no** acredita respaldo independiente |
| EV-21 | `/home/gus/scientific-closure-runtime/env/venv-v4` | `RECONSTRUCTED_ENVIRONMENT_NOT_THE_HISTORIC_IMAGE`; Python 3.11.16; 23 paquetes coincidentes con el pip-freeze histórico (numpy 2.4.6, pandas 3.0.5, scikit-learn 1.9.0, scipy 1.17.1, pyarrow 25.0.1, joblib 1.6.0, threadpoolctl 3.6.0, pytest 9.1.1, ruff 0.16.6, black 26.5.1) | Entorno de verificación estructural; **no** es la imagen aprobada ni se afirma equivalencia |
| EV-22 | `scripts/readonly_role_sandbox.sh`; `scripts/verify_readonly_sandbox.sh` | `PRESENT_VERIFIED_PASS`; bubblewrap 0.11.1; escritura al repositorio y a `$HOME` falla con EROFS, sin red, `/tmp` efímero, sin fugas | Enforcement de solo lectura por rol. Limitación: el harness no coloca el proceso del subagente dentro del sandbox |
| EV-23 | `openspec/scientific-closure/readiness-resolution-linux-2026-09-20/` | `INSPECTED_DOCUMENT`; registros de la campaña de resolución de readiness | Fuente de los estados de esta actualización; **no** es auditoría independiente ni PASS de `sc-02` |

Limitaciones explícitas de esta actualización: ninguna fila acredita ejecución
de A, B o C; la condición 4 de ADR-0011 permanece `NOT_SATISFIED` (el protocolo
detallado en `origin/main` es una versión anterior y `214735e` no es ancestro de
`origin/main`); no existe auditoría independiente sobre los registros de
`readiness-resolution-linux-2026-09-20`. Se mantiene la regla histórica: la
ausencia no demuestra inexistencia, y ningún campo `DESCONOCIDO` se completa por
inferencia.
