# Crítica independiente de la EJECUCIÓN del complemento H

> Informe del `scientific_critic` sobre la ejecución de H y su evidencia.
> Sesión nueva y separada, de solo lectura.
> Transcripción literal. No se corrige ni se resume.

He terminado. Trabajé en solo lectura; no modifiqué nada en el respaldo, el runtime ni el repositorio (verifiqué `git status --porcelain` vacío al final; corrí pytest con `-p no:cacheprovider` y `PYTHONDONTWRITEBYTECODE=1`).

## Qué intenté refutar y no pude (comprobaciones que pasaron)

Recalculadas por mí, no leídas del informe:

| Comprobación | Resultado |
|---|---|
| `sha256sum -c manifest/SHA256SUMS` del respaldo H | 54/54 OK |
| `integrity_manifest.json` contra los 17 artefactos | 17/17 OK; su propio sha = `4fe37ed4…` = el declarado en `execution-record` |
| Hash canónico del paquete (payload sin `package_sha256`, sort_keys, separators) | `6f2143e0…` = declarado |
| Hash de la respuesta humana (archivo) | `5a0cc469…` = declarado |
| Anclas de git vs respaldo (`contract-H-frozen`, ambos `*-freeze`) | idénticas byte a byte |
| `sha256sum -c` de la campaña A/B/C | 91/91 OK, 0 FAILED; `ledger/holdout.sqlite` incluido y con mtime 05:01 (previo a H, 19:15) |
| Reglas temporales sobre los 120 eventos | horizonte = 3 días en 120/120; `validated_at ≥ target+1d` en 120/120; `fecha` ∈ [2021-01-01, 2021-12-28] y `target` ∈ [2021-01-04, 2021-12-31] en 120/120. Cero filas de 2022 revisadas; cero fechas de 2023-2025 en ninguna parte (`dataset_fingerprint`: max feature 2022-12-28, max target 2022-12-31) |
| Autorreferencia | `source ≠ successor` en las 5 semillas; 15 `model_id` distintos; el sucesor definitivo se deriva de las etiquetas corregidas reales (no del identificador provisional, cuya infalsificabilidad ya estaba declarada en E-04) |
| Separación de pistas | origins {simulado:100, humano_controlado:20}, roles {simulated_reviewer_oracle:100, authorized_experimental_operator:20}: ningún artefacto mezcla |
| `agreement-analysis.json` contra el paquete | 20/20 filas exactas; los 4 registros inconsistentes son `H-SC-004/008/009/020`, derivables además de `feedback_events_human.json` (`recorded_label` vs `reference_label_available_to_runner`) |
| Suite focalizada | reproduje `74 passed` |
| Diseño congelado, parámetro por parámetro | `docs/research/scientific-closure-decisions.md` es byte-idéntico a `origin/main`; RF 100/8/5/n_jobs=1, ventanas, P20 congelado, 20 eventos, 10/10, corrupción 10 %, semillas [0,1,2,3,4], revisor simulado: todos conformes — **salvo F-01** |
| 13 afirmaciones prohibidas | grep exhaustivo del árbol: toda aparición está dentro de una negación, una lista de prohibiciones o una limitación declarada. **No encontré ninguna afirmación prohibida sostenida** |
| Relajación de criterios | `verdict_criteria` y `stop_conditions` sin cambios; la desviación de reproducibilidad se registró en vez de reescribir el contrato |

---

## Hallazgos

### F-01 · MATERIAL · Artefacto exigido por el diseño congelado que no se emitió
- **Requisito:** `docs/research/scientific-closure-decisions.md:96-98`, bloque padre «Evaluaciones complementarias», que el propio contrato invoca como autoridad (`design_frozen_auxiliary_hitl_v1.seeds_source`): *«Artefactos nuevos por protocolo: configuración, commit/imagen/dependencias, hashes fuente/derivado, fechas, semillas, **predicciones por fecha**, métricas, soporte, advertencias y límites»*.
- **Ubicación:** `src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py:1640` (`_arm_to_json`) y `evidence/first-attempt/integrity_manifest.json`.
- **Comprobación:** `grep -n "prediction" auxiliary_hitl_v1.py` → sin resultados; `_arm_to_json` devuelve sólo `arm/model_id/n_training_rows/trained_through/metrics`; los 17 artefactos no incluyen ningún fichero de predicciones (los únicos «predicted» del árbol son los bins de calibración).
- **Esperado:** predicciones por fecha de cada brazo sobre las 362 filas de evaluación.
- **Observado:** ausentes, y **no declaradas como limitación** en ningún artefacto.
- **Consecuencia real:** ni MCC, ni AP, ni Brier, ni F1, ni la matriz de confusión, ni los episodios de onset pueden ser recomputados por un auditor sin reejecutar el runner. Los otros nueve ítems de esa lista sí están. El contrato v4 no trasladó este requisito y las tres rondas previas de crítica no lo detectaron.
- **Subsanable sin nueva pausa humana:** la corrida es bit-reproducible, de modo que las predicciones pueden regenerarse sin volver a decidir nada.

