# Matriz requisito → tarea → prueba → evidencia

Fuente estructurada: requirements.json. Criterios completos: spec científica.
Estado histórico de este encabezado (2026-09-19): declaraba que «cada fila
tiene estado PENDING». Esa afirmación es **incorrecta desde el 2026-09-20**
para SC-GOV-001/003/004/005, cuyos artefactos existen en
`openspec/changes/sc-01-evidence-scope/` y fueron auditados. El estado real por
requisito figura en la sección «Estado por requisito», reescrita el 2026-09-20
por la sesión de verificación de cierre; sus estados prevalecen sobre cualquier
lectura de este encabezado. Se mantiene
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

## Estado por requisito — 2026-09-21 (CAMPAÑA A → B → C EJECUTADA)

Esta sección **prevalece** sobre la de 2026-09-20, que se conserva íntegra abajo
como registro histórico. La campaña se ejecutó el 2026-09-21 y **el holdout
2024–2025 fue abierto**, de modo que varias afirmaciones de la sección histórica
—«A no fue ejecutada», «B no fue ejecutada», «el ledger no está inicializado»,
«el holdout permanece cerrado. Ningún valor reservado fue leído»— **son hoy
falsas**. No se reescriben allí; se corrigen aquí.

| Requisito | Estado | Base |
| --- | --- | --- |
| **SC-GOV-001** | PASS | Identidad de sesión verificada directamente (rama, HEAD, árbol limpio, remoto). |
| **SC-GOV-002** | PASS | Autorización explícita del responsable para readiness, respaldo y campaña A→B→C. |
| **SC-GOV-003** | PASS | v3, UI y `src/` intactos; `git diff origin/main` vacío en `frontend/` y `src/`. |
| **SC-GOV-004** | PASS | Inventario de evidencia reproducible con hashes y respaldo externo verificado. |
| **SC-GOV-005** | PASS_WITH_LIMITATIONS | Afirmaciones trazadas; CL-06 (H) queda sin evidencia y CL-10 no es alcanzable hoy. |
| **SC-GOV-006** | PASS_WITH_LIMITATIONS | Revisión independiente efectiva mediante tres auditores en sesiones separadas. **Sustitución declarada:** no se usaron los cinco perfiles `.codex`; el runtime efectivo de esta sesión es Claude Opus 5 con subagentes independientes. Se documenta la sustitución, no se la presenta como equivalencia. |
| **SC-GOV-007** | PASS | `changes.json` con transiciones, aprobación y auditoría por cada change ejecutado. |
| **SC-GOV-008** | PASS | Auditores independientes distintos del implementador en A, B y cierre final. |
| **SC-GOV-009** | PASS | Identidad ejecutable `214735e` (ancestro de HEAD) frente a documental `37eed42`; delta de 7 archivos clasificado sin efecto numérico y verificado por dos auditores. Resuelve GD-25/RK-09. |
| **SC-GOV-010** | PASS | `sc-03-stage-a/temporal-contract-check.json`: fronteras 2015–2022 / 2023 / 2024–2025, contrato de 8 features idéntico en las tres etapas, sin fuga. |
| **SC-GOV-011** | PASS | `sc-03-stage-a/gate-review.json`: GA satisfecho; `SIN_GANADOR_ESTABLE` con desempate de simplicidad; soporte 3/3 folds y 5000/5000 réplicas. |
| **SC-GOV-012** | PASS | `sc-04-stage-b/gate-review.json`: GB satisfecho; `CANDIDATE_VALIDATED` por **no inferioridad** (el intervalo incluye el cero). |
| **SC-GOV-013** | PASS | `sc-04-stage-b/custody-review.json`: intento único, reserva previa a la lectura de valores, sin recuperación ni repetición. |
| **SC-GOV-014** | PASS | `sc-05-stage-c/holdout-review.json`: GC satisfecho por integridad y unicidad; apertura única, nominal e irreversible; ledger `CONFIRMADA`. |
| **SC-GOV-015** | PASS_WITH_LIMITATIONS | `sc-03-stage-a/statistical-review.json`: bootstrap reproducido de forma independiente en A, B y C. Salvedad declarada: intervalos percentiles sin corrección por multiplicidad ni calibración de cobertura; ~24 unidades efectivas en C. |
| **SC-GOV-016** | PASS_WITH_LIMITATIONS | Revisión de sobreinterpretación superada; se añadieron calibración degradada y deriva de prevalencia tras la auditoría final. |
| **SC-GOV-017** | PASS_WITH_LIMITATIONS | Procedencia verificada por hash. **Condición 2 de ADR-0011 (licencia NASA POWER) sigue `PENDING_CONFIRMATION`**, aceptada como limitación vía GD-13. |
| **SC-GOV-018** | PASS | Respaldo externo en disco USB físicamente independiente, con manifiesto, inventario, hashes y ensayo de recuperación PASS en sus cuatro componentes. |
| **SC-GOV-019** | PASS_WITH_LIMITATIONS | Trazabilidad de commits y push registrada; RK-14 ratificado en ADR-0011. **Limitación (hallazgo EV-03):** la ratificación **reconoce y autoriza conservar** la desviación, pero el propio ADR-0011 dice que **«no subsana el incumplimiento: RK-14 permanece registrado como desviación reconocida»**. No existe artefacto que lo cure, de modo que este requisito **no** puede declararse PASS pleno. |
| **SC-GOV-020** | PASS | Checker exit 0, pruebas de gobernanza 15/15, suite v4 488 passed / 3 skipped (checkout) y 483 passed / 3 skipped (imagen). Archivado en `evidence/governance/closure-campaign-2026-09-21/validation/validation-record.json` tras el hallazgo EV-04. |
| **SC-GOV-021** | BLOCKED | R `NOT_REQUIRED`, pero la decisión de suficiencia GD-12 sigue sin crítica ni auditoría independiente. |
| **SC-GOV-022** | BLOCKED | **H (HITL) está declarado `REQUIRED` y no tiene runner implementado ni evidencia alguna.** No se ejecutó. |
| **SC-GOV-023** | BLOCKED | N `NOT_REQUIRED`, misma razón que SC-GOV-021. |
| **SC-GOV-024** | BLOCKED | S `NOT_REQUIRED`, misma razón que SC-GOV-021. |
| **SC-GOV-025** | BLOCKED | **Gate GF no alcanzable hoy:** el plan exige todos los `REQUIRED` con PASS y H no lo está. |

Resumen: **PASS 14, PASS_WITH_LIMITATIONS 6, BLOCKED 5, NOT_APPLICABLE 0** (total 25).
Recuento corregido el 2026-09-21 tras el hallazgo EV-02 del verificador de evidencia:
una versión intermedia de esta tabla declaraba `SC-GOV-019` como PASS, lo que daba
15/5/5 y no coincidía con el resumen. Al degradar `SC-GOV-019` a
PASS_WITH_LIMITATIONS —porque ADR-0011 declara que la ratificación de RK-14 **no**
subsana el incumplimiento— el recuento pasa a ser 14/6/5, que es el que figura arriba.

