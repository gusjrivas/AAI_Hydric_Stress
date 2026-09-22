# Revisión crítica independiente — paquete HITL v3 (complemento H)

> Informe del `scientific_critic`, ronda 3, sesión nueva y separada, de solo lectura.
> Objeto: el paquete de intervención humana v3, tras corregir la ronda 2.
> Transcripción literal. No se corrige ni se resume.

Sesión nueva, solo lectura. No modifiqué nada. `git status --porcelain` vacío, `git diff --check` vacío.

Resumen ejecutivo: **el paquete v3 aguanta**. Las cuatro correcciones materiales de la ronda 2 están hechas de verdad, las pruebas nuevas son contingentes (las hice fallar mentalmente caso por caso y una de ellas —la de reproducibilidad del paquete— la reproduje yo mismo bit a bit), y no encontré ningún defecto material nuevo. Quedan tres MENORES y varias observaciones.

---

## A) Hallazgos previos

### Ronda 1 (C-01..C-14)

| ID | Veredicto | Comprobación |
|---|---|---|
| **C-01, C-02** | RESUELTO (ver E-01) | `hidden_from_participant` = 5 ítems, ninguno menciona etiqueta limpia / corrupción / proporción / revisor simulado. `explicitly_not_claimed_hidden` declara los 5 derivables. Derivé yo los 20 escenarios: 4/20 con `recorded_label` ≠ `(observed < p20)`, y el paquete lo declara derivable, no oculto. |
| **C-03** | RESUELTO | `grep 42` en el contrato: solo aparece dentro de hashes y en el texto del propio hallazgo. `primary_seed_for_human_package: 0`, `seed: 0` en paquete y ancla. |
| **C-04** | RESUELTO | Reemplazada por `test_package_does_not_claim_a_blinding_it_does_not_have` (tests 724-758), que además exige `0 < mismatches < 20` sobre los escenarios reales. Ver D-02. |
| **C-05** | RESUELTO | Los 10 invariantes se computan sobre datos de la corrida o se declaran `not_measured_in_run` con `measured_where`. Ninguna constante literal. |
| **C-06, C-14, C-13** | RESUELTO como limitación / ancla | `declared_limitations_predeclared` conserva las entradas; el ancla `human-package-freeze.json` está commiteada (fbd6499) y es **byte-idéntica** a la copia del respaldo (`diff` vacío). |
| **C-07** | RESUELTO | `assert_package_contains_no_data_beyond_feedback_window` recorre fechas publicadas; el test la falsifica con `target_date=2022-01-04` y exige `HitlValidationError`. |
| **C-08** | RESUELTO | `SIMULATED_REVIEWER_ROLE`; `validate_feedback_events` restringe el rol por origen (`simulado`→sólo oráculo, `humano_controlado`→sólo whitelist). Cruzarlos se rechaza (2 pruebas). |
| **C-09** | RESUELTO | SIM usa `2022-01-01` fijo; HUMAN usa `responded_at_utc`; ausente → exit 9. Test 1060 lo verifica en ambos sentidos. |
| **C-10** | RESUELTO | `validate_human_response` compara contra `expected_operator.operator_id`. |
| **C-11** | RESUELTO | `select_review_events` aborta con `HitlNotEvaluableError` si el equiespaciado colapsa; no hay camino de respaldo. |
| **C-12** | RESUELTO | Ver D-05. |

Ninguno regresó.

### Ronda 2 (D-01..D-15)