### F-02 · MENOR · Fechas de congelamiento y de las rondas 2 y 3 no corroboradas por git
- **Ubicación:** `contract-H-frozen.json` → `frozen_at_utc: 13:35:00Z`, `…round_2.review_date_utc: 13:00:00Z`, `…round_3.review_date_utc: 13:30:00Z`.
- **Comprobación:** `git log --date=iso` — v2 = `547c1a9` 12:35:43 (coherente con la ronda 1 a 12:35), pero **v3 = `6afe076` 16:42:33** y **v4 = `e1510a6` 16:55:49**. La ronda 3 declara haber dictaminado APTO sobre el paquete v3 a las 13:30, tres horas antes de que ese contenido exista en git.
- **Lectura honesta:** es compatible con revisiones sobre el árbol de trabajo y commits diferidos (hay un hueco de 12:44 a 16:42 sin commits), pero son fechas autodeclaradas no derivables de ningún artefacto. **Lo que sí está corroborado** y es lo que importa para la preinscripción: contrato y paquete congelados (16:57:46) **antes** de la respuesta del operador (19:14:26) y **antes** de la corrida (19:15:27).

### F-03 · MENOR · Dos identidades ejecutables sin reconciliar (la forma de D-05, que el contrato daba por cerrada)
- **Ubicación:** `execution-record.json:17` → `executable_sha: 1bee852f…`; `evidence/first-attempt/code_version.json` → `commit: 742d9592…`.
- **Comprobación:** `git diff --stat 742d9592 1bee852f -- src tests` → **vacío**. El código es el mismo; 217b924b y 1bee852f sólo agregan JSON de gobernanza.
- **Esperado:** que el registro nombre una identidad o explique la relación entre ambas.
- **Observado:** dos commits distintos en dos campos homónimos, sin nota. El artefacto emitido por la corrida (`code_version.json`) dice 742d9592 porque ésa es la identidad de la imagen; `execution-record` dice 1bee852 porque ése era el HEAD del host.

### F-04 · MENOR · `response_sha256` publicado con dos valores distintos y el mismo nombre
- **Ubicación:** `5a0cc469…` en `execution-record.inputs`, `review.json`, `human-response-freeze.json`; **`ae89c9dc…`** en `evidence/first-attempt/human_response_record.json`.
- **Comprobación:** el primero es el sha256 del archivo; el segundo es `content_sha256` (canonical JSON, `auxiliary_hitl_v1.py:314-331`). Recomputé ambos: los dos son correctos.
- **Observado:** ningún registro dice que son dos funciones distintas sobre el mismo objeto. El paquete sí documenta su canonicalización (`package_canonicalization`); la respuesta no. Un auditor que compare los dos campos ve una discrepancia.

### F-05 · MENOR · `agreement-analysis.json` sin productor versionado
- **Ubicación:** `evidence/auxiliary/agreement-analysis.json`.
- **Comprobación:** no existe script ni función en el repositorio que lo emita (`grep -rl agreement` sólo toca documentos de la verificación 2026-09-20); no está en `integrity_manifest.json`; no hay comando registrado. Además `validation-record` lo referencia en `evidence/auxiliary/sc-08-aux-hitl/agreement-analysis.json` y el respaldo lo guarda en `evidence/auxiliary/`.
- **Observado:** lo recomputé íntegramente desde `package/human-package.json` y desde los eventos de la corrida: **0 discrepancias en 20/20 filas**. No hay invención. Lo que falta es procedimiento reproducible: su procedencia es una narración.
- **Respuesta a la pregunta del encargo:** el análisis **no altera, no reinterpreta y no reemplaza** la respuesta humana. Es posterior, descriptivo y derivable de la evidencia de la corrida.

