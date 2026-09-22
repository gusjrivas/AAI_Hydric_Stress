# Revisión independiente — paquete ciego H (HITL), campaña `hitl-complement-2026-09-21`

> Informe del `scientific_critic`, ronda 1, sesión separada de solo lectura.
> Objeto: el paquete de intervención humana v1, antes de mostrarlo al operador.
> Transcripción literal. No se corrige ni se resume.

---

## C-01 · MATERIAL · Fuga: la etiqueta "limpia" y la corrupción son derivables de forma trivial y exacta en los 20 escenarios

**Requisito afectado:** `human-package.json:hidden_from_participant[0]`, `[1]` y `[7]`; contrato `human_intervention_package.hidden_from_participant`.

**Ubicación:** `/mnt/scientific-backup/AAI_Hydric_Stress/hitl-complement-2026-09-21/package/human-package.json`, campos por escenario `observed_soil_moisture_at_target` y `p20_threshold_frozen` (presentes en los 20), contrastados con `recorded_label`.

**Comprobación reproducible:**
```
python3 -c "
import json
d=json.load(open('/mnt/.../package/human-package.json'))
for s in d['scenarios']:
    clean = 1 if s['observed_soil_moisture_at_target'] < s['p20_threshold_frozen'] else 0
    print(s['scenario_id'], clean, s['recorded_label'], 'CORRUPTA' if clean!=s['recorded_label'] else '')"
```
La regla de etiquetado es exactamente `build_target` en `/home/gus/work/AAI_Hydric_Stress_scientific_hitl/src/experiment_runner/controlled_daily_v4/features.py:269-272` (`stress = 1 si future_soil_moisture < p20`). No hay ningún empate en el paquete, así que la derivación es determinista.

**Esperado:** que el participante no pueda saber cuál fue la etiqueta limpia ni cuáles escenarios fueron corrompidos.

**Observado:** la etiqueta limpia es calculable en los 20/20 escenarios con una comparación aritmética. Quedan identificados exactamente los 4 escenarios corrompidos —**H-SC-004, H-SC-008, H-SC-009, H-SC-020**— y por tanto la proporción en el paquete (4/20 = 20 %). Esto refuta simultáneamente los ítems (a), (b) y (h) de la pregunta 1 y las tres afirmaciones correspondientes de `hidden_from_participant`, que el propio paquete le muestra al participante como garantía. El paquete no es ciego; a lo sumo es "no etiquetado".

Atenuante que corresponde registrar con honestidad: el contrato **sí** predeclara como limitación que la intervención "no es ciega respecto de la observación madurada" (`contract-H-frozen.json:declared_limitations_predeclared[1]`). Eso no salva el hallazgo: una cosa es declarar la limitación en el contrato y otra es que el artefacto que se le entrega a la persona le afirme lo contrario.

---

## C-02 · MATERIAL · El contrato es internamente contradictorio: autoriza mostrar exactamente el par de campos que determina lo que declara oculto

**Requisito afectado:** coherencia interna de `human_intervention_package`.

**Ubicación:** `contract-H-frozen.json`, `human_intervention_package.visible_to_participant[3]` ("La humedad de suelo observada y madurada en la fecha objetivo") y `[4]` ("El umbral P20 congelado del train inicial"), contra `hidden_from_participant[0]`, `[1]`, `[7]`.

**Comprobación:** lectura literal de ambas listas; la función de etiquetado es una comparación de esos dos escalares.

**Esperado:** que `visible_to_participant` y `hidden_from_participant` sean conjuntos consistentes bajo cierre deductivo.

**Observado:** `visible ⊨ ¬hidden`. La defensa "el contrato lo permite" no es sostenible, porque el contrato también lo prohíbe. Congelar un contrato autocontradictorio y luego invocar la mitad conveniente no es predeclaración: es elección posterior. Mientras la contradicción esté en el contrato congelado, cualquier veredicto que se apoye en `hidden_from_participant` es indecidible.