| ID | Veredicto | Comprobación concreta |
|---|---|---|
| **D-01** (MAT) | **RESUELTO** | El sexto ítem («qué decisión tomó el revisor simulado») fue retirado de `PACKAGE_HIDDEN_FIELDS` (diff 6afe076) y aparece ahora en `explicitly_not_claimed_hidden`, en contrato y paquete. Derivé yo el resto (ver E-01 por un residuo de redacción). |
| **D-02** (MAT) | **RESUELTO** | Analicé aserción por aserción las líneas 733-758: `_false_hiding_claims(package) == []` puede dar no-vacío (lo demuestra el test negativo 761-771, que muta el paquete y exige `== ["limpia"]` y `== ["revisor simulado"]`); `0 < len(mismatches) < 20` es contingente sobre datos (observado: 4). No queda ningún `X or True` ni ningún filtro siempre verdadero. |
| **D-03** (MAT) | **RESUELTO** | `abc_paths_opened` no existe en ningún lado salvo en el texto del hallazgo. `abc_paths_referenced_in_configuration` **sí existe** en el runner (línea 2323), se publica con `_kind: structural_guard` y una nota que dice explícitamente que es 0 por construcción. El test 1108-1113 fija ambas condiciones. |
| **D-04** (MAT) | **RESUELTO** | Verifiqué la clasificación uno por uno (ver abajo). 6 `structural_guard` + 1 `contingent_measurement` + 3 `not_measured_in_run`; el test exige los recuentos y, para INV-02, exige **fidelidad** (`inv_02["holds"] == (ambient == [])`), que es la forma correcta de hacerlo contingente. |
| **D-05** (MEN) | **RESUELTO** | Las cuatro identidades coinciden: ancla, `package-preparation-record.code_version.commit`, `preflight.preflight_recapture.head_commit` y `environment/build_identity.json` = `6afe0765abb9…`; imagen `sha256:234fe49f…` en ancla, preflight e `image-id.txt`. GD-27 ya no transcribe la identidad: delega en el ancla. |
| **D-06** (MEN) | **PARCIAL** | Ver E-06: sobrevive el encabezado `# Paquete ciego y respuesta humana` en `tests/test_auxiliary_hitl_v1.py:661`. |
| **D-07** (MEN) | **RESUELTO** (con observación E-04) | La validación precede a `apply_feedback` (diff verificado); `apply_feedback` levanta `HitlValidationError [R06]` ante vocabulario desconocido y `[R07]` ante `corrected_label` inválido. Comprobé que **no se perdió ninguna comprobación**: la única que cambió de operando es R20 (ver E-04), y la propiedad real queda cubierta por R19 + el chequeo explícito `with_corr_model_id == frozen_model_id`. |
| **D-08** (MEN) | **RESUELTO** | Declarado en `blinding.consequence_declared`, en `explicitly_not_claimed_hidden` ítem 4 y en las limitaciones. |
| **D-09** (MEN) | **RESUELTO, evadible por omisión** | Ver E-02. |
| **D-10** (MEN) | **PARCIAL** | Ver E-03: rechaza semillas fuera del conjunto, pero acepta cualquier subconjunto. |
| **D-11** (OBS) | **RESUELTO** | `what_is_blinded` solo enumera métricas, 2022 y 2023-2025. |
| **D-12** (OBS) | **RESUELTO** | `altered_scenario` reescrito según lo que efectivamente se verifica (hash + `scenario_id` ajeno). |
| **D-13** (OBS) | **RESUELTO** | `resolve()` presente; el test 1130 crea un symlink de nombre inocuo hacia `evidence/A` y exige detección — sin `resolve()` fallaría. Ver E-08 por un matiz. |
| **D-14** (OBS) | **PARCIAL** | Alias documentado (`n_no_change_note`) ✓, pero ver E-05. |
| **D-15** (OBS) | **RESUELTO** como limitación declarada. |

**Honestidad de la clasificación `kind`** (revisada una por una): INV-01 (aborta en `_assert_no_future_data`), INV-04 (P20 único en `build_hitl_frames`), INV-05 (mismo `frames.evaluation` a los tres brazos), INV-06 (ventanas disjuntas 2021/2022), INV-08 (un solo `origin` por llamada), INV-09 (`arm` entra en el hash del `model_id`) → los seis son efectivamente incapaces de dar falso con este código: `structural_guard` es la etiqueta correcta, y los `guaranteed_by`/`would_break_if` que declaran son ciertos. INV-02 sí puede dar falso (mide `sys.modules` del proceso) y declara su alcance y su limitación. INV-03/07/10 realmente no se miden en una corrida única. **No encontré ningún caso de guarda estructural disfrazada de medición ni al revés.**

---

## B) Hallazgos nuevos

