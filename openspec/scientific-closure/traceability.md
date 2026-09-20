# Matriz requisito → tarea → prueba → evidencia

Fuente estructurada: requirements.json. Criterios completos: spec científica.
Estado histórico de este encabezado (2026-09-19): declaraba que «cada fila
tiene estado PENDING». Esa afirmación es **incorrecta desde el 2026-09-20**
para SC-GOV-001/003/004/005, cuyos artefactos existen en
`openspec/changes/sc-01-evidence-scope/` y fueron auditados. El estado real por
requisito figura en la sección «Estado por requisito — 2026-09-20». Se mantiene
la regla de fondo: no atribuir resultados a artefactos meramente esperados.
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

## Estado por requisito — 2026-09-20

Vocabulario cerrado, sin otros valores: `PASS`, `PASS_WITH_LIMITATIONS`,
`BLOCKED`, `NOT_APPLICABLE`.

**`BLOCKED` no es un estado terminal.** El checker normativo del repositorio
(`scripts/check_scientific_closure.py`) considera terminales únicamente `PASS`
y `NOT_APPLICABLE`, y su grafo de transiciones admite `BLOCKED → APPROVED`. Un
requisito `BLOCKED` está **irresuelto**, a la espera de un insumo externo. Esta
tabla no lo convierte en resuelto: lo declara como el estado en que esta sesión
lo deja, que es cosa distinta. Los identificadores de esta tabla se
escriben en negrita (`**SC-GOV-0NN**`) para que la fila normativa de cada
requisito siga siendo única en la matriz de arriba.

Alcance de esta columna: refleja el **estado de la evidencia existente**, no un
PASS de gate ni de auditoría final. Ningún estado de esta tabla autoriza
ejecutar A, B o C, inicializar el ledger ni abrir el holdout. Fuentes leídas:
`openspec/scientific-closure/changes.json`,
`openspec/scientific-closure/readiness-resolution-linux-2026-09-20/*.json`,
`openspec/scientific-closure/input-migration-linux-2026-09-20/*.json`,
`openspec/scientific-closure/claims.md` y los artefactos de
`openspec/changes/sc-01-evidence-scope/`. Ante duda se registra `BLOCKED` con la
razón explícita.

Estado de los changes en `changes.json` al 2026-09-20: `sc-01-evidence-scope`
`PASS` (auditoría independiente, veredicto PASS sobre el snapshot `a0d8bf7`,
alcance documental); `sc-02` a `sc-10` `BLOCKED`.