### F-06 · MENOR · «Por su propia iniciativa» no está sostenido por ningún artefacto
- **Ubicación:** `response/human-response.json` → `transcription_sequence.what_changed`.
- **Comprobación:** el texto de la declaración formal es una reproducción casi literal de la fórmula que el propio contrato exige (`operator.declaration_required_from_operator`). No existe transcripción de lo que se le dijo al operador entre 19:14:26 y 19:14:51.
- **Lo que sí es verificable y está registrado con honestidad:** la transcripción 1 (`45cd5a83…`, anclada en el freeze) **declaró explícitamente** que el operador NO había pronunciado la fórmula y remitió el juicio al auditor; las 20 decisiones son idénticas entre transcripción 1 y respuesta final (`responses equal: True`); la declaración precede a la corrida. **No es una alteración encubierta.** Lo que debe retirarse o evidenciarse es la atribución de iniciativa.

### F-07 · MENOR · El mecanismo no valida el CONTENIDO de la declaración de rol
- **Ubicación:** `validate_human_response`, `auxiliary_hitl_v1.py:1212-1214`: sólo exige `isinstance(str)` y no vacío.
- **Comprobación:** con la transcripción 1, cuyo campo `operator_declaration` contenía «te confirmo que las 20 están ok…», la validación habría pasado.
- **Observado:** el contrato se cumple literalmente («declaración ausente produce rechazo cerrado»), pero `declaration_required_from_operator` lo hace cumplir una lectura humana, no el mecanismo. La evidencia enumera «identidad, rol y declaración» entre lo demostrado; para la declaración eso es más débil de lo que se lee.

### F-08 · MENOR · Atribución imprecisa de los caminos no ejercitados
- **Ubicación:** `auxiliary/H/review.json` → `human_intervention.material_consequence`: «Los caminos no ejercitados quedan demostrados por la pista simulada (5 recalibraciones con linaje completo) y por la suite focalizada».
- **Comprobación:** `n_reject = 0` en las cinco semillas SIM y en HUMAN (`track_simulated.per_seed[*].applied_feedback`, `mechanism_metrics.human_track`). **RECHAZAR no se ejercitó en ninguna pista científica**: sólo en pruebas con fixtures. Igual ocurre con la recalibración sucesiva (`recalibrate_again`, contrato `recalibration_criteria.successive_recalibration`): única referencia en `tests/test_auxiliary_hitl_v1.py:615`; todos los linajes de la corrida son `cycle-1`.
- **Observado:** la frase no es estrictamente falsa (nombra la suite como alternativa), pero invita a leer que la pista SIM demostró el rechazo. Debe decir: corrección y recalibración por SIM; **rechazo y recalibración sucesiva, sólo por la suite**.

### F-09 · MENOR · Suavización interpretativa sobre el motivo del operador
- **Ubicación:** `agreement-analysis.json` → «NO significa que el operador se haya equivocado en un sentido científicamente relevante: el contrato no le exigía seguir la regla».
- **Comprobación aritmética sobre el paquete:** H-SC-004 (0.35196), H-SC-008 (0.47396), H-SC-009 (0.40808) tienen humedad ≥ P20 = 0.31862 con `recorded_label = 1`; H-SC-020 (0.24946) < P20 con `recorded_label = 0`.
- **Esperado:** que algún artefacto diga llanamente que el motivo declarado —«las 20 están ok **de acuerdo al umbral**»— es aritméticamente incorrecto para esos cuatro, porque el propio operador invocó la regla.
- **Observado:** la frase argumenta contra una exigencia que nadie hizo («el contrato no le exigía seguir la regla») y esquiva que el operador sí la invocó. **Todos los hechos necesarios están registrados** (filas por escenario, lista de divergencias, motivo literal, `n_accept=20`, `NO_RECALIBRATION` con razón). Es suavización, no ocultamiento; pero la oración debe corregirse.