**Naturaleza de los artefactos de gate (hallazgo EV-06).** Los seis artefactos
`temporal-contract-check.json`, `gate-review.json` (A y B), `statistical-review.json`,
`custody-review.json` y `holdout-review.json` **no** son salidas del runner: son
**atestaciones retrospectivas** producidas el 2026-09-21T04:20:00Z, después de
ejecutar la campaña, para cerrar el hallazgo F-02 de la auditoría final. Su contenido
numérico se reconcilia íntegramente con la evidencia intacta de A, B y C —verificado
de forma independiente— pero no deben leerse como registros emitidos durante la
ejecución. La evidencia científica sí es contemporánea y no fue modificada.

**Lectura honesta del conjunto.** La campaña experimental A→B→C está completa,
auditada y respaldada. El **cierre científico global NO está completo**: el
complemento H sigue siendo alcance aprobado sin ejecutar, y sin él el gate GF no
puede evaluarse como PASS. Ausencia de mejora general, `SIN_GANADOR_ESTABLE` y la
no inferioridad de B son **resultados válidos**, no defectos a corregir.

## Estado por requisito — 2026-09-20 (revisado 2026-09-20, sesión de verificación)

Vocabulario cerrado, sin otros valores: `PASS`, `PASS_WITH_LIMITATIONS`,
`BLOCKED`, `NOT_APPLICABLE`.

**`BLOCKED` no es un estado terminal.** El checker normativo del repositorio
(`scripts/check_scientific_closure.py`) considera terminales únicamente `PASS`
y `NOT_APPLICABLE`, y su grafo de transiciones admite `BLOCKED → APPROVED`. Un
requisito `BLOCKED` está **irresuelto y suspendido**, a la espera de un insumo
externo. Esta tabla no lo convierte en resuelto: declara el estado en que esta
sesión lo deja. El veredicto de sesión `SCIENTIFIC_CLOSURE_BLOCKED` es, en el
mismo sentido, **suspensivo**: describe dónde se detuvo el trabajo, no que el
trabajo sea irrealizable (hallazgo C-01 de la crítica independiente).

Alcance de esta columna: refleja el **estado de la evidencia existente**, no un
PASS de gate ni de auditoría final. Ningún estado de esta tabla autoriza
ejecutar A, B o C, inicializar el ledger ni abrir el holdout.

**Esta sección fue reescrita el 2026-09-20 por la sesión de verificación de
cierre** tras una crítica independiente sobre el snapshot publicado `b9fefbf`
que produjo diez hallazgos materiales (C-01..C-10) y siete menores. La versión
anterior contenía afirmaciones que eran falsas en `b9fefbf`: declaraba
`dc0d3f5` como «HEAD vigente» cuando estaba diez commits atrás (C-06), contaba
17 eventos de flujo donde había 23 (C-07), negaba en su párrafo de cierre la
existencia de la crítica y la auditoría que sus propias filas citaban (C-03), y
omitía que la cláusula «no push en preparación» del criterio de aceptación de
SC-GOV-019 había sido incumplida (C-02). Los informes exactos están en
[`closure-verification-2026-09-20/review-critic.md`](closure-verification-2026-09-20/review-critic.md)
y
[`closure-verification-2026-09-20/review-evidence-checker.md`](closure-verification-2026-09-20/review-evidence-checker.md);
la resolución de cada hallazgo, en
[`findings-resolution.json`](closure-verification-2026-09-20/findings-resolution.json).

**Identidad del snapshot.** Esta tabla no repite un SHA de HEAD, porque
cualquier SHA escrito aquí queda obsoleto en el mismo commit que lo escribe.
El HEAD y la base de cada commit de sesión están en
`closure-verification-2026-09-20/checkpoints.json` y en
`readiness-resolution-linux-2026-09-20/checkpoints.json`, que son las fuentes
autoritativas. La crítica que originó esta reescritura se realizó sobre
`b9fefbf36037ca259f4b17b68642d330bc489d39`.

Estado de los changes en `changes.json`: `sc-01-evidence-scope` `PASS`
(auditoría independiente sobre el snapshot `a0d8bf7`, alcance documental);
`sc-02` a `sc-10` `BLOCKED`.

