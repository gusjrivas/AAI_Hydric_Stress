# Auditoría final independiente del complemento H

> Informe del `scientific_auditor`, sesión nueva y separada, de solo lectura.
> Objeto: snapshot final de H (commit `5aec15d4`), el gate GF y SC-GOV-025.
> Transcripción literal. No se corrige ni se resume.

I have completed my independent verification. Here is my audit.

---

```json
{
  "verdict": "PASS",

  "verdict_qualification": "PASS a nivel REQUISITO SC-GOV-022 y sujeto a condiciones, no PASS de change ni de gate. El criterio de aceptación congelado de SC-GOV-022 se satisface y lo comprobé yo mismo, recomputando desde los datos y no leyendo los resúmenes del implementador. Pero: (a) hay UN hallazgo MATERIAL propio, AUD-H-01, sobre la cadena de revisión, que no invalida la ciencia de H y sí debe remediarse antes de registrar sc-08-aux-hitl como PASS de change; (b) tres puntos quedan BLOCKED-por-punto porque no pude comprobarlos con las herramientas disponibles y no acepto el testimonio del implementador como cierre (AUD-H-09); (c) el PASS está condicionado a que se declaren las cinco limitaciones de `limitations_that_must_remain_declared`. NO confirmo el PASS_WITH_LIMITATIONS del implementador tal como está redactado: le falta el hecho más saliente de la pista humana (AUD-H-04) y sobreenuncia la identidad del primer intento (AUD-H-03).",

  "scope": "Complemento H (auxiliary_hitl_v1) del cierre científico de AAI_Hydric_Stress: contrato, paquete, intervención humana, ejecución, evidencia, gobernanza y respaldo externo. Incluye pronunciamiento sobre el gate GF y sobre SC-GOV-025. NO es la auditoría final requisito-por-requisito que SC-GOV-025 exige: no audité A, B, C ni los 25 requisitos.",

  "snapshot": {
    "commit_auditado": "5aec15d4d75234384f2d54ebdfdae57d0c9d3291",
    "rama": "feat/scientific-closure-hitl-complement",
    "base": "a742e56936ae7a27e230b09b6575e98037f08932",
    "diff_contra_base": "3 archivos nuevos (runner 2560 líneas, test 1298 líneas, contrato) + changes.json + decisions.md + 2 anclas de congelamiento. Verificado por mí con git diff --stat.",
    "respaldo": "/mnt/scientific-backup/AAI_Hydric_Stress/hitl-complement-2026-09-21 (93 entradas en SHA256SUMS)"
  },

  "checks_performed": [

    { "id": "CK-01", "check": "Preinscripción por git, no por documento. Reconstruí la cronología con `git log --date=iso` y los timestamps de los artefactos.", "result": "PASS — VERIFICADO. Contrato v4 anclado 16:55:49Z (e1510a6) → congelamiento del paquete anclado 16:57:51Z (217b924) → respuesta del operador 19:14:26Z / 19:14:51Z → congelamiento de la respuesta anclado 19:15:14Z (1bee852) → corrida 19:15:27→19:15:36Z, exit 0 (logs/h-run-window.txt) → corrida de completado 19:46:43Z. El paquete quedó fijado en git 2h17m ANTES de que el operador respondiera, y la respuesta quedó fijada en git 13 segundos ANTES de ejecutar. La preinscripción se sostiene sobre el único ancla resistente a manipulación." },

    { "id": "CK-02", "check": "Recomputé yo el package_sha256 con la canonicalización declarada (json.dumps sort_keys, separators, ensure_ascii=False, sin el propio campo).", "result": "PASS — 6f2143e0680cfde452f9a0f509a12e39f1087e45b6fbcd7de7a045a51233b6de, idéntico al declarado y al que figura en el objeto git de 217b924. El hash no se autoancla: el ancla está fuera del montaje escribible." },

    { "id": "CK-03", "check": "sha256sum propio de la respuesta humana y del contrato contra las anclas de git.", "result": "PASS — respuesta 5a0cc469… coincide con human-response.sha256 y con human-response-freeze.json; contrato 2ebd6732… idéntico en HEAD, en el respaldo y en la declaración del paquete." },

    { "id": "CK-04", "check": "Recomputé la concordancia 16/20 desde cero: regla determinista (humedad observada en target < P20 congelado) aplicada a los 20 escenarios del paquete, contra recorded_label y contra la decisión registrada.", "result": "PASS — 16/20 confirmado. Divergentes exactamente H-SC-004 (0.35196, label 1), H-SC-008 (0.47396, label 1), H-SC-009 (0.40808, label 1), H-SC-020 (0.24946, label 0) frente a P20 = 0.31861666666666666. Las 20 decisiones son ACEPTAR con un único motivo agregado literal. El motivo invocado por el operador («de acuerdo al umbral») es aritméticamente incorrecto para esos cuatro. El hecho está registrado en review.json (F-09) sin suavizar." },

    { "id": "CK-05", "check": "Recomputé 72 métricas (MCC, F1, Brier, Average Precision de los 18 brazos) desde los 18 CSV de predicciones, con implementaciones propias en Python puro — deliberadamente SIN sklearn, para no depender de la misma biblioteca que las produjo.", "result": "PASS — 72/72 recomputadas, 0 discrepancias con tolerancia 1e-9. También verifiqué n_observations = 362 en los 18 brazos. Esta es la comprobación más fuerte del expediente: acredita que las métricas publicadas en el PRIMER INTENTO derivan de las predicciones y que la corrida de completado es la misma computación. Cierra materialmente F-01." },

    { "id": "CK-06", "check": "Comparé archivo por archivo, por sha256, el primer intento (18 artefactos) contra la corrida de completado (38).", "result": "PARCIAL — 15 byte-idénticos. TRES difieren, no dos: code_version.json (solo el campo commit), mechanism_metrics.json (solo configured_paths.output_dir, que es una ENTRADA) e integrity_manifest.json, que findings-resolution NO menciona. Ver AUD-H-03." },

    { "id": "CK-07", "check": "Verifiqué los dos manifiestos de integridad recomputando el sha256 de cada archivo listado.", "result": "PASS — primer intento 17/17 OK; completado 37/37 OK; 0 mismatches, 0 ausentes." },

    { "id": "CK-08", "check": "Verifiqué las reglas temporales sobre los 120 eventos de feedback (no sobre una muestra): horizonte, ventana de adquisición, maduración, origen.", "result": "PASS — 120/120 con horizonte exactamente 3 días; emisión y target ambos dentro de 2021; validated_at posterior al día objetivo en todos; ningún cruce de origen ni de rol. Dos valores distintos de validated_at: 2022-01-01T00:00:00Z (SIM, fijo y declarado como valor modelado) y 2026-09-21T19:14:26.798Z (humano, instante real)." },

    { "id": "CK-09", "check": "Estratificación 10 alertas / 10 no-alertas por semilla, desde feedback_events_index.json, en las SEIS agrupaciones (no sólo la semilla 0, que era el límite del hallazgo F-13).", "result": "PASS — 10/10 en las 6 agrupaciones. Además verifiqué que las 5 semillas SIM producen 5 conjuntos de fechas DISTINTOS: las semillas sí varían el muestreo, no es una constante disfrazada. La pista humana comparte fechas con SIM seed 0, que es lo esperado por diseño." },

    { "id": "CK-10", "check": "Crucé las 4 divergencias humanas contra las posiciones corrompidas de la semilla 0 y contra las decisiones del oráculo simulado sobre los MISMOS 20 eventos.", "result": "HALLAZGO — coincidencia exacta. Los 4 registros que el operador aceptó (H-SC-004/008/009/020) son exactamente los 4 que el stream de corrupción invirtió y exactamente los 4 que el revisor simulado marcó CORREGIR. Ver AUD-H-04." },

    { "id": "CK-11", "check": "Cotas temporales: máximo absoluto de fecha en predicciones, en la huella del conjunto y en los eventos.", "result": "PASS — máximo target 2022-12-31, máxima emisión 2022-12-28, huella del conjunto elegible 2015-01-07…2022-12-28, 2913 filas. Ningún dato de 2023, 2024 ni 2025. Fuentes: pergamino_era5land y pergamino_nasa_power, lat -33.9 / lon -60.6: Pergamino, nunca Balcarce." },

    { "id": "CK-12", "check": "Integridad de A/B/C: sha256sum -c sobre evidence-snapshots/final/SHA256SUMS y barrido de mtimes posteriores al inicio de la campaña H.", "result": "PASS — 91/91 OK, 0 FAILED. Ningún archivo del respaldo A/B/C modificado después de 2026-09-21 12:00. Confirma INV-03 de forma independiente del implementador." },

    { "id": "CK-13", "check": "Abrí los ledgers en modo=ro con sqlite3 y leí su estado, en lugar de creer al validation-record.", "result": "PASS — holdout.sqlite: 1 registro, estado CONFIRMADA, attempt 2121cdc901454df6be922c54a42d208d, autorización nominal registrada. stage_b.sqlite: 1 intento, 2 eventos (RESERVED 03:51:14, FINALIZED 03:51:29 del 2026-09-21). mtimes 05:01:34, anteriores a H. El holdout no fue reabierto ni releído." },

    { "id": "CK-14", "check": "Integridad y recuperabilidad del respaldo de H: sha256sum -c sobre manifest/SHA256SUMS.", "result": "PASS — 93/93 OK. Los 2 archivos no cubiertos son el propio SHA256SUMS y inventory.tsv, lo cual es correcto. Nota: recovery-rehearsal.json declara 53 archivos y findings-resolution cita «54/54»: ambos números corresponden al estado ANTERIOR a la corrida de completado; hoy son 93 y verifican." },

    { "id": "CK-15", "check": "Conformidad parámetro por parámetro contra el diseño congelado auxiliary_hitl_v1, leyendo el código fuente del runner, no la declaración.", "result": "PASS — RF(n_estimators=100, max_depth=8, min_samples_leaf=5, n_jobs=1, random_state=seed) sin ponderación; EVENT_BUDGET_PER_SEED=20; EVENTS_PER_STRATUM=10; CORRUPTION_FRACTION=0.10; DEFAULT_SEEDS=(0,1,2,3,4) y el runner rechaza en modo científico cualquier otro conjunto; P20 calculado UNA vez sobre el train inicial y aplicado a las tres ventanas, con re-derivación verificada (INV-04); corrupción con stream independiente default_rng(seed+10000) como exige el diseño; tres brazos sobre las MISMAS 362 filas de evaluación; intersección revisadas∩evaluación = 0." },

    { "id": "CK-16", "check": "Bloque padre «Evaluaciones complementarias»: artefactos exigidos por protocolo, uno por uno.", "result": "PARCIAL — configuración (resolved_config), commit/imagen/dependencias (code_version + environment + constraints_identity), hashes fuente/derivado (input_hashes + dataset_fingerprint + integrity_manifest), fechas, semillas, predicciones por fecha (18 CSV, emitidos recién tras F-01), métricas, soporte y advertencias (warnings.json = []) están presentes. «Límites» NO se emite en el paquete de evidencia del runner: sólo existe en gobernanza y en el contrato. Ver AUD-H-06." },

    { "id": "CK-17", "check": "Las 13 afirmaciones prohibidas del contrato, barridas sobre evidencia, contrato, paquete y respuesta.", "result": "PASS — ninguna sostenida. Todas las apariciones de «mejora», «beneficio», «superioridad», «ciego», «pericia» y «experto» están en negaciones o en listas de prohibición. Verifiqué en particular la 13.ª («invariantes estructurales presentados como evidencia contingente»): invariants.json rotula cada invariante con su `kind` y execution-record declara F-11 llanamente, de modo que tampoco se sostiene. Pero la enumeración de review.json lista 12 de 13: ver AUD-H-05." },

    { "id": "CK-18", "check": "¿NO_RECALIBRATION estaba predeclarado como válido ANTES de que el operador viera nada?", "result": "PASS — SÍ. contract-H-frozen.json, `recalibration_criteria.no_change_is_a_valid_outcome: true` y `no_change_when: \"Todas las decisiones son ACEPTAR\"`, más `verdict_criteria.improvement_not_required`. El contrato v4 está anclado en git en e1510a6 (16:55:49Z), 2h19m antes de la respuesta. No es una racionalización posterior." },

    { "id": "CK-19", "check": "GD-29 (ausencia de agrónomo): verifiqué cada documento que cita.", "result": "PASS con una imprecisión. Corroborados: openspec/project.md línea 17 excluye «validación agronómica longitudinal multi-campaña»; ADR-0011 línea 50 dice «nunca validación agronómica in situ»; claims.md prohíbe afirmar «eficacia agronómica»; el diseño congelado de H ordena «No afirmar feedback humano genuino ni eficacia agronómica». La única casilla del repositorio que nombra a un agrónomo es openspec/changes/simplify-producer-ui/tasks.md:9, de comprensión de interfaz. NO corroborado: la cita a README.md; ver AUD-H-08. Conclusión: NINGÚN documento vigente exige un agrónomo para cerrar H, HU5 ni GF." },

    { "id": "CK-20", "check": "Estado real de la gobernanza en el snapshot: git diff de la rama sobre openspec/scientific-closure/.", "result": "HALLAZGO — traceability.md, claims.md, plan.md y requirements.json NO fueron tocados. SC-GOV-022 sigue diciendo «no tiene runner implementado ni evidencia alguna. No se ejecutó», que hoy es falso. changes.json deja sc-08-aux-hitl en IN_PROGRESS con audit=null. Ver AUD-H-10." },

    { "id": "CK-21", "check": "Recuento propio de CL-01..CL-10 con A/B/C y H ejecutados (el auditor del 2026-09-20 halló 6 de 10 sin evidencia ni limitación aceptada).", "result": "9 de 10 hoy. Detalle abajo en scientific_sufficiency_for_GF." },

    { "id": "CK-22", "check": "¿Existe la auditoría final requisito-por-requisito que SC-GOV-025 exige, sobre el snapshot post-campaña?", "result": "NO — closure-verification-2026-09-20/scientific-closure-audit.json audita el snapshot 5b40a55 del 2026-09-20, ANTERIOR a la ejecución de A/B/C y de H. Es evidencia obsoleta para el estado actual. Tampoco existe síntesis de resultados: docs/research/scientific-closure-synthesis-2026-09-20.md es previo a la ejecución y, como dice la propia fila SC-GOV-016, «no existe ninguna afirmación de resultado que revisar»." },

    { "id": "CK-23", "check": "Preservación verbatim de las cuatro rondas de crítica independiente sobre H.", "result": "FALLA — ver AUD-H-01. No existe ningún informe preservado." },

    { "id": "CK-24", "check": "Re-ejecución propia de las 74 pruebas focalizadas y de la reproducción byte a byte.", "result": "NO PUDE — sklearn y pytest no están disponibles en el entorno de auditoría y el encargo prohíbe ejecutar el runner. BLOCKED para ese punto; ver AUD-H-09. No lo doy por PASS por confianza." }
  ],

  "findings": [

    {
      "id": "AUD-H-01",
      "severity": "MATERIAL",
      "titulo": "Ninguna de las cuatro rondas de crítica independiente sobre H conserva el informe del crítico. Sólo existen resúmenes escritos por el implementador.",
      "ubicacion": "package/human-package-freeze.json → independent_reviews_before_freezing; evidence/governance/hitl-complement-2026-09-21/sc-08-aux-hitl/findings-resolution.json → reviewer, reviewer_verdict_on_the_proposed_verdict, findings[], critic_confirmations_preserved[]",
      "reproduccion": "find sobre todo el respaldo y sobre openspec/changes/sc-08-aux-hitl/ buscando *critic*, *review*.md → 0 resultados. El directorio sc-08-aux-hitl contiene únicamente contract-H-frozen.json, human-package-freeze.json, human-response-freeze.json, proposal.md, tasks.md y specs/.",
      "esperado": "El precedente de esta misma campaña lo fija: closure-verification-2026-09-20/ conserva review-critic.md, review-audit.md, review-audit-2.md, review-audit-3.md y review-evidence-checker.md, los informes completos y en las palabras de sus autores. Y el hallazgo AUD-F-01/AUD-F-02 del 2026-09-20 degradó explícitamente una fila de la matriz por «atribución falsa»: presentar como del crítico una lista compuesta por el orquestador.",
      "observado": "Las rondas 1 y 2 (NO_APTO) y 3 (APTO_PARA_MOSTRAR) se registran sólo como IDs de hallazgo (C-01..C-05, D-01..D-04, E-01..E-09) con veredicto, sin texto. La crítica sobre la ejecución se registra con una cita entrecomillada atribuida al crítico —«NO CONFIRMO PASS_WITH_LIMITATIONS tal como esta. Tampoco corresponde FAIL ni BLOCKED. F-01 es material y esta abierto.»— y con dieciséis hallazgos F-01..F-16 transcritos por el implementador, sin ningún artefacto contra el cual contrastarlos. Consecuencia verificable: no puedo comprobar (a) que el crítico dijera lo que se le atribuye, (b) que no se haya omitido ningún hallazgo, ni (c) la identidad separada implementador/crítico que SC-GOV-008 exige acreditar. Esto es exactamente la forma que AUD-F-02 condenó, reaparecida en el complemento.",
      "impacto": "NO invalida la ciencia de H: verifiqué numéricamente y por mi cuenta todo lo sustantivo (CK-04, CK-05, CK-08, CK-09, CK-10, CK-15). Sí impide registrar sc-08-aux-hitl como PASS de change y sí impide afirmar en la memoria o en la matriz que H pasó por crítica independiente documentada.",
      "remediacion": "Preservar los cuatro informes verbatim junto a la evidencia; o, si no existen ya, declarar explícitamente en findings-resolution.json y en la matriz que los informes no se conservaron y que la enumeración de hallazgos es una transcripción del implementador no verificable, tal como AUD-F-02 obligó a hacer."
    },

    {
      "id": "AUD-H-02",
      "severity": "MATERIAL",
      "titulo": "Los RESULTADOS de H no tienen ancla en git. Sólo viven en un montaje escribible.",
      "ubicacion": "git diff a742e56..HEAD; /mnt/scientific-backup/.../hitl-complement-2026-09-21 (drwxrwxrwx, root)",
      "reproduccion": "`git ls-files | grep evidence/` → ningún artefacto de evidencia científica está versionado. El diff de la rama son 7 archivos: el runner, su test, el contrato, las dos anclas de congelamiento, changes.json y decisions.md.",
      "esperado": "Que la propiedad de inmutabilidad que el propio recovery-rehearsal.json invoca —«la inmutabilidad real de los artefactos criticos descansa en los hashes anclados en commits de la rama»— cubra también los resultados, no sólo las entradas.",
      "observado": "Contrato, paquete y respuesta SÍ están anclados en git y los verifiqué (CK-02, CK-03): la preinscripción es sólida. Pero track_human.json, track_simulated.json, mechanism_metrics.json, los 18 CSV de predicciones, review.json, execution-record.json y findings-resolution.json no tienen ningún hash comprometido en un objeto git. Su integridad descansa en SHA256SUMS, que vive en el mismo montaje escribible que los archivos que protege.",
      "impacto": "Exposición estructural idéntica a la de A/B/C y preexistente, no una regresión introducida por H; recovery-rehearsal.json la declara con honestidad. Debe permanecer como limitación viva y no debe presentarse como resuelta por el ensayo de recuperación, que acredita integridad de la copia, no resistencia a edición deliberada."
    },

    {
      "id": "AUD-H-03",
      "severity": "MENOR",
      "titulo": "findings-resolution afirma que hay exactamente dos diferencias entre el primer intento y la corrida de completado. Hay tres.",
      "ubicacion": "findings-resolution.json → first_attempt_proof y completion_run.original_artifacts_differing",
      "reproduccion": "sha256sum de los 18 archivos de evidence/first-attempt contra sus homónimos en evidence/first-attempt-completed.",
      "esperado": "Que el recuento cierre: 18 archivos = idénticos + diferentes.",
      "observado": "15 idénticos + 2 declarados como diferentes = 17, no 18. El decimoctavo, integrity_manifest.json, también difiere y no se menciona en ningún lado. La diferencia es benigna y necesaria —el manifiesto de la corrida de completado cubre 37 archivos y el del primer intento 17, y ambos verifican íntegros (CK-07)— pero la frase «las dos únicas diferencias son» es literalmente falsa en un artefacto cuya función es precisamente acreditar que el primer intento no se tocó.",
      "remediacion": "Corregir a tres diferencias, con la explicación del manifiesto."
    },

    {
      "id": "AUD-H-04",
      "severity": "MENOR",
      "titulo": "El hecho más saliente de la pista humana no está enunciado en ningún artefacto: el operador no detectó ninguna de las cuatro corrupciones que se le presentaron, sobre los mismos eventos en que el revisor simulado detectó las cuatro.",
      "ubicacion": "evidence/first-attempt-completed/agreement_analysis.json; auxiliary/H/review.json → human_intervention; execution-record.json → interpretation_limits",
      "reproduccion": "Crucé feedback_events_index.json: los eventos de controlled_human_feedback con record_consistent_with_reference=false son {H-SC-004, H-SC-008, H-SC-009, H-SC-020}; los de simulated_supervised_feedback seed 0 con record_consistent_with_reference=false son el MISMO conjunto; los que el oráculo simulado marcó CORREGIR son el MISMO conjunto; y las fechas de ambas pistas coinciden exactamente. Las decisiones humanas sobre esos cuatro son ACEPTAR, ACEPTAR, ACEPTAR, ACEPTAR.",
      "esperado": "Que la evidencia enuncie la consecuencia, no sólo sus insumos. Sobre la única tarea determinable que se le presentó —revisión de calidad de dato con la regla enunciada en las propias instrucciones y con la observación madurada y el P20 a la vista— la tasa de detección de la pista humana fue 0 de 4, frente a 4 de 4 del oráculo simulado sobre los eventos idénticos.",
      "observado": "Todos los insumos están publicados y los recomputé sin discrepancias: agreement_analysis.json da 4 divergencias, review.json declara F-09 y nombra los cuatro escenarios con sus valores, y execution-record declara que la pista humana no ejercitó corrección ni recalibración. Nada es falso ni está oculto. Pero el enunciado se queda en «concordancia 16/20» y en «el motivo es aritméticamente incorrecto para cuatro registros», que son descripciones más suaves del mismo hecho. La comparación directa con el oráculo sobre los mismos eventos —que es la que un lector externo hará— no aparece.",
      "impacto": "Atenuación por omisión de énfasis, no falsedad. Debe enunciarse explícitamente: es la limitación que fija de verdad el alcance de la pista humana y la que hace imprescindible la validación de campo que el propio operador declaró como trabajo futuro."
    },

    {
      "id": "AUD-H-05",
      "severity": "MENOR",
      "titulo": "review.json enumera 12 de las 13 afirmaciones prohibidas del contrato, y omite precisamente la que estuvo más cerca de violarse.",
      "ubicacion": "auxiliary/H/review.json → prohibited_assertions_not_made; contract-H-frozen.json → prohibited_assertions",
      "reproduccion": "Conteo directo: el contrato lista 13, review.json lista 12. La ausente es «Invariantes estructurales presentados como evidencia contingente de la corrida».",
      "esperado": "Las 13, sobre todo esa, que es el objeto del hallazgo F-11.",
      "observado": "Comprobé por mi cuenta que esa afirmación NO se sostiene: invariants.json rotula cada invariante con su `kind` (6 structural_guard, 1 contingent_measurement, 3 not_measured_in_run), mechanism_metrics hace lo mismo, y execution-record declara llanamente que los diez son, de hecho, guardas de regresión. La omisión es de la enumeración, no de la conducta. Pero en un artefacto que se presenta como control exhaustivo, omitir justo el ítem sensible degrada el valor del control."
    },

    {
      "id": "AUD-H-06",
      "severity": "OBSERVACIÓN",
      "titulo": "El bloque padre congelado exige «límites» entre los artefactos por protocolo; el paquete de evidencia del runner no emite ninguno.",
      "ubicacion": "docs/research/scientific-closure-decisions.md, «Evaluaciones complementarias»; evidence/first-attempt-completed/",
      "reproduccion": "Barrido de los 38 artefactos buscando limitaciones declaradas: sólo invariants.json contiene la palabra, y para una limitación de medición de INV-02. Ninguna limitación científica de H está en el paquete de evidencia.",
      "esperado": "Misma exigencia que produjo F-01 para «predicciones por fecha»: el bloque padre enumera «advertencias y límites» en la misma frase.",
      "observado": "Las limitaciones existen, son sustantivas y están completas: 13 en contract-H-frozen.json (declared_limitations_predeclared), 9 en execution-record (interpretation_limits) y 12 en review.json. Y son recuperables desde la evidencia: contract_reference.json fija el contract_sha256 2ebd6732…, que está anclado en git. Por eso es una observación y no un F-01 bis: a diferencia de las predicciones, aquí no hay nada irrecuperable. Pero el paquete de evidencia, leído solo, no lleva sus propios límites."
    },

    {
      "id": "AUD-H-07",
      "severity": "OBSERVACIÓN",
      "titulo": "Los frozen_at_utc del contrato preceden sistemáticamente en unas 3h20m a sus commits. Corroboro la discrepancia; no afecta lo que importa.",
      "ubicacion": "openspec/changes/sc-08-aux-hitl/contract-H-frozen.json a lo largo de su historia",
      "reproduccion": "git show <commit>:<archivo> en cada commit: v1 declara 12:05Z y se commitea 12:16; v2 declara 12:40Z y se commitea 12:35 (anterior); v3 declara 13:05Z y se commitea 16:42; v4 declara 13:35Z y se commitea 16:55.",
      "esperado": "Nada verificable: son autodeclaraciones.",
      "observado": "Ya aceptado como F-02 y declarado como limitación. Lo corroboro de forma independiente y confirmo su evaluación: el orden que sostiene la preinscripción no depende de esos valores, sino de los commits, y ese orden se verifica (CK-01). Ninguna versión del contrato posterior a la respuesta del operador existe."
    },

    {
      "id": "AUD-H-08",
      "severity": "OBSERVACIÓN",
      "titulo": "GD-29 cita un documento que no dice lo que se le atribuye.",
      "ubicacion": "openspec/scientific-closure/decisions.md, GD-29",
      "reproduccion": "grep de «agronom/agrónom» sobre README.md y sobre openspec/scientific-closure/README.md → sin coincidencias.",
      "esperado": "Que la cita «`README.md` excluye la validación agronómica de los requisitos de esta campaña» se corresponda con un texto.",
      "observado": "No existe. La conclusión de fondo de GD-29 está bien sostenida por las otras cuatro citas, que sí verifiqué (project.md:17, ADR-0011:50, claims.md, diseño congelado de H). Corregir la cita o retirarla."
    },

    {
      "id": "AUD-H-09",
      "severity": "OBSERVACIÓN — BLOCKED POR PUNTO",
      "titulo": "Tres afirmaciones no las pude comprobar y no las doy por buenas.",
      "ubicacion": "validation-record.json (74 + 45 pruebas, INV-10); reproduction-record.json (reproduction_2, 18/18 byte a byte con ruta constante)",
      "reproduccion": "`python3 -c 'import sklearn'` → ModuleNotFoundError; no hay venv ni pytest en el entorno de auditoría; el encargo prohíbe ejecutar el runner. Los outputs de las dos reproducciones no se conservaron en el respaldo, de modo que tampoco puedo compararlos a posteriori.",
      "esperado": "Verificación propia.",
      "observado": "(1) INV-10 «actuación cerrada ante entradas inválidas» descansa enteramente en las 74 pruebas focalizadas, que sólo conozco por logs/focused-tests.log del implementador. (2) La reproducción estricta 18/18 no es re-verificable. (3) Por extensión, RECHAZO y recalibración sucesiva —que sólo se ejercitan en esa suite con fixtures— quedan sin respaldo que yo pueda comprobar, y el propio expediente ya declara que fixtures no son evidencia científica. COMPENSACIÓN PARCIAL, no equivalencia: obtuve por mi cuenta una propiedad vecina y fuerte, que 15 de 18 artefactos son byte-idénticos entre dos corridas con commit y directorio de salida distintos, y que las 72 métricas recomputan exactamente desde las predicciones. Eso acredita determinismo de la computación, no actuación cerrada ante entradas inválidas."
    },

    {
      "id": "AUD-H-10",
      "severity": "MATERIAL PARA EL GATE, no para H",
      "titulo": "La matriz de trazabilidad no fue actualizada y hoy afirma algo falso sobre SC-GOV-022.",
      "ubicacion": "openspec/scientific-closure/traceability.md líneas 78 y 173; changes.json → sc-08-aux-hitl",
      "reproduccion": "git diff a742e56..HEAD -- openspec/scientific-closure/ → sólo changes.json y decisions.md.",
      "esperado": "Que la matriz refleje el snapshot.",
      "observado": "SC-GOV-022 sigue leyéndose «H (HITL) está declarado REQUIRED y no tiene runner implementado ni evidencia alguna. No se ejecutó» y «no existe runner para el diseño H». Ambas proposiciones son hoy falsas: el runner está en git y la evidencia existe y la verifiqué. La «Lectura honesta del conjunto» sigue diciendo que H «sigue siendo alcance aprobado sin ejecutar». changes.json deja sc-08-aux-hitl en IN_PROGRESS con audit=null, lo cual es correcto hasta que se registre esta auditoría, pero deja el expediente internamente contradictorio."
    }
  ],

  "scientific_sufficiency_for_GF": {
    "veredicto": "INSUFFICIENT",

    "suficiencia_de_H_sobre_SU_alcance": "SUFICIENTE, y lo separo deliberadamente de la suficiencia para GF. El criterio de aceptación congelado de SC-GOV-022 tiene cuatro conjuntos y los cuatro se cumplen, verificados por mí: (1) «Tres brazos y maduración separados» — frozen / refit_no_corrections / refit_with_corrections sobre las mismas 362 filas, train hasta 2020-12-31 y 2021-12-31 respectivamente, feedback en 2021, evaluación en 2022, intersección revisadas∩evaluación = 0, P20 congelado único; (2) «20 eventos/seed conforme diseño H» — 20 por semilla en las cinco semillas congeladas, estratificación 10/10 verificada en las seis agrupaciones, selección sólo con predicciones emitidas en 2021; (3) «simulación identificada» — dos pistas con origen y rol propios, no intercambiables, sin ningún artefacto que los mezcle; (4) «implementación funcional HU5 no prueba beneficio» — deltas de signo mixto (3 positivos, 2 negativos entre semillas), sin intervalos, sin afirmación inferencial, y ninguna de las 13 afirmaciones prohibidas sostenida.",

    "sobre_la_pregunta_de_si_la_demostracion_del_mecanismo_se_sostiene": "Se sostiene PARCIALMENTE y el expediente ya lo dice, pero conviene ser preciso sobre qué demostró cada pista. Demostrado por evidencia científica: recepción y registro del feedback, validación de identidad y rol, validación estructural y temporal con maduración, aceptación conforme al contrato, NO_RECALIBRATION registrada con su razón (pista humana); y CORRECCIÓN + RECALIBRACIÓN con linaje completo y predecesor preservado, cinco veces (pista SIM). NO demostrado por ninguna pista científica: RECHAZO y recalibración SUCESIVA, que sólo se ejercitan en la suite con fixtures —y el propio contrato establece que un fixture jamás es evidencia científica—. La frase de review.json «La demostracion del mecanismo HITL se completa entre la pista simulada, la intervencion humana controlada y la suite focalizada» es admisible sólo porque nombra la suite como tercer término, pero el verbo «se completa» es más fuerte de lo que el conjunto autoriza; el enunciado correcto es el de execution-record, que separa los caminos ejercitados de los no ejercitados. La pista humana, por su parte, sólo ejercitó la aceptación, y con tasa de detección 0/4 sobre lo único determinable (AUD-H-04).",

    "NO_RECALIBRATION_predeclarado": "SÍ, verificado en git. El contrato v4 (anclado 16:55:49Z, 2h19m antes de la respuesta) declara no_change_is_a_valid_outcome: true, no_change_must_be_recorded y improvement_not_required. El resultado nulo no es una racionalización posterior y no debe leerse como fallo.",

    "recuento_propio_de_CL_01_a_CL_10": {
      "metodo": "El auditor del 2026-09-20 halló 6 de 10 sin evidencia ni limitación aceptada, porque PENDING designa evidencia futura faltante y no un límite aceptado. Las seis con PENDING eran CL-01, CL-02, CL-03, CL-06, CL-09 y CL-10; las cuatro que ya estaban cubiertas por limitación aceptada eran CL-04, CL-05, CL-07 y CL-08. Rehíce el recuento contra el estado de hoy.",
      "CL-01": "CUBIERTA — A ejecutada; gate-review y temporal-contract-check con SC-GOV-011 PASS; SIN_GANADOR_ESTABLE con desempate por simplicidad, soporte 3/3 folds y 5000/5000 réplicas. El PENDING se consumió.",
      "CL-02": "CUBIERTA — B ejecutada; CANDIDATE_VALIDATED por NO INFERIORIDAD (el intervalo incluye el cero), SC-GOV-012 PASS, intento único con custodia verificada.",
      "CL-03": "CUBIERTA — C abierta una sola vez, ledger CONFIRMADA que leí directamente, SC-GOV-014 PASS.",
      "CL-04": "CUBIERTA por limitación aceptada — v3 REFERENCED, preservada y no recalculada.",
      "CL-05": "CUBIERTA por limitación aceptada — la afirmación de regresión no se sostiene en esta campaña; la brecha es condicional a una ampliación de alcance, no un PENDING.",
      "CL-06": "CUBIERTA CON LIMITACIONES — es la que H acaba de mover. Comparación de tres brazos predeclarada (contrato anclado en git antes de ejecutar) y ahora auditada; aporte cuantitativo de correcciones supervisadas SIMULADAS reportado sin afirmar beneficio y sin intervalos; nunca beneficio de una persona real, como exige la propia redacción de CL-06. Se cierra en cuanto esta auditoría se registre.",
      "CL-07": "CUBIERTA por limitación aceptada — no se afirma detección reservada.",
      "CL-08": "CUBIERTA por limitación aceptada — robustez limitada a lo documentado en v3, sin extrapolar a sensores ausentes.",
      "CL-09": "CUBIERTA — métricas onset, episodios, censura y soporte presentes en la evidencia de A, B y C (verificado: metrics.json de las cuatro carpetas contiene onset).",
      "CL-10": "NO CUBIERTA TODAVÍA — es la única que falta, y su texto explica por qué: exige «Terminal A/B/C auditado, H auditado, trazabilidad y límites». Terminal A/B/C auditado ✓. H auditado: se cumple con este informe, una vez registrado. Límites ✓. TRAZABILIDAD: ✗ — la matriz no fue actualizada y hoy afirma sobre SC-GOV-022 algo factualmente falso (AUD-H-10).",
      "conteo": "9 de 10 hoy, contra 4 de 10 el 2026-09-20. La décima, CL-10, es cerrable por trabajo documental: registrar esta auditoría y actualizar la matriz. No requiere ejecutar nada nuevo."
    },

    "por_que_INSUFFICIENT_pese_a_9_de_10": "Porque el criterio de aceptación de SC-GOV-025 tiene cinco conjuntos y la cobertura de afirmaciones es sólo el primero. Evalúo los cinco: (1) «Todas las afirmaciones tienen evidencia o limitación aceptada» — 9/10, la décima cerrable documentalmente. (2) «Terminal negativo válido documentado» — SATISFECHO: SIN_GANADOR_ESTABLE, la no inferioridad de B y el NO_RECALIBRATION de H están documentados como resultados válidos, no como defectos. (3) «Complementos justificados» — NO SATISFECHO: R, N y S son NOT_REQUIRED por la decisión de suficiencia GD-12, que sigue sin crítica ni auditoría independiente, y sus artefactos auxiliary/R|N|S/review.json no existen; SC-GOV-021, 023 y 024 permanecen BLOCKED por esa causa exacta y la causa no ha cambiado. (4) «Memoria caps.2/3 trazada» — NO SATISFECHO: no encontré ningún artefacto de trazabilidad a los capítulos 2 y 3; sólo prosa en README.md y operations.md que dice que debe hacerse. (5) «Ningún obligatorio sin resolver» — NO SATISFECHO: cinco requisitos siguen BLOCKED y la propia matriz establece que BLOCKED es «irresuelto y suspendido», no terminal. A eso se suma que la Comprobación que SC-GOV-025 prescribe —auditoría final independiente requisito por requisito sobre el alcance aprobado— no existe para el estado actual: el scientific-closure-audit.json disponible audita el snapshot 5b40a55 del 2026-09-20, anterior a A/B/C y a H, y no existe ninguna síntesis de los resultados realmente obtenidos."
  },

  "SC_GOV_022_recommended_state": {
    "estado": "PASS_WITH_LIMITATIONS",
    "cambia_desde": "BLOCKED",
    "la_causa_declarada_del_bloqueo_esta_resuelta": "SÍ, sin ambigüedad. traceability.md línea 78 daba como causa: «H está declarado REQUIRED y no tiene runner implementado ni evidencia alguna. No se ejecutó». Hoy el runner existe y está anclado en git (src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py, 2560 líneas, commit 5f30880 y siguientes); la evidencia existe, verifica y la recomputé; el artefacto exigido auxiliary/H/review.json existe; y la comprobación prescrita por el requisito —«Revisión de fechas de feedback, separación de refit/correcciones, fixtures del diseño auxiliary_hitl_v1»— la ejecuté yo mismo con resultado favorable en los tres términos.",
    "condiciones_para_registrarlo": [
      "Declarar las cinco limitaciones de limitations_that_must_remain_declared, en particular la de AUD-H-04, que hoy no está enunciada en ningún artefacto.",
      "Remediar AUD-H-01: preservar los informes verbatim de las cuatro rondas de crítica, o declarar expresamente que no se conservaron y que la enumeración de hallazgos es transcripción no verificable del implementador.",
      "Corregir AUD-H-03 (tres diferencias, no dos) y AUD-H-05 (13 afirmaciones prohibidas, no 12).",
      "Actualizar traceability.md: la redacción vigente de SC-GOV-022 es hoy factualmente falsa.",
      "Registrar que PASS_WITH_LIMITATIONS de requisito NO es PASS de change: sc-08-aux-hitl no puede pasar a PASS mientras AUD-H-01 siga abierto, porque SC-GOV-008 exige acreditar identidad distinta implementador/auditor y no hay artefacto que lo acredite para la cadena de crítica de H."
    ],
    "advertencia": "Registrar además, en la fila de la matriz, que dos puntos del expediente de H (INV-10 vía las 74 pruebas focalizadas, y la reproducción estricta 18/18) NO fueron verificados de forma independiente por esta auditoría, por indisponibilidad de herramientas (AUD-H-09). No deben presentarse como auditados."
  },

  "SC_GOV_025_recommended_state": {
    "estado": "BLOCKED",
    "cambia_desde": "BLOCKED — mismo estado, causa distinta",
    "causa_anterior_que_SI_se_resolvio": "«Gate GF no alcanzable hoy: el plan exige todos los REQUIRED con PASS y H no lo está». Esa causa ya no rige: H es el ÚNICO complemento REQUIRED (claims.md fija R, N y S como NOT_REQUIRED y H como REQUIRED, para CL-06 y CL-10), y H pasa a PASS_WITH_LIMITATIONS.",
    "causas_que_lo_mantienen_BLOCKED": [
      "La Comprobación que el propio requisito prescribe no está cumplida: no existe auditoría final independiente REQUISITO POR REQUISITO sobre el snapshot post-campaña. El scientific-closure-audit.json disponible audita 5b40a55 del 2026-09-20, previo a la ejecución de A/B/C y de H; es evidencia obsoleta. Este informe NO la sustituye: mi alcance es H, no los 25 requisitos.",
      "No existe síntesis científica de los resultados obtenidos. docs/research/scientific-closure-synthesis-2026-09-20.md es anterior a toda ejecución, y la propia fila SC-GOV-016 reconoce que «la revisión sólo puede cubrir afirmaciones de no ejecución, porque no existe ninguna afirmación de resultado que revisar». sc-06-scientific-synthesis sigue BLOCKED con audit=null.",
      "«Complementos justificados»: la decisión de suficiencia GD-12 (R/N/S NOT_REQUIRED) sigue sin crítica ni auditoría independiente, y auxiliary/R|N|S/review.json no existen. SC-GOV-021, 023 y 024 siguen BLOCKED por esa causa intacta.",
      "«Memoria caps.2/3 trazada»: sin artefacto de trazabilidad. Sólo prosa normativa que lo ordena.",
      "«Ningún obligatorio sin resolver»: cinco requisitos BLOCKED, y BLOCKED es por definición de la propia matriz un estado irresuelto y suspendido.",
      "CL-10 no está cubierta mientras la matriz no se actualice (AUD-H-10)."
    ],
    "respuesta_directa_a_si_021_023_024_impiden_GF": "SÍ, lo impiden, y quiero ser preciso sobre el mecanismo, porque hay un argumento tentador y equivocado. El argumento equivocado: plan.md dice que sc-06 exige «todos los REQUIRED con PASS»; R, N y S son NOT_REQUIRED; luego no cuentan. Es equivocado por dos razones. Primera: SC-GOV-025 tiene su propio criterio de aceptación, más exigente que la cláusula de sc-06, y ese criterio pide «complementos justificados» y «ningún obligatorio sin resolver» — y SC-GOV-021, 023 y 024 son requisitos obligatorios de la especificación que están sin resolver, con independencia de que el complemento que gobiernan sea NOT_REQUIRED. Segunda, y de fondo: lo que está sin auditar es precisamente un JUICIO DE SUFICIENCIA —que R, N y S no hacen falta para el alcance aprobado—, y evaluar la suficiencia científica del alcance aprobado es exactamente lo que SC-GOV-025 manda hacer. Un auditor final no puede declarar suficiente un alcance cuya delimitación nunca fue criticada por nadie independiente. Es el mismo razonamiento que el hallazgo C-09 y la decisión GD-23 ya fijaron cuando degradaron esas tres filas desde NOT_APPLICABLE a BLOCKED, y yo lo ratifico. Tampoco puedo resolverlo yo: mi encargo es H, los artefactos de revisión de R, N y S no existen, y soy de solo lectura."
  },

  "GF_recommended_state": {
    "estado": "NO EVALUABLE COMO PASS — permanece bloqueado",
    "fundamento": "La entrada del gate GF es «Terminal científico auditado y obligaciones aplicables cumplidas» y su condición de avance es «Auditor final PASS sobre suficiencia del alcance completo», con salida «Afirmaciones trazadas, límites/pendientes y memoria; no sólo software verde». El terminal científico A→B→C está auditado y respaldado, y lo verifiqué íntegro (91/91 hashes, ledgers en el estado declarado). H, que era el obstáculo nombrado, deja de serlo. Pero GF no puede ser PASS porque su condición de avance ES el PASS del auditor final sobre suficiencia, y ese auditor no ha emitido tal PASS sobre el estado actual: la única auditoría final existente es del 2026-09-20 y precede a toda ejecución. GF no puede autoconcederse con la auditoría de un complemento.",
    "distancia_real_al_gate": "Menor de lo que la matriz sugiere, y conviene decirlo con la misma precisión con que digo que está bloqueado. De los seis obstáculos que enumero, tres son documentales y no requieren ejecutar nada: actualizar la matriz, redactar la síntesis de los resultados ya obtenidos y trazar las afirmaciones a los capítulos 2 y 3 de la memoria. Dos requieren trabajo de revisión, no de cómputo: la crítica y auditoría independientes de GD-12 (que desbloquearía SC-GOV-021, 023 y 024 de una vez), y la auditoría final requisito por requisito sobre el snapshot post-campaña. Uno es remediación: AUD-H-01. Ninguno exige reabrir el holdout, reejecutar A, B o C, ni ejecutar R, N o S. La campaña científica está hecha; lo que falta es el cierre y su revisión.",
    "advertencia_expresa": "No acepto como cierre científico que el checker dé exit 0, que ruff y black pasen, que la suite dé 824 passed ni que el ensayo de recuperación dé PASS. Todo eso está verde y nada de eso es suficiencia científica. El propio criterio de SC-GOV-020 lo dice: «ningún PASS estructural equivale a cierre científico»."
  },

  "limitations_that_must_remain_declared": [
    "AUD-H-04, la que falta y es la más importante: sobre la única tarea determinable que se le presentó, la pista humana no detectó NINGUNA de las cuatro etiquetas corrompidas —H-SC-004, H-SC-008, H-SC-009, H-SC-020—, que son exactamente las cuatro que el revisor simulado corrigió sobre los eventos idénticos. Tasa de detección humana 0/4 frente a 4/4 del oráculo. El motivo declarado por el operador invoca el umbral y es aritméticamente incorrecto para esos cuatro registros frente a P20 = 0.318617. La decisión se conserva literal y no se reinterpreta.",
    "La pista humana sólo ejercitó la ACEPTACIÓN. Corrección y recalibración quedan demostradas únicamente por la pista SIMULADA. RECHAZO y recalibración SUCESIVA no se ejercitaron en NINGUNA pista científica: sólo en la suite con fixtures, que por contrato no es evidencia científica. Y esa suite no fue reverificada por esta auditoría (AUD-H-09).",
    "El cegamiento fue PARCIAL y declarado antes de la intervención: el paquete mostraba la observación madurada y el P20, de modo que la etiqueta correcta era determinable y las propias instrucciones enunciaban la regla. La pista humana prueba el cumplimiento de un procedimiento dictado, no criterio propio, ni pericia, ni juicio bajo incertidumbre. Además el operador es el autor del código y del generador de corrupción y la semilla figura en el paquete: el cegamiento frente a él es nominal.",
    "Un único operador, 20 eventos, cinco semillas que no son cinco poblaciones, datos de reanálisis de un solo sitio, deltas puntuales sin intervalo porque el diseño congelado no predeclara bootstrap para H. Ninguna afirmación inferencial, ni de mejora ni de deterioro. La corrupción de la pista SIM es un modelo de error artificial, no una medición de la tasa de error de un revisor real.",
    "No hubo intervención de un agrónomo ni validación agronómica de campo, y NINGÚN documento vigente la exige para cerrar H, HU5 ni GF — lo verifiqué contra project.md, ADR-0011, claims.md y el diseño congelado. Está correctamente registrada como limitación y trabajo futuro, y además declarada por el propio operador con sus palabras: «hay que probarlo a futuro en el campo con una persona que pueda realmnete estar viendo si las predicciones son certeras con la realidad», preservada sin corregir la errata. GD-29 es correcta en el fondo; corregir su cita a README.md (AUD-H-08).",
    "Los RESULTADOS de H no tienen ancla en git: viven en un montaje escribible protegido por un manifiesto que reside en ese mismo montaje (AUD-H-02). El ensayo de recuperación acredita integridad y recuperabilidad de la copia, NO resistencia a edición deliberada con privilegios. Las ENTRADAS —contrato, paquete, respuesta— sí están ancladas y lo verifiqué.",
    "Los diez invariantes son, de hecho, guardas de regresión: esta corrida no publica ninguno cuyo valor pudiera haber diferido con este mismo código. El mecanismo valida que la declaración de rol exista, no su contenido semántico."
  ],

  "remaining_blockers": [
    { "id": "RB-01", "bloquea": "sc-08-aux-hitl como PASS de change; SC-GOV-008 para H", "que_falta": "AUD-H-01 — preservar verbatim los cuatro informes de crítica independiente sobre H, o declarar expresamente que no se conservaron y que los hallazgos son transcripción no verificable del implementador. Sin esto no hay artefacto que acredite identidad separada implementador/crítico, y se repite el patrón que AUD-F-02 condenó el 2026-09-20." },
    { "id": "RB-02", "bloquea": "CL-10, SC-GOV-025, GF", "que_falta": "AUD-H-10 — actualizar traceability.md, claims.md, requirements.json y changes.json. La matriz afirma hoy sobre SC-GOV-022 algo factualmente falso." },
    { "id": "RB-03", "bloquea": "SC-GOV-021, SC-GOV-023, SC-GOV-024 y, por vía del criterio «complementos justificados» y «ningún obligatorio sin resolver», SC-GOV-025 y GF", "que_falta": "Crítica y auditoría independientes de la decisión de suficiencia GD-12 (R/N/S NOT_REQUIRED), con los artefactos auxiliary/R/review.json, auxiliary/N/review.json y auxiliary/S/review.json, que no existen. Fuera de mi alcance y no resoluble en solo lectura." },
    { "id": "RB-04", "bloquea": "sc-06-scientific-synthesis, SC-GOV-016 sobre resultados reales, SC-GOV-025, GF", "que_falta": "Síntesis científica de los resultados efectivamente obtenidos en A, B, C y H. La única existente es del 2026-09-20 y no contiene ninguna afirmación de resultado." },
    { "id": "RB-05", "bloquea": "SC-GOV-025, GF", "que_falta": "La auditoría final independiente requisito por requisito sobre el snapshot post-campaña, con su artefacto scientific-closure-audit.json. El existente audita 5b40a55, anterior a toda ejecución. Este informe cubre H y no lo sustituye." },
    { "id": "RB-06", "bloquea": "SC-GOV-025", "que_falta": "Trazabilidad de las afirmaciones a los capítulos 2 y 3 de la memoria. No hay artefacto; sólo prosa normativa que lo ordena." },
    { "id": "RB-07", "bloquea": "Nada por sí solo; debe quedar declarado", "que_falta": "AUD-H-09 — INV-10 (las 74 pruebas focalizadas) y la reproducción estricta 18/18 no fueron verificados de forma independiente por esta auditoría, por ausencia de sklearn/pytest en el entorno y por la prohibición de ejecutar el runner. BLOCKED para esos dos puntos; no los doy por PASS por confianza." },
    { "id": "RB-08", "bloquea": "Nada; correcciones menores", "que_falta": "AUD-H-03 (tres diferencias entre intentos, no dos), AUD-H-05 (13 afirmaciones prohibidas, no 12), AUD-H-06 (emitir los límites en el paquete de evidencia del runner), AUD-H-08 (corregir la cita de GD-29)." }
  ]
}
```

**Lo esencial, en prosa.** Verifiqué la ciencia de H por mi cuenta y se sostiene: recompute las 72 métricas desde los CSV con implementaciones propias en Python puro, sin sklearn, y dieron 0 discrepancias; reconstruí la concordancia 16/20 desde los datos crudos; comprobé las reglas temporales en los 120 eventos y la estratificación en las seis agrupaciones; leí los ledgers en modo `ro` y confirmé 91/91 hashes de A/B/C intactos. La preinscripción se sostiene sobre git y no sobre lo que dicen los documentos: paquete congelado y commiteado a las 16:57:51Z, respuesta del operador a las 19:14:26Z, respuesta anclada a las 19:15:14Z, corrida a las 19:15:27Z.

Tres cosas que el implementador no dice y hay que decir. La primera y más importante: los cuatro registros que el operador aceptó son exactamente los cuatro que el generador de corrupción invirtió y exactamente los cuatro que el oráculo simulado corrigió sobre los mismos eventos — detección humana 0/4 contra 4/4. Todo el insumo está publicado, pero la conclusión no está enunciada en ningún artefacto. La segunda: no se conservó ningún informe de las cuatro rondas de crítica independiente, sólo resúmenes del propio implementador, que es la forma exacta que el hallazgo AUD-F-02 condenó hace un día en este mismo proyecto. La tercera: entre el primer intento y la corrida de completado hay tres diferencias, no dos.

Sobre el gate: H deja de ser el obstáculo, y SC-GOV-022 puede pasar a PASS_WITH_LIMITATIONS. El recuento de afirmaciones pasa de 4/10 a 9/10. Pero GF no puede evaluarse como PASS ni SC-GOV-025 salir de BLOCKED, por razones ajenas a H: la decisión GD-12 que declara innecesarios a R, N y S nunca fue criticada por nadie independiente, no existe síntesis de los resultados realmente obtenidos, no hay trazabilidad a la memoria y la auditoría final requisito por requisito que el propio requisito prescribe audita un snapshot anterior a toda ejecución. Lo que falta es cierre y revisión, no cómputo: nada de ello exige reabrir el holdout ni reejecutar A, B o C.
