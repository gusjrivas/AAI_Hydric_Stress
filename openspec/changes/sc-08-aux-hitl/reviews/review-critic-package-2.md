# Revisión crítica independiente — paquete HITL v2 (complemento H)

> Informe del `scientific_critic`, ronda 2, sesión nueva y separada, de solo lectura.
> Objeto: el paquete de intervención humana v2, tras corregir la ronda 1.
> Transcripción literal. No se corrige ni se resume.

Sesión nueva, solo lectura. No modifiqué nada. `git status --porcelain` vacío, `git diff --check` vacío.

## 0. Verificaciones mecánicas (hechas por mí)

| Comprobación | Resultado |
|---|---|
| SHA-256 canónico del paquete (payload sin `package_sha256`, `sort_keys=True`, `separators=(',',':')`, `ensure_ascii=False`) | `29afedc9d951b332f61ed48bd8aada2bb30467b0c082db24489b5f9bcd9cdea8` = `package_sha256` ✔ |
| Igual al de `human-package-freeze.json` (repo y respaldo) y al de `package-preparation-record.json` | ✔ los tres coinciden |
| `sha256sum` del archivo de contrato (repo y respaldo) | `e74bc31235f9aa38808fb026aa3f7a0ec9e2de5bf9ca2f432e3f2ccd23dc917a` = `contract_sha256` del paquete y del ancla ✔ |
| `diff` contrato repo vs respaldo; ancla repo vs respaldo | idénticos ✔ |
| `sha256sum -c manifest/SHA256SUMS` (HITL) | **14 OK, 0 FAILED** ✔ |
| `sha256sum -c SHA256SUMS` (closure-campaign/evidence-snapshots/final) | **91 OK, 0 FAILED** ✔ (lo esperado) |
| Ledger holdout en `mode=ro` | tabla `holdout_registry`: `state=CONFIRMADA`, `reserved_by_attempt_id=2121cdc901454df6be922c54a42d208d` ✔ |
| Suite focalizada | literal: `..................... [100%]` / **`69 passed in 18.24s`** |
| `git log --oneline -8` | `f347b88, 4ae6df0, 2c257c9, 547c1a9, eb9cf17, 5f30880, a742e56, 5355aee` |
| `git diff origin/main --stat -- src/ frontend/ backend/` | un solo archivo: `src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py` (+2215). Nada de A/B/C tocado ✔ |
| `docs/research/scientific-closure-decisions.md` vs `origin/main` | **no aparece en el diff**: el diseño congelado NO fue alterado ✔ |

Derivación que hice sobre el paquete: la etiqueta limpia es determinable en **20/20**; hay **4 registros corrompidos** (H-SC-004, 008, 009, 020); estratos **10 alertas / 10 no-alertas** ✔; `max(target_date)=2021-12-31`, `max(emission_date)=2021-12-28` ✔.

## A. Los 14 hallazgos