| Requisito | Estado | Base verificada y limitación |
| --- | --- | --- |
| **SC-GOV-001** | PASS_WITH_LIMITATIONS | `session-identity.json` existe y fue auditado PASS dentro de `sc-01`. Esta sesión agregó `closure-verification-2026-09-20/session-identity.json`, con identidad, entorno, autorización aplicable y sustitución de agentes. Limitación: el artefacto de `sc-01` registra el commit documental `a70022d3…` sobre el snapshot auditado `a0d8bf7`, muy anterior al HEAD actual; describe aquella sesión, no ésta |
| **SC-GOV-002** | BLOCKED | `readiness-resolution-linux-2026-09-20/authorizations.json` registra `AUTH-ABC-2026-09-20` como `GRANTED_BUT_NOT_EXERCISABLE`. La instrucción de sesión del 2026-09-20 amplía la autorización (incluye ejecutar A/B/C «cuando sus gates estén satisfechos» y push a `origin/feat/scientific-closure`) pero **no** levanta la condición 4 de ADR-0011, que es condición congelada de un ADR aceptado. Condición 4 `NOT_SATISFIED`, verificado de nuevo en esta sesión: el ADR está mergeado byte a byte en `origin/main` (`9fcbfd9f…`, sha256 `a8dabbc4…` en ambas refs), pero el protocolo detallado allí es una versión anterior a la que le falta la sección titulada «Condiciones de interpretación y soporte previas a ejecución» y cuya sección 4 todavía afirma que el contrato de features es «heredado de `controlled_daily_v3`, sin modificación», afirmación falsa frente a `features.py`. Además `docs/research/scientific-closure-decisions.md` y `scientific-closure-runbook.md`, normativos para la rama, **no existen en `main`**. `214735e…` no es ancestro de `origin/main`; eso es contexto del merge pendiente, no parte del texto de la condición 4. Precisión (C-17): la numeración duplicada «16» fue introducida por `214735e` en esta rama, de modo que es preexistente a esta sesión pero **no** al protocolo mergeado . **Irregularidad de orden registrada (C-19, AUD-F-04), en los términos del auditor:** `authorizations.json` declara por sí mismo que la evidencia de `sc-02` se produjo **antes** de que `sc-02` estuviera aprobado, contra `operations.md`. Es real, fue **declarada voluntariamente y no ocultada**, no relajó ningún gate, y es una razón más por la que `sc-02` no es `PASS`. No queda subsanada por esta sesión |
| **SC-GOV-003** | PASS_WITH_LIMITATIONS | `preservation.json` existe y fue auditado PASS en `sc-01`. Verificado de nuevo en esta sesión: `scientific-baseline-v3`, `technical-baseline-v1` y `technical-baseline-v2` no se movieron, `src/` permanece byte-idéntico a `214735e…` y ningún commit de sesión tocó `frontend/`. Limitación: el diff acreditado en `sc-01` tiene por base `a70022d3…` y no cubre por sí solo los commits posteriores; la cobertura posterior proviene de los checkpoints y de la verificación mecánica, no de aquel artefacto |
| **SC-GOV-004** | PASS_WITH_LIMITATIONS | `inventory.json` existe y fue auditado PASS en `sc-01`; la reconciliación posterior está en `inventory.md`. El verificador de evidencia independiente de esta sesión contrastó artefacto por artefacto los 25 esperados contra el disco: 12 presentes, 13 ausentes, partición **idéntica** a la declarada aquí y en `changes.json`, sin sobredeclaración. Limitación: varias entradas del artefacto original quedaron superadas por la migración de entradas a Linux |
| **SC-GOV-005** | PASS_WITH_LIMITATIONS | `claims-assessment.json` existe y fue auditado PASS en `sc-01`, con alcance explícitamente documental. Limitación viva: `claims.md` declara que la decisión vigente R/H/N/S «permanece pendiente de crítica y auditoría independiente». Mientras esa auditoría no exista, SC-GOV-021, 023 y 024 permanecen `BLOCKED` y no `NOT_APPLICABLE` |
| **SC-GOV-006** | BLOCKED | **Degradado desde `PASS_WITH_LIMITATIONS` por el hallazgo C-05.** El criterio del requisito exige «carga efectiva y permisos» de los cinco perfiles. Eso sigue sin acreditarse: `agent-capabilities.json` concede que los perfiles `.codex/agents` **no son cargables** en este runtime y que `effective_model_introspectable: false`; `checker-remediation-linux.json` registra `CRIT-SUB-01: OPEN/BLOCKED, no resuelto`; `preparation-resumption-audit-2026-09-19.md` registra `AUD-SUB-02` como **bloqueante** de este mismo requisito. GD-17 resuelve el *enforcement de solo lectura*, que es cosa distinta de la carga de perfiles, y no existe transición registrada de bloqueante a cerrado. Lo que sí está acreditado y se conserva: enforcement reproducible por `scripts/readonly_role_sandbox.sh` con bubblewrap 0.11.1, **11 pruebas** (corrección C-11; los valores «8» y «10» de otros documentos corresponden a versiones anteriores), reejecutado PASS de forma independiente en esta sesión. La auditoría independiente **derrotó** la primera versión del mecanismo (A-01: `curl.exe` de Windows desde dentro del sandbox devolvió HTTP 200) y una re-auditoría encontró una segunda vía (NF-01: sockets `/run/WSL/*_interop`); ambas fueron cerradas con prueba de regresión. La afirmación válida es «solo lectura y sin red **para procesos Linux**, con las dos vías conocidas cerradas», nunca aislamiento absoluto, y no se excluye una tercera vía. Los subagentes de esta sesión corrieron con solo lectura **instruida**, no impuesta |
| **SC-GOV-007** | PASS_WITH_LIMITATIONS | El artefacto esperado existe: `readiness-resolution-linux-2026-09-20/workflow-events.jsonl`, con **23 líneas al snapshot `b9fefbf`** (corrección C-07; la cifra «17» correspondía a una versión anterior del registro). Contiene identidad de sesión, despacho y reporte de cada rol, asignaciones de escritor exclusivas y disjuntas, validaciones con exit code, evaluaciones de gate, ciclos de corrección y la constancia de que ningún `state_event` fue fabricado; los despachos de lector incluyen `review_manifest` con el commit exacto revisado. Limitaciones: (a) la primera versión carecía de esos manifiestos por SHA y el estado se elevó antes de tenerlos — corregido tras el hallazgo F-02; (b) el detalle por archivo vive en `evidence-manifest.json`, no en el `jsonl`; (c) no hay eventos de A/B/C porque no existieron; (d) **excepción declarada al escritor único** (C-16): `agent-capabilities.json` registra que este mismo archivo `traceability.md` fue escrito primero por el implementador y después por el orquestador, de modo que el archivo que registra el cumplimiento es el archivo cuya regla se excepcionó; en esta sesión el orquestador fue escritor único de todo el archivo y **ningún lector independiente escribió nada**. No se declara aquí un número de lectores: una cifra escrita en este registro queda falsada por el ciclo siguiente, que es el hallazgo FA-01. Los lectores de esta campaña son exactamente los archivos `closure-verification-2026-09-20/review-*.md`; enumerarlos es la comprobación, no leer un número |
| **SC-GOV-008** | BLOCKED | `sc-06-scientific-synthesis` está `BLOCKED` y su gate exige una etapa terminal A/B/C auditada. `audit.json` no existe. El gate no es alcanzable mientras SC-GOV-002 y SC-GOV-009 sigan `BLOCKED` |
| **SC-GOV-009** | BLOCKED | `execution-manifest.json` declara `container_image.status: NOT_AVAILABLE` y `ledger_initialised: false`. Hecho favorable reverificado por el checker de evidencia de esta sesión mediante identidad de árboles y blobs, no sólo por diff vacío: `src` (tree `0308057…`), `docker` (tree `84230fc…`) y `pyproject.toml` (blob `da4a2e9…`) en HEAD son **byte-idénticos** a `214735e…`. Aun así la identidad ejecutable no puede certificarse sin la imagen. Reconciliación añadida en esta sesión (C-18, decisión GD-21): la imagen aprobada `sha256:55bc923e…b297af` **sí fue ejecutada el 2026-09-19 desde el host Windows** (15 tests, 15 OK, 0,552 s, registrado en `final-preparation-audit.md`); lo inalcanzable es el runtime de contenedores **desde esta distro WSL**, no la existencia de la imagen. Además el runbook ejecuta cada comando A/B/C a través de `docker`, de modo que este bloqueo impide ejecutar la campaña, no sólo inspeccionar la imagen |
| **SC-GOV-010** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `temporal-contract-check.json` no existe; el gate depende de `sc-02` PASS, que no se alcanzó. Verificado positivamente en software, no en campaña: `test_controlled_daily_v4_splits.py`, `..._stage_window.py` y `..._features.py` pasan dentro de las 545 pruebas de esta sesión |
| **SC-GOV-011** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `A/gate-review.json` no existe; A no fue ejecutada. La regla de soporte está implementada y probada (`selection.py`: menos de dos folds con MCC finito ⇒ `NO_VALID_SELECTION`), lo que es evidencia técnica, no resultado |
| **SC-GOV-012** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/gate-review.json` no existe; B no fue ejecutada |
| **SC-GOV-013** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/custody-review.json` no existe; no hay registro de custodia ni intento reservado. Verificado mecánicamente: los únicos SQLite existentes son fixtures de ensayo cuyo contenido se autodeclara sintético |
| **SC-GOV-014** | BLOCKED | `sc-05-stage-c` `BLOCKED`; `C/holdout-review.json` no existe; el ledger **no** está inicializado (`/home/gus/scientific-closure-runtime/ledger/` verificado vacío) y el holdout 2024–2025 permanece cerrado. Ningún valor reservado fue leído |
| **SC-GOV-015** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `statistical-review.json` no existe; no hay métricas ni bootstrap de campaña. El piso de 80 % de réplicas válidas y las semillas normativas están implementados y probados |
| **SC-GOV-016** | PASS_WITH_LIMITATIONS | **Cambia desde `BLOCKED`.** El artefacto exigido existe: `closure-verification-2026-09-20/claim-evidence-review.json`, revisión frase a frase de `docs/research/scientific-closure-synthesis-2026-09-20.md` contra `claims.md`. **Corrección AUD-F-02:** la versión anterior de esta fila decía que esa revisión fue «realizada por un crítico independiente y transcrita sin alterar su veredicto». Eso era una **atribución falsa**: la lista de dieciséis ítems fue **compuesta por el orquestador**, y siete de ellos no aparecen en el informe preservado del crítico. Lo que sí es cierto, y es lo que sostiene el estado: **dos lectores independientes**, en contextos separados y con sus propias palabras, llegaron a la misma conclusión sustantiva sobre el mismo documento —el crítico mientras intentaba refutarlo, y el auditor mientras levantaba este mismo hallazgo—: la síntesis **no** sobreafirma, no declara ningún resultado, no presenta fixtures como ciencia, no implica que el holdout se haya tocado, y distingue correctamente hashear un CSV de leer valores reservados. Ambas conclusiones están citadas textualmente en el artefacto y sus informes completos preservados en `review-critic.md` y `review-audit.md`. Limitaciones: (a) la revisión sólo puede cubrir afirmaciones de no ejecución, porque no existe ninguna afirmación de resultado que revisar; (b) la estructura por ítems es del orquestador, no de un lector; (c) `sc-06-scientific-synthesis` sigue `BLOCKED` porque su gate exige además una etapa terminal A/B/C auditada; (d) un `PASS_WITH_LIMITATIONS` de requisito no es un PASS de change ni de gate |
| **SC-GOV-017** | PASS_WITH_LIMITATIONS | Artefacto: `readiness-resolution-linux-2026-09-20/provenance-and-licence-assessment.json`, que decide `ADMISSIBLE_WITH_EXPLICIT_LIMITATIONS` (GD-13). Precisión de nombre (C-15): `requirements.json` declara el nombre esperado `provenance-assessment.json`; ese archivo existe con ese nombre exacto en `input-migration-linux-2026-09-20/`, y el de `readiness-resolution-*` es una evaluación posterior y más amplia. Ambos se citan a propósito. La validación de procedencia del propio runner fue reejecutada de forma independiente en esta sesión: exit 0, `Provenance OK`, sin entrenar y sin producir artefactos. Limitaciones preservadas: la fecha efectiva de adquisición es `DESCONOCIDO` y no se infiere de mtimes; los términos vigentes al instante de adquisición no se verificaron; `downloaded_service_version` de NASA POWER sigue `DESCONOCIDO`; y la condición 2 de ADR-0011 está resuelta **en sustancia**, no contra el manifiesto, que conserva `PENDING_CONFIRMATION` (C-08) |
| **SC-GOV-018** | BLOCKED | `recovery-rehearsal.json` y `storage-and-backup-independence.json` acreditan copia lógica con hashes idénticos y ensayo de restauración con fixture técnico (exit 0), pero `physical_independence: NOT_ACHIEVED`. Reverificado en esta sesión: las cuatro raíces (checkout, runtime, inputs, backup) comparten el dispositivo 2128 (`/dev/sdf`, ext4) y ambos CSV son byte-idénticos entre primaria y copia. Precisión nueva (E-04): el sistema de archivos raíz está respaldado por `ext4.vhdx` **dentro del volumen C:**, de modo que montar `/dev/sdd` no está demostrado que logre independencia física; el insumo faltante es almacenamiento no respaldado por el mismo volumen del host, no sólo privilegio de root |
| **SC-GOV-019** | BLOCKED | **Degradado desde `PASS_WITH_LIMITATIONS` por el hallazgo C-02.** El criterio de aceptación del requisito exige, literalmente, «no `git add -A` ni **push en preparación**», y `AGENTS.md` repite «En preparacion: sin push». El reflog local demuestra **dos pushes** durante la preparación: `dc0d3f5` a las 2026-09-20T03:52:42Z y `b9fefbf` a las 05:54:37Z, ocho segundos después de crear ese commit; `git ls-remote` confirma el remoto en `b9fefbf`. Dos registros de auditoría de aquella sesión afirman lo contrario («no push (remote still at dc0d3f5)»); esos informes se conservan **sin alterar**, conforme a la regla de preservar informes exactos de lectores, y la corrección se registra aparte en `findings-resolution.json`. Ningún revisor lo detectó porque los tres corrieron sin red, aunque el reflog es local. La instrucción de sesión del 2026-09-20 autoriza push a `origin/feat/scientific-closure` **hacia adelante**; no puede autorizar retroactivamente los dos anteriores, de modo que el incumplimiento queda registrado, no subsanado. Lo que sí se cumple: `git diff --check` exit 0 y rutas explícitas en cada `git add`, nunca `git add -A`. Corrección adicional (C-04): `checkpoints.json` de la sesión anterior afirma que falta «exactamente UN» commit cuando faltan dos (`8e31f78` y `b9fefbf`); el registro de esta sesión evita el defecto declarando la regla en lugar de un número |
| **SC-GOV-020** | PASS_WITH_LIMITATIONS | `structural-validation.json`: 11/11 ítems de `scientific-closure` pasan `@fission-ai/openspec@1.13.1 validate --strict`, resultado **reproducido íntegramente en esta sesión** (11/11 exit 0); `scripts/check_scientific_closure.py` exit 0 con `PASS (estructura; runtime no verificado)`. Precondición de reproducibilidad descubierta aquí (E-01, decisión GD-20): con el `PATH` de login por defecto, `npx` resuelve al binario **de Windows**, CMD.EXE rechaza el directorio UNC de WSL, cae a `C:\Windows` y el CLI no lee ningún repositorio; las once validaciones terminan 1 con «no deltas found», y un identificador de change inexistente produce **exactamente el mismo** mensaje y código, lo que prueba que no se lee nada. El comando sólo es reproducible con el node Linux de `/home/gus/scientific-closure-runtime/env/node/bin` primero en `PATH`; ese binario fue verificado byte-idéntico a la release oficial v22.20.0. Pruebas negativas del checker formal ejecutadas sobre una **copia** del árbol: un `PASS` forjado y un `NOT_APPLICABLE` forjado son rechazados con exit 1 y hallazgos de estado, aprobación, auditoría y gate de dependencias; el checker no es vacío. Límite documentado del checker: **no** verifica existencia de artefactos en disco, por diseño, porque los nombres de `requirements.json` son artefactos esperados de una campaña futura; esa verificación es el rol mecánico del `evidence_checker`, ejercido aquí. Limitaciones: `validate --all --strict` termina 1 por 42 changes preexistentes de otras capacidades, fuera de alcance y no modificados; la validación corrió en el entorno reconstruido, no en la imagen aprobada |
| **SC-GOV-021** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09.** `claims.md` fija R `NOT_REQUIRED` (CL-01, CL-05, CL-10) y `sc-07-aux-regression` es `conditional: true` con gate «R REQUIRED», pero `NOT_APPLICABLE` es **terminal** para el checker, igual de definitivo que `PASS`, y la decisión que lo sostendría es la que `claims.md` declara «pendiente de crítica y auditoría independiente». Un estado terminal sobre una decisión autodeclarada no auditada contradice la regla de cerrar sólo con PASS de auditor. Además el artefacto declarado `auxiliary/R/review.json` **no existe** y la versión anterior de esta fila no lo decía. El estado volverá a `NOT_APPLICABLE` únicamente cuando exista auditoría independiente favorable de la decisión de suficiencia GD-12 |
| **SC-GOV-022** | BLOCKED | `claims.md` fija H `REQUIRED` (CL-06, CL-10). `sc-08-aux-hitl` está `BLOCKED` y su gate exige `sc-01` y `sc-02` PASS; `sc-02` no lo está. `auxiliary/H/review.json` no existe y **no existe runner** para el diseño H. Es el único complemento activo y sigue sin evidencia: un pendiente explícito, no una decisión de suficiencia |
| **SC-GOV-023** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09**, por la misma razón que SC-GOV-021. `claims.md` fija N `NOT_REQUIRED` (CL-04, CL-07, CL-10) y prohíbe afirmar detección reservada; el artefacto `auxiliary/N/review.json` no existe. La prohibición de afirmar detección reservada sigue vigente con independencia del estado de esta fila |
| **SC-GOV-024** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09**, por la misma razón que SC-GOV-021. `claims.md` fija S `NOT_REQUIRED` bajo el límite aprobado (CL-08); el artefacto `auxiliary/S/review.json` no existe. Sigue prohibido extrapolar a mediciones o sensores ausentes |
| **SC-GOV-025** | BLOCKED | El artefacto `closure-verification-2026-09-20/scientific-closure-audit.json` existe y recoge una auditoría final independiente, requisito por requisito, sobre el snapshot publicado; el informe exacto del auditor está en `review-audit.md`. Esta sesión la encargó precisamente porque ninguna revisión cubría `b9fefbf` (hallazgo C-10). **Corrección AUD-F-01:** la versión anterior de esta fila afirmaba que ese artefacto «ya existe» y enunciaba su veredicto **antes de que la auditoría se realizara**. Era falso y además prejuzgaba al auditor; el artefacto se escribió recién al recibir su informe. Veredicto real del auditor sobre el snapshot `5b40a55`: `BLOCKED`, suspensivo, por dos hallazgos documentales corregibles (AUD-F-01 y AUD-F-02, ambos aplicados) y tres insumos externos. Sobre **suficiencia científica** su veredicto es negativo y no depende de aquellos dos: seis de diez afirmaciones aprobadas no tienen evidencia ni limitación aceptada que las sustituya, porque `PENDING` designa evidencia futura faltante, no un límite aceptado. El requisito queda `BLOCKED` **con artefacto presente y causa registrada**, que es distinto de `BLOCKED` por artefacto ausente |

