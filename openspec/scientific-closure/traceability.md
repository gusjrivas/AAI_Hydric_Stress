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
| **SC-GOV-002** | BLOCKED | `readiness-resolution-linux-2026-09-20/authorizations.json` registra `AUTH-ABC-2026-09-20` como `GRANTED_BUT_NOT_EXERCISABLE`. La instrucción de sesión del 2026-09-20 amplía la autorización (incluye ejecutar A/B/C «cuando sus gates estén satisfechos» y push a `origin/feat/scientific-closure`) pero **no** levanta la condición 4 de ADR-0011, que es condición congelada de un ADR aceptado. Condición 4 `NOT_SATISFIED`, verificado de nuevo en esta sesión: el ADR está mergeado byte a byte en `origin/main` (`9fcbfd9f…`, sha256 `a8dabbc4…` en ambas refs), pero el protocolo detallado allí es una versión anterior a la que le falta la sección titulada «Condiciones de interpretación y soporte previas a ejecución» y cuya sección 4 todavía afirma que el contrato de features es «heredado de `controlled_daily_v3`, sin modificación», afirmación falsa frente a `features.py`. Además `docs/research/scientific-closure-decisions.md` y `scientific-closure-runbook.md`, normativos para la rama, **no existen en `main`**. `214735e…` no es ancestro de `origin/main`; eso es contexto del merge pendiente, no parte del texto de la condición 4. Precisión (C-17): la numeración duplicada «16» fue introducida por `214735e` en esta rama, de modo que es preexistente a esta sesión pero **no** al protocolo mergeado |
| **SC-GOV-003** | PASS_WITH_LIMITATIONS | `preservation.json` existe y fue auditado PASS en `sc-01`. Verificado de nuevo en esta sesión: `scientific-baseline-v3`, `technical-baseline-v1` y `technical-baseline-v2` no se movieron, `src/` permanece byte-idéntico a `214735e…` y ningún commit de sesión tocó `frontend/`. Limitación: el diff acreditado en `sc-01` tiene por base `a70022d3…` y no cubre por sí solo los commits posteriores; la cobertura posterior proviene de los checkpoints y de la verificación mecánica, no de aquel artefacto |
| **SC-GOV-004** | PASS_WITH_LIMITATIONS | `inventory.json` existe y fue auditado PASS en `sc-01`; la reconciliación posterior está en `inventory.md`. El verificador de evidencia independiente de esta sesión contrastó artefacto por artefacto los 25 esperados contra el disco: 12 presentes, 13 ausentes, partición **idéntica** a la declarada aquí y en `changes.json`, sin sobredeclaración. Limitación: varias entradas del artefacto original quedaron superadas por la migración de entradas a Linux |
| **SC-GOV-005** | PASS_WITH_LIMITATIONS | `claims-assessment.json` existe y fue auditado PASS en `sc-01`, con alcance explícitamente documental. Limitación viva: `claims.md` declara que la decisión vigente R/H/N/S «permanece pendiente de crítica y auditoría independiente». Mientras esa auditoría no exista, SC-GOV-021, 023 y 024 permanecen `BLOCKED` y no `NOT_APPLICABLE` |
| **SC-GOV-006** | BLOCKED | **Degradado desde `PASS_WITH_LIMITATIONS` por el hallazgo C-05.** El criterio del requisito exige «carga efectiva y permisos» de los cinco perfiles. Eso sigue sin acreditarse: `agent-capabilities.json` concede que los perfiles `.codex/agents` **no son cargables** en este runtime y que `effective_model_introspectable: false`; `checker-remediation-linux.json` registra `CRIT-SUB-01: OPEN/BLOCKED, no resuelto`; `preparation-resumption-audit-2026-09-19.md` registra `AUD-SUB-02` como **bloqueante** de este mismo requisito. GD-17 resuelve el *enforcement de solo lectura*, que es cosa distinta de la carga de perfiles, y no existe transición registrada de bloqueante a cerrado. Lo que sí está acreditado y se conserva: enforcement reproducible por `scripts/readonly_role_sandbox.sh` con bubblewrap 0.11.1, **11 pruebas** (corrección C-11; los valores «8» y «10» de otros documentos corresponden a versiones anteriores), reejecutado PASS de forma independiente en esta sesión. La auditoría independiente **derrotó** la primera versión del mecanismo (A-01: `curl.exe` de Windows desde dentro del sandbox devolvió HTTP 200) y una re-auditoría encontró una segunda vía (NF-01: sockets `/run/WSL/*_interop`); ambas fueron cerradas con prueba de regresión. La afirmación válida es «solo lectura y sin red **para procesos Linux**, con las dos vías conocidas cerradas», nunca aislamiento absoluto, y no se excluye una tercera vía. Los subagentes de esta sesión corrieron con solo lectura **instruida**, no impuesta |
| **SC-GOV-007** | PASS_WITH_LIMITATIONS | El artefacto esperado existe: `readiness-resolution-linux-2026-09-20/workflow-events.jsonl`, con **23 líneas al snapshot `b9fefbf`** (corrección C-07; la cifra «17» correspondía a una versión anterior del registro). Contiene identidad de sesión, despacho y reporte de cada rol, asignaciones de escritor exclusivas y disjuntas, validaciones con exit code, evaluaciones de gate, ciclos de corrección y la constancia de que ningún `state_event` fue fabricado; los despachos de lector incluyen `review_manifest` con el commit exacto revisado. Limitaciones: (a) la primera versión carecía de esos manifiestos por SHA y el estado se elevó antes de tenerlos — corregido tras el hallazgo F-02; (b) el detalle por archivo vive en `evidence-manifest.json`, no en el `jsonl`; (c) no hay eventos de A/B/C porque no existieron; (d) **excepción declarada al escritor único** (C-16): `agent-capabilities.json` registra que este mismo archivo `traceability.md` fue escrito primero por el implementador y después por el orquestador, de modo que el archivo que registra el cumplimiento es el archivo cuya regla se excepcionó; en esta sesión el orquestador fue escritor único de todo el conjunto y los tres lectores no escribieron |
| **SC-GOV-008** | BLOCKED | `sc-06-scientific-synthesis` está `BLOCKED` y su gate exige una etapa terminal A/B/C auditada. `audit.json` no existe. El gate no es alcanzable mientras SC-GOV-002 y SC-GOV-009 sigan `BLOCKED` |
| **SC-GOV-009** | BLOCKED | `execution-manifest.json` declara `container_image.status: NOT_AVAILABLE` y `ledger_initialised: false`. Hecho favorable reverificado por el checker de evidencia de esta sesión mediante identidad de árboles y blobs, no sólo por diff vacío: `src` (tree `0308057…`), `docker` (tree `84230fc…`) y `pyproject.toml` (blob `da4a2e9…`) en HEAD son **byte-idénticos** a `214735e…`. Aun así la identidad ejecutable no puede certificarse sin la imagen. Reconciliación añadida en esta sesión (C-18, decisión GD-21): la imagen aprobada `sha256:55bc923e…b297af` **sí fue ejecutada el 2026-09-19 desde el host Windows** (15 tests, 15 OK, 0,552 s, registrado en `final-preparation-audit.md`); lo inalcanzable es el runtime de contenedores **desde esta distro WSL**, no la existencia de la imagen. Además el runbook ejecuta cada comando A/B/C a través de `docker`, de modo que este bloqueo impide ejecutar la campaña, no sólo inspeccionar la imagen |
| **SC-GOV-010** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `temporal-contract-check.json` no existe; el gate depende de `sc-02` PASS, que no se alcanzó. Verificado positivamente en software, no en campaña: `test_controlled_daily_v4_splits.py`, `..._stage_window.py` y `..._features.py` pasan dentro de las 545 pruebas de esta sesión |
| **SC-GOV-011** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `A/gate-review.json` no existe; A no fue ejecutada. La regla de soporte está implementada y probada (`selection.py`: menos de dos folds con MCC finito ⇒ `NO_VALID_SELECTION`), lo que es evidencia técnica, no resultado |
| **SC-GOV-012** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/gate-review.json` no existe; B no fue ejecutada |
| **SC-GOV-013** | BLOCKED | `sc-04-stage-b` `BLOCKED`; `B/custody-review.json` no existe; no hay registro de custodia ni intento reservado. Verificado mecánicamente: los únicos SQLite existentes son fixtures de ensayo cuyo contenido se autodeclara sintético |
| **SC-GOV-014** | BLOCKED | `sc-05-stage-c` `BLOCKED`; `C/holdout-review.json` no existe; el ledger **no** está inicializado (`/home/gus/scientific-closure-runtime/ledger/` verificado vacío) y el holdout 2024–2025 permanece cerrado. Ningún valor reservado fue leído |
| **SC-GOV-015** | BLOCKED | `sc-03-stage-a` `BLOCKED`; `statistical-review.json` no existe; no hay métricas ni bootstrap de campaña. El piso de 80 % de réplicas válidas y las semillas normativas están implementados y probados |
| **SC-GOV-016** | PASS_WITH_LIMITATIONS | **Cambia desde `BLOCKED`.** El artefacto exigido ya existe: `closure-verification-2026-09-20/claim-evidence-review.json`, revisión frase a frase de `docs/research/scientific-closure-synthesis-2026-09-20.md` contra `claims.md`, realizada por un crítico independiente en contexto separado sobre el snapshot `b9fefbf` y transcrita sin alterar su veredicto. Resultado: la síntesis **no** sobreafirma; no declara ningún resultado, no presenta fixtures como ciencia, no implica que el holdout se haya tocado, y distingue correctamente hashear un CSV de leer valores reservados. Limitaciones: (a) la revisión sólo puede cubrir afirmaciones de no ejecución, porque no existe ninguna afirmación de resultado que revisar; (b) `sc-06-scientific-synthesis` sigue `BLOCKED` porque su gate exige además una etapa terminal A/B/C auditada; (c) un `PASS_WITH_LIMITATIONS` de requisito no es un PASS de change ni de gate |
| **SC-GOV-017** | PASS_WITH_LIMITATIONS | Artefacto: `readiness-resolution-linux-2026-09-20/provenance-and-licence-assessment.json`, que decide `ADMISSIBLE_WITH_EXPLICIT_LIMITATIONS` (GD-13). Precisión de nombre (C-15): `requirements.json` declara el nombre esperado `provenance-assessment.json`; ese archivo existe con ese nombre exacto en `input-migration-linux-2026-09-20/`, y el de `readiness-resolution-*` es una evaluación posterior y más amplia. Ambos se citan a propósito. La validación de procedencia del propio runner fue reejecutada de forma independiente en esta sesión: exit 0, `Provenance OK`, sin entrenar y sin producir artefactos. Limitaciones preservadas: la fecha efectiva de adquisición es `DESCONOCIDO` y no se infiere de mtimes; los términos vigentes al instante de adquisición no se verificaron; `downloaded_service_version` de NASA POWER sigue `DESCONOCIDO`; y la condición 2 de ADR-0011 está resuelta **en sustancia**, no contra el manifiesto, que conserva `PENDING_CONFIRMATION` (C-08) |
| **SC-GOV-018** | BLOCKED | `recovery-rehearsal.json` y `storage-and-backup-independence.json` acreditan copia lógica con hashes idénticos y ensayo de restauración con fixture técnico (exit 0), pero `physical_independence: NOT_ACHIEVED`. Reverificado en esta sesión: las cuatro raíces (checkout, runtime, inputs, backup) comparten el dispositivo 2128 (`/dev/sdf`, ext4) y ambos CSV son byte-idénticos entre primaria y copia. Precisión nueva (E-04): el sistema de archivos raíz está respaldado por `ext4.vhdx` **dentro del volumen C:**, de modo que montar `/dev/sdd` no está demostrado que logre independencia física; el insumo faltante es almacenamiento no respaldado por el mismo volumen del host, no sólo privilegio de root |
| **SC-GOV-019** | BLOCKED | **Degradado desde `PASS_WITH_LIMITATIONS` por el hallazgo C-02.** El criterio de aceptación del requisito exige, literalmente, «no `git add -A` ni **push en preparación**», y `AGENTS.md` repite «En preparacion: sin push». El reflog local demuestra **dos pushes** durante la preparación: `dc0d3f5` a las 2026-09-20T03:52:42Z y `b9fefbf` a las 05:54:37Z, ocho segundos después de crear ese commit; `git ls-remote` confirma el remoto en `b9fefbf`. Dos registros de auditoría de aquella sesión afirman lo contrario («no push (remote still at dc0d3f5)»); esos informes se conservan **sin alterar**, conforme a la regla de preservar informes exactos de lectores, y la corrección se registra aparte en `findings-resolution.json`. Ningún revisor lo detectó porque los tres corrieron sin red, aunque el reflog es local. La instrucción de sesión del 2026-09-20 autoriza push a `origin/feat/scientific-closure` **hacia adelante**; no puede autorizar retroactivamente los dos anteriores, de modo que el incumplimiento queda registrado, no subsanado. Lo que sí se cumple: `git diff --check` exit 0 y rutas explícitas en cada `git add`, nunca `git add -A`. Corrección adicional (C-04): `checkpoints.json` de la sesión anterior afirma que falta «exactamente UN» commit cuando faltan dos (`8e31f78` y `b9fefbf`); el registro de esta sesión evita el defecto declarando la regla en lugar de un número |
| **SC-GOV-020** | PASS_WITH_LIMITATIONS | `structural-validation.json`: 11/11 ítems de `scientific-closure` pasan `@fission-ai/openspec@1.13.1 validate --strict`, resultado **reproducido íntegramente en esta sesión** (11/11 exit 0); `scripts/check_scientific_closure.py` exit 0 con `PASS (estructura; runtime no verificado)`. Precondición de reproducibilidad descubierta aquí (E-01, decisión GD-20): con el `PATH` de login por defecto, `npx` resuelve al binario **de Windows**, CMD.EXE rechaza el directorio UNC de WSL, cae a `C:\Windows` y el CLI no lee ningún repositorio; las once validaciones terminan 1 con «no deltas found», y un identificador de change inexistente produce **exactamente el mismo** mensaje y código, lo que prueba que no se lee nada. El comando sólo es reproducible con el node Linux de `/home/gus/scientific-closure-runtime/env/node/bin` primero en `PATH`; ese binario fue verificado byte-idéntico a la release oficial v22.20.0. Pruebas negativas del checker formal ejecutadas sobre una **copia** del árbol: un `PASS` forjado y un `NOT_APPLICABLE` forjado son rechazados con exit 1 y hallazgos de estado, aprobación, auditoría y gate de dependencias; el checker no es vacío. Límite documentado del checker: **no** verifica existencia de artefactos en disco, por diseño, porque los nombres de `requirements.json` son artefactos esperados de una campaña futura; esa verificación es el rol mecánico del `evidence_checker`, ejercido aquí. Limitaciones: `validate --all --strict` termina 1 por 42 changes preexistentes de otras capacidades, fuera de alcance y no modificados; la validación corrió en el entorno reconstruido, no en la imagen aprobada |
| **SC-GOV-021** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09.** `claims.md` fija R `NOT_REQUIRED` (CL-01, CL-05, CL-10) y `sc-07-aux-regression` es `conditional: true` con gate «R REQUIRED», pero `NOT_APPLICABLE` es **terminal** para el checker, igual de definitivo que `PASS`, y la decisión que lo sostendría es la que `claims.md` declara «pendiente de crítica y auditoría independiente». Un estado terminal sobre una decisión autodeclarada no auditada contradice la regla de cerrar sólo con PASS de auditor. Además el artefacto declarado `auxiliary/R/review.json` **no existe** y la versión anterior de esta fila no lo decía. El estado volverá a `NOT_APPLICABLE` únicamente cuando exista auditoría independiente favorable de la decisión de suficiencia GD-12 |
| **SC-GOV-022** | BLOCKED | `claims.md` fija H `REQUIRED` (CL-06, CL-10). `sc-08-aux-hitl` está `BLOCKED` y su gate exige `sc-01` y `sc-02` PASS; `sc-02` no lo está. `auxiliary/H/review.json` no existe y **no existe runner** para el diseño H. Es el único complemento activo y sigue sin evidencia: un pendiente explícito, no una decisión de suficiencia |
| **SC-GOV-023** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09**, por la misma razón que SC-GOV-021. `claims.md` fija N `NOT_REQUIRED` (CL-04, CL-07, CL-10) y prohíbe afirmar detección reservada; el artefacto `auxiliary/N/review.json` no existe. La prohibición de afirmar detección reservada sigue vigente con independencia del estado de esta fila |
| **SC-GOV-024** | BLOCKED | **Degradado desde `NOT_APPLICABLE` por el hallazgo C-09**, por la misma razón que SC-GOV-021. `claims.md` fija S `NOT_REQUIRED` bajo el límite aprobado (CL-08); el artefacto `auxiliary/S/review.json` no existe. Sigue prohibido extrapolar a mediciones o sensores ausentes |
| **SC-GOV-025** | BLOCKED | El artefacto `closure-verification-2026-09-20/scientific-closure-audit.json` **ya existe**: una auditoría final independiente requisito por requisito sobre el snapshot publicado, que esta sesión encargó precisamente porque no existía ninguna revisión de `b9fefbf` (hallazgo C-10). Su veredicto sobre **suficiencia científica** es negativo por construcción: no hay etapa terminal A/B/C, de modo que el alcance científico aprobado no puede evaluarse. El requisito queda `BLOCKED` con artefacto presente y causa registrada, que es distinto de `BLOCKED` por artefacto ausente |

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