| # | Veredicto | Comprobación concreta |
|---|---|---|
| **C-01** | **PARCIAL** | Cierto: se retiró la garantía falsa, `blinding.level=PARCIAL`, `explicitly_not_claimed_hidden` declara los tres puntos, y la limitación entró en `declared_limitations_predeclared`. **Pero** `hidden_from_participant` sigue conteniendo un ítem falso: «qué decisión tomó el revisor simulado en el mismo escenario». Ese vector es derivable en 20/20 con los mismos campos visibles (ver D-01). La lista NO es verdadera campo por campo. |
| **C-02** | **PARCIAL** | Contrato y paquete dicen lo mismo entre sí (verifiqué ítem por ítem: las 6 entradas de `hidden_from_participant` son idénticas). Pero ambos arrastran el mismo ítem falso, y `blinding.what_is_blinded[0]` del contrato vuelve a enunciar, bajo el rótulo «lo que SÍ está cegado», que «el operador no sabe cuáles escenarios fueron corrompidos», salvado sólo por la coletilla «en el sentido de que el paquete no se lo dice» (D-11). |
| **C-03** | **RESUELTO** | `grep '42'` en el contrato v2: única aparición es la narración del propio hallazgo. Prosa (`human_intervention_package.scenarios`) dice «semilla primaria 0»; `primary_seed_for_human_package: 0`; paquete `seed: 0`; `PRIMARY_SEED_FOR_HUMAN_PACKAGE = 0`. Coherente. |
| **C-04** | **NO_RESUELTO** | La prueba de reemplazo `test_package_does_not_claim_a_blinding_it_does_not_have` contiene **dos aserciones vacuas**: el filtro `if (1 if a < b else 0) is not None` es siempre verdadero (reproducido: sobre un paquete falsificado con `observed == p20` el `len(determinable)==20` sigue dando `True`), y la línea 726 es literalmente `assert "explicitly_not_claimed_hidden" not in package or True`. Sólo la parte léxica (líneas 721-725) puede fallar, y no detecta el ítem 6. Ver D-02. |
| **C-05** | **PARCIAL / RESUELTO_PERO_INTRODUCE_OTRO_DEFECTO** | Los `True` literales desaparecieron y los tres `NOT_MEASURED_IN_RUN` **son legítimos** (INV-07 exige una segunda corrida; INV-10 exige entradas inválidas; INV-03 exige hashes externos: ninguno es medible en una corrida única — no es una excusa). Pero 6 de los 10 invariantes ahora son **tautologías por construcción**, y dos «métricas decisivas» siguen sin poder valer otra cosa (D-03, D-04). Además `abc_paths_opened`, que el contrato v2 lista como decisiva, **no existe** en el runner ni en la evidencia. |
| **C-06** | **RESUELTO** (como limitación) | Entrada nueva y explícita en `declared_limitations_predeclared`; replicada en `blinding.what_is_NOT_blinded[1]` y en `explicitly_not_claimed_hidden[2]` del paquete. |
| **C-07** | **RESUELTO** | `assert_package_contains_no_data_beyond_feedback_window` recorre `emission_date`/`target_date` de los 20 escenarios y aborta; el test 748 muta `target_date="2022-01-04"` y exige la excepción — falsable de verdad. Docstring de `prepare_human_package` corregido y ahora admite que filas de 2022 sí se materializan. |
| **C-08** | **RESUELTO** | `SIMULATED_REVIEWER_ROLE="simulated_reviewer_oracle"`; `validate_feedback_events` fija `allowed_roles` **por origen** (simulado→sólo oráculo, humano→sólo whitelist). Tests 267 y 282 cubren los dos cruces. Revisé también `run_track_for_seed` y `recalibrate_again`: no hay camino donde se crucen. |
| **C-09** | **RESUELTO** | `main()` exige `responded_at_utc` y retorna 9 si falta; SIM conserva `2022-01-01T00:00:00Z`. Test 1002 verifica ambos prefijos. |
| **C-10** | **RESUELTO** | `validate_human_response` compara `operator_id` con `package["expected_operator"]["operator_id"]`; test 831. |
| **C-11** | **RESUELTO** | El camino de respaldo se eliminó; ahora `HitlNotEvaluableError` si el equiespaciado colapsa (rama defensiva inalcanzable con `len≥10`) y si el estrato es insuficiente (test 214). |
| **C-12** | **NO_RESUELTO** | `preflight-H.json.preflight_recapture_2026_09_21` declara `head_commit: 547c1a9…` e `h_image_id: sha256:7a9575db…`. El paquete entregado fue producido por `commit 4ae6df0…` con `image sha256:563d0b9f…` (`build_identity.json`, `code/HEAD.txt`, `environment/image-id.txt`, ancla, registro de preparación). El preflight sigue sin cubrir el commit ni la imagen finales. Ver D-05. |
| **C-13** | **PARCIAL** | El ancla existe y está commiteada (`2c257c9`, actualizada en `f347b88`); verifiqué que el `package_sha256` es idéntico en ambas versiones del ancla. Pero nada en el runner contrasta el paquete contra el ancla: `main()` sólo recalcula su **autohash** (línea 2085-2091). El ancla externa es un control humano, no un control ejecutado. |
| **C-14** | **RESUELTO** (como registro) | Interpretación asentada en GD-28 y en `tracks.HUMAN.authority`; sometida a esta auditoría. |

