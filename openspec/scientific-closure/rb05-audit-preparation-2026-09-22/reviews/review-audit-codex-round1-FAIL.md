
• # Auditoría científica final RB-05 — snapshot 88ced62

  Veredicto: FAIL. El snapshot tiene la identidad exigida y las
  validaciones documentales pasan, pero encontré contradicciones
  materiales en la cronología registrada de los gates A→B→C. El
  registro afirma que B y C fueron aprobadas con auditorías previas
  que, según sus propios timestamps, todavía no habían ocurrido.
  También conserva una afirmación falsa sobre Docker en la trazabilidad
  a la memoria. No ejecuté campañas ni runners, no abrí el holdout y no
  modifiqué archivos.

  ## 1. Identidad del snapshot auditado

  Repositorio: /home/gus/work/AAI_Hydric_Stress_scientific_closure
  Rama: feat/scientific-closure-final-main
  HEAD completo: 88ced622dd653cf6e6f892fd8212a2857acb77b7
  Base de comparación: 22da0dd00bf84d9434582cc414a98d398debd2d0

  Estos son los comandos de la fase 1 y sus salidas reales. Los
  comandos sin texto debajo produjeron salida vacía y código 0.

  $ git status --porcelain --untracked-files=all

  $ git branch --show-current
  feat/scientific-closure-final-main

  $ git rev-parse HEAD
  88ced622dd653cf6e6f892fd8212a2857acb77b7

  $ git rev-parse origin/main
  2079d03dded19e0229e34873aa98eb4ed0c757ae

  $ git rev-parse origin/feat/scientific-closure
  0ebd5bc5f69ed98362b5e4300b168809ff1f38be

  $ git merge-base --is-ancestor origin/main HEAD
  $ echo $?
  0

  $ git merge-base --is-ancestor origin/feat/scientific-closure HEAD
  $ echo $?
  0

  $ git diff --name-status 22da0dd00bf84d9434582cc414a98d398debd2d0
  88ced62
  M     openspec/scientific-closure/README.md
  A     openspec/scientific-closure/rb05-audit-preparation-2026-09-22/rb05-
  dossier.md
  A     openspec/scientific-closure/rb05-audit-preparation-2026-09-22/
  session-identity.json

  $ git diff --stat 22da0dd00bf84d9434582cc414a98d398debd2d0 88ced62
   openspec/scientific-closure/README.md              |   4 +
   .../rb05-dossier.md                                | 215 +++++++++++
   ++++++++++
   .../session-identity.json                          |  62 ++++++
   3 files changed, 281 insertions(+)

  $ git diff --check 22da0dd00bf84d9434582cc414a98d398debd2d0 88ced62

  La fase 1 permite continuar: rama, HEAD, limpieza y relaciones de
  ancestro coinciden. El diff de preparación no contiene cambios Python
  ni resultados científicos.

  ## 2. Archivos y fuentes examinadas

  Leí la especificación de 25 requisitos (openspec/specs/scientific-
  closure/spec.md:9), openspec/scientific-closure/requirements.json:1,
  openspec/scientific-closure/traceability.md:1, openspec/scientific-
  closure/claims.md:1, openspec/scientific-closure/decisions.md:1,
  openspec/scientific-closure/plan.md:1, openspec/scientific-closure/
  operations.md:1, checkpoint vigente (openspec/scientific-closure/
  current-execution-checkpoint.md:1), README (openspec/scientific-
  closure/README.md:1), proyecto (openspec/project.md:1), protocolo v3
  (docs/research/protocolo-experimental-v3.md:1) y ADR-0011 (docs/
  adr/0011-protocolo-controlled-daily-v4-external-pergamino.md:1).

  Contrasté el dossier RB-05 (openspec/scientific-closure/rb05-audit-
  preparation-2026-09-22/rb05-dossier.md:1) y su identidad de sesión
  (openspec/scientific-closure/rb05-audit-preparation-2026-09-22/
  session-identity.json:1) con la tabla de reconciliación (openspec/
  scientific-closure/reconciliation-2026-09-22/reconciliation-
  table.md:1), la trazabilidad a la memoria (openspec/scientific-
  closure/reconciliation-2026-09-22/thesis-traceability.md:1), el
  directorio sufficiency-review-2026-09-22 (openspec/scientific-
  closure/sufficiency-review-2026-09-22/gd12-sufficiency-dossier.md:1),
  la síntesis RB-04 (docs/research/scientific-closure-synthesis-2026-
  09-22.md:1), HU8 (docs/research/hu8-resultados-discusion-
  conclusiones.md:1), las tareas de sc-06 (openspec/changes/sc-06-
  scientific-synthesis/tasks.md:1) y los informes preservados de sc-06
  (openspec/changes/sc-06-scientific-synthesis/reviews/README.md:1) y H
  (openspec/changes/sc-08-aux-hitl/reviews/README.md:1). Leí los
  artefactos de gobernanza A/B/C del runtime mediante sus execution-
  record.json y gate-review.json, y el registro openspec/scientific-
  closure/changes.json:1. No abrí artefactos de valores del holdout.

  Los registros de A, B y C incluyen metadatos de auditoría y
  atestaciones retrospectivas; no encontré informes verbatim
  individuales de sus auditores en los directorios de gobernanza
  inspeccionados. Las auditorías posteriores de H y de la primera ronda
  RB-05 corroboran resultados y custodias, pero no sustituyen una
  prueba contemporánea del orden de los gates. Esta limitación importa
  para los hallazgos cronológicos.

  ## 3. Auditoría individual de SC-GOV-001..025

  En la columna «Estado» consigno la propuesta vigente reconstruida
  desde la matriz, no mi aprobación. «Sostenido» admite las
  limitaciones expresas; NOT_APPLICABLE significa decisión condicional
  auditada, no experimento ejecutado. Cada criterio está transcrito de
  la spec; cada cita de evidencia remite a una línea primaria
  independiente del dossier.

   ID y título; criterio de aceptación textual
    001 Identidad y aislamiento (openspec/specs/scientific-closure/
    spec.md:11). «Coinciden ruta y rama fijadas; status vacío; se
    conserva SHA inicial y final. Cualquier discrepancia impide
    modificaciones.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Mi preflight da rama, HEAD y status exigidos; identidad RB-05:19
    (openspec/scientific-closure/rb05-audit-preparation-2026-09-22/
    session-identity.json:19): «"head_at_start":
    "22da0dd00bf84d9434582cc414a98d398debd2d0"».
   Limitación o condición; conclusión propia
    El SHA final lo fija este informe. Sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    002 Autoridad y autorización (openspec/specs/scientific-closure/
    spec.md:27). «Para cada etapa al despacharla, existe autorización
    trazable por responsable, alcance y fecha; la ausencia bloquea solo
    esa etapa. Readiness verifica el mecanismo y registra permisos
    pendientes, sin exigir B/ledger/C anticipadamente.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Authorizations:11 (openspec/scientific-closure/readiness-
    resolution-linux-2026-09-20/authorizations.json:11): «A technical
    PASS never implies execution permission.» Las aprobaciones A/B/C
    (openspec/scientific-closure/changes.json:300) registran
    responsable y alcance.
   Limitación o condición; conclusión propia
    La autorización existe; no acredita por sí misma gates satisfechos.
    Sostenido en su criterio de permiso.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    003 Preservación (openspec/specs/scientific-closure/spec.md:43).
    «Diff de campaña solo contiene rutas autorizadas; hashes de
    artefactos históricos preservados; no push/merge/rebase/tag/
    release/PR sin encargo futuro explícito.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Los hashes históricos figuran en openspec/changes/sc-01-evidence-
    scope/preservation.json:23. Pero ADR-0011:105 (docs/adr/0011-
    protocolo-controlled-daily-v4-external-pergamino.md:105) reconoce
    «dos pushes históricos» bajo una autorización que los
    prohibía; :127 (docs/adr/0011-protocolo-controlled-daily-v4-
    external-pergamino.md:127) dice «no subsana el incumplimiento».
   Limitación o condición; conclusión propia
    v3 y resultados permanecen preservados, pero el criterio textual
    incluye la prohibición infringida. No sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    004 Inventario con procedencia (openspec/specs/scientific-closure/
    spec.md:59). «Cada entrada tiene ubicación, procedencia, fecha,
    estado de inspección, HU/afirmación y limitación; faltantes
    permanecen explícitos.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Inventario:32 (openspec/changes/sc-01-evidence-scope/
    inventory.json:32): «"state": "REFERENCED", "inspection":
    "HASH_ONLY"» para EV-01A; inventario documental:3 (openspec/
    scientific-closure/inventory.md:3) fecha la inspección global.
   Limitación o condición; conclusión propia
    La fecha es global y algunos campos se expresan por estado o
    agrupación, no como clave en cada entrada JSON. No detecté un
    faltante ocultado que altere el cierre. Sostenido con esa
    limitación de granularidad.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    005 Alcance de afirmaciones (openspec/specs/scientific-closure/
    spec.md:75). «Cada afirmación tiene fuente, evidencia suficiente o
    brecha; cada complemento REQUIRED/NOT_REQUIRED/UNRESOLVED con
    justificación anterior a ejecución; no reducir hipótesis
    tácitamente.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Claims:157 (openspec/scientific-closure/claims.md:157): «pendiente
    de la auditoría única del snapshot reconciliado (RB-05)».
   Limitación o condición; conclusión propia
    CL-10 sigue condicionada; la decisión GD-12 antecede a la
    ejecución, pero su auditoría fue posterior. Sostenido con
    limitación.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    006 Separación de roles (openspec/specs/scientific-closure/
    spec.md:91). «Agentes con nombre/descripción/instrucciones; cuatro
    lectores read-only; implementador no aprueba; máximo cuatro
    subagentes; modelos y sustituciones explícitos.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Capacidades:29 (openspec/scientific-closure/readiness-resolution-
    linux-2026-09-20/agent-capabilities.json:29): «those profiles are
    not loadable. The substitution is declared here and is NOT
    presented as compliance with the configured profiles.»
   Limitación o condición; conclusión propia
    Modelo efectivo no introspectable; aislamiento de comandos no
    equivale a aislamiento del proceso completo. Sostenido sólo con la
    sustitución declarada.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    007 Cambios y dependencias (openspec/specs/scientific-closure/
    spec.md:107). «Registro identifica cambio, dueño, rutas,
    dependencias PASS y sesión; lectores revisan snapshot estable;
    tareas no se cierran con solo tests verdes.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Changes:328 (openspec/scientific-closure/changes.json:328) afirma
    «sc-03 PASS» para aprobar B a las 03:20; A terminó a las 03:39:29
    (/home/gus/scientific-closure-runtime/evidence/governance/closure-
    campaign-2026-09-21/sc-03-stage-a/execution-record.json:21) y su
    PASS registrado es 04:30 (openspec/scientific-closure/
    changes.json:225). C:415 (openspec/scientific-closure/
    changes.json:415) repite el patrón respecto de B.
   Limitación o condición; conclusión propia
    Las dependencias no podían estar en PASS en los instantes
    registrados. No sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    008 Revisión independiente (openspec/specs/scientific-closure/
    spec.md:123). «Informe identifica snapshot, requisitos revisados,
    comandos, resultados y hallazgos reproducibles; FAIL corrige y
    repite; BLOCKED suspende dependientes.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Tareas sc-06:16 (openspec/changes/sc-06-scientific-synthesis/
    tasks.md:16): «No corrió como pasada separada» el checker; :17
    (openspec/changes/sc-06-scientific-synthesis/tasks.md:17): «No
    corrió sobre este snapshot» el crítico. Aun así T08 figura [x]
    (openspec/changes/sc-06-scientific-synthesis/tasks.md:11).
   Limitación o condición; conclusión propia
    No existe la cadena completa exigida para acreditar T08 en sc-06.
    La auditoría acotada de reconciliación lo declara. No sostenido
    como PASS vigente.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    009 Identidad reproducible (openspec/specs/scientific-closure/
    spec.md:139). «Misma identidad ejecutable e imagen A/B/C; SHA
    documental separado; constraints contrastados; semillas modelo 42 y
    bootstrap 20250109, 5000 réplicas.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Checkpoint:37 (openspec/scientific-closure/current-execution-
    checkpoint.md:37) distingue SHA ejecutable 214735e… del
    documental:38 (openspec/scientific-closure/current-execution-
    checkpoint.md:38); semillas:41 (openspec/scientific-closure/
    current-execution-checkpoint.md:41): «bootstrap 20250109, modelo
    42».
   Limitación o condición; conclusión propia
    La fila 3.5 de RB-06 contiene una afirmación ambiental obsoleta; no
    cambia la identidad registrada de A/B/C. Sostenido para las
    corridas, con ese defecto documental separado.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    010 Causalidad temporal (openspec/specs/scientific-closure/
    spec.md:155). «No se agregan ni generan features fuera de etapa
    autorizada; max target train < min emisión validación; ocho
    features iguales entre candidatos.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Control temporal:31 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-03-stage-a/temporal-
    contract-check.json:31): «Invariante causal max(target_train) <
    min(feature_validation) en 3 outer y 9 inner folds», PASS.
   Limitación o condición; conclusión propia
    El artefacto es una atestación retrospectiva; no verifica
    imputación. La corrección RB-04 remite esa propiedad al código.
    Sostenido para el criterio citado.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    011 Gate A (openspec/specs/scientific-closure/spec.md:171).
    «Contrato transferible scientific_run, candidato primary_selection
    y soporte válido; NO_VALID_SELECTION conserva diagnósticos y
    bloquea B; empate práctico no se llama superioridad.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Gate A:20 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-03-stage-a/gate-
    review.json:20):
    «tie_break_simplicity_predeclarada_no_superioridad».
   Limitación o condición; conclusión propia
    El resultado científico de A se sostiene; su auditoría registrada a
    las 04:30 no acredita avance oportuno a B. Sostenido para selección
    y soporte, no para el despacho siguiente.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    012 Gate B (openspec/specs/scientific-closure/spec.md:187).
    «CANDIDATE_VALIDATED únicamente si MCC>0 y límite inferior CI delta
    frente a persistencia >=-0.05 con soporte; monoclase o negativo no
    habilitan C ni otro candidato.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Gate B:18 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-04-stage-b/gate-
    review.json:18): «"verdict": "CANDIDATE_VALIDATED"»; la regla
    numérica figura en :16 (/home/gus/scientific-closure-runtime/
    evidence/governance/closure-campaign-2026-09-21/sc-04-stage-b/gate-
    review.json:16). Pero plan:22 (openspec/scientific-closure/
    plan.md:22) exige auditor A PASS antes de B; B empezó 03:51 (/home/
    gus/scientific-closure-runtime/evidence/governance/closure-
    campaign-2026-09-21/sc-04-stage-b/execution-record.json:19), frente
    al PASS de A 04:30 (openspec/scientific-closure/changes.json:225).
   Limitación o condición; conclusión propia
    La no inferioridad numérica está respaldada, pero la secuencia
    autorizada de gate no lo está. No sostenido como cumplimiento
    integral.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    013 Custodia de B (openspec/specs/scientific-closure/spec.md:203).
    «Clave fija protocolo/sitio/profundidad/2023; reserva guarda
    candidato/identidad/hashes; segundo intento bloqueado; recuperación
    solo de artefactos completos íntegros sin entrenar.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Custodia:21 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-04-stage-b/custody-
    review.json:21): «Reserva exclusiva ANTES de cargar valores de
    2023», PASS; :24 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-04-stage-b/custody-
    review.json:24) registra una sola fila de intento.
   Limitación o condición; conclusión propia
    Custodia técnica distinguida de la aprobación previa de A.
    Sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    014 Gate C y holdout (openspec/specs/scientific-closure/
    spec.md:219). «Train targets <=2023-12-31; emisiones 2024-01-
    01..2025-12-28; apertura única 2024–2025; no ajuste/repetición;
    estado incierto se trata como abierto.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Registro C:31 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-05-stage-c/execution-
    record.json:31) fecha su arranque a las 04:06:10; plan:23
    (openspec/scientific-closure/plan.md:23) exige auditor B PASS; éste
    figura a 04:30 (openspec/scientific-closure/changes.json:311).
   Limitación o condición; conclusión propia
    La apertura única y la ausencia de selección posterior fueron
    auditadas; la precondición temporal del gate no está acreditada y
    el registro la contradice. No sostenido como gate íntegro.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    015 Estadística y soporte (openspec/specs/scientific-closure/
    spec.md:235). «>=2 de 3 folds definidos por familia y >=4000/5000
    bootstrap; bloques 30 días no circulares por segmento; null con
    razón, sin sustitución por cero; no tratar seeds como poblaciones.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Revisión estadística:15 (/home/gus/scientific-closure-runtime/
    evidence/governance/closure-campaign-2026-09-21/sc-03-stage-a/
    statistical-review.json:15): «"A": {"valid": 5000, "discarded": 0,
    "segments": 3»; :35 (/home/gus/scientific-closure-runtime/evidence/
    governance/closure-campaign-2026-09-21/sc-03-stage-a/statistical-
    review.json:35) declara aproximadamente 24 unidades efectivas en C.
   Limitación o condición; conclusión propia
    Intervalos percentiles sin corrección por multiplicidad ni
    calibración de cobertura. Sostenido con limitaciones.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    016 Interpretación científica (openspec/specs/scientific-closure/
    spec.md:251). «No afirmar estrés fisiológico, mejora general,
    anticipación operativa, portabilidad o eficacia HITL sin evidencia
    propia; onset y episode_recall diferenciados.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Síntesis:390 (docs/research/scientific-closure-synthesis-2026-09-
    22.md:390): «La pista humana no sostiene ninguna afirmación
    cuantitativa.» La sección 11 (docs/research/scientific-closure-
    synthesis-2026-09-22.md:541) enumera lo no afirmado.
   Limitación o condición; conclusión propia
    La revisión RB-04 es documental y no autoriza eficacia general.
    Sostenido con limitaciones.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    017 Procedencia desconocida (openspec/specs/scientific-closure/
    spec.md:267). «No se inventan fecha ni URL real de descarga;
    fuentes verificadas se distinguen de adquisición efectiva;
    conflicto normativo o licencia sin decisión bloquea gate de
    preparación.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Evaluación de procedencia:118 (openspec/scientific-closure/
    readiness-resolution-linux-2026-09-20/provenance-and-licence-
    assessment.json:118): «The effective acquisition date of both files
    remains UNKNOWN».
   Limitación o condición; conclusión propia
    Licencia específica NASA POWER aún PENDING_CONFIRMATION en el
    manifiesto; admisibilidad decidida con límites. Sostenido con
    limitaciones.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    018 Backup y recuperación (openspec/specs/scientific-closure/
    spec.md:283). «Copia nueva con hashes y segunda copia
    independiente; SQLite quiescente o API backup; ensayo de
    restauración con fixtures; intento incompleto no liberado.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Checkpoint:29 (openspec/scientific-closure/current-execution-
    checkpoint.md:29) identifica el «disco USB 1» físicamente distinto;
    ensayo:25 (openspec/scientific-closure/readiness-resolution-linux-
    2026-09-20/recovery-rehearsal.json:25) registra sqlite3
    Connection.backup().
   Limitación o condición; conclusión propia
    El ensayo temprano fue copia lógica; la segunda copia física se
    acreditó después. No protege frente a edición deliberada con
    privilegios. Sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    019 Checkpoints (openspec/specs/scientific-closure/spec.md:299).
    «git add con rutas explícitas; diff completo y staged revisados;
    SHA y alcance por checkpoint; no git add -A ni push en
    preparación.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    ADR-0011:127 (docs/adr/0011-protocolo-controlled-daily-v4-external-
    pergamino.md:127): «no subsana el incumplimiento: RK-14 permanece
    registrado como desviación reconocida».
   Limitación o condición; conclusión propia
    La aceptación textual prohíbe push en preparación y hubo dos.
    Reconocerlos no satisface la cláusula. No sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    020 Validación de especificaciones (openspec/specs/scientific-
    closure/spec.md:315). «OpenSpec estricto para capacidad y cambios
    nuevos; tests documentales pasan; cada requisito tiene tarea/
    comprobación/artefacto; ningún PASS estructural equivale a cierre
    científico.»
   Estado propuesto
    PASS
   Evidencia primaria comprobada y cita textual exacta
    Mis 11 validaciones OpenSpec dieron exit 0; el checker (scripts/
    check_scientific_closure.py:1) devolvió literalmente «PASS
    (estructura; runtime no verificado)».
   Limitación o condición; conclusión propia
    Resultado estructural, sin inferencia científica. Sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    021 Regresión condicional (openspec/specs/scientific-closure/
    spec.md:331). «NOT_REQUIRED para sola clasificación P20; REQUIRED
    exige diseño R, runner validado, MAE/RMSE en m3/m3 y comparación
    contra persistencia; sin confundir con MCC.»
   Estado propuesto
    NOT_APPLICABLE
   Evidencia primaria comprobada y cita textual exacta
    openspec/scientific-closure/sufficiency-review-2026-09-22/
    auxiliary/R/review.json:24: «SC-GOV-021 usa «solo si»». La decisión
    RB-03 recibió PASS independiente (openspec/changes/sc-07-aux-
    regression/reviews/review-audit-gd12.md:1).
   Limitación o condición; conclusión propia
    No se midió error continuo de humedad. NOT_APPLICABLE sostenido,
    condicionado al alcance P20.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    022 HITL condicional (openspec/specs/scientific-closure/
    spec.md:347). «Tres brazos y maduración separados, 20 eventos/seed
    conforme diseño H; simulación identificada; implementación
    funcional HU5 no prueba beneficio.»
   Estado propuesto
    PASS_WITH_LIMITATIONS
   Evidencia primaria comprobada y cita textual exacta
    Auditor H, CK-09 (openspec/changes/sc-08-aux-hitl/reviews/review-
    audit-final.md:48): «10/10 en las 6 agrupaciones». La síntesis:384
    (docs/research/scientific-closure-synthesis-2026-09-22.md:384)
    registra «Tasa de detección humana: 0 de 4.»
   Limitación o condición; conclusión propia
    Humano: sólo aceptación, cegamiento parcial; rechazo y
    recalibración sucesiva no ejercitados científicamente. INV-10 y
    reproducción estricta no verificados por aquel auditor. Sostenido
    sólo para el mecanismo acotado.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    023 Anomalías condicionales (openspec/specs/scientific-closure/
    spec.md:363). «Fit solo train, inyección reservada conocida y
    métricas/soporte conforme diseño N; no convertir anomalías
    simuladas en fallas reales.»
   Estado propuesto
    NOT_APPLICABLE
   Evidencia primaria comprobada y cita textual exacta
    HU8 §8.2:194 (docs/research/hu8-resultados-discusion-
    conclusiones.md:194): «Evidencia mixta (F1/MCC débil-positivo, AP
    negativo en 5/5 semillas)». openspec/scientific-closure/
    sufficiency-review-2026-09-22/auxiliary/N/review.json:24 funda la
    clasificación en fuentes independientes de GD-12.
   Limitación o condición; conclusión propia
    Es aporte como predictor, sin cifra de detección reservada.
    NOT_APPLICABLE sostenido.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    024 Robustez condicional (openspec/specs/scientific-closure/
    spec.md:379). «Cuatro condiciones fijas, cinco seeds, target limpio
    común, máscaras e imputación registradas; escasez de etiquetas no
    equivale a sensores ausentes.»
   Estado propuesto
    NOT_APPLICABLE bajo CL-08
   Evidencia primaria comprobada y cita textual exacta
    openspec/scientific-closure/sufficiency-review-2026-09-22/
    auxiliary/S/review.json:106: «en cuanto la síntesis científica
    pendiente (RB-04) enuncie CUALQUIER resultado de robustez» se
    reabre. HU8 §8.4:216 (docs/research/hu8-resultados-discusion-
    conclusiones.md:216) declara 75,96 % de cobertura real.
   Limitación o condición; conclusión propia
    Leí la síntesis completa: describe imputación v3 como amenaza, sin
    resultado de robustez ante ausencia de mediciones. La cláusula no
    se activa en este snapshot. NOT_APPLICABLE sostenido bajo ese
    límite vivo.
  ─────────────────────────────────────────────────────────────────────
   ID y título; criterio de aceptación textual
    025 Cierre científico (openspec/specs/scientific-closure/
    spec.md:395). «Todas las afirmaciones tienen evidencia o limitación
    aceptada; terminal negativo válido documentado; complementos
    justificados; memoria caps.2/3 trazada; ningún obligatorio sin
    resolver.»
   Estado propuesto
    PENDIENTE
   Evidencia primaria comprobada y cita textual exacta
    Plan:24 (openspec/scientific-closure/plan.md:24): «Auditor final
    PASS sobre suficiencia del alcance completo». La trazabilidad a
    memoria se contradice entre sus filas 3.4 y 3.5 (openspec/
    scientific-closure/reconciliation-2026-09-22/thesis-
    traceability.md:72), y quedan requisitos no sostenidos arriba.
   Limitación o condición; conclusión propia
    Los cuatro primeros términos tienen entregables, pero el cuarto
    contiene un dato falso y el quinto no se cumple. Bloqueado;
    PENDIENTE es el estado escrito correcto, sin PASS derivable.

  Verificación matemática: la spec tiene 25 IDs únicos y
  requirements.json tiene 25, en el mismo orden. Esta tabla contiene 25
  filas. Sus estados propuestos suman 14 PASS + 7 PASS_WITH_LIMITATIONS
  + 3 NOT_APPLICABLE + 1 PENDIENTE = 25. Mi adjudicación suma 18
  sostenidos + 6 no sostenidos + 1 bloqueado = 25.

  ## 4. Intentos de refutación

   Hipótesis atacada
    1. Las secciones poscampaña superseden los estados históricos
    002/003/009.
   Comandos, búsquedas o comparación; evidencia encontrada
    Comparé traceability:46 (openspec/scientific-closure/
    traceability.md:46), la sección de integración en :222 (openspec/
    scientific-closure/traceability.md:222), y checkpoint:3 (openspec/
    scientific-closure/current-execution-checkpoint.md:3). La sección
    histórica declara que A/B/C no se habían ejecutado; la vigente
    registra la ejecución.
   Conclusión e impacto
    Supersesión sostenida para la cronología documental. No cura la
    infracción histórica de push de 003 ni el nuevo hallazgo sobre
    gates.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    2. R/N/S NOT_APPLICABLE no dependen de razonamiento circular.
   Comandos, búsquedas o comparación; evidencia encontrada
    Comparé el «solo si» de 021 (openspec/specs/scientific-closure/
    spec.md:333) con el «si» de 023/024 (openspec/specs/scientific-
    closure/spec.md:365), openspec/project.md:11, HU8 §8.2 y los tres
    review.json. El auditor RB-03 (openspec/changes/sc-07-aux-
    regression/reviews/review-audit-gd12.md:8) comprobó el mismo punto
    contra fuentes originales.
   Conclusión e impacto
    Sostenida con alcance limitado: R deriva de la condición necesaria;
    N/S se justifican positivamente por el alcance. claims.md,
    redactado con GD-12, queda como registro y no como prueba
    independiente.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    3. RB-04 no activa la reapertura de S.
   Comandos, búsquedas o comparación; evidencia encontrada
    Leí las 552 líneas de la síntesis (docs/research/scientific-
    closure-synthesis-2026-09-22.md:1) y busqué robust, imputación y
    afirmaciones positivas. El ítem 5(e) (docs/research/scientific-
    closure-synthesis-2026-09-22.md:254) trata la imputación como
    límite; §11 (docs/research/scientific-closure-synthesis-2026-09-
    22.md:541) excluye robustez ante sensores caídos.
   Conclusión e impacto
    No activada en este snapshot. Cualquier nueva afirmación de
    robustez exige repetir esta comprobación.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    4. H sostiene exactamente 022, sin beneficio humano.
   Comandos, búsquedas o comparación; evidencia encontrada
    Contrasté auditor H (openspec/changes/sc-08-aux-hitl/reviews/
    review-audit-final.md:12), claims CL-06 (openspec/scientific-
    closure/claims.md:153) y síntesis §6 (docs/research/scientific-
    closure-synthesis-2026-09-22.md:297): tres brazos, cinco semillas,
    20 eventos, pista simulada separada y humano 0/4.
   Conclusión e impacto
    Sostenida con limitaciones; no acredita pericia, mejora atribuible
    al humano ni eficacia agronómica.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    5. Ningún FAIL se usa como aprobación.
   Comandos, búsquedas o comparación; evidencia encontrada
    Leí los dos informes: ronda 1 (openspec/changes/sc-06-scientific-
    synthesis/reviews/review-audit-final-round1-FAIL.md:18) y ronda 2
    (openspec/changes/sc-06-scientific-synthesis/reviews/review-audit-
    final-round2-FAIL.md:19). `git show f355272:...
   Conclusión e impacto
    sha256sumdio respectivamenteb75c1023…c5f6d2y7bd872b3…b2cf`,
    idénticos a los archivos preservados.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    6. Se satisfacen los cinco términos de 025.
   Comandos, búsquedas o comparación; evidencia encontrada
    Crucé spec:399 (openspec/specs/scientific-closure/spec.md:399),
    claims final:146 (openspec/scientific-closure/claims.md:146), A/B/
    C/H, RB-03 y RB-06 (openspec/scientific-closure/reconciliation-
    2026-09-22/thesis-traceability.md:1). Hay terminal negativo y
    complementos justificados, pero RB-06 contiene la contradicción
    Docker y los gates tienen incumplimientos temporales.
   Conclusión e impacto
    Refutada. El quinto término, «ningún obligatorio sin resolver»,
    falla; el cuarto necesita corrección documental. Impide PASS de 025
    y GF.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    7. No queda obligatorio BLOCKED, PENDIENTE o UNRESOLVED.
   Comandos, búsquedas o comparación; evidencia encontrada
    La matriz deja 025 PENDIENTE (openspec/scientific-closure/
    traceability.md:368); sc-06/T25 (openspec/changes/sc-06-scientific-
    synthesis/tasks.md:13) sigue sin marcar, y mi auditoría identifica
    otros requisitos no sostenidos. Los changes condicionales sc-
    07/09/10 permanecen BLOCKED por aplicabilidad negativa y no son,
    por ese solo hecho, experimentos obligatorios pendientes.
   Conclusión e impacto
    Refutada para los requisitos obligatorios de cierre.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    8. «9 de 10» frente a diez filas cubiertas está supersedido.
   Comandos, búsquedas o comparación; evidencia encontrada
    Conté las diez filas históricas 83–92 (openspec/scientific-closure/
    claims.md:83) y comparé la clasificación final (openspec/
    scientific-closure/claims.md:113), que declara CL-10 pendiente de
    RB-05 en :157 (openspec/scientific-closure/claims.md:157).
   Conclusión e impacto
    Sí está supersedida como estado vigente, aunque la inconsistencia
    histórica se conserva. Hay nueve afirmaciones resueltas y CL-10
    condicionada.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    9. El ~24 % imputado acompaña el uso vigente de v3.
   Comandos, búsquedas o comparación; evidencia encontrada
    Busqué 75,96, 24 % y causal_ffill en HU8 §8.4 (docs/research/hu8-
    resultados-discusion-conclusiones.md:214), claims CL-04/08
    (openspec/scientific-closure/claims.md:151), síntesis §5(e) (docs/
    research/scientific-closure-synthesis-2026-09-22.md:254) y RB-06
    fila 2.12 (openspec/scientific-closure/reconciliation-2026-09-22/
    thesis-traceability.md:61).
   Conclusión e impacto
    Declarada en las fuentes interpretativas vigentes inspeccionadas.
    No es prueba de robustez; el efecto de imputar no fue
    caracterizado.
  ─────────────────────────────────────────────────────────────────────
   Hipótesis atacada
    10. Integrar origin/main no invalidó identidad ni trazabilidad.
   Comandos, búsquedas o comparación; evidencia encontrada
    git merge-base dio 0 para ambas ramas; git diff origin/main HEAD --
    src/ docker/ frontend/ tests/ mostró solo build.ps1, runner/test H
    y pruebas de gobernanza añadidas, sin delta v4; git diff 22da0dd…
    88ced62 -- src/ docker/ tests/ frontend/ fue vacío. Contrasté
    además RB-06:72–73 (openspec/scientific-closure/reconciliation-
    2026-09-22/thesis-traceability.md:72) con checkpoint:27 (openspec/
    scientific-closure/current-execution-checkpoint.md:27).
   Conclusión e impacto
    La integración no muestra cambio del ejecutable v4, pero sí queda
    una contradicción vigente en RB-06: una fila dice que Docker
    respondió desde la misma distro y la siguiente que es inalcanzable.
    Impacto material sobre la trazabilidad documental.

  ## 5. Validaciones propias

  El repositorio prescribe unittest de gobernanza y OpenSpec estricto
  (openspec/scientific-closure/plan.md:53), y el checker de cierre
  (scripts/check_scientific_closure.py:1). Los ejecuté una vez cada
  uno. No corrí la suite completa, ruff, black ni runners.

   Comando exacto ejecutado      Código    Salida o resumen real
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PYTHONDONTWRITEBYTECODE=1          0    Ran 15 tests in 0.024s / OK
   python3 -m unittest
   discover -s tests -p
   test_scientific_closure_go
   vernance.py
  ────────────────────────────  ────────  ─────────────────────────────
   PYTHONDONTWRITEBYTECODE=1          0    scientific-closure checker:
   PYTHONPATH=src python3                  PASS (estructura; runtime
   scripts/                                no verificado)
   check_scientific_closure.p
   y
  ────────────────────────────  ────────  ─────────────────────────────
   git diff --check                   0    Salida vacía
  ────────────────────────────  ────────  ─────────────────────────────
   npx --yes --offline                1    WSL 1 is not supported.
   @fission-ai/                            Please upgrade to WSL 2 or
   openspec@1.13.1 validate                above. / Could not
   scientific-closure --type               determine Node.js install
   spec --strict                           directory

  El fallo de npx ocurrió en el lanzador Windows del PATH, antes de
  validar la spec. Usé el mismo paquete OpenSpec 1.13.1 ya presente con
  Node Linux. Estos son los once comandos exactos sustitutos; cada uno
  dio exit 0. La spec produjo Specification 'scientific-closure' is
  valid más 25 mensajes INFO sobre longitud de requisito; cada change
  produjo Change '…' is valid.

  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate scientific-closure --type spec --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-01-evidence-scope --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-02-runtime-readiness --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-03-stage-a --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-04-stage-b --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-05-stage-c --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-06-scientific-synthesis --type change
  --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-07-aux-regression --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-08-aux-hitl --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-09-aux-anomalies --type change --strict
  /home/gus/scientific-closure-runtime/env/node/bin/node /home/
  gus/.npm/_npx/7a74150b208fdb68/node_modules/@fission-ai/openspec/bin/
  openspec.js validate sc-10-aux-robustness --type change --strict

  La comprobación estructural no detecta la contradicción temporal:
  toma los estados declarados del registro, no demuestra que cada PASS
  existiera antes del despacho dependiente.

  ## 6. Integridad de auditorías previas

  A, B y C figuran PASS en openspec/scientific-closure/
  changes.json:220, con snapshot
  37eed42716803baa9bdbed912356b981adac093a, actor /
  auditor_independiente_cierre_cientifico y timestamp 04:30 para las
  tres. La calificación literal de C es PASS_WITH_LIMITATIONS para la
  campaña y suficiencia INSUFFICIENT para GF, según el mismo registro.
  La primera auditoría RB-05, aun con veredicto global FAIL (openspec/
  changes/sc-06-scientific-synthesis/reviews/review-audit-final-round1-
  FAIL.md:84), contrastó resultados de A/B/C; ese trabajo sustantivo no
  convierte el FAIL en aprobación de la secuencia.

  El PASS de H (openspec/changes/sc-08-aux-hitl/reviews/review-audit-
  final.md:12) cubre SC-GOV-022 con condiciones, y expresamente no
  cubre GF ni los 25 requisitos. El PASS de RB-03 (openspec/changes/sc-
  07-aux-regression/reviews/review-audit-gd12.md:8) cubre la
  suficiencia documental de R/N/S. Verifiqué con git diff 65ca852 HEAD
  -- que su directorio y los informes de sc-07/09/10 no cambiaron. El
  PASS de reconciliación (openspec/changes/sc-06-scientific-synthesis/
  reviews/review-audit-reconciliation.md:196) se limita a seis ítems y
  declara expresamente que no descarga RB-05/T25.

  Las dos rondas históricas RB-05 son FAIL; sus SHA-256 coinciden byte
  por byte con los objetos originales de f355272. La renuncia del
  auditor anterior a una tercera ronda aparece como antecedente, nunca
  como un tercer PASS.

  ## 7. Hallazgos materiales

  M-01 — Orden de gates incompatible con el registro. A terminó
  03:39:29 (/home/gus/scientific-closure-runtime/evidence/governance/
  closure-campaign-2026-09-21/sc-03-stage-a/execution-record.json:21).
  El registro dice que B ya estaba aprobada por «sc-03 PASS, auditoría
  independiente de A» a 03:20 (openspec/scientific-closure/
  changes.json:325), mientras el PASS de A se fecha 04:30 (openspec/
  scientific-closure/changes.json:225). B comenzó 03:51 (/home/gus/
  scientific-closure-runtime/evidence/governance/closure-campaign-2026-
  09-21/sc-04-stage-b/execution-record.json:19). C fue aprobada por
  «sc-04 PASS, auditoría independiente de B» también a 03:20 (openspec/
  scientific-closure/changes.json:411), comenzó 04:06 (/home/gus/
  scientific-closure-runtime/evidence/governance/closure-campaign-2026-
  09-21/sc-05-stage-c/execution-record.json:31), y el PASS de B se
  fecha 04:30 (openspec/scientific-closure/changes.json:311). El plan
  (openspec/scientific-closure/plan.md:21) exige esas auditorías antes
  de B y C. No hay en las fuentes inspeccionadas un informe individual
  anterior que resuelva esta contradicción. Afecta 007, 012, 014 y la
  suficiencia de 025; no implica recomputar ni corregir resultados
  científicos.

  M-02 — T08 marcada cumplida sin cadena de revisión requerida en sc-
  06. T08 está [x] (openspec/changes/sc-06-scientific-synthesis/
  tasks.md:11), mientras REVIEW-3 y REVIEW-4 están [ ] (openspec/
  changes/sc-06-scientific-synthesis/tasks.md:16). La auditoría de
  reconciliación reconoce que el snapshot no recibió crítica
  adversarial independiente. El PASS propuesto de 008 excede esa
  evidencia.

  M-03 — Contradicción en RB-06. La fila 3.4 (openspec/scientific-
  closure/reconciliation-2026-09-22/thesis-traceability.md:72) dice que
  Docker respondió y ejecutó la imagen desde Ubuntu/WSL el 2026-09-21.
  La fila 3.5 (openspec/scientific-closure/reconciliation-2026-09-22/
  thesis-traceability.md:73) aún dice que «el runtime de contenedores
  no es alcanzable desde la distro WSL usada para validar». El
  checkpoint vigente (openspec/scientific-closure/current-execution-
  checkpoint.md:27) declara resuelta esa inalcanzabilidad. La fila 3.5
  no puede pasar a la memoria como limitación vigente.

  M-04 — Pushes de preparación frente a criterios literales. ADR-0011
  (docs/adr/0011-protocolo-controlled-daily-v4-external-
  pergamino.md:105) acredita dos pushes prohibidos y declara que su
  ratificación no subsana el incumplimiento. PASS para 003 y
  PASS_WITH_LIMITATIONS para 019 no satisfacen sus criterios textuales
  completos.

  ## 8. Observaciones no bloqueantes

  La sección histórica de claims.md conserva «9 de 10» junto a diez
  filas rotuladas cubiertas; la clasificación final posterior vuelve
  CL-10 condicional a RB-05 y evita usar esa cuenta antigua como
  vigente. La documentación de v3 declara el ~24 % imputado en los
  lugares interpretativos inspeccionados. H conserva la distinción
  entre resultado simulado, intervención humana y evidencia técnica. La
  preparación RB-05 no alteró código ni resultados.

  No encontré informes verbatim individuales de las auditorías
  originales de A, B y C en las rutas de gobernanza inspeccionadas. Esa
  ausencia limita la comprobación de su cronología; no la completo
  suponiendo que existieron revisiones anteriores a las fechas
  registradas.

  ## 9. Limitaciones que deben permanecer declaradas

  A terminó en SIN_GANADOR_ESTABLE; la elección fue por simplicidad
  predeclarada. B cumplió no inferioridad, con IC que incluye cero. C
  muestra ventaja en MCC en una serie retrospectiva, junto a
  calibración degradada, falsos avisos, dos episodios no detectados y
  aproximadamente 24 unidades efectivas; no demuestra superioridad
  general ni eficacia agronómica. H tuvo deltas simulados de signo
  mixto y detección humana 0/4; no demuestra beneficio humano. La
  evidencia formal v3 contiene aproximadamente 24 % de días de humedad
  imputados con causal_ffill, sin caracterización de su efecto; no
  demuestra robustez ante mediciones ausentes. Persisten la condición
  documental NASA POWER, la exposición de resultados sin ancla Git y la
  desviación histórica RK-14.

  ## 10–13. Recuento, veredicto y estados derivables

   Recuento sobre 25                                          Cantidad
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━
   Sostenidos, incluidas limitaciones y tres                        18
   NOT_APPLICABLE legítimos
  ─────────────────────────────────────────────────────────  ──────────
   No sostenidos: 003, 007, 008, 012, 014, 019                       6
  ─────────────────────────────────────────────────────────  ──────────
   Bloqueado: 025                                                    1
  ─────────────────────────────────────────────────────────  ──────────
   Total                                                            25

  RB-05: FAIL. La causa son contradicciones materiales comprobadas, no
  resultados científicos negativos ni pruebas fallidas. De este
  veredicto se deriva, sin escribir ningún estado, que sc-06-
  scientific-synthesis no puede pasar a PASS, SC-GOV-025 permanece sin
  resolver y el gate GF permanece PENDIENTE. El snapshot auditado es
  88ced622dd653cf6e6f892fd8212a2857acb77b7.

  CODEX_RB05_AUDIT_FAIL