---

## C-03 · MATERIAL · El contrato congelado nombra una semilla que no pertenece al diseño congelado

**Requisito afectado:** diseño congelado, bloque padre: "Seeds [0,1,2,3,4]" (`docs/research/scientific-closure-decisions.md:95`).

**Ubicación:** `contract-H-frozen.json` → `human_intervention_package.scenarios`: *"Los 20 eventos del presupuesto de la **semilla primaria 42**…"*, contra `design_frozen_auxiliary_hitl_v1.primary_seed_for_human_package: 0`, `design_frozen_auxiliary_hitl_v1.seeds: [0,1,2,3,4]`, y `human-package.json:seed = 0`.

**Comprobación:** `grep -n "42" contract-H-frozen.json` y lectura de los tres campos.

**Esperado:** una única semilla, dentro de `[0,1,2,3,4]`.

**Observado:** el mismo documento congelado declara dos semillas primarias distintas (42 y 0), y 42 **no** está en el conjunto congelado. El paquete usa 0, que sí es válido, de modo que el artefacto es correcto y el contrato es el que está mal. Pero un contrato congelado que menciona una semilla fuera del diseño deja abierta, documentalmente, exactamente la puerta que el propio contrato prohíbe ("PROHIBIDO seleccionar semillas favorables"). No es reparable sin descongelar.

---

## C-04 · MATERIAL · La prueba que supuestamente verifica la ausencia de fuga es puramente léxica y da falsa garantía

**Requisito afectado:** cobertura de la verificación de no-fuga.

**Ubicación:** `/home/gus/work/AAI_Hydric_Stress_scientific_hitl/tests/test_auxiliary_hitl_v1.py:642-656`, `test_package_hides_the_information_that_would_induce_a_response`.

**Comprobación:** lectura del test. Sus aserciones son `"clean_label" not in scenario`, `"corrupted" not in scenario`, `"expected_decision" not in scenario`, ausencia de las cadenas `"2023"/"2024"/"2025"` y de `"mcc"/"holdout"/"brier"/"average_precision"/"delta"` en el serializado.

**Esperado:** una verificación semántica, p. ej. que ningún subconjunto de campos visibles permita reconstruir `stress_label`.

**Observado:** el test solo busca subcadenas. Pasa con el paquete actual pese a C-01. Es decir, la suite certifica "sin fuga" precisamente en el caso en que hay fuga total. Esto convierte la evidencia de testing en no informativa para esta propiedad, y debe considerarse así al puntuar el criterio "todas las pruebas focalizadas pasan" de `verdict_criteria.PASS`.

---

## C-05 · MATERIAL · Sobreafirmación: invariantes y "métricas de mecanismo decisivas" declarados pero nunca computados

**Requisito afectado:** `contract-H-frozen.json:technical_metrics.mechanism_metrics_decisive`; docstring del runner ("Fronteras duras … **verificadas en ejecución y no meramente documentadas**", `auxiliary_hitl_v1.py:22-27`).

**Ubicación:** `auxiliary_hitl_v1.py:1706-1745` (`run_complement_h`, dicts `mechanism` e `invariants`).

**Comprobación:**
```
grep -n "bitwise_reproducible\|closed_failure_on_invalid_inputs\|INV-07\|INV-10\|abc_artifacts_touched\|holdout_access_attempts" \
  src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py tests/test_auxiliary_hitl_v1.py
```
Resultado: solo dos coincidencias, ambas literales constantes (`"holdout_access_attempts": 0`, `"abc_artifacts_touched": 0`). Ninguna para `bitwise_reproducible`, `closed_failure_on_invalid_inputs`, `INV-07`, `INV-10`.

**Esperado:** las métricas declaradas decisivas se miden.