## B. Hallazgos nuevos

**D-01 — MATERIAL. `hidden_from_participant` sigue conteniendo una afirmación falsa que se le muestra al participante.**
Ubicación: `auxiliary_hitl_v1.py:1036` (`PACKAGE_HIDDEN_FIELDS[5]`), `human-package.json:32`, contrato línea 224.
Comprobación: el diseño congelado y el contrato (`tracks.SIM.reviewer`, `design_frozen.simulated_reviewer`) publican que el revisor simulado *restituye la etiqueta limpia y deja sin cambio las confirmaciones*. La etiqueta limpia es determinable en 20/20. Por lo tanto la decisión del oráculo es derivable exactamente: `CORREGIR` en H-SC-004/008/009/020 y `ACEPTAR` en los otros 16. Lo reproduje con un script de 6 líneas sobre el propio paquete.
Esperado: la lista enumera *sólo* lo que efectivamente está oculto (es la resolución que el propio contrato declara para C-02).
Observado: enumera una sexta cosa que es derivable con los campos visibles. Es el mismo defecto que C-01/C-02, sobreviviendo en el único ítem que no se revisó. Bloqueante: el paquete le afirma al operador algo falso.

**D-02 — MATERIAL. La prueba escrita para cerrar C-04 es vacua.**
Ubicación: `tests/test_auxiliary_hitl_v1.py:705-726`.
Comprobación: el filtro `if (1 if s["observed_soil_moisture_at_target"] < s["p20_threshold_frozen"] else 0) is not None` compara un `int` con `None`: siempre verdadero. Ejecuté la comprensión sobre un paquete alterado en el que la etiqueta no es determinable y `len(determinable) == len(scenarios)` sigue dando `True`. La línea 726, `assert "explicitly_not_claimed_hidden" not in package or True`, es un `assert X or True`: no puede fallar, y además su condición está invertida (afirma la *ausencia* de la clave que el paquete debe tener).
Esperado: una prueba que falle si el paquete no es determinable o si no declara `explicitly_not_claimed_hidden`.
Observado: dos aserciones que pasan con cualquier entrada. C-04 se declaró resuelto con una prueba del mismo género que condenaba.

**D-03 — MATERIAL. Métrica decisiva declarada que no existe en la evidencia, y su sucedánea es constante.**
Ubicación: contrato `technical_metrics.mechanism_metrics_decisive[9]` (`"abc_paths_opened (debe ser 0)"`) vs `auxiliary_hitl_v1.py:2199`.
Comprobación: `grep -rn "abc_paths_opened" src/ tests/` → sólo aparece en el contrato. Lo que el runner emite es `abc_paths_referenced_in_configuration = len(reserved)`, y `main()` retorna 11 y aborta si `reserved` no está vacío (líneas 2020-2027): en cualquier artefacto publicado ese valor es **0 por construcción**.
Esperado: que las métricas decisivas existan con el nombre contratado y puedan tomar más de un valor.
Observado: nombre inexistente + contador que no puede ser distinto de 0. Es la recurrencia literal del sub-hallazgo de C-05 («dos métricas decisivas no existían en la evidencia»), corregido para dos y reintroducido para una.