| ID | Sev. | Ubicación | Comprobación / Esperado vs. Observado |
|---|---|---|---|
| **E-01** | MENOR | `auxiliary_hitl_v1.py:1052` (`PACKAGE_HIDDEN_FIELDS[0]`) y contrato `human_intervention_package.hidden_from_participant[0]` | El paquete declara oculta «cualquier métrica de cualquier brazo, en cualquier pista», pero muestra `model_probability` y `model_alert` del brazo `frozen` en los 20 escenarios, y la etiqueta limpia es derivable. Computé la matriz de confusión del brazo congelado sobre las 20 fechas revisadas: **TP=8, FP=2, TN=7, FN=3** (aciertos 15/20). Esperado: que lo declarado oculto no sea derivable. Observado: una métrica del brazo `frozen` sobre 2021 sí lo es. **No es material**: no revela ninguna métrica de evaluación (todas se computan sobre 2022), no informa el efecto de ninguna decisión y no puede inducir la respuesta, que ya está determinada por la regla que el paquete enuncia. Corrección de una línea: «ninguna métrica de **evaluación** (2022) de ningún brazo». |
| **E-02** | MENOR | `main()` líneas 2087, 2133-2135, 2194-2208 | `--contract` y `--package-anchor` son opcionales (`default=None`). Si se omite `--contract`, `contract_sha256 == ""` y la comparación queda cortocircuitada por `if contract_sha256 and …`: el vínculo paquete↔contrato **no se verifica** y la evidencia registra `contract_sha256: ""`. Si se omite `--package-anchor`, el ancla de git no se contrasta. Además el ancla solo se compara por `package_sha256`, no por `contract_sha256` ni por `commit`. Esperado: que D-09 no sea evadible. Observado: se evade omitiendo un flag. **Afecta al `run`, no a mostrar el paquete.** Arreglo: exigir ambos en `--mode run` y comparar también `contract_sha256`. |
| **E-03** | MENOR | `main()` líneas 2225-2232 | `if not set(seeds) <= set(DEFAULT_SEEDS)` rechaza semillas ajenas, pero acepta cualquier **subconjunto**: `--seeds 0` pasa la validación. La prohibición congelada es «sin seleccionar semillas favorables», y seleccionar un subconjunto es exactamente ese vector. Además `tuple(int(s) for s in args.seeds.split(","))` levanta `ValueError` sin tipar ante entrada no numérica, en vez de un rechazo cerrado con motivo. Arreglo: exigir igualdad con el conjunto congelado en corrida científica. |
| **E-04** | OBSERVACIÓN | `auxiliary_hitl_v1.py:1385-1406` | El `provisional_successor_id` se deriva de `content_sha256([event_id…])`, que nunca puede coincidir con `event["model_version"]`: **R20 queda infalsificable dentro de la corrida**. No hay falso negativo real —R19 fuerza `model_version == frozen_model_id`, y la autorreferencia verdadera la cierra la línea 1426— pero esa línea tampoco puede dispararse jamás, porque `frozen` y `refit_with_corrections` difieren en `arm` y en `track` dentro del hash. Es correcto que INV-09 se publique como `structural_guard`; lo que sobra es el comentario «basta para detectar autorreferencia», que afirma más de lo que el código hace. |
| **E-05** | OBSERVACIÓN | `tests/test_auxiliary_hitl_v1.py:995` | `daily_series=None if False else _DAILY_SERIES_HOLDER["value"]` — expresión muerta y tautológica dentro de la prueba escrita para D-04. No hace la prueba vacua (ninguna aserción depende de ella), pero es residuo de la misma familia que D-14. |
| **E-06** | OBSERVACIÓN | `tests/test_auxiliary_hitl_v1.py:661` | Encabezado `# Paquete ciego y respuesta humana`. D-06 declaró eliminado el lenguaje de «paquete ciego» de encabezados y pruebas; este sobrevivió. |
| **E-07** | OBSERVACIÓN | Contrato `visible_to_participant` | Enumera 7 ítems; el paquete publica además `sensor_id`, `position`, `model_version`, `target_threshold` y `decision_options`. Inocuos, pero la lista se lee como exhaustiva y no lo es. |
| **E-08** | OBSERVACIÓN | `assert_no_reserved_paths:258-261` | Tras D-13 solo se compara la ruta **resuelta**; la cadena cruda ya no se comprueba (salvo fallback por `OSError`). Lo robusto es comprobar ambas. Además `--package-anchor` no entra en `configured_paths`, así que esa ruta no pasa por la guarda. |
| **E-09** | OBSERVACIÓN | Paquete `version: 1` (hardcodeado en `build_human_package:1141`); `preflight-H.json` | Tres paquetes congelados distintos llevan todos `version: 1`; solo el hash y el `contract_sha256` incrustado los distinguen. Y el preflight conserva un bloque `repository` viejo (`head_commit: a742e56`, `tree_clean: true`) junto al bloque de recaptura (`6afe076`, `tree_clean: false`). Verifiqué que el `tree_clean:false` es inocuo —a las 16:43:35 lo único sucio era el propio ancla, commiteada 11 s después en fbd6499— pero la convivencia de dos identidades en un mismo archivo es justo la forma de D-05 y conviene marcar el bloque viejo como superado *in situ*. |

No encontré: sobreafirmación agronómica (13 aserciones prohibidas, `expert_agronomic_feedback` bloqueado en código y probado), fuga temporal (`R12`/`R13`/`R14`/`R15` + frontera dura), contaminación del holdout, ni relajación de nada.

---

## C) Verificaciones mecánicas (hechas por mí)

