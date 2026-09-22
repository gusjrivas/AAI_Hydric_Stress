# scientific-closure Specification

## Purpose

Gestionar el cierre auditable de HU7/HU8 (Épica 4), con vínculos a HU2–HU5, sin cambiar hipótesis, alcance ni arquitectura. CRISP-DM: comprensión de datos, preparación, modelado y evaluación. Esta capacidad gobierna el trabajo; experiment-runner conserva los contratos de ejecución. No cambia configuraciones base/+sintéticos/+anomalías/completa ni v3. La preparación no ejecuta A/B/C.

Autoridad científica: `docs/research/controlled-daily-v4-external-pergamino-protocol.md`, decisiones preejecución y ADR-0009/0010/0011. El índice operativo es `openspec/scientific-closure/README.md`. La matriz `requirements.json` vincula cada requisito a tareas, comprobaciones y evidencia esperada (todavía no producida).

## Requirements

### Requirement: SC-GOV-001 Identidad y aislamiento

El orquestador DEBE comprobar worktree, rama, HEAD, upstream y árbol limpio antes de escribir o ejecutar. The system SHALL enforce this requirement.

Criterio de aceptación: Coinciden ruta y rama fijadas; status vacío; se conserva SHA inicial y final. Cualquier discrepancia impide modificaciones.

Comprobación: git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --porcelain=v1 --untracked-files=all

Tarea: sc-01-evidence-scope/T01. Evidencia esperada relativa al directorio de gobernanza de campaña: `session-identity.json`.

#### Scenario: SC-GOV-001 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-002 Autoridad y autorización

El sistema DEBE separar especificación, preparación y autorización de cada etapa; nunca inferir permiso de ejecución de un PASS técnico. The system SHALL enforce this requirement.

Criterio de aceptación: Para cada etapa al despacharla, existe autorización trazable por responsable, alcance y fecha; la ausencia bloquea solo esa etapa. Readiness verifica el mecanismo y registra permisos pendientes, sin exigir B/ledger/C anticipadamente.

Comprobación: Revisión de autorización contra instrucciones de sesión, protocolo y ADR-0011; registrar discrepancias sin resolverlas unilateralmente.

Tarea: sc-02-runtime-readiness/T02. Evidencia esperada relativa al directorio de gobernanza de campaña: `authorizations.json`.

#### Scenario: SC-GOV-002 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-003 Preservación

El sistema DEBE preservar v3, evidencia histórica, main, UI, datos fuente y registros de intentos. The system SHALL enforce this requirement.

Criterio de aceptación: Diff de campaña solo contiene rutas autorizadas; hashes de artefactos históricos preservados; no push/merge/rebase/tag/release/PR sin encargo futuro explícito.

Comprobación: git diff --name-status BASE..HEAD; comparar hashes de archivos históricos sin analizar sus resultados.

Tarea: sc-01-evidence-scope/T03. Evidencia esperada relativa al directorio de gobernanza de campaña: `preservation.json`.

#### Scenario: SC-GOV-003 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-004 Inventario con procedencia

El explorador DEBE clasificar evidencia existente, referenciada, faltante y no inspeccionada sin equiparar estos estados. The system SHALL enforce this requirement.

Criterio de aceptación: Cada entrada tiene ubicación, procedencia, fecha, estado de inspección, HU/afirmación y limitación; faltantes permanecen explícitos.

Comprobación: Contrastar inventario con rutas y documentación permitidas; jamás llenar resultados por inferencia.

Tarea: sc-01-evidence-scope/T04. Evidencia esperada relativa al directorio de gobernanza de campaña: `inventory.json`.

#### Scenario: SC-GOV-004 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-005 Alcance de afirmaciones

El sistema DEBE decidir necesidad de evidencia por afirmación y alcance aprobado, sin hacer obligatorios automáticamente R/H/N/S. The system SHALL enforce this requirement.

Criterio de aceptación: Cada afirmación tiene fuente, evidencia suficiente o brecha; cada complemento REQUIRED/NOT_REQUIRED/UNRESOLVED con justificación anterior a ejecución; no reducir hipótesis tácitamente.

Comprobación: Auditoría de claims.md contra project.md, ADR-0009/0010/0011 y decisiones de cierre.

Tarea: sc-01-evidence-scope/T05. Evidencia esperada relativa al directorio de gobernanza de campaña: `claims-assessment.json`.

#### Scenario: SC-GOV-005 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-006 Separación de roles

El sistema DEBE usar explorador, implementador, checker, crítico y auditor independientes según sus permisos. The system SHALL enforce this requirement.

Criterio de aceptación: Agentes con nombre/descripción/instrucciones; cuatro lectores read-only; implementador no aprueba; máximo cuatro subagentes; modelos y sustituciones explícitos.