| Requisito | Estado 2026-09-20 | Base verificada y limitación |
| --- | --- | --- |
| **SC-GOV-001** | PASS_WITH_LIMITATIONS | `session-identity.json` existe y fue auditado PASS dentro de `sc-01`. Limitación: registra el commit documental `a70022d3…` y el snapshot auditado es `a0d8bf7`; el HEAD vigente es `dc0d3f5b4dbed235078c1bc93a3c863b6f65d3c6`, por lo que la identidad registrada no describe el estado actual |
| **SC-GOV-002** | BLOCKED | `readiness-resolution-linux-2026-09-20/authorizations.json` registra `AUTH-ABC-2026-09-20` como `GRANTED_BUT_NOT_EXERCISABLE`. Condición 4 de ADR-0011 `NOT_SATISFIED`: el ADR está mergeado byte a byte en `origin/main` (`9fcbfd9f…`), pero el protocolo detallado allí es una versión anterior a la que le falta la sección titulada «Condiciones de interpretación y soporte previas a ejecución» (numerada «16» en la rama, duplicando a «16. Provenance», que sí está en `main`). `214735e…` tampoco es ancestro de `origin/main`, lo que es contexto del merge pendiente y no parte del texto de la condición 4 |
| **SC-GOV-003** | PASS_WITH_LIMITATIONS | `preservation.json` existe y fue auditado PASS en `sc-01`. Limitación: el diff acreditado tiene por base `a70022d3…`; no cubre los commits posteriores hasta `dc0d3f5` |
| **SC-GOV-004** | PASS_WITH_LIMITATIONS | `inventory.json` existe y fue auditado PASS en `sc-01`. Limitación: varias entradas quedaron superadas por la migración de entradas a Linux; la reconciliación está en `inventory.md`, sección «Actualización 2026-09-20», y no ha sido auditada de forma independiente |
| **SC-GOV-005** | PASS_WITH_LIMITATIONS | `claims-assessment.json` existe y fue auditado PASS en `sc-01`, con alcance explícitamente documental. Limitación: `claims.md` declara que la decisión vigente R/H/N/S «permanece pendiente de crítica y auditoría independiente» |
| **SC-GOV-006** | PASS_WITH_LIMITATIONS | `readiness-resolution-linux-2026-09-20/agent-capabilities.json` registra `PASS_WITH_LIMITATIONS`: existe enforcement reproducible (`scripts/readonly_role_sandbox.sh`, bubblewrap 0.11.1; escritura al repositorio y a `$HOME` con EROFS, sin red, `/tmp` y `/dev` efímeros), cubierto por 10 pruebas. **La auditoría independiente derrotó la primera versión de este mecanismo** (hallazgo A-01): ejecutó `/mnt/c/Windows/System32/curl.exe` desde dentro del sandbox y obtuvo HTTP 200, y creó un archivo en la raíz del repositorio vía `\\wsl.localhost`. Los binarios PE de Windows corren en el host, fuera de todo namespace de Linux. El escape fue reproducido, cerrado (`/mnt` vaciado, ayudante binfmt neutralizado, variables WSL limpiadas) y cubierto por una prueba de regresión. Limitaciones: la afirmación vale **para procesos Linux** y para la vía de interop conocida, no como aislamiento absoluto; el harness no coloca el proceso del subagente dentro del sandbox; y los perfiles `.codex/agents` no son cargables en este runtime, con sustitución de modelos declarada |
| **SC-GOV-007** | PASS_WITH_LIMITATIONS | El artefacto esperado existe: `readiness-resolution-linux-2026-09-20/workflow-events.jsonl` (17 eventos: identidad de sesión, despacho y reporte de cada rol, asignaciones de escritor exclusivas y disjuntas, validaciones con exit code, evaluaciones de gate, ciclo de corrección y la constancia de que ningún `state_event` fue fabricado). Los eventos de despacho de lector incluyen un `review_manifest` con el commit exacto del snapshot revisado, su base y el estado del árbol. Limitaciones: (a) la primera versión de este registro carecía de esos manifiestos por SHA y el estado se elevó antes de tenerlos — corregido tras el hallazgo F-02 del crítico; (b) el manifiesto por SHA identifica el snapshot, y el detalle por archivo vive en `evidence-manifest.json`, no en el propio `jsonl`; (c) cubre esta campaña de readiness: no hay eventos de A/B/C porque no existieron |
| **SC-GOV-008** | BLOCKED | `sc-06-scientific-synthesis` está `BLOCKED` y su gate exige una etapa terminal A/B/C auditada. `audit.json` no existe. El gate no es alcanzable mientras SC-GOV-002 y SC-GOV-009 sigan `BLOCKED` |
| **SC-GOV-009** | BLOCKED | `execution-manifest.json` existe pero declara `container_image.status: NOT_AVAILABLE` y `ledger_initialised: false`. La imagen aprobada `sha256:55bc923e…b297af` no fue inspeccionada: el daemon Docker es inalcanzable. Hecho favorable verificado: `src/`, `docker/` y `pyproject.toml` en HEAD son byte-idénticos a `214735e…`. Aun así la identidad ejecutable no puede certificarse sin la imagen |
| **SC-GOV-010** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `temporal-contract-check.json` no existe; el gate depende de `sc-02` PASS, que no se alcanzó |
| **SC-GOV-011** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `A/gate-review.json` no existe; A no fue ejecutada |
| **SC-GOV-012** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/gate-review.json` no existe; B no fue ejecutada |
| **SC-GOV-013** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/custody-review.json` no existe; no hay registro de custodia ni intento reservado |
| **SC-GOV-014** | BLOCKED | `sc-05-stage-c` `BLOCKED`; `C/holdout-review.json` no existe; el ledger no está inicializado y el holdout 2024–2025 permanece cerrado |
| **SC-GOV-015** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `statistical-review.json` no existe; no hay métricas ni bootstrap de campaña |
| **SC-GOV-016** | BLOCKED | Existe una síntesis: `docs/research/scientific-closure-synthesis-2026-09-20.md`, que distingue hecho, resultado, inferencia y limitación y declara que A/B/C no se ejecutaron. Lo que **no** existe es el artefacto exigido `claim-evidence-review.json`, es decir la revisión frase a frase **independiente** de esa síntesis contra `claims.md`. `sc-06-scientific-synthesis` sigue `BLOCKED`. La síntesis fue sometida a crítica adversarial independiente (hallazgos F-01, F-09 y N-06, corregidos), lo que no sustituye ese artefacto |
| **SC-GOV-017** | PASS_WITH_LIMITATIONS | `readiness-resolution-linux-2026-09-20/provenance-and-licence-assessment.json` decide `ADMISSIBLE_WITH_EXPLICIT_LIMITATIONS` (GD-13) y la validación de procedencia del runner terminó exit 0. Limitaciones preservadas: la fecha efectiva de adquisición de ambos archivos es `DESCONOCIDO` y no se infiere de mtimes; los términos vigentes al instante de adquisición no se verificaron; `downloaded_service_version` de NASA POWER sigue `DESCONOCIDO` |
| **SC-GOV-018** | BLOCKED | `input-migration-linux-2026-09-20/recovery-rehearsal.json` y `storage-and-backup-independence.json` acreditan copia lógica con hashes idénticos y ensayo de restauración con fixture técnico (exit 0), pero `physical_independence: NOT_ACHIEVED`: primaria, copia y ensayo comparten el dispositivo 2128 (`/dev/sdf`, ext4). Montar `/dev/sdd` requiere root y `sudo` exige autenticación interactiva. El requisito de segunda copia independiente sigue incumplido |
| **SC-GOV-019** | PASS_WITH_LIMITATIONS | El artefacto esperado existe: `readiness-resolution-linux-2026-09-20/checkpoints.json`, con todos los commits de la sesión (SHA, propósito, archivos, revisión de diff) sobre la base `dc0d3f5`, salvo el commit final, que un registro no puede contener porque introduce el propio archivo; ese límite queda declarado en `self_reference_limit`. `git diff --check` exit 0; rutas explícitas en cada `git add`, nunca `git add -A`. Limitación: un checkpoint no es aceptación ni PASS de auditoría; `sc-02` a `sc-10` siguen `BLOCKED` |
| **SC-GOV-020** | PASS_WITH_LIMITATIONS | `structural-validation.json`: 11/11 ítems de `scientific-closure` pasan `@fission-ai/openspec@1.13.1 validate --strict`; `scripts/check_scientific_closure.py` exit 0 con `PASS (estructura; runtime no verificado)`. Limitaciones: `validate --all --strict` termina 1 por 42 changes preexistentes de otras capacidades, fuera de alcance y no modificados; la validación corrió en el entorno reconstruido, no en la imagen aprobada; el propio checker declara que el runtime no está verificado |
| **SC-GOV-021** | NOT_APPLICABLE | `claims.md` fija la decisión vigente previa a ejecución: R `NOT_REQUIRED` (CL-01, CL-05, CL-10). `sc-07-aux-regression` es `conditional: true` con gate «R REQUIRED». Limitación: la propia `claims.md` declara esa decisión pendiente de crítica y auditoría independiente; si se revirtiera a `REQUIRED`, el estado pasaría a `BLOCKED` |
| **SC-GOV-022** | BLOCKED | `claims.md` fija H `REQUIRED` (CL-06, CL-10). `sc-08-aux-hitl` está `BLOCKED` y su gate exige `sc-01` y `sc-02` PASS; `sc-02` no lo está. `auxiliary/H/review.json` no existe |
| **SC-GOV-023** | NOT_APPLICABLE | `claims.md` fija N `NOT_REQUIRED` (CL-04, CL-07, CL-10) y prohíbe afirmar detección reservada. `sc-09-aux-anomalies` es `conditional: true` con gate «N REQUIRED». Misma limitación de reversibilidad que SC-GOV-021 |
| **SC-GOV-024** | NOT_APPLICABLE | `claims.md` fija S `NOT_REQUIRED` bajo el límite aprobado (CL-08, CL-10). `sc-10-aux-robustness` es `conditional: true` con gate «S REQUIRED». Misma limitación de reversibilidad que SC-GOV-021 |
| **SC-GOV-025** | BLOCKED | `sc-06-scientific-synthesis` `BLOCKED`; `scientific-closure-audit.json` no existe. La auditoría final requisito por requisito no es alcanzable sin etapa terminal auditada ni suficiencia científica evaluable |