Resumen mecánico: `PASS` 0; `PASS_WITH_LIMITATIONS` 8 (SC-GOV-001, 003, 004,
005, 007, 016, 017, 020); `BLOCKED` 17 (SC-GOV-002, 006, 008, 009, 010, 011,
012, 013, 014, 015, 018, 019, 021, 022, 023, 024, 025); `NOT_APPLICABLE` 0.
Total 25.

**Diecisiete de veinticinco requisitos quedan irresueltos.** Respecto de la
versión anterior de esta tabla, **cinco filas empeoran** tras la crítica
independiente (SC-GOV-006, 019, 021, 023 y 024; tres de ellas por el mismo
hallazgo C-09) y una **mejora** con artefacto nuevo (SC-GOV-016).
Ninguna mejora proviene de ejecución científica, porque no la hubo. Una tabla
que empeora tras una revisión independiente es el comportamiento esperado de
este procedimiento, no una falla de él.

Sobre los cinco requisitos degradados: ninguno se degradó por evidencia nueva
en contra, sino porque el estado anterior **excedía** la evidencia que lo
sostenía. Revertirlos exige evidencia, no redacción.

Distinción explícita: los estados `PASS_WITH_LIMITATIONS` de esta tabla derivan
de **evidencia documental y de verificaciones técnicas**, nunca de ejecución
científica. No existe ninguna corrida de A, B o C, ninguna métrica, ninguna
predicción ni ningún valor reservado leído. Los registros de
`readiness-resolution-linux-2026-09-20` **sí** recibieron crítica y auditoría
independientes (`review-critic.json`, `review-audit.json`, `review-audit-2.json`
en ese mismo directorio); la frase en contrario de la versión anterior de esta
sección era falsa y fue el hallazgo C-03. Los registros de
`closure-verification-2026-09-20` recibieron crítica y auditoría independientes
en esta sesión, sobre el snapshot indicado en cada informe.