**Observado:**
- `INV-03`, `INV-04`, `INV-05`, `INV-06`, `INV-08` están **hardcodeados a `True`**; `holdout_access_attempts` y `abc_artifacts_touched` a `0`. Son declaraciones, no comprobaciones.
- `bitwise_reproducible` y `closed_failure_on_invalid_inputs`, listados como decisivos, **no existen** en la evidencia.
- `n_events_rejected_by_rule` es siempre `{}` y `n_events_received == n_events_valid` por construcción, porque los eventos los fabrica el propio runner; esas dos métricas no pueden discriminar nada en una corrida real.
- `INV-02` se verifica por `sys.modules`, lo que detecta un import pero no un `sqlite3.connect` directo.

El contrato afirma más de lo que la evidencia podrá sostener. Único invariante con comprobación genuina: `INV-01` y `INV-09`.

---

## C-06 · MENOR · El paquete publica la semilla, y el operador es el autor del generador de corrupción

**Ubicación:** `human-package.json:seed = 0`; `auxiliary_hitl_v1.py:535-556` (`corrupt_training_labels`, `np.random.default_rng(seed + 10_000)`).

**Comprobación:** con `seed=0` y el repositorio (`/mnt/.../code/checkout-HEAD-5f30880.tar.gz`, incluido en el respaldo), las posiciones invertidas se reproducen en tres líneas.

**Esperado:** que el material entregado no baste para regenerar la corrupción.

**Observado:** el operador declarado (`expected_operator.operator_id = "Gustavo Julián Rivas"`) es quien escribió el generador. El cegamiento es, en el mejor caso, nominal — independientemente de C-01. Esto no es subsanable por diseño con un único operador que es el autor; corresponde declararlo como limitación del alcance, no tratarlo como paquete ciego.

---

## C-07 · MENOR · La guarda anti-contaminación de `prepare_human_package` es vacua y su docstring afirma algo falso

**Ubicación:** `auxiliary_hitl_v1.py:1592-1648`.

**Comprobación:** `prepare_human_package` llama a `build_hitl_frames`, que en `:373-390` ejecuta `validate_stage_window_full_coverage(daily_series, HITL_WINDOW_BOUNDS)` (2015-01-07 … **2022-12-28**), construye `evaluation = _window(HITL_EVALUATION_BOUNDS)` y calcula `compute_dataset_fingerprint(eligible, …)` sobre el conjunto elegible 2015-2022. Luego la guarda comprueba `max(events_frame["target_timestamp"]) > 2021-12-31`, pero `events_frame` proviene de `frames.feedback`, enmascarado por construcción a `target <= 2021-12-31` (`:384-386`, `HITL_FEEDBACK_BOUNDS`). La condición **nunca puede ser verdadera**.

**Esperado:** o bien no leer 2022, o bien no afirmar que no se lee.

**Observado:** el docstring dice "Se verifica **explícitamente** que ninguna fila de 2022 intervenga en la preparación". Se leen y materializan filas de 2022, y la verificación es tautológica.

Matiz favorable, verificado: **ninguna información de 2022 entra en el contenido del paquete**. El modelo congelado se entrena con targets ≤ 2020-12-31, el P20 sale de ese train, y las 20 emisiones y sus observaciones son todas de 2021 (verificado: los únicos años en datos del paquete son 2021; las cadenas "2023/2024/2025" aparecen solo en el texto meta de `hidden_from_participant`). Respondiendo literalmente a la pregunta 6: **sí, la preparación tocó filas posteriores a 2021-12-31** (todo 2022), pero no las filtró al paquete, y el contrato admite la ventana 2015-2022. El defecto es la afirmación, no la contaminación.

---

## C-08 · MENOR · El revisor simulado se registra con el rol de operador humano autorizado

**Requisito afectado:** `contract-H-frozen.json:tracks.separation_rule`; `operator.authorized_roles_whitelist`.