### F-10 a F-16 · OBSERVACIONES
- **F-10** `execution-record.result.agreement_between_human_and_deterministic_reference` está dentro de `result`, junto a salidas del runner, sin rotularse como análisis posterior externo (aunque es derivable de los artefactos de la corrida).
- **F-11** INV-02 es el único invariante rotulado `contingent_measurement`, pero en el proceso dedicado de la CLI su valor queda determinado por el grafo estático de imports, que un test prohíbe que contenga `holdout_ledger`. Su falsabilidad es de la misma clase que la de las guardas estructurales: en la práctica esta corrida publica **cero** invariantes cuyo valor pudiera haber diferido con este mismo código.
- **F-12** `feedback_events_simulated.json` tiene 100 eventos con sólo **20 `event_id`/`scenario_id` distintos** (cada uno ×5) y ningún campo `seed`. La semilla sólo se recupera por posición o por `model_version`. Además `H-SC-0NN` designa fechas distintas según la semilla (p. ej. H-SC-005 = 2021-03-01 en seed 0 y 2021-03-02 en seed 2).
- **F-13** La estratificación 10/10 es verificable **sólo para la semilla 0** (vía `model_alert` del paquete). Los eventos no registran `model_alert`, de modo que `events_per_stratum: 10` en `review.json` es la constante configurada, no una medición: debería rotularse como guarda estructural según la propia `invariants_measurement_policy` del contrato.
- **F-14** `preflight-H.json` → `preflight_recapture_2026_09_21.tree_clean: false` (16:57:46), y `stop_conditions` lista «árbol de trabajo sucio … en el momento de ejecutar». Ningún artefacto registra el estado del árbol a las 19:15:27; `code_version.dirty: false` proviene de `.build_identity.json` capturado a las 16:56:59, no del instante de la corrida. Hoy el árbol está limpio y el delta 742d9592→1bee852f no toca código, así que nada sugiere un cambio; el registro, sin embargo, no cierra la condición.
- **F-15** `attempts_total: 1` no menciona que el runner se ejecutó dos veces más en modo `run` para las reproducciones (sí documentadas en `reproduction-record`). `n_evidence_files: 17` frente a 18 archivos en disco.
- **F-16** El diseño congelado sigue diciendo «Estado: DISEÑADAS, RUNNERS NO IMPLEMENTADOS, NO EJECUTADAS» (línea 91). Correcto no editarlo (es byte-idéntico a `origin/main`), pero queda contradicho por esta campaña.

---

## Punto 5: la desviación de reproducibilidad, ¿obliga a FAIL?

**No.** El criterio predeclarado estaba **incompleto**, no fue violado.

- Reproducción 1 (ruta variable): difiere sólo `mechanism_metrics.configured_paths.output_dir`.
- Reproducción 2 (ruta constante): **18/18 idénticos, con CERO exclusiones** — incluido `integrity_manifest`, que el criterio predeclarado permitía excluir. Es decir, se verificó una propiedad **más fuerte** que la predeclarada.
- La ruta de salida es una **entrada** de la corrida; que el artefacto la registre es auditoría, no no-determinismo.
- Registrar la incompletitud en vez de enmendar el contrato después de ver el resultado es exactamente la conducta correcta.

Corroboración independiente que sí pude hacer: en `/home/gus/hitl-complement-runtime/reproduction/` los tamaños de `h-run-repro` coinciden con el primer intento en 16/18, y los dos que difieren lo hacen en **exactamente 23 bytes cada uno** = la diferencia de longitud entre las dos rutas de salida; `h-run-samepath` coincide en los **18/18** tamaños. El primer intento conserva mtime 19:15.

---

## Limitaciones de esta crítica (lo que no pude comprobar, y no asumo)

1. **No pude leer el contenido** de `reproduction/h-run-repro/`, `h-run-samepath/` ni del primer intento vivo: son `root:0600`. Mi corroboración de INV-07 es por tamaño de archivo, no byte a byte. Sí verifiqué que la caché legible (`logs/first-attempt-cache/`) es **byte-idéntica** al respaldo; el eslabón original→caché descansa en el `recovery-rehearsal`, que no puedo auditar.
2. **No reejecuté el runner** (prohibido), de modo que no verifiqué de forma independiente MCC/AP/Brier/F1 ni la corrupción por semilla. F-01 es precisamente lo que impediría hacerlo aun con permiso.
3. **No hay grabación de la sesión con el operador**: la secuencia 19:14:26 → 19:14:51 la conozco sólo por las dos transcripciones y sus hashes.
4. **No pude verificar los `sha256sum -c` de A/B/C «antes» de H**: verifiqué el estado actual (91/91) y el mtime del ledger (05:01, previo). El «antes» descansa en `preflight-H.json` y `validation-record`.
5. **No evalúo GF**, por encargo.