**Limitación conocida del registro (KL-01).** Cuatro revisiones independientes
sucesivas hallaron, cada una, una instancia de la misma clase de defecto: un
registro que enuncia una cardinalidad o acredita un artefacto, escrito durante
un proceso cuyo paso siguiente cambia esa cardinalidad o crea ese artefacto. La
severidad decrece de forma estricta —matriz normativa, luego capa de integridad
de evidencia, luego campos narrativos e índices— y el mecanismo es estructural:
cada ciclo de corrección agrega un lector y un conjunto de hallazgos, lo que
falsa cualquier recuento que el ciclo anterior haya escrito sobre esos mismos
conjuntos. El remedio aplicado es sustituir los recuentos por instrucciones de
recomputación o acotarlos a un snapshot nombrado. Por recomendación expresa del
tercer auditor y por la regla de no perseguir indefinidamente una causa que
persiste tras tres ciclos, **se detiene la iteración y la clase queda
registrada** en `findings-resolution.json` bajo `KL-01`. Ninguna instancia de
esta clase tocó jamás custodia, fuga, identidad ejecutable, el estado de un
requisito ni una afirmación científica; los cuatro lectores lo afirmaron por
separado. Ante cualquier número de este registro que importe: recomputarlo.
## Actualización por integración de `origin/main` — 2026-09-21