**Ubicación:** `auxiliary_hitl_v1.py:1670` — la pista SIM se ejecuta con `operator_role=AUTHORIZED_OPERATOR_ROLES[0]`, es decir `"authorized_experimental_operator"`.

**Esperado:** que un oráculo determinista no lleve el rol reservado a la persona autorizada.

**Observado:** `feedback_origin` y `operator_id` sí separan las pistas, pero el campo `operator_role` de los eventos simulados es indistinguible del de los eventos humanos. Cualquier agregación posterior por `operator_role` mezcla simulación y humano — exactamente el riesgo que `separation_rule` dice cerrar.

---

## C-09 · MENOR · `validated_at` de la pista HUMAN queda retrofechado a 2022-01-01

**Ubicación:** `auxiliary_hitl_v1.py:1862-1866` (`validated_at` por defecto `datetime(2022,1,1, tz=utc)`), aplicado por igual a SIM y HUMAN en `run_complement_h:1655,1686`.

**Esperado:** que la procedencia temporal de una decisión humana refleje cuándo se tomó.

**Observado:** salvo que se pase `--validated-at`, el evento humano registrará `validated_at = 2022-01-01T00:00:00Z`, unos 4,7 años antes de la decisión real (2026-09-21). Cumple formalmente las dos reglas temporales del contrato, y hay una razón legítima (reproducibilidad bit a bit), pero produce un registro de procedencia humano que no es cierto. Debería documentarse explícitamente o pasarse el valor real.

---

## C-10 · MENOR · `validate_human_response` no verifica la identidad contra la esperada

**Ubicación:** `auxiliary_hitl_v1.py:1063-1075`.

**Comprobación:** el código exige `operator_id` `str` no vacío y `operator_role ∈ AUTHORIZED_OPERATOR_ROLES`, pero nunca compara con `package["expected_operator"]["operator_id"]` ni con `EXPECTED_OPERATOR_ID`.

**Esperado:** dado que el contrato predeclara un operador único y nominado, la respuesta de cualquier otra persona debería rechazarse de forma cerrada.

**Observado:** cualquier cadena no vacía pasa. El campo `expected_operator` del paquete es decorativo.

---

## C-11 · OBSERVACIÓN · El muestreo tiene un camino de respaldo que rompe el equiespaciado en silencio

**Ubicación:** `auxiliary_hitl_v1.py:513-527`.

**Observado:** si `np.unique` colapsa posiciones, el bucle completa con índices desde `candidate = 0`, produciendo una selección sesgada al inicio del estrato mientras el contrato (`design_frozen_auxiliary_hitl_v1.sampling`) y el docstring afirman "10 posiciones equiespaciadas". No se activó para la semilla 0 (ambos estratos son amplios: 10 alertas y 10 no-alertas verificadas), así que **no afecta a este paquete**; lo señalo por si se ejecutan las otras cuatro semillas.

---

## C-12 · OBSERVACIÓN · El preflight no atestigua el commit que produjo el paquete

**Ubicación:** `preflight-H.json:repository.head_commit = a742e56…`; `package-preparation-record.json:code_version.commit = 5f30880…`; `git log` actual en HEAD `eb9cf17`.

**Observado:** el preflight se capturó a las 11:57:56Z sobre `a742e56`; el paquete se preparó a las 12:19:15Z sobre `5f30880`. El registro de preparación sí declara `dirty: false` y el respaldo incluye el checkout de ese commit, así que la identidad ejecutable del paquete está capturada. Simplemente: el preflight no la cubre.

---

## C-13 · OBSERVACIÓN · El congelamiento es verificable y correcto, pero se ancla a sí mismo sobre un montaje escribible

**Comprobación reproducible (punto 3, hecha):**
```
python3 -c "
import json,hashlib
d=json.load(open('/mnt/.../package/human-package.json',encoding='utf-8'))
d2={k:v for k,v in d.items() if k!='package_sha256'}
print(hashlib.sha256(json.dumps(d2,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest())"
```
→ `a9d0ee2d57d5212794ae2ac9e976212cbabd81c38fabd01073cc626d7e3cef29`, **idéntico** al campo `package_sha256` y al de `package-preparation-record.json`.