Comprobación: python -m unittest discover -s tests -p test_scientific_closure_governance.py; verificar carga efectiva y permisos en Codex.

Tarea: sc-02-runtime-readiness/T06. Evidencia esperada relativa al directorio de gobernanza de campaña: `agent-capabilities.json`.

#### Scenario: SC-GOV-006 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-007 Cambios y dependencias

El orquestador DEBE elegir solo cambios aprobados con dependencias satisfechas y un único escritor por archivo. The system SHALL enforce this requirement.

Criterio de aceptación: Registro identifica cambio, dueño, rutas, dependencias PASS y sesión; lectores revisan snapshot estable; tareas no se cierran con solo tests verdes.

Comprobación: Inspección del DAG, registro de asignaciones y manifiestos de revisión por SHA.

Tarea: sc-02-runtime-readiness/T07. Evidencia esperada relativa al directorio de gobernanza de campaña: `workflow-events.jsonl`.

#### Scenario: SC-GOV-007 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-008 Revisión independiente

El sistema DEBE cerrar cambios solo con PASS del auditor posterior a checker y crítico sin hallazgos materiales abiertos. The system SHALL enforce this requirement.

Criterio de aceptación: Informe identifica snapshot, requisitos revisados, comandos, resultados y hallazgos reproducibles; FAIL corrige y repite; BLOCKED suspende dependientes.

Comprobación: Aplicar operations.md a cada cambio y verificar identidad distinta implementador/auditor.

Tarea: sc-06-scientific-synthesis/T08. Evidencia esperada relativa al directorio de gobernanza de campaña: `audit.json`.

#### Scenario: SC-GOV-008 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-009 Identidad reproducible

Cada ejecución DEBE registrar commit ejecutable, imagen inmutable, configuración, semillas, datos/hashes, comandos, entorno y resultados. The system SHALL enforce this requirement.

Criterio de aceptación: Misma identidad ejecutable e imagen A/B/C; SHA documental separado; constraints contrastados; semillas modelo 42 y bootstrap 20250109, 5000 réplicas.

Comprobación: tests/test_controlled_daily_v4_reproducibility_artifacts.py; tests/test_controlled_daily_v4_environment_validation.py; docker inspect y pip check.

Tarea: sc-02-runtime-readiness/T09. Evidencia esperada relativa al directorio de gobernanza de campaña: `execution-manifest.json`.

#### Scenario: SC-GOV-009 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-010 Causalidad temporal

El sistema DEBE respetar fronteras v4, target observado t+3, P20 train, imputación causal solo de entradas y fit fold-local. The system SHALL enforce this requirement.

Criterio de aceptación: No se agregan ni generan features fuera de etapa autorizada; max target train < min emisión validación; ocho features iguales entre candidatos.

Comprobación: tests/test_controlled_daily_v4_stage_window.py; tests/test_controlled_daily_v4_splits.py; tests/test_controlled_daily_v4_features.py.

Tarea: sc-03-stage-a/T10. Evidencia esperada relativa al directorio de gobernanza de campaña: `temporal-contract-check.json`.

#### Scenario: SC-GOV-010 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-011 Gate A

A DEBE seleccionar y congelar solo con desarrollo 2015–2022 conforme a protocolo y soporte, sin consultar B/C. The system SHALL enforce this requirement.

Criterio de aceptación: Contrato transferible scientific_run, candidato primary_selection y soporte válido; NO_VALID_SELECTION conserva diagnósticos y bloquea B; empate práctico no se llama superioridad.

Comprobación: tests/test_controlled_daily_v4_selection.py; tests/test_controlled_daily_v4_freezing.py; tests/test_controlled_daily_v4_stage_a_integration.py; auditar frozen_config.json.

Tarea: sc-03-stage-a/T11. Evidencia esperada relativa al directorio de gobernanza de campaña: `A/gate-review.json`.

#### Scenario: SC-GOV-011 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-012 Gate B

B DEBE evaluar una sola vez el candidato congelado sobre 2023, tras gate A y autorización. The system SHALL enforce this requirement.

Criterio de aceptación: CANDIDATE_VALIDATED únicamente si MCC>0 y límite inferior CI delta frente a persistencia >=-0.05 con soporte; monoclase o negativo no habilitan C ni otro candidato.

Comprobación: tests/test_controlled_daily_v4_stage_b_runner.py; tests/test_controlled_daily_v4_stage_b_integration.py; contrastar decision.json.

Tarea: sc-04-stage-b/T12. Evidencia esperada relativa al directorio de gobernanza de campaña: `B/gate-review.json`.

#### Scenario: SC-GOV-012 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-013 Custodia de B