Esta sección **no** cambia el estado de ningún requisito. Registra qué hechos
citados en las filas anteriores dejaron de ser ciertos tras integrar
`origin/main` (`a65701477b19ecad172fa613aea8b8dbf94bab9c`, PR #206) en
`feat/scientific-closure`.

- **SC-GOV-002** sigue `BLOCKED`. Cambia el hecho, no el estado: el protocolo
  detallado vigente, `docs/research/scientific-closure-decisions.md` y
  `docs/research/scientific-closure-runbook.md` **ya existen** en `origin/main`,
  y `docs/adr/0011-...md` registra la condición 4 de ADR-0011 como cumplida al
  mergear ese cambio. Esa condición es un prerrequisito de integración, no una
  autorización: no habilita ejecutar A, B ni C. Sigue vigente que
  `214735e…` **no** es ancestro de `origin/main` ni del merge, y las condiciones
  1 (parcial), 2 (parcial) y 3 de ADR-0011 no cambian.
- **SC-GOV-003** sigue `PASS_WITH_LIMITATIONS`, con dos hechos de la fila
  revisados. (a) Deja de ser cierto que `src/` permanezca byte-idéntico a
  `214735e…`: el merge incorpora las correcciones auditadas del PR #206 en
  `src/experiment_runner/controlled_daily_v4/`. (b) La frase «ningún commit de
  sesión tocó `frontend/`» sigue siendo cierta **de los commits de esta rama**
  —`git diff b82d445e HEAD -- frontend/` está vacío— pero ya no describe el
  árbol: el merge trae 17 archivos de `frontend/` **desde `main`**, y tras el
  merge `git diff origin/main -- frontend/` está vacío, es decir el árbol
  reproduce la UI de `main` sin modificarla. Ninguna línea de UI fue escrita ni
  alterada por esta rama. Siguen ciertos sin cambio los demás hechos de la fila
  (`scientific-baseline-v3`, `technical-baseline-v1` y `technical-baseline-v2`
  no se movieron).
- **SC-GOV-009** sigue `BLOCKED`, y con una razón adicional: además de que la
  imagen aprobada no es inspeccionable desde esta distro, el árbol `src/` ya no
  coincide con el commit ejecutable declarado, de modo que la identidad
  ejecutable debe redeclararse y volver a verificarse antes de ejecutar.
- La numeración duplicada «16» del protocolo, registrada como precisión C-17,
  quedó corregida por el merge: la sección es la 19 y no hay duplicado.

No se ejecutó A, B ni C, no se abrió el holdout 2024–2025 y no se inicializó el
ledger definitivo. Ninguna compuerta se relaja por esta actualización.

## Estado por requisito — 2026-09-21, complemento H (HITL)

Esta sección **no reescribe** las tablas anteriores: las supersede para los dos
requisitos que el complemento H toca. El resto conserva el estado que fijó la
sesión del 2026-09-21 tras la campaña A→B→C.

| Requisito | Estado | Fundamento |
| --- | --- | --- |
| **SC-GOV-022** | PASS_WITH_LIMITATIONS | **Supersede la fila anterior, que hoy es factualmente falsa.** Aquella decía «H (HITL) está declarado `REQUIRED` y no tiene runner implementado ni evidencia alguna. No se ejecutó» y «no existe runner para el diseño H». Ambas proposiciones dejaron de ser ciertas el 2026-09-21: el runner `src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py` está en la rama, H se ejecutó **una sola vez** y el artefacto `auxiliary/H/review.json` existe. El auditor final independiente verificó por su cuenta el criterio de aceptación congelado —tres brazos y maduración separados sobre las mismas 362 filas, 20 eventos por semilla en las cinco semillas congeladas con estratificación 10/10 en las seis agrupaciones, simulación identificada, sin afirmación de beneficio— y recomputó 72 métricas desde las predicciones en Python puro, sin `sklearn`, con 0 discrepancias. **No es PASS pleno:** la pista humana sólo ejercitó la aceptación; RECHAZO y recalibración sucesiva no fueron ejercitados por ninguna pista científica; el cegamiento fue PARCIAL y declarado; y dos puntos del expediente (INV-10 y la reproducción estricta 18/18) **no** fueron verificados de forma independiente por la auditoría, por indisponibilidad de herramientas — no deben presentarse como auditados. Ver `openspec/changes/sc-08-aux-hitl/reviews/` |
| **SC-GOV-025** | BLOCKED | **Mismo estado, causa distinta.** La causa anterior —«el plan exige todos los `REQUIRED` con PASS y H no lo está»— quedó resuelta: H es el único complemento `REQUIRED` y pasa a PASS_WITH_LIMITATIONS. Lo que hoy lo mantiene bloqueado es ajeno a H y el auditor final lo enumeró: no existe la auditoría final **requisito por requisito** sobre el snapshot posterior a la campaña (la disponible audita `5b40a55`, anterior a toda ejecución); no existe síntesis científica de los resultados efectivamente obtenidos; la decisión de suficiencia GD-12 sobre R/N/S sigue sin crítica ni auditoría independiente, de modo que SC-GOV-021, 023 y 024 continúan BLOCKED; y no hay artefacto de trazabilidad de las afirmaciones a los capítulos 2 y 3 de la memoria |

**Gate GF: no evaluable como PASS.** Su condición de avance es el PASS del
auditor final sobre la suficiencia del alcance **completo**, y ese PASS no
existe para el estado actual. H deja de ser el obstáculo nombrado, pero GF no
puede autoconcederse con la auditoría de un complemento. El auditor añadió una
precisión que conviene conservar: la distancia real al gate es menor de lo que
sugiere la matriz —tres obstáculos son documentales, dos son de revisión y uno
es remediación—, y **ninguno exige reabrir el holdout ni reejecutar A, B o C**.
La campaña científica está hecha; lo que falta es el cierre y su revisión.

**Recuento de afirmaciones.** El auditor rehízo el recuento de `CL-01..CL-10`:
**9 de 10** tienen hoy evidencia o limitación aceptada, frente a 4 de 10 el
2026-09-20. La décima, `CL-10`, exige «trazabilidad», que esta misma sección
provee; se cierra al registrarse la auditoría.

**Limitación de procedimiento registrada.** La auditoría final levantó el
hallazgo material **AUD-H-01**: ninguna de las cuatro rondas de crítica
independiente sobre H conservaba el informe de su autor, sólo resúmenes del
implementador — la forma exacta que `AUD-F-02` condenó el 2026-09-20. Se
remedió preservándolos verbatim en
`openspec/changes/sc-08-aux-hitl/reviews/`. Segundo hallazgo material,
**AUD-H-02**: los **resultados** de H no tienen ancla en git y viven en un
montaje escribible; las **entradas** —contrato, paquete y respuesta— sí la
tienen. Es una exposición estructural preexistente, idéntica a la de A/B/C, y
permanece declarada.

**Resultado nulo, válido y predeclarado.** El operador experimental autorizado
aceptó los veinte registros y la pista humana terminó en `NO_RECALIBRATION`. El
contrato declaraba `no_change_is_a_valid_outcome` **antes** de que el operador
viera nada, y el auditor verificó esa anterioridad en git. No es un fallo. Y
debe enunciarse junto a su consecuencia, sin atenuar: el operador **no detectó
ninguna** de las cuatro etiquetas corrompidas —`H-SC-004`, `H-SC-008`,
`H-SC-009`, `H-SC-020`—, que son exactamente las cuatro que el revisor simulado
corrigió sobre los mismos eventos. Detección humana 0/4 frente a 4/4 del
oráculo. Eso fija el alcance real de la pista humana y es lo que hace
imprescindible la validación de campo que el propio operador declaró como
trabajo futuro.

## Estado por requisito — 2026-09-22, decisión de suficiencia GD-12 (RB-03)

Esta sección **no reescribe** las tablas anteriores: las supersede para los tres
requisitos que la decisión de suficiencia toca. El resto conserva el estado que
fijaron las secciones del 2026-09-21. El movimiento lo habilita el **PASS de la
auditoría final independiente** sobre el snapshot `6878184`, no el orquestador.

| Requisito | Estado | Fundamento |
| --- | --- | --- |
| **SC-GOV-021** | NOT_APPLICABLE | **Supersede la fila degradada por el hallazgo C-09 el 2026-09-20.** Aquella decía «`NOT_APPLICABLE` es terminal y su única base era una decisión autodeclarada no auditada» y «el artefacto `auxiliary/R/review.json` no existe». **Las dos causas están resueltas**: la decisión GD-12 pasó por crítica y por auditoría independientes, ambas favorables, y el artefacto existe en `openspec/scientific-closure/sufficiency-review-2026-09-22/auxiliary/R/review.json`. `operations.md` reserva `NOT_APPLICABLE` a «complementos `NOT_REQUIRED` con **decisión de suficiencia auditada**», que es exactamente este caso. La norma lo respalda sola: `SC-GOV-021` usa «**solo si**», condición necesaria, de modo que la falla del primer término impone `NOT_REQUIRED`; y su propio criterio de aceptación dice «`NOT_REQUIRED` para sola clasificación P20». **Límites permanentes:** no puede afirmarse que el sistema predice, estima o pronostica el **valor** de humedad de suelo; no puede reportarse MAE, RMSE ni R² como desempeño predictivo de humedad de la campaña P20 o de la arquitectura de detección temprana; no puede traducirse MCC/AP/Brier/F1 a exactitud sobre humedad; y no puede presentarse la ausencia de esos números como evidencia en ningún sentido. El riesgo preejecución **SC08 sigue siendo limitación viva, no resuelta** |
| **SC-GOV-023** | NOT_APPLICABLE | **Supersede la fila degradada por C-09**, por las mismas dos causas ya resueltas, con `auxiliary/N/review.json`. **La norma NO alcanza por sí sola:** `SC-GOV-023` usa «si», condición suficiente que calla sobre el caso negativo, de modo que `NOT_REQUIRED` **no** se infiere de ella —hacerlo sería negar el antecedente— sino de una demostración positiva sobre fuentes independientes de la decisión: CA2 de HU8 pide «el **aporte** de los componentes», y la lista «Incluye» de `project.md` junto con ADR-0001 enumeran cuatro configuraciones comparativas y nada más. La afirmación que el cierre sí sostiene —aporte de las anomalías como predictoras— tiene evidencia formal v3 y su lectura vigente es «evidencia mixta (F1/MCC débil-positivo, AP negativo en 5/5 semillas)». **Límites permanentes:** no puede afirmarse que el sistema **detecta** anomalías, corrupciones o fallas de sensor, con ninguna cifra de detección; ni lo inverso; la demostración de HU3 es **funcional** y así debe llamarse; y el aporte no puede presentarse como «mejora». **SC10 sigue siendo limitación viva** |
| **SC-GOV-024** | NOT_APPLICABLE **bajo el límite expreso de `CL-08`** | **Supersede la fila degradada por C-09**, con `auxiliary/S/review.json`. Misma forma «si» que `SC-GOV-023`, con la misma demostración positiva: la conclusión científica vigente (HU8 §8.3) **no sostiene robustez de ninguna clase**, así que no hay afirmación que exceder, y el criterio de aceptación del propio requisito manda **distinguir** escasez de etiquetas de sensores ausentes, que es lo que la decisión hace. **Hecho incorporado por el hallazgo material C-11 y confirmado por la auditoría:** las mediciones ausentes **no están fuera de la evidencia, están dentro y sin caracterizar** — el dataset `melchor_romero_2024_consolidado` tiene **75,96 % de cobertura en humedad de suelo**, es decir ~24 % de días son huecos reales del producto satelital imputados con `causal_ffill`, en las **ocho** configuraciones formales. **Límites permanentes:** no puede afirmarse robustez ante ausencia de mediciones, caída de sensores o huecos de telemetría; no puede extrapolarse `coverage_fraction`/`recent_fraction` a falta de mediciones; el ruido gaussiano de v3 no es ruido real de sensor; y **ningún resultado de v3 puede presentarse sin declarar ese ~24 % de huecos imputados**. **SC11 sigue siendo limitación viva.** **Reapertura vinculante:** S vuelve a `REQUIRED` en cuanto la síntesis científica pendiente (`RB-04`) enuncie **cualquier** resultado de robustez |

**Los tres changes NO se mueven.** `sc-07`, `sc-09` y `sc-10` permanecen
`BLOCKED`, cada uno con su campo `applicability_decision`. Su `extra_gate` exige
la condición `REQUIRED`, que no se cumple y no se cumplirá, y su propio campo
`block` asigna `BLOCKED` a `NOT_REQUIRED`. `BLOCKED` no describe aquí un defecto
removible: describe correctamente un complemento condicional que no hay que
ejecutar. Ver GD-31.

**Incumplimiento registrado, no ocultado.** Esta misma sesión movió los tres
changes a `APPROVED` y a `IN_PROGRESS` con la compuerta negativa, contra
`plan.md` y `operations.md`, y lo revirtió tras los hallazgos materiales C-05 y
C-06 de la crítica independiente. Los eventos indebidos **se conservan** en
`changes.json`, conforme a la prohibición de borrarlos. Ver GD-32, que sigue el
precedente de GD-19.

**Qué NO cambia.** `SC-GOV-025` sigue `BLOCKED` y el gate `GF` sigue sin ser
evaluable como `PASS`. De los cinco términos del criterio de aceptación de
`SC-GOV-025`, esta decisión atiende **uno solo**, «complementos justificados».
Siguen abiertos e intactos **RB-04** (síntesis científica de los resultados
efectivamente obtenidos), **RB-05** (auditoría final requisito por requisito
sobre el snapshot posterior a la campaña) y **RB-06** (trazabilidad a los
capítulos 2 y 3 de la memoria). El auditor lo dijo expresamente: este `PASS`
**no los acerca**.

**Obligación hacia adelante, señalada por la auditoría y no resuelta aquí.** El
~24 % de días de humedad imputados con `causal_ffill` **no figura** entre las
amenazas a la validez de HU8 §8.4 ni en `claims.md`. Incorporarlo corresponde a
`RB-04`. Se suma la inconsistencia de recuento de `claims.md` —su prosa dice
«9 de 10» y su tabla marca **diez** filas `CUBIERTA`—, también diferida.

## Estado por requisito — 2026-09-22, reconciliación RB-04/05/06

Esta sección **no reescribe** las anteriores: las complementa. La sección RB-03
inmediatamente anterior **no cambia** — `SC-GOV-021`, `SC-GOV-023` y
`SC-GOV-024` siguen `NOT_APPLICABLE` y no se tocan aquí.

**Origen del trabajo portado.** RB-04 (síntesis) y RB-06 (trazabilidad a la
memoria) se redactaron originalmente en `feat/scientific-evidence-finalization`
(PR #211, commit `7e63d1c`, corregido hasta `f355272`) y se incorporan aquí
como entregables reconciliados. Detalle completo de qué se portó, qué se
corrigió y qué se descartó en
`openspec/scientific-closure/reconciliation-2026-09-22/reconciliation-table.md`.

| Requisito | Estado | Fundamento |
| --- | --- | --- |
| **SC-GOV-016** | PASS_WITH_LIMITATIONS | **Cambia de base, no cambia de sentido.** Hasta hoy la revisión sólo podía cubrir afirmaciones de no ejecución, porque no existía ninguna afirmación de resultado que revisar. Hoy existe `docs/research/scientific-closure-synthesis-2026-09-22.md`, la síntesis de los resultados efectivamente obtenidos en A, B, C y H. **Limitación:** la revisión de esta reconciliación es documental — contrasta la síntesis contra `claims.md` y contra los valores que las auditorías de A/B/C/H y de RB-03 ya recomputaron; no recomputa métricas nuevas. Pendiente de la auditoría única solicitada más abajo para su verificación final |
| **RB-04** (síntesis científica) | CUBIERTO, pendiente de auditoría única | `docs/research/scientific-closure-synthesis-2026-09-22.md`. Trece secciones: pregunta e hipótesis, identidad del objeto, resultados de A/B/C/H con sus limitaciones, validez interna y externa, catorce limitaciones consolidadas, trabajo futuro y lo que la campaña explícitamente no afirma. Incorpora, como corrección de esta reconciliación, la limitación de imputación causal en la evidencia v3 (~24 %, `causal_ffill`), ausente en la versión original |
| **RB-06** (trazabilidad a memoria) | CUBIERTO, pendiente de auditoría única | `openspec/scientific-closure/reconciliation-2026-09-22/thesis-traceability.md`. Traza evidencia hacia capítulos 2 y 3, con resultado utilizable, afirmación permitida, límite obligatorio, figura recomendada y ajuste pendiente por fila; separa explícitamente qué resultados pertenecen al capítulo 4 bajo la plantilla TTFA. Incorpora la fila `2.12` sobre imputación causal, nueva en esta reconciliación |
| **RB-05** (auditoría final requisito por requisito) | **NO CUBIERTO como PASS formal — dos precedentes `FAIL`, ninguno re-auditado** | Dos rondas de auditoría independiente sobre el snapshot de `f355272` (`7e63d1c` y `0dbc976`), preservadas verbatim en `openspec/changes/sc-06-scientific-synthesis/reviews/review-audit-final-round{1,2}-FAIL.md`. **Las dos terminaron en `FAIL`** por defectos documentales (la matriz acreditaba una auditoría antes de que existiera; el recuento no coincidía con su propia tabla; una corrección de la ronda 1 reincidió en el mismo patrón). El auditor de la ronda 2 declaró por escrito un veredicto de fondo `PASS_WITH_LIMITATIONS` y **renunció expresamente a una tercera ronda**, pero ninguna auditoría verificó la corrección resultante. **Esa renuncia no se trata aquí como un `PASS`.** RB-05 queda cubierto por una **auditoría única nueva**, sobre el snapshot reconciliado, solicitada a continuación |
| **SC-GOV-025** | **PENDIENTE — no se declara `PASS_WITH_LIMITATIONS` todavía** | De sus cinco términos de aceptación: «afirmaciones con evidencia o limitación aceptada» y «terminal negativo válido documentado» están cubiertos desde A/B/C/H; «complementos justificados» está cubierto por RB-03 (`PASS` del auditor independiente, intocado); «memoria caps. 2/3 trazada» está cubierto por RB-06. **«Ningún obligatorio sin resolver» no está cubierto**: RB-05 no tiene un `PASS` formal. El estado se actualizará en un commit separado, exclusivamente sobre el veredicto de la auditoría única de esta reconciliación |
| Gate **GF** | **PENDIENTE, no evaluable como PASS todavía** | Su condición de avance es el `PASS` del auditor final sobre la suficiencia del alcance completo. Ese `PASS` no existe todavía para el snapshot reconciliado. Ninguno de los cinco obstáculos exige reabrir el holdout ni reejecutar A, B, C, H, R, N o S |

**Amenaza a la validez declarada, no evidencia de robustez.** El dataset
`melchor_romero_2024_consolidado`, que produce toda la evidencia formal de
`controlled_daily_v3` citada por `CL-04` y `CL-08`, tiene 75,96 % de cobertura
real en humedad de suelo: ~24 % de sus días son huecos del producto satelital,
imputados con `causal_ffill`, en las ocho configuraciones formales por igual,
sin condición limpia de comparación. Declarado en
`hu8-resultados-discusion-conclusiones.md` §8.4, en `claims.md` (`CL-04`,
`CL-08`) y en `thesis-traceability.md` (fila `2.12`). **No** se afirma que S se
haya ejecutado ni que exista evidencia de robustez ante mediciones ausentes; la
campaña A/B/C/H (Pergamino, no Melchor Romero) **no imputa** —el runner de v4
aborta ante huecos del calendario diario en vez de repararlos
(`controlled_daily_v4/features.py::validate_continuous_daily_calendar`)— y
`causal_ffill` es una propiedad exclusiva del contrato de v3
(`predictive_modeling/contract.py`), y esto no cambia. **Corrección tras el
hallazgo `F-01` de la auditoría de esta reconciliación:** la redacción anterior
atribuía a `temporal-contract-check.json` una verificación de imputación que
ese artefacto no contiene.

**Auditoría independiente única solicitada.** Sobre el snapshot que congela
esta reconciliación, con el alcance exacto: (1) que RB-03 siga conforme al
`PASS` de su propio auditor, sin reabrirlo; (2) que RB-04, RB-05 y RB-06 estén
realmente cubiertos por lo portado y lo añadido aquí; (3) que no existan
sobreafirmaciones; (4) que el estado que se proponga para `SC-GOV-025` y `GF`
se derive de evidencia vigente; (5) que la limitación de imputación causal esté
declarada donde corresponde; (6) que ningún `FAIL` histórico se presente como
`PASS`. No repite recómputo de hashes, métricas ni suites completas.