**Cobertura del hash:** verifiqué las 16 claves de nivel superior; el único campo excluido es `package_sha256`. No hay ningún campo del paquete fuera del hash: `instructions`, `hidden_from_participant`, `presentation_order`, `seed`, `expected_operator`, `contract_sha256` y los 20 escenarios completos están todos cubiertos. Alterar cualquiera cambia el hash. **Este punto pasa.**

`contract_sha256 = a124db1a…` coincide con `sha256sum` del archivo de contrato tanto en el worktree como en `/mnt/.../contract/`. `manifest/SHA256SUMS` verifica 14/14 (`sha256sum -c` → todo OK).

**Reserva:** el hash es autoanclado (vive en el mismo archivo) y el único ancla externa, `manifest/SHA256SUMS`, está en el mismo directorio `drwxrwxrwx` y `preflight-H.json:backup_mount.writable = true`. Quien pueda editar el paquete puede recalcular ambos. Esto no invalida nada, pero el congelamiento es un control de integridad accidental, no de manipulación deliberada.

---

## C-14 · OBSERVACIÓN · Tensión entre `may_be_presented_as_human_evidence: true` y el diseño congelado

**Ubicación:** `contract-H-frozen.json:tracks.HUMAN.may_be_presented_as_human_evidence` vs. `scientific-closure-decisions.md:134` ("No afirmar feedback humano genuino ni eficacia agronómica").

**Observado:** la línea 135 del diseño ("Feedback real futuro necesita protocolo de revisión y procedencia propia") habilita razonablemente la lectura del contrato, y la línea 134 está en el párrafo del escenario simulado. La lectura del contrato es defendible, pero es una **interpretación**, no una lectura literal, y conviene que el veredicto la registre como tal.

---

## Puntos que SÍ pasan la revisión (verificados, no asumidos)

- **Punto 2, inducción:** el texto de `instructions` es neutro, no nombra ninguna decisión como preferible, no menciona métricas ni consecuencias. Homogeneidad estructural verificada: los 20 escenarios tienen conjunto de claves idéntico (1 clase de equivalencia), el mismo conjunto de features, un único `p20_threshold_frozen`, un único `model_version` y `decision_options` idénticas. No hay redacción libre por escenario. Orden cronológico ascendente y sin agrupar por estrato. **Salvedad:** `model_probability`/`model_alert` son una señal orientadora débil (5 escenarios muestran desacuerdo `model_alert ≠ recorded_label`: H-SC-004, 009, 012, 014, 017), pero es un cue mucho más ruidoso que C-01 y está explícitamente autorizado por el contrato.
- **Punto 4, coherencia:** 20 escenarios; 10 con `model_alert=1` y 10 con `0`; todas las emisiones y targets en 2021 (2021-01-01 … 2021-12-28 / 2021-01-04 … 2021-12-31); `target = emisión + 3 días` en 20/20; `presentation_order` registrado, igual al orden de `scenarios`, cronológico, `position` 1..20; `seed = 0 ∈ [0,1,2,3,4]`. **Todo conforme.**
- **Punto 1 (d),(e),(f),(g):** no hay ninguna métrica de ningún brazo, ningún dato de 2023-2025, nada del holdout y nada de las Etapas A/B/C en los datos de los escenarios. Las cadenas "2023/2024/2025", "holdout" y "Etapa" aparecen únicamente dentro de `hidden_from_participant`, como texto meta.
- **Punto 5, clase de evidencia:** `evidence_class = "controlled_human_feedback"` y `evidence_class_is_not = "expert_agronomic_feedback"` en paquete y registro de preparación; `expected_operator.role_is_not = [agronomist, domain_expert, field_validator]`; las instrucciones dicen literalmente "no como agrónomo: tus decisiones no constituyen asesoramiento ni validación agronómica". No hay en todo el paquete ninguna afirmación de participación, validación o conocimiento agronómico. **Conforme.** (Ver C-08 por la contaminación del `operator_role` en la pista SIM.)
- **Punto 7, relajación:** no encontré relajación de los parámetros congelados. `EVENT_BUDGET_PER_SEED=20`, `EVENTS_PER_STRATUM=10`, `CORRUPTION_FRACTION=0.10`, `DEFAULT_SEEDS=(0,1,2,3,4)`, tres brazos, P20 congelado (`INV-04`, un solo `compute_p20_threshold` sobre `train_initial`), maduración separada (`HITL_EVALUATION_BOUNDS.train_target_cutoff = 2021-12-31`) — todos coinciden con `scientific-closure-decisions.md:118-139`. El contrato **endurece** SC-GOV-022 al añadir la pista HUMAN como requisito de PASS, no lo ablanda. La única anomalía documental es C-03.