**D-04 — MATERIAL. Seis de los diez invariantes y dos «métricas decisivas» son tautologías: se computan, pero no pueden fallar.**
Ubicación: `auxiliary_hitl_v1.py:1831-1836, 1857-1861, 1464-1467, 1873-1954`.
Comprobaciones:
- INV-04: `build_hitl_frames:448` asigna `stress_label = build_target(future_soil_moisture, p20_frozen)`, y `build_target` (`features.py:272`) es `(x < threshold).astype(int)`. El chequeo recomputa **la misma expresión con el mismo `p20_frozen` sobre la misma columna**.
- INV-05: `evaluate_arm` recibe siempre `frames.evaluation`; `n_observations = len(y_true)`. `set(...) == {n_evaluation_rows}` no puede fallar.
- INV-06: las ventanas de feedback y evaluación se construyen con máscaras disjuntas sobre `target_ts`; la intersección es vacía por construcción.
- INV-08: `origin` entra como constante única a `build_feedback_events`; cada conjunto tiene cardinal 1 por construcción.
- INV-09 y `predecessor_preserved`: `deterministic_model_id` hashea el literal `arm` entre sus entradas, así que `frozen` / `refit_no_corrections` / `refit_with_corrections` **nunca** pueden colisionar. `predecessor_preserved` compara tres hashes que difieren por definición; no mide preservación de artefactos.
- `lineage_chain_complete`: `all((r.lineage is not None) == (r.recalibration_status == APPLIED))`, siendo que `lineage_payload` se asigna *iff* el estado es `APPLIED` en la misma función. Identidad pura.
- INV-01: `_assert_no_future_data` ya abortó aguas arriba; en cualquier artefacto publicado `satisfied` es constante.
El propio test lo confirma: `test_invariants_are_measured_not_declared:986-994` **hardcodea** `satisfied is True` para los seis.
Esperado: derivación de una comprobación que pueda dar falso (política `invariants_measurement_policy`).
Observado: sólo INV-02 es contingente y está bien construido (el test verifica la *fidelidad* de la medición contra `sys.modules` ambiente). Los otros son guardas de regresión de código útiles, pero se publican como si fueran evidencia de la corrida. Si se conservan, deben etiquetarse `structural_guard` y no `measured/satisfied`.

**D-05 — MENOR. Tres identidades ejecutables distintas en tres artefactos de gobernanza.**
Ubicación: `preflight-H.json` (`547c1a9` / `sha256:7a9575db…`), ancla y respaldo (`4ae6df0` / `sha256:563d0b9f…`), `openspec/scientific-closure/decisions.md` GD-27 (`5f30880` / `sha256:e8ac0629…`).
Esperado: el preflight y GD-27 nombran el commit e imagen que produjeron el paquete.
Observado: ninguno de los dos lo hace. La nota `package_hash_stability_note` del ancla mitiga el impacto (el hash es idéntico) pero no cierra C-12.

**D-06 — MENOR. Lenguaje residual de «paquete ciego» en el código que construye el paquete.**
Ubicación: `auxiliary_hitl_v1.py:1012` (encabezado de sección), `:1077` (docstring de `build_human_package`: «Construye el paquete **ciego**… Deliberadamente **no** incluye la etiqueta limpia, la posición de la corrupción»), `:1977` (ayuda de la CLI), `tests:661`.
Esperado: coherencia con `prohibited_assertions[9]` («Cegamiento de la intervención humana respecto de la etiqueta correcta»).
Observado: la función que genera el artefacto sigue autodescribiéndose como ciega. No afecta el JSON entregado, pero es exactamente la afirmación prohibida, en el lugar donde la crítica la había encontrado.

**D-07 — MENOR. `apply_feedback` se ejecuta antes de `validate_feedback_events` y una decisión desconocida produce `TypeError`, no un rechazo cerrado con motivo.**
Ubicación: `auxiliary_hitl_v1.py:1354` (aplicación) vs `:1372` (validación); rama `else` en `:945-949`; `main():2122` sólo captura `HitlValidationError`/`HitlNotEvaluableError`.
Comprobación reproducida: `apply_feedback(events=[{'fecha':…,'decision':'DECISION_INVENTADA','corrected_label':None}])` → `TypeError: int() argument must be a string… not 'NoneType'`.
Esperado (contrato `incomplete_or_contradictory_policy`): «Rechaza de forma cerrada y detiene la ejecución… registrando el motivo».
Observado: traceback no tipado. Sigue siendo fail-closed (no se publica ningún artefacto, la escritura ocurre después), pero no registra el motivo y cualquier decisión inventada *con* `corrected_label` válido se aplica antes de que R06 la rechace.