Resumen mecánico: PASS 0; PASS_WITH_LIMITATIONS 9 (SC-GOV-001, 003, 004, 005,
006, 007, 017, 019, 020); BLOCKED 13 (SC-GOV-002, 008, 009, 010, 011, 012, 013,
014, 015, 016, 018, 022, 025); NOT_APPLICABLE 3 (SC-GOV-021, 023, 024). Total 25.

**Trece de veinticinco requisitos quedan irresueltos.** `BLOCKED` describe
exactamente eso. Esta tabla no debe leerse como una matriz completa: debe
leerse como el registro de qué se resolvió y qué no, y por qué.

Sobre los tres `NOT_APPLICABLE`: se refieren al **requisito**, cuya activación
está condicionada a que R/N/S sean `REQUIRED`, y no al **change** `sc-07`,
`sc-09` y `sc-10`, que permanecen `BLOCKED` en `changes.json` porque su cierre
individual exige además `sc-02` PASS. Ambos estados conviven sin contradicción
y se registran por separado a propósito.

Distinción explícita: los estados `PASS_WITH_LIMITATIONS` de esta tabla derivan
de **evidencia documental y de verificaciones técnicas**, nunca de ejecución
científica. No existe ninguna corrida de A, B o C, ninguna métrica, ninguna
predicción ni ningún valor reservado leído en esta preparación. Los registros de
`readiness-resolution-linux-2026-09-20` **no** han recibido crítica ni auditoría
independiente al momento de escribir esta sección.