- **SHA-256 canónico del paquete**: recalculado = `e1c3eb70aa15532b3318ac7dcd16fa9070f81d516a8322671ddbc6b77e8d42c9` = `package_sha256` del paquete = ancla = registro de preparación = preflight. ✅
- **SHA-256 del contrato**: `71e41896345d8d4dba4e913fc5d717e3ff7ad39c3d52bf57c124f55349e5a1ef` = repo = copia respaldada = `contract_sha256` del paquete = del ancla = del preflight. ✅ Los hashes declarados en `supersedes` para v1 (`a124db1a…`, 5f30880) y v2 (`e74bc312…`, 547c1a9) los recalculé desde git: **correctos**. ✅
- **Identidad ejecutable**: commit `6afe0765abb9be5202f4ea479b6bea483ac4d330` e imagen `sha256:234fe49f…` coinciden en ancla, registro de preparación, preflight y `build_identity.json`. **D-05 cerrado.** ✅
- **`sha256sum -c manifest/SHA256SUMS`** (HITL): 14/14 OK, 0 FAILED; además verifiqué que el manifiesto **cubre todos** los archivos del directorio (ningún archivo sin listar). ✅
- **`sha256sum -c SHA256SUMS`** (A/B/C final): **91 OK, 0 FAILED**. ✅
- **Ledger holdout (solo lectura, `mode=ro`)**: estado `CONFIRMADA`, `reserved_by_attempt_id = 2121cdc901454df6be922c54a42d208d`, `finalized_result_reference = /runtime/evidence/C`. ✅
- **Suite focalizada**: `73 passed in 14.02s`. ✅
- **Reproducción independiente del paquete** (extra, no pedida): regeneré `prepare_human_package` en mi propio intérprete, fuera del contenedor, desde los CSV crudos, y obtuve un paquete **idéntico byte a byte** (mismo `package_sha256`). Es la verificación más fuerte del conjunto. ✅
- **Git**: `git status --porcelain` vacío; `git diff --check` limpio; `git diff origin/main --stat -- src/ frontend/ backend/` = un único archivo nuevo (`auxiliary_hitl_v1.py`, +2345), sin tocar frontend ni backend. ✅
- **Contrato v1 vs v2 vs v3**: `verdict_criteria` **idéntico en las tres versiones**; `stop_conditions` idéntico; `invariants` idéntico; `prohibited_assertions` solo creció (+2 en v3); `declared_limitations_predeclared` solo creció (+3 en v3). **Ninguna relajación.** ✅
- **Diseño congelado**: `docs/research/scientific-closure-decisions.md` no difiere de `origin/main`. Contrasté parámetro por parámetro (RF 100/8/5/`n_jobs=1`/seed, train ≤2020-12-31, P20 congelado, feedback 2021, evaluación emisiones 2022-01-01..12-28, tres brazos, 20 eventos 10/10, estrato insuficiente → NOT_EVALUABLE, selección solo con predicciones de 2021, corrupción 10% con stream independiente, revisor restituye limpia, `validated_at ≥` fin del día objetivo, seeds [0,1,2,3,4], métricas MCC/AP/Brier/F1/FP/FN/episodios, ambos deltas): **todo coincide, nada se alteró.** ✅

**Limitaciones de esta revisión**: (1) no pude verificar los `package_sha256` de los dos paquetes superados —ya no existen en ningún lado— así que su no-uso descansa en la declaración del ancla; (2) `preflight-H.json` y `manifest/SHA256SUMS` viven solo en el montaje escribible (solo el ancla está en git), de modo que la cadena de custodia real es el hash anclado en fbd6499; (3) no ejecuté el runner en modo `run`, como se me indicó, así que E-02/E-03 los establezco por lectura de código y no por ejecución.

---

## Veredicto final: **APTO_PARA_MOSTRAR**

Razones: el paquete que se le va a mostrar al operador es reproducible bit a bit desde entradas congeladas (lo regeneré yo), su hash coincide en las cuatro fuentes y está anclado en git antes de cualquier respuesta, el contrato v3 no relaja ni un criterio respecto de v1/v2, el diseño congelado está intacto parámetro por parámetro, A/B/C sigue verificando 91/91, el holdout sigue CONFIRMADA con el mismo `attempt_id`, y —lo decisivo para esta tercera ronda— **las cuatro correcciones materiales de la ronda 2 son reales y las pruebas escritas para cerrarlas son contingentes**: cada aserción nueva puede fallar, dos de ellas incluyen caso negativo por mutación, y la clasificación `kind` de los invariantes es honesta ítem por ítem. El patrón de «la corrección introduce el defecto siguiente» **no se repitió a nivel material**.

Lo que falta, y que **no impide mostrar**:
1. **E-01** — una línea de redacción en `hidden_from_participant`. Si deciden corregirla, hay que recongelar y re-anclar **antes** de mostrar nada; si no, basta con no repetir esa frase en el informe. Mi recomendación: corregirla solo si van a recongelar por otro motivo.
2. **E-02 y E-03 sí deben cerrarse antes de ejecutar `--mode run`**: son los controles de la corrida, no del paquete. Concretamente, exigir `--contract` y `--package-anchor` en modo `run`, y exigir el conjunto de semillas completo.
3. E-04..E-09 son higiene: comentario que sobreafirma, dos residuos de código muerto/lenguaje, dos listas incompletas y un bloque viejo en el preflight.