---

## Limitaciones de esta revisión

- No ejecuté el runner ni las pruebas (modo solo lectura), así que no puedo confirmar empíricamente que `prepare_human_package` con `seed=0` reproduzca byte a byte este paquete. La cadena documental (registro de preparación + checkout del commit + `SHA256SUMS`) es consistente, pero es atestación, no reproducción.
- No pude comprobar `INV-03` (artefactos A/B/C intactos) por observación directa: el preflight dice que los directorios vivos son `root:0600` e inaccesibles. Verifiqué solo lo que el preflight declara.
- No revisé `run_track_for_seed`, `apply_feedback` ni `build_lineage` en detalle; quedan fuera del alcance "paquete antes de mostrarlo". C-05 podría tener más casos allí.
- No puedo determinar si el operador conocerá la regla `label = 1 sii obs < P20` de manera independiente del paquete. Es irrelevante en la práctica: es el autor del código, y además la regla se infiere de los propios 20 escenarios (16 consistentes con un corte limpio en P20).

---

# VEREDICTO: **NO_APTO**

**Razones que bloquean, en orden:**

1. **C-01** — El paquete no es ciego. La etiqueta limpia es derivable con exactitud en los 20/20 escenarios, y con ella la identidad de los 4 escenarios corrompidos y su proporción. Mostrarlo tal cual, acompañado de una lista `hidden_from_participant` que le afirma a la persona lo contrario, hace que la evidencia resultante no pueda sostener ninguna afirmación de cegamiento.
2. **C-02** — El contrato congelado se contradice a sí mismo sobre este punto exacto, de modo que no es posible resolver C-01 apelando al contrato. Cualquier resolución exige una decisión explícita y registrada (quitar los campos, o retirar las garantías y reencuadrar el paquete como "no ciego, con observación madurada visible" — esta última es coherente con la limitación ya predeclarada).
3. **C-04** — La única prueba automatizada que cubría esta propiedad no la cubre. No hay red de seguridad.
4. **C-03** — El contrato congelado nombra una semilla ajena al diseño congelado.
5. **C-05** — Varias métricas declaradas decisivas y cinco de los diez invariantes son constantes literales, no comprobaciones. La evidencia no podrá sostener el criterio de PASS tal como está escrito.

C-01 a C-05 son hallazgos materiales. El propio `verdict_criteria.PASS` exige que "no quede ningún hallazgo material de crítica o auditoría", de modo que mostrar el paquete en su estado actual conduciría a un PASS insostenible.

**No bloquean:** el congelamiento criptográfico (C-13, verificado y correcto), la coherencia con el diseño (punto 4, conforme), la clase de evidencia (punto 5, conforme) y la ausencia de inducción textual (punto 2, conforme salvo la señal débil del modelo). Los defectos están concentrados en qué se muestra, no en cómo se congela ni en cómo se rotula.