**D-08 — MENOR. Las instrucciones entregan el algoritmo que determina unívocamente las 20 respuestas, y eso no está declarado.**
Argumento a favor de que induce: `PACKAGE_INSTRUCTIONS` enuncia la regla de etiquetado *y* señala que el paquete muestra ambos operandos. Quien la aplique produce exactamente el vector del oráculo simulado (16 ACEPTAR + 4 desacuerdos), salvo la elección RECHAZAR/CORREGIR. Dar la regla que determina las 20 respuestas es funcionalmente sugerirlas, y `non_inducement_rules[0]` dice «No se sugiere ninguna respuesta».
Argumento en contra: la determinabilidad ya existía (C-01); callarla no la elimina, sólo engaña. La instrucción no nombra ningún escenario, no preferencia RECHAZAR sobre CORREGIR, no menciona efectos sobre métricas y es idéntica para los 20 escenarios — cumple las cuatro reglas al pie de la letra. El contrato ya prohíbe afirmar juicio y pericia, y declara la pista como «revisión de CALIDAD DE DATO con respuesta determinable».
Conclusión: **no viola la letra de las reglas y es preferible a ocultarlo**, pero convierte la pista HUMANA en una prueba de cumplimiento de un procedimiento dictado, no en una revisión. Falta la declaración correspondiente: ni el contrato ni el paquete dicen que *las propias instrucciones contienen la regla que determina la respuesta correcta en 20/20*. Debe añadirse a `consequence_declared` y a `declared_limitations_predeclared`.

**D-09 — MENOR. En modo `run` no se contrasta el contrato ni el ancla.**
Ubicación: `main():2029-2033, 2085-2091`. `contract_sha256` se recalcula del archivo que se pase por `--contract` y se escribe en la evidencia, sin compararlo nunca con `package["contract_sha256"]`. El paquete sólo se valida contra su propio hash; el ancla de git (`human-package-freeze.json`) no se lee.
Esperado: rechazo si el contrato no es el que congeló el paquete, y verificación contra el ancla externa.
Observado: ambas comprobaciones quedan a cargo de un humano.

**D-10 — MENOR. `--seeds` no se valida contra el conjunto congelado.**
Ubicación: `main():2108`, `seeds = tuple(int(s) for s in args.seeds.split(","))`. `DEFAULT_SEEDS` sólo es el valor por defecto. El contrato dice «PROHIBIDO seleccionar semillas favorables». La prohibición es trivialmente ejecutable en código y no lo está (queda auditable en `resolved_config.seeds`, lo cual atenúa).

**D-11 — OBSERVACIÓN. `blinding.what_is_blinded[0]` del contrato reinstala la afirmación condenada bajo el rótulo contrario.** «El operador no sabe cuáles escenarios fueron corrompidos… en el sentido de que el paquete no se lo dice» convive con `what_is_NOT_blinded[0]` («identifica exactamente qué registros son incorrectos»). La coletilla la salva de ser una contradicción formal, pero un lector del bloque «lo que SÍ está cegado» se lleva la impresión falsa.

**D-12 — OBSERVACIÓN. La regla `response_validation.altered_scenario` es inaplicable tal como está escrita.** La respuesta sólo transporta `scenario_id`, `decision`, `corrected_label`, `reason`: no hay contenido de escenario que comparar. Lo que sí se verifica es `package_sha256`. El contrato debería decir eso, o el esquema de respuesta debería exigir una copia del escenario.

**D-13 — OBSERVACIÓN. `assert_no_reserved_paths` es sólo coincidencia de subcadena sobre seis argumentos de CLI.** No hace `Path.resolve()` ni sigue enlaces simbólicos, y sólo cubre rutas pasadas por línea de comandos. Un enlace simbólico con nombre inocuo lo evade. La limitación está declarada en el docstring de INV-02, no en el contrato.

**D-14 — OBSERVACIÓN. Restos de código muerto y métricas redundantes.** `tests:942` `daily_series=None if False else _DAILY_SERIES_HOLDER["value"]`; `mechanism["n_events_received"]` y `["n_events_valid"]` son la misma expresión; `mechanism["human_track"]["n_no_change"]` es un alias de `n_accept`; `validate_feedback_events` siempre retorna `{}` (línea 894, inalcanzable con `by_rule` no vacío).