B DEBE reservar un intento en registro persistente único antes de analizar valores y conservar toda falla posterior. The system SHALL enforce this requirement.

Criterio de aceptación: Clave fija protocolo/sitio/profundidad/2023; reserva guarda candidato/identidad/hashes; segundo intento bloqueado; recuperación solo de artefactos completos íntegros sin entrenar.

Comprobación: tests/test_controlled_daily_v4_scientific_closure.py: custodia, concurrencia, reserva antes de validación y recuperación.

Tarea: sc-04-stage-b/T13. Evidencia esperada relativa al directorio de gobernanza de campaña: `B/custody-review.json`.

#### Scenario: SC-GOV-013 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-014 Gate C y holdout

C DEBE requerir B validada, autorización adicional e inicialización explícita custodiada; jamás seleccionar con holdout. The system SHALL enforce this requirement.

Criterio de aceptación: Train targets <=2023-12-31; emisiones 2024-01-01..2025-12-28; apertura única 2024–2025; no ajuste/repetición; estado incierto se trata como abierto.

Comprobación: tests/test_controlled_daily_v4_stage_c_admissibility.py; tests/test_controlled_daily_v4_holdout_ledger.py; tests/test_controlled_daily_v4_stage_c_recovery.py.

Tarea: sc-05-stage-c/T14. Evidencia esperada relativa al directorio de gobernanza de campaña: `C/holdout-review.json`.

#### Scenario: SC-GOV-014 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-015 Estadística y soporte

El reporte DEBE conservar indefiniciones, soportes y limitaciones de inferencia del protocolo. The system SHALL enforce this requirement.

Criterio de aceptación: >=2 de 3 folds definidos por familia y >=4000/5000 bootstrap; bloques 30 días no circulares por segmento; null con razón, sin sustitución por cero; no tratar seeds como poblaciones.

Comprobación: tests/test_controlled_daily_v4_bootstrap.py; tests/test_controlled_daily_v4_metrics.py; tests/test_controlled_daily_v4_scientific_closure.py.

Tarea: sc-03-stage-a/T15. Evidencia esperada relativa al directorio de gobernanza de campaña: `statistical-review.json`.

#### Scenario: SC-GOV-015 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-016 Interpretación científica

El cierre DEBE distinguir hechos, resultados, inferencias, limitaciones y pendientes; aceptar conclusiones negativas válidas. The system SHALL enforce this requirement.

Criterio de aceptación: No afirmar estrés fisiológico, mejora general, anticipación operativa, portabilidad o eficacia HITL sin evidencia propia; onset y episode_recall diferenciados.

Comprobación: Revisión frase a frase de síntesis contra claims.md, predicciones autorizadas y métricas con soporte.

Tarea: sc-06-scientific-synthesis/T16. Evidencia esperada relativa al directorio de gobernanza de campaña: `claim-evidence-review.json`.

#### Scenario: SC-GOV-016 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-017 Procedencia desconocida

El sistema DEBE registrar adquisición/licencia/versiones históricas desconocidas y resolver su admisibilidad antes de ejecutar. The system SHALL enforce this requirement.

Criterio de aceptación: No se inventan fecha ni URL real de descarga; fuentes verificadas se distinguen de adquisición efectiva; conflicto normativo o licencia sin decisión bloquea gate de preparación.

Comprobación: Revisar manifiesto v4, ADR-0011 y evidencia documental aportada por responsable; no consultar valores reservados.

Tarea: sc-02-runtime-readiness/T17. Evidencia esperada relativa al directorio de gobernanza de campaña: `provenance-assessment.json`.

#### Scenario: SC-GOV-017 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-018 Backup y recuperación

El sistema DEBE respaldar evidencia y ledger coherentemente sin permitir volver a un estado previo para obtener otro intento. The system SHALL enforce this requirement.

Criterio de aceptación: Copia nueva con hashes y segunda copia independiente; SQLite quiescente o API backup; ensayo de restauración con fixtures; intento incompleto no liberado.

Comprobación: Ensayo sintético de backup/restauración más tests/test_controlled_daily_v4_stage_c_recovery.py; revisión de rutas por responsable.

Tarea: sc-02-runtime-readiness/T18. Evidencia esperada relativa al directorio de gobernanza de campaña: `recovery-rehearsal.json`.

#### Scenario: SC-GOV-018 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-019 Checkpoints

El orquestador DEBE crear commits pequeños revisados y distinguir commit de checkpoint de cierre auditado. The system SHALL enforce this requirement.

Criterio de aceptación: git add con rutas explícitas; diff completo y staged revisados; SHA y alcance por checkpoint; no git add -A ni push en preparación.

Comprobación: git diff --check; git diff --cached; git log; registro de checkpoints y estado.