---

## Punto 9: suficiencia para el gate GF y SC-GOV-025

- La evidencia de H **alcanza para levantar SC-GOV-022 de su causa registrada** («no tiene runner implementado ni evidencia alguna», `traceability.md:173`): el runner existe, el criterio de aceptación congelado se satisface (tres brazos, maduración separada, 20 eventos × 5 semillas, simulación identificada, sin afirmación de beneficio) y hay artefacto `auxiliary/H/review.json`. **Falta REVIEW-5**: la auditoría independiente, que el propio `review.json` declara pendiente.
- **Lo que impide GF, y no depende de H:** SC-GOV-021/023/024 siguen BLOCKED porque la decisión de suficiencia GD-12 no tiene crítica ni auditoría independiente; SC-GOV-005 registra que CL-10 «no es alcanzable hoy»; SC-GOV-025 exige `scientific-closure-audit.json` de sc-06, cuyo veredicto de suficiencia era negativo por seis de diez afirmaciones sin evidencia. H no toca nada de eso.
- **Lo que impide GF y sí depende de H:** F-01 abierto.

---

## Veredicto sobre el veredicto propuesto

**NO CONFIRMO PASS_WITH_LIMITATIONS tal como está. Tampoco corresponde FAIL ni BLOCKED.**

- **No es FAIL.** Ninguna de las cuatro condiciones de `verdict_criteria.FAIL` se cumple: no se violó ningún invariante; la respuesta humana validó contra el paquete congelado; la reproducción coincide (y en la variante estricta coincide con cero exclusiones); y no encontré ninguna de las 13 afirmaciones prohibidas sostenida en ningún artefacto.
- **No es BLOCKED.** No hay impedimento científico, técnico ni externo que impida ejecutar o verificar. Todo lo que no pude comprobar es cuestión de permisos de archivo o de la prohibición de reejecutar, no de un bloqueo real.
- **No es PASS, ni todavía PASS_WITH_LIMITATIONS.** El contrato exige, para ambos, que «no quede ningún hallazgo material de crítica o auditoría». **F-01 es material y está abierto**: el diseño congelado exige predicciones por fecha entre los artefactos de protocolo, H no las emitió y ningún registro declara la omisión. La consecuencia no es cosmética: hoy ninguna métrica publicada puede recomputarse desde la evidencia.

**Camino de salida, sin nueva pausa humana y sin reabrir ninguna decisión:** (a) emitir las predicciones por fecha por brazo y ventana, regeneradas desde la corrida bit-reproducible, o bien declarar expresamente la omisión como desviación del diseño congelado con su justificación —lo primero es preferible y es lo que el diseño pide—; (b) corregir en el registro F-03, F-04, F-06, F-08 y F-09, que son afirmaciones o atribuciones que hoy no se sostienen tal como están redactadas; (c) dejar F-02, F-05, F-07 y F-10 a F-16 como limitaciones declaradas. Subsanado F-01, **PASS_WITH_LIMITATIONS queda sostenible**, y las limitaciones que restan son sustantivas pero ya están todas predeclaradas en el contrato v4.

Una observación final, por si ayuda al auditor: sobre el punto que el encargo señalaba como el más delicado —la pista humana—, mi conclusión es que la evidencia **no sobreafirma**. El contrato predeclaró `no_change_is_a_valid_outcome: true` antes de que el operador viera nada; la divergencia 16/20 está registrada, es derivable de los artefactos de la corrida y la recomputé exacta; y `review.json` enumera con precisión qué demostró la pista humana y qué no. El mecanismo HITL **no** queda demostrado por la intervención humana en sus caminos de corrección, rechazo y recalibración —eso lo dice la propia evidencia—, y el rechazo, además, no lo demostró ninguna pista científica (F-08).