**D-15 — OBSERVACIÓN. El paquete vive únicamente en un montaje escribible.** `preflight-H.json.backup_mount.writable = true`; `human-package.json` no está en git (sólo su hash, vía el ancla). Es el diseño previsto por C-13, pero conviene registrarlo: la inmutabilidad real descansa en un único commit.

## Veredicto final

# NO_APTO

Razones que bloquean, por sí solas:

1. **D-01 (MATERIAL)**: el paquete que se le mostraría a la persona **sigue afirmándole algo falso**. La lista `hidden_from_participant` no es verdadera campo por campo: la decisión del revisor simulado es derivable en 20/20 con los mismos dos campos que ya hicieron caer la v1. La corrección de C-01/C-02 se aplicó a cinco de seis ítems y dejó el sexto intacto. Mientras ese ítem esté en el paquete, mostrarlo repite la falta original.
2. **D-02 (MATERIAL)**: la prueba redactada específicamente para cerrar C-04 no puede fallar. C-04 no está cerrado; está reemplazado por otra prueba del mismo defecto.
3. **D-03 y D-04 (MATERIAL)**: C-05 está resuelto en su forma literal (no quedan `True` constantes) pero no en su sustancia: 6 de 10 invariantes y dos de las métricas declaradas decisivas no pueden tomar otro valor, y una métrica decisiva del contrato v2 no existe en el código.

Lo que sí está bien y debe reconocerse: no hubo **ninguna relajación** del criterio de PASS. El diff v1→v2 muestra que `verdict_criteria` y `stop_conditions` quedaron **sin cambios**, que `prohibited_assertions` **sumó** dos prohibiciones y `declared_limitations_predeclared` **sumó** tres limitaciones: la v2 es estrictamente más restrictiva. Tampoco se alteró retrospectivamente ninguna condición congelada: verifiqué parámetro por parámetro contra `scientific-closure-decisions.md` (que no difiere de `origin/main`) — RF 100/8/5/`n_jobs=1`/`random_state=seed`, ventanas 2015-2020 / 2021 / 2022-01-01..12-28, P20 del train inicial congelado, los tres brazos, 20 eventos por semilla, estratos 10/10, corrupción 10 % con stream independiente (`default_rng(seed+10_000)`), revisor simulado que restituye la etiqueta limpia, semillas [0,1,2,3,4], las siete métricas y los dos deltas, y ventanas disjuntas que garantizan «no usar filas de recalibración en evaluación». Todo coincide. La separación de roles (C-08), el instante real de la respuesta humana (C-09), la validación de identidad (C-10), la guarda falsable del contenido del paquete (C-07) y las dos pruebas de aislamiento por AST y subproceso limpio están genuinamente bien hechas.

Para pasar a APTO alcanzaría con: quitar el ítem 6 de `hidden_from_participant` en `PACKAGE_HIDDEN_FIELDS`, el contrato y el paquete (lo que cambia el `package_sha256`, el ancla y el manifiesto, y exige recongelar); reescribir las dos aserciones vacuas de la prueba C-04 por una que falle sobre un paquete que declare ocultar algo derivable; y, para D-03/D-04, o bien eliminar `abc_paths_opened` del contrato y renombrar los seis invariantes tautológicos como guardas estructurales, o bien darles una medición contingente.

**Limitaciones de esta revisión**, declaradas en vez de asumidas: no ejecuté el runner en modo `run` (instrucción expresa), así que no observé `invariants.json` ni `mechanism_metrics` reales — mis conclusiones sobre D-03/D-04 provienen de lectura del código y del test que fija sus valores esperados. No pude verificar la existencia ni el contenido de `reproduction-record.json` ni de `validation-record.json`, que el contrato nombra como lugar de medición de INV-07 e INV-10: **no están en el respaldo** (el manifiesto lista 14 archivos y ninguno es esos dos). No verifiqué la imagen Docker `sha256:563d0b9f…` ni la afirmación de que su `pip freeze --all` es idéntico al histórico. No verifiqué los directorios vivos `evidence/A,B,C` (modo 0600, root); me apoyé en el respaldo externo, cuyos 91 hashes sí verifiqué.