Tarea: sc-02-runtime-readiness/T19. Evidencia esperada relativa al directorio de gobernanza de campaña: `checkpoints.json`.

#### Scenario: SC-GOV-019 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-020 Validación de especificaciones

El sistema DEBE validar OpenSpec, TOML, referencias, IDs y matriz antes de entregar preparación. The system SHALL enforce this requirement.

Criterio de aceptación: OpenSpec estricto para capacidad y cambios nuevos; tests documentales pasan; cada requisito tiene tarea/comprobación/artefacto; ningún PASS estructural equivale a cierre científico.

Comprobación: OpenSpec 1.13.1 validate; python -m unittest discover -s tests -p test_scientific_closure_governance.py.

Tarea: sc-02-runtime-readiness/T20. Evidencia esperada relativa al directorio de gobernanza de campaña: `structural-validation.json`.

#### Scenario: SC-GOV-020 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-021 Regresión condicional

R DEBE activarse solo si se pretende sostener desempeño sobre humedad continua y la evidencia existente no lo cubre. The system SHALL enforce this requirement.

Criterio de aceptación: NOT_REQUIRED para sola clasificación P20; REQUIRED exige diseño R, runner validado, MAE/RMSE en m3/m3 y comparación contra persistencia; sin confundir con MCC.

Comprobación: Revisión claims-assessment y fixtures específicos del diseño auxiliary_soil_regression_v1 antes de cualquier ejecución.

Tarea: sc-07-aux-regression/T21. Evidencia esperada relativa al directorio de gobernanza de campaña: `auxiliary/R/review.json`.

#### Scenario: SC-GOV-021 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-022 HITL condicional

H DEBE activarse si se sostendrá aporte cuantitativo de correcciones y falta evaluación prospectiva válida. The system SHALL enforce this requirement.

Criterio de aceptación: Tres brazos y maduración separados, 20 eventos/seed conforme diseño H; simulación identificada; implementación funcional HU5 no prueba beneficio.

Comprobación: Revisión de fechas de feedback, separación de refit/correcciones, fixtures del diseño auxiliary_hitl_v1.

Tarea: sc-08-aux-hitl/T22. Evidencia esperada relativa al directorio de gobernanza de campaña: `auxiliary/H/review.json`.

#### Scenario: SC-GOV-022 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-023 Anomalías condicionales

N DEBE activarse si se afirmará detección reservada de corrupciones y la demostración disponible es insuficiente. The system SHALL enforce this requirement.

Criterio de aceptación: Fit solo train, inyección reservada conocida y métricas/soporte conforme diseño N; no convertir anomalías simuladas en fallas reales.

Comprobación: Fixtures de inyección, fit/reserva y matriz de confusión del diseño auxiliary_anomalies_v1.

Tarea: sc-09-aux-anomalies/T23. Evidencia esperada relativa al directorio de gobernanza de campaña: `auxiliary/N/review.json`.

#### Scenario: SC-GOV-023 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-024 Robustez condicional

S DEBE activarse si se sostendrá robustez ante ausencia de mediciones/ruido más allá de evidencia ya válida. The system SHALL enforce this requirement.

Criterio de aceptación: Cuatro condiciones fijas, cinco seeds, target limpio común, máscaras e imputación registradas; escasez de etiquetas no equivale a sensores ausentes.

Comprobación: Fixtures de grilla causal, perturbaciones y fechas comunes del diseño auxiliary_robustness_v1.

Tarea: sc-10-aux-robustness/T24. Evidencia esperada relativa al directorio de gobernanza de campaña: `auxiliary/S/review.json`.

#### Scenario: SC-GOV-024 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado

### Requirement: SC-GOV-025 Cierre científico

El auditor DEBE evaluar el alcance científico completo aprobado y no solo software o candidato. The system SHALL enforce this requirement.

Criterio de aceptación: Todas las afirmaciones tienen evidencia o limitación aceptada; terminal negativo válido documentado; complementos justificados; memoria caps.2/3 trazada; ningún obligatorio sin resolver.

Comprobación: Auditoría final independiente requisito por requisito y evaluación de suficiencia científica sobre el alcance aprobado.

Tarea: sc-06-scientific-synthesis/T25. Evidencia esperada relativa al directorio de gobernanza de campaña: `scientific-closure-audit.json`.

#### Scenario: SC-GOV-025 aceptación verificable

- **GIVEN** el cambio aplicable y sus dependencias documentadas
- **WHEN** se contrasta el requisito con la comprobación y el artefacto indicado
- **THEN** se acepta únicamente si se cumple el criterio anterior; la evidencia faltante queda BLOCKED y la contradicción comprobada queda FAIL, sin fabricar un resultado
