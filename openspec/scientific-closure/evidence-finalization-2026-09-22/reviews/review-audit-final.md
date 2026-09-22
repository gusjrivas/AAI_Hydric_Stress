> **Nota del orquestador, fuera del informe.** Lo que sigue es la transcripción
> literal de la respuesta del `scientific_auditor` independiente, sesión nueva y
> separada, de solo lectura. Objeto: snapshot `7e63d1c054ca295009fb3285b051bb0a10022688`.
> No se corrige, no se resume, no se reordena y no se altera el veredicto.

---

He completado la auditoría independiente. Informe para preservar verbatim.

---

# Auditoría final independiente del cierre documental — `scientific_auditor`

> Sesión nueva, separada, de solo lectura. No escribí, no edité, no ejecuté runners, no abrí ni releí el holdout. Todo lo que declaro como verificado lo ejecuté yo.

---

## 1. `verdict`

**`FAIL`** — incumplimiento material demostrado, **documental, acotado y corregible sin evidencia científica nueva**.

Calificación, porque la palabra sola sería engañosa en los dos sentidos:

La **ciencia se sostiene y la suficiencia del alcance aprobado también**. Recomputé y contrasté alrededor de sesenta cifras de A, B, C y H contra los artefactos que las publican y encontré **cero discrepancias numéricas**. Verifiqué por mi cuenta que la evidencia no fue alterada, que el holdout no fue reabierto, que `GD-12` es anterior a la ejecución y que las condiciones de activación de R, N y S efectivamente no se dan. Sobre el fondo, **`GF` y `SC-GOV-025` en `PASS_WITH_LIMITATIONS` es el estado correcto**: ni `BLOCKED`, porque las causas del bloqueo anterior están resueltas, ni `PASS` pleno, porque diez requisitos conservan limitaciones no subsanadas.

El `FAIL` **no es sobre la ciencia: es sobre el registro**. La matriz final —el artefacto que el propio documento declara «la matriz final exigida por SC-GOV-025» y que «supersede a todas las anteriores»— contiene tres afirmaciones falsas en el snapshot auditado. La más grave es que **acredita la existencia de esta auditoría y fija el estado de `SC-GOV-025` sobre esa base, antes de que la auditoría se realizara**. Ése es, literalmente, el hallazgo `AUD-F-01` que el mismo archivo condena 172 líneas más arriba, en la misma fila de requisito. No puedo ratificar un registro que prejuzga mi veredicto sin repetir el defecto que se me pide detectar.

`FAIL` vuelve al implementador con tres correcciones acotadas. Ninguna exige reabrir el holdout, reejecutar A, B, C ni H, ni producir evidencia científica nueva. Corregidas, el estado que el implementador propone es el que yo mismo sostengo.

---

## 2. `snapshot`

| Elemento | Valor |
| --- | --- |
| Repositorio | `/home/gus/work/AAI_Hydric_Stress_scientific_finalization` (worktree) |
| Rama | `feat/scientific-evidence-finalization` |
| HEAD auditado | `7e63d1c054ca295009fb3285b051bb0a10022688` (2026-09-22T00:54:55Z) |
| Base comparada | `1c33aad8cbee765e2968bd164b5d4890743eea0a` |
| Árbol | limpio (`git status --porcelain=v1 --untracked-files=all` sin salida) |
| Alcance del diff | **13 archivos**, no 12 como dice el encargo: 6 nuevos, 7 modificados; todos documentales o de gobernanza. Ninguno en `src/`, `docker/`, `tests/`, `scripts/` ni en resultados |
| Push | ninguno: `refs/remotes/origin/feat/scientific-evidence-finalization` no existe; `git branch -a --contains 7e63d1c` devuelve sólo la rama local |

Comandos con que lo fijé:

```
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
git diff --name-status 1c33aad 7e63d1c
git diff --check 1c33aad 7e63d1c            # exit 0
git branch -a --contains 7e63d1c
git reflog show refs/remotes/origin/feat/scientific-evidence-finalization   # unknown revision
```

Entorno de verificación: `/home/gus/scientific-closure-runtime/env/venv-v4/bin/python` (3.11.16) con `PYTHONPATH=src`; para OpenSpec, `/home/gus/scientific-closure-runtime/env/node/bin` al frente del `PATH` (precondición `GD-20`, verificada: `which npx` → binario Linux).

---

## 3. `checks_performed`

Cada ítem describe **lo que hice yo**, no lo que dice el documento.

### Integridad y no alteración

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-01** | `sha256sum -c SHA256SUMS` sobre `/mnt/scientific-backup/.../closure-campaign-2026-09-21/evidence-snapshots/final/` | **PASS — 91/91 OK, 0 FAILED.** Incluye `ledger/holdout.sqlite` y `ledger/stage_b.sqlite` |
| **CK-02** | Recomputé en Python el SHA-256 de **los originales** de `/home/gus/scientific-closure-runtime/evidence/` contra las 91 líneas del respaldo | **PARCIAL — 14 OK, 0 MISMATCH, 75 ilegibles** (`root:root`, modo 600, como declara el encargo). Los 14 legibles coinciden exactamente. Para los 75 restantes mi verificación descansa en el respaldo, que sí verifiqué entero |
| **CK-03** | `find /home/gus/scientific-closure-runtime/evidence -newermt "2026-09-21 05:00"` | **PASS — salida vacía.** Ningún archivo de evidencia de A/B/C fue modificado después de la campaña |
| **CK-04** | `find` sobre `/home/gus/scientific-closure-runtime/ledger` con marcas de tiempo | **PASS** — `holdout.sqlite` 2026-09-21 04:06, `stage_b.sqlite` 2026-09-21 03:51. Ninguno tocado después. El holdout **no** fue reabierto ni por la campaña H (19:15Z) ni por esta sesión |
| **CK-05** | Abrí **yo** los dos ledgers con `sqlite3.connect("file:...?mode=ro", uri=True)` y leí todas las tablas | **PASS** — `holdout_registry`: 1 fila, `state=CONFIRMADA`, `reserved_by_attempt_id=2121cdc901454df6be922c54a42d208d`, `confirmed_at` epoch 1789963571,52 = 2026-09-21T04:06:11Z, autorización nominal presente. `stage_b`: 1 intento `7eb5bb7c…`, 2 eventos, `RESERVED` 03:51:14.548988Z y `FINALIZED` 03:51:29.229088Z |
| **CK-06** | `sha256sum -c manifest/SHA256SUMS` en `/mnt/scientific-backup/.../hitl-complement-2026-09-21/` | **PASS — 100/100 OK, 0 FAILED.** El aumento de 93 a 100 respecto de la auditoría de H se explica por los cinco informes de crítica preservados después (remediación de `AUD-H-01`); lo comprobé listando el directorio |

### Anterioridad de `GD-12` (verificada en git, no en el documento)

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-07** | `git log --format='%H %ad %s' --date=iso -S 'GD-12' -- openspec/scientific-closure/decisions.md` | **PASS** — primera aparición en `a0d8bf7`, **2026-09-19T08:23:14Z**. La campaña A/B/C corrió el 2026-09-21 entre 03:39 y 04:06Z; H a las 19:15Z. Anterioridad de **dos días**, verificada en el único ancla resistente a manipulación |
| **CK-08** | Extraje el texto literal de la fila `GD-12` en `a0d8bf7`, en `495555c` y en HEAD y los comparé | **PASS — los tres son idénticos carácter por carácter.** El contenido de fondo (R/N/S `NOT_REQUIRED`, H `REQUIRED`) **no** fue retocado retroactivamente. Esto es lo que sostiene `GD-30`, y lo sostiene con independencia de los artefactos escritos hoy |

### Etapa A — recomputada contra la evidencia

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-09** | Leí `A/metrics.json` y `A/selection_decision.json` y contrasté las cuatro MCC OOF y los tres deltas de la tabla de la síntesis | **PASS** — `soft_voting` 0,7080275344 → 0,708028 ✓; `logistic_regression` 0,6979681131 → 0,697968 ✓; `random_forest` 0,695372286 → 0,695372 ✓; `hist_gradient_boosting` 0,685798943 → 0,685799 ✓. Deltas 0,010059 / 0,012655 / 0,022229 recalculados por mí: exactos |
| **CK-10** | Revisé los doce intervalos pareados de `selection_decision.json` (seis pares únicos) contra la afirmación «cinco de seis incluyen el cero» | **PASS** — único par que excluye el cero: `soft_voting|hist_gradient_boosting` [0,0006577; 0,0490694], límite inferior de orden 10⁻⁴. `logistic_regression|soft_voting` = [−0,026747; 0,004064], incluye el cero. Ambos transcritos correctamente |
| **CK-11** | Leí `A/frozen_config.json` y comparé configuración congelada, folds y P20 | **PASS** — `median_mcc` 0,7162796571 → 0,716280 ✓; `fold_mcc` [0,716280; 0,658721; 0,732069] ✓; `final_p20_train` 0,30266666… → 0,302667 ✓; `ScaledLogisticRegression`, `l2`, `lbfgs`, `max_iter` 2000, `C`=1,0, `sample_weight_balanced` ✓; huella `8062605b…38931`, 2913 filas ✓; commit `214735e42ee…` ✓; las ocho features coinciden una a una |
| **CK-12** | Verifiqué el soporte declarado en `bootstrap_diagnostics` | **PASS** — 5000 solicitadas / 5000 válidas / 0 descartadas, 3 segmentos de 728, bloque 30, semilla 20250109, `support_sufficient: true`. `warnings.json` = `[]` |
| **CK-13** | Leí `A_sensitivity_7_28cm/metrics.json` y calculé yo el conjunto de equivalencia a δ=0,05 | **PASS** — MCC 0,820087–0,871745, que es lo que la síntesis escribe como «0,820–0,872». Máximo 0,871745 (`logistic_regression`); dentro de δ quedan logreg, `soft_voting` (Δ0,0134) y `random_forest` (Δ0,0303); `hist_gradient_boosting` queda fuera (Δ0,0516). **El conjunto se reduce a tres familias, exactamente como afirma la síntesis.** `depth_role = sensitivity_only_no_selection_effect` verificado en `frozen_config.json` |

### Etapa B — recomputada contra la evidencia

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-14** | Leí `B/metrics.json`, `B/decision.json` y `B/bootstrap.json` y contrasté la tabla de siete métricas para candidato y persistencia | **PASS — 14/14 valores exactos.** Candidato: MCC 0,7013628 ✓, F1 0,7792208 ✓, precisión 0,6666667 ✓, recall 0,9375 ✓, Brier 0,1125602 ✓, `episode_recall` 0,8571429 ✓, matriz [[221,45],[6,90]] ✓. Persistencia: 0,6147437 ✓, 0,7157895 ✓, 0,7234043 ✓, 0,7083333 ✓, 0,1491713 ✓, 0,4285714 ✓, [[240,26],[28,68]] ✓ |
| **CK-15** | Verifiqué Δ y el intervalo, y la regla de la compuerta | **PASS** — Δ 0,08661917 → 0,086619 ✓; IC [−0,014552905; 0,209198163] → [−0,014553; 0,209198] ✓. **El intervalo incluye el cero**, y `decision.json` publica la regla literal `mcc_candidate_must_be_positive` + `delta_mcc_lower_bound_minimum: -0.05`: es una compuerta de **no inferioridad**, no de superioridad |
| **CK-16** | Verifiqué los episodios y los falsos avisos | **PASS** — 14 totales, 14 evaluables, 0 censurados, 12 anticipados, 0 mismo día, 2 no detectados con `onset` 2023-01-24 y 2023-04-29 y `lead_days: null` ✓; 45 días de falso aviso en 19 rachas ✓; mediana 3,0 ✓; tasa de alerta 0,3729282 → 1/0,3729 = 2,68 ≈ «un día de cada 2,7» ✓; prevalencia 96/362 = 26,5 % ✓ |
| **CK-17** | Verifiqué la custodia y el orden temporal contra el ledger, no contra el documento | **PASS** — `started_at` 03:51:14.530182Z, `RESERVED` 03:51:14.548988Z: la reserva sucede **18,8 ms** después del arranque, lo que la síntesis redondea a 19 ms ✓. Un solo intento, `recover_stage_b: false`, 0 reintentos |

### Etapa C — recomputada contra la evidencia

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-18** | Leí `C/metrics.json` y contrasté las nueve filas de la tabla para ambos brazos | **PASS con una omisión (ver F-08).** Candidato: MCC 0,66477003 ✓, F1 0,7192429 ✓, precisión 0,6031746 ✓, recall 0,890625 ✓, Brier 0,0975124 ✓, ROC-AUC 0,9390495 ✓, `episode_recall` 0,9 ✓, tasa de alerta 0,2596154 ✓, [[525,75],[14,114]] ✓. Persistencia: 0,5734375 ✓, 0,6484375 ✓, 0,6484375 ✓, 0,6484375 ✓, 0,1236264 ✓, tasa 0,1758242 ✓, [[555,45],[45,83]] ✓ |
| **CK-19** | Verifiqué Δ y el intervalo de C | **PASS** — Δ 0,09133253 → 0,091333 ✓; IC [0,022657592; 0,178418259] → [0,022658; 0,178418] ✓; **excluye el cero**, como dice la síntesis, y es el único de la campaña |
| **CK-20** | Verifiqué los cinco bins de calibración que la síntesis publica | **PASS — los cinco exactos.** 0,0–0,1: 0,0229014 / 0,0 / n=372 ✓; 0,1–0,2: 0,1428329 / 0,0 / n=62 ✓; 0,7–0,8: 0,7567205 / 0,5526316 / n=38 ✓; 0,8–0,9: 0,8577074 / 0,6190476 / n=21 ✓; 0,9–1,0: 0,9642958 / **0,6626506** / n=83 ✓. «Cuando el modelo dice 96 %, acierta 66 %» es literalmente cierto |
| **CK-21** | Verifiqué falsos avisos y episodios de C | **PASS** — 75 días en 26 rachas ✓; 3,0906593 FP/30 días → 3,09 ✓; precisión de alerta 0,6031746 → 0,603, y 1−0,603 = 0,397 ≈ «cuatro de cada diez alertas» ✓; 20 episodios, 19 evaluables, 1 censurado, 16 anticipados, 1 mismo día (2025-12-07), 0 tardíos, 2 no detectados (2024-12-12, 2025-02-23) ✓; 16+1+0+2 = 19 ✓; mediana 2,0 ✓ |
| **CK-22** | Calculé yo la deriva de prevalencia | **PASS** — A: 727/2184 = 33,29 % → 33,3 % ✓; B: 96/362 = 26,52 % → 26,5 % ✓; C: 128/728 = 17,58 % → 17,6 % ✓ |
| **CK-23** | Verifiqué P20 de C y el valor contaminado | **PASS** — `C/p20_train.json` = 0,300275 ✓. El 0,301917 contaminado está en `temporal-contract-check.json:30` y en `holdout-review.json:29` con su `n=4009`, literal ✓ |
| **CK-24** | Verifiqué que «~24 unidades efectivas» no sea una invención de la síntesis | **PASS** — aparece literal y con la misma redacción en **tres** artefactos de gobernanza de la campaña: `statistical-review.json:35`, `holdout-review.json:57` y `execution-record.json:157` |
| **CK-25** | Verifiqué las fronteras de C contra el criterio de `SC-GOV-014` | **PASS** — `C/temporal_boundaries.json`: corte de train `2023-12-31`, evaluación `2024-01-04` a `2025-12-31` en fecha objetivo, que con horizonte 3 equivale a emisiones `2024-01-01`…`2025-12-28`, exactamente el criterio congelado |
| **CK-26** | Barrí `metrics.json` de B y C buscando toda métrica con `status != defined` | **PASS** — las razones son `constant_prediction`, `no_predicted_positives`, `no_predicted_and_no_true_positives`, `no_observations_in_bin` y `no_detected_evaluable_episodes`. Ningún `null` sustituido por cero. Coincide con lo que la síntesis transcribe |

### Complemento H — recomputado contra la evidencia

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-27** | Leí `track_simulated.json` y extraje las quince MCC de la tabla por semilla y brazo | **PASS — 15/15 exactas** (0,453707/0,510678/0,476741; 0,475442/0,431719/0,440070; 0,479627/0,482246/0,489338; 0,446347/0,502817/0,507204; 0,464042/0,469509/0,468237) |
| **CK-28** | Calculé yo los deltas que aíslan correcciones (`refit_with_corrections − refit_no_corrections`) | **PASS** — −0,033937 / +0,008351 / +0,007091 / +0,004388 / −0,001271. **Signo mixto: tres positivos, dos negativos**, como declara la síntesis |
| **CK-29** | Calculé yo el otro contraste y lo comparé con lo que la síntesis publica | **HALLAZGO — ver F-07.** Los cinco valores publicados corresponden a `refit_no_corrections − frozen` (la actualización temporal **sin** correcciones), no al contraste que mezcla ambas. Los números son correctos; el rótulo no |
| **CK-30** | Verifiqué recalibraciones y rechazos por semilla | **PASS** — `RECALIBRATION_APPLIED` en las cinco; `n_correct` 4/4/2/1/1 y `n_reject` 0 en todas ✓ |
| **CK-31** | **Recomputé yo el 0/4 desde el paquete crudo**: apliqué la regla determinista (`observed_soil_moisture_at_target < p20_threshold_frozen`) a los veinte escenarios de `package/human-package.json` | **PASS — confirmado de forma independiente.** P20 = 0,31861666666666666. Divergentes exactamente cuatro: `H-SC-004` (0,3519583, etiqueta 1), `H-SC-008` (0,4739583, 1), `H-SC-009` (0,4080833, 1), `H-SC-020` (0,2494583, 0). Concordancia global **16/20** |
| **CK-32** | Conté las decisiones en `response/human-response.json` | **PASS** — `Counter({'ACEPTAR': 20})`, 20 registros. Cero `RECHAZAR`, cero `CORREGIR`. **Detección humana 0 de 4**, recomputada por mí, no leída |
| **CK-33** | Comparé las cuatro humedades con lo que la síntesis imprime | **PASS** — 0,351958 / 0,473958 / 0,408083 / 0,249458 y P20 0,318617: los seis valores redondean exacto desde los originales |

### Gobernanza, estructura y preservación

| ID | Qué hice | Resultado |
| --- | --- | --- |
| **CK-34** | `python scripts/check_scientific_closure.py` | **PASS — exit 0**, «PASS (estructura; runtime no verificado)» |
| **CK-35** | `pytest tests/test_scientific_closure_governance.py tests/test_scientific_closure_checker.py -q` | **PASS — 48 passed, 14 subtests passed** (15+33 y 4+10, coincide con el `validation-record.json`) |
| **CK-36** | OpenSpec 1.13.1 `--strict` sobre los diez `sc-*` y sobre `scientific-closure`, con el node Linux al frente del `PATH` | **PASS — 11/11 exit 0.** Un único `[INFO]` no bloqueante sobre la longitud del requisito 24 |
| **CK-37** | Conté **yo** los estados de la matriz final con una expresión regular sobre la sección del 2026-09-22 | **HALLAZGO — ver F-03.** PASS 12, PASS_WITH_LIMITATIONS 10, NOT_APPLICABLE 3. El documento declara 11/11/3 |
| **CK-38** | `find . -name 'scientific-closure-audit.json'` y `ls /home/gus/scientific-closure-runtime/evidence/governance/` | **HALLAZGO — ver F-01.** Único resultado: `closure-verification-2026-09-20/scientific-closure-audit.json`, que audita `5b40a55`. En el runtime sólo existe `closure-campaign-2026-09-21`. **El artefacto de esta sesión no existe** |
| **CK-39** | Leí `independent_review` en los tres `auxiliary/{R,N,S}/review.json` y en `claim-evidence-review.json` | **HALLAZGO — ver F-02.** Los cuatro: `"state": "PENDING"`, `"verbatim_report": null` |
| **CK-40** | `git diff --stat a6570147 HEAD` sobre las seis rutas que `SC-GOV-003` declara preservadas | **PASS — salida vacía, 0 archivos.** `git diff --name-status a6570147 HEAD -- src/` devuelve una sola línea: `A src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py`. Exactamente lo declarado |
| **CK-41** | `git rev-parse origin/main` y `git merge-base --is-ancestor origin/main HEAD` | **PASS** — `origin/main` = `2079d03dded…` y **no** es ancestro de HEAD. La corrección que `SC-GOV-003` introduce (enunciar la propiedad contra un commit inmutable en vez de contra una referencia móvil) es correcta y yo la reproduzco |
| **CK-42** | `git diff --stat 214735e HEAD -- src/experiment_runner/controlled_daily_v4/` | **PASS como hecho declarado** — 7 archivos, +50/−13. Es el delta que `SC-GOV-009` declara y clasifica «sin efecto numérico». No lo reevalué: pertenece a una auditoría histórica que el encargo toma por válida |
| **CK-43** | Verifiqué que `RK-10`, `RK-14` y `RK-19`, citados en la matriz, existen con ese contenido en `risks.md` | **PASS** — líneas 40, 49 y 57, los tres `ABIERTO`, `RK-14` explícitamente «REGISTRADO, NO SUBSANADO» |
| **CK-44** | `ls openspec/changes/sc-08-aux-hitl/reviews/` | **PASS** — los cuatro informes de crítica (`package-1/2/3`, `execution`) más `review-audit-final.md` y un `README.md` que declara la limitación de que son transcripciones del orquestador y no firmas verificables. **`RB-01` está remediado** |
| **CK-45** | Revisé `requirements.json` para comprobar si `AUD-H-10` dejó allí algún estado falso | **PASS — sin hallazgo.** El archivo mapea requisito → tarea → comprobación → evidencia esperada y **no contiene estados**, de modo que nada allí quedó desactualizado. Sí refuerza F-01: declara `scientific-closure-audit.json` como la evidencia esperada de `SC-GOV-025` |
| **CK-46** | Barrido de palabras prohibidas (`superior`, `mejora`, `benefici`, `eficac`, `demuestra`, `agronóm`, `experto`, `pericia`, `ahorro`) sobre la síntesis y `thesis-traceability.md` | **PASS — ninguna afirmación sostenida.** Todas las apariciones están en negaciones, en listas de prohibición o en la tabla de trabajo futuro |

### Lo que **no** pude verificar y declaro `BLOCKED` por punto

| ID | Punto | Por qué |
| --- | --- | --- |
| **CK-B1** | 75 de los 91 archivos originales de `evidence/{A,B,C}` | `root:root` modo 600, ilegibles para uid 1000. Mi verificación de esos 75 descansa en el respaldo, que sí verifiqué entero (CK-01). No los doy por verificados en origen |
| **CK-B2** | La imagen `sha256:55bc923e…b297af` | No la inspeccioné. `docker` en `PATH` es el binario de Windows (`GD-21`). No afirmo nada sobre su contenido |
| **CK-B3** | `INV-10` (74 pruebas focalizadas de H) y la reproducción estricta 18/18 | Heredo `RB-07` sin modificarlo: siguen sin verificación independiente. Tampoco los verifiqué yo. **No deben presentarse como auditados** |
| **CK-B4** | La suite v4 completa (488 passed) | No la reejecuté; esta fase no toca código. Su último resultado conocido es del 2026-09-21 |
| **CK-B5** | Las auditorías históricas de A, B, C y H | Fuera de mi encargo por instrucción expresa. Las tomo por válidas salvo contradicción concreta, y no hallé ninguna |

---

## 4. `findings`

> **Sí hay hallazgos materiales: tres.** Los tres son del registro, no de la ciencia. Ninguno exige evidencia científica nueva. Ninguno toca A, B, C, H ni el holdout.

---

### `F-01` — **MATERIAL** — Recurrencia literal de `AUD-F-01`: la matriz final acredita un artefacto inexistente y prejuzga al auditor

- **Ubicación.** `openspec/scientific-closure/traceability.md:348` (fila `SC-GOV-025` de la matriz final) y `:404` (fila «Evidencia primaria» del gate `GF`).
- **Reproducción.**
  ```
  find . -name 'scientific-closure-audit.json' -not -path './.git/*'
  #  → ./openspec/scientific-closure/closure-verification-2026-09-20/scientific-closure-audit.json   (audita 5b40a55)
  ls /home/gus/scientific-closure-runtime/evidence/governance/
  #  → closure-campaign-2026-09-21          (no existe evidence-finalization-2026-09-22)
  ls openspec/scientific-closure/evidence-finalization-2026-09-22/
  #  → auxiliary/  claim-evidence-review.json  thesis-traceability.md  validation-record.json
  git log -1 --format=%cI 7e63d1c   →  2026-09-22T00:54:55Z
  ```
- **Esperado.** Que la fila no afirme la existencia de un artefacto que no existe, y que el estado de `SC-GOV-025` no se fije sobre una auditoría no realizada.
- **Observado.** La fila dice, en presente y como hecho: «La auditoría final requisito por requisito sobre el snapshot posterior a la campaña **existe** (`scientific-closure-audit.json`, esta sesión)», y sobre esa base declara `SC-GOV-025` en `PASS_WITH_LIMITATIONS`. La fila de `GF` lo lista como **evidencia primaria**. El commit es de las 00:54:55Z; esta auditoría corrió después.
- **Impacto.** El mismo archivo, en `traceability.md:176`, conserva la corrección `AUD-F-01` del 2026-09-20: *«la versión anterior de esta fila afirmaba que ese artefacto "ya existe" y enunciaba su veredicto **antes de que la auditoría se realizara**. Era falso y además prejuzgaba al auditor; el artefacto se escribió recién al recibir su informe»*. `current-execution-checkpoint.md:222` lo describe idéntico: «una fila que acreditaba un artefacto inexistente y prejuzgaba al auditor». **Es la misma fila de requisito, en el mismo archivo, reincidiendo en el mismo defecto dos días después.** Y en este mismo commit `GD-31` invoca `AUD-F-02` como razón para **no** relajar la herramienta de verificación: la coherencia obliga a no relajar el registro documental por la vía que `AUD-F-01` ya condenó. Éste es el hallazgo que fuerza el `FAIL`.
- **Remediación.** Reescribir las dos filas para que (a) citen este informe por su ubicación real una vez preservado, y (b) emitan `scientific-closure-audit.json` **a partir de** él, no antes. Si el informe no fuera favorable, la fila tendría que decir otra cosa: ése es precisamente el punto.

---

### `F-02` — **MATERIAL** — El conjunto 3 y `GD-30` declaran «criticada y auditada» una revisión que los propios artefactos marcan `PENDING`

- **Ubicación.** `traceability.md:415` (conjunto 3 de `SC-GOV-025`), `:328` (fila `SC-GOV-005`), `:391`; `decisions.md:65` (`GD-30`); `plan.md:89`.
- **Reproducción.**
  ```
  python -c "import json;print([json.load(open(f'openspec/scientific-closure/evidence-finalization-2026-09-22/auxiliary/{k}/review.json'))['independent_review'] for k in 'RNS'])"
  #  → los tres:  {'state': 'PENDING', 'note': '... NO cierra SC-GOV-0xx', 'verbatim_report': None}
  #  idéntico en claim-evidence-review.json
  ```
- **Esperado.** Coherencia entre el registro que cita los artefactos y los artefactos citados.
- **Observado.** El conjunto 3 dice «SATISFECHO — R, N y S con revisión propia, **criticada y auditada**». `GD-30` dice «la revisión independiente final de esta sesión los critica y los audita, **con su informe preservado verbatim**». Los cuatro artefactos dicen `PENDING` y `verbatim_report: null`, y añaden que «hasta entonces este artefacto es una propuesta del implementador y **NO cierra** SC-GOV-0xx».
- **Impacto.** Misma familia que `F-01`. Es notable, y lo digo a favor del implementador, que **los artefactos son honestos y el registro que los cita no lo es**: el defecto está en la matriz y en las decisiones, no en la evidencia. Eso hace la remediación trivial.
- **Remediación.** Completar `independent_review` en los cuatro artefactos con el veredicto de este informe y su ubicación, y sólo entonces declarar SATISFECHO el conjunto 3.

---

### `F-03` — **MATERIAL** — El recuento final contradice la propia tabla de la matriz final

- **Ubicación.** `traceability.md:350` y el párrafo inmediato (`:350–357`).
- **Reproducción.**
  ```python
  sec = open('openspec/scientific-closure/traceability.md').read().split('## Matriz final de requisitos — 2026-09-22')[1]
  rows = re.findall(r'^\| \*\*(SC-GOV-\d{3})\*\* \| ([A-Z_]+) \|', sec, re.M)
  Counter(s for _, s in rows)
  #  → {'PASS': 12, 'PASS_WITH_LIMITATIONS': 10, 'NOT_APPLICABLE': 3}   (25 filas)
  ```
- **Esperado.** Que el resumen coincida con la tabla que resume.
- **Observado.** «**Recuento final: PASS 11, PASS_WITH_LIMITATIONS 11, NOT_APPLICABLE 3, BLOCKED 0**». El real es **12 / 10 / 3**. PASS son `001, 002, 004, 005, 007, 009, 010, 011, 012, 013, 014, 020`; `PASS_WITH_LIMITATIONS` son `003, 006, 008, 015, 016, 017, 018, 019, 022, 025`.
- **Causa raíz que reconstruí.** El párrafo cuenta a `SC-GOV-016` como un descenso `PASS → PASS_WITH_LIMITATIONS`, pero `SC-GOV-016` **ya figuraba** `PASS_WITH_LIMITATIONS` en la sección del 2026-09-21 (`traceability.md:81`); y a la vez omite el ascenso `BLOCKED → PASS_WITH_LIMITATIONS` de `SC-GOV-022`, que la sección del complemento H ya había fijado (`traceability.md:266`). Los dos errores se compensan en el total 25 y desplazan una unidad de PASS a PASS_WITH_LIMITATIONS.
- **Impacto.** El hallazgo `EV-02` del 2026-09-21 fue **exactamente esto** —un resumen que no coincidía con su tabla, 15/5/5 contra 14/6/5— y se corrigió entonces. Reincide. La dirección del error es conservadora (subdeclara PASS), lo que **no** lo vuelve admisible: un número falso en la matriz canónica es un número falso, y es el único de los tres hallazgos materiales que ningún informe favorable puede curar por sí solo.
- **Remediación.** Corregir a **PASS 12 / PASS_WITH_LIMITATIONS 10 / NOT_APPLICABLE 3 / BLOCKED 0** y rehacer la enumeración de transiciones (ver `F-04`).

---

### `F-04` — **MENOR** — La enumeración de transiciones dice «ocho» y lista nueve, y atribuye a `SC-GOV-016` un descenso que no ocurrió

- **Ubicación.** `traceability.md:350–357`; `decisions.md:69` (`GD-34`).
- **Reproducción.** El párrafo enumera: `005` sube; `021/023/024` pasan a `NOT_APPLICABLE`; `025` pasa a `PASS_WITH_LIMITATIONS`; `003, 008, 016 y 018` bajan de PASS. Son **nueve** ítems bajo el encabezado «Los cambios son **ocho**». Y `traceability.md:81` acredita que `SC-GOV-016` ya era `PASS_WITH_LIMITATIONS` el 2026-09-21, de modo que no bajó de PASS; la propia fila nueva lo reconoce al decir «**Cambia de base, no de estado**» (`:344`), contradiciendo al párrafo y a `GD-34` en la misma sesión.
- **Impacto.** Menor en magnitud, pero es la causa aritmética de `F-03` y hace que `GD-34` describa mal su propia decisión.
- **Remediación.** Corregir `GD-34` a tres descensos (`003, 008, 018`) y enumerar las transiciones contra una línea de base declarada sin ambigüedad —la del 2026-09-21 **post-H**, 14/7/4, que es la que hace verdadera la palabra «ocho»—.

---

### `F-05` — **MENOR** — Tres cifras distintas para el mismo conjunto de requisitos con limitaciones vivas

- **Ubicación.** «once requisitos» en `decisions.md:68` (`GD-33`) y `plan.md:89`; «nueve requisitos» y «nueve limitaciones vivas» en `traceability.md:405` y `:407`; la fila `SC-GOV-025` (`:348`) enumera nueve por su ID.
- **Observado.** El valor real es **diez** `PASS_WITH_LIMITATIONS`, de los cuales nueve son distintos de `SC-GOV-025` mismo. «Nueve» es defendible con ese recorte; «once» no lo es bajo ninguna lectura.
- **Impacto.** `GD-33` y `plan.md` son los dos lugares donde un lector busca por qué `GF` no es `PASS` pleno, y ambos dan una cifra falsa.
- **Remediación.** Unificar en «diez requisitos en `PASS_WITH_LIMITATIONS`, nueve de ellos distintos de `SC-GOV-025`».

---

### `F-06` — **MENOR** — `claims.md` conserva en tiempo presente, sin marca de supersesión, dos afirmaciones hoy falsas

- **Ubicación.** `openspec/scientific-closure/claims.md:44–46` y `:55–57`.
- **Observado.** Líneas 44–46, **sin fecha y en presente**: «Esta decisión permanece pendiente de crítica y auditoría independiente». Líneas 55–57: «Los artefactos `auxiliary/R/review.json`, `auxiliary/N/review.json` y `auxiliary/S/review.json` **no existen**». Ambas dejaron de ser ciertas en este mismo commit.
- **Atenuante que registro.** El bloque 48–57 está encabezado «**Consecuencia registrada el 2026-09-20 (hallazgo C-09, decisión GD-23)**», de modo que se lee como registro fechado. El bloque 44–46 **no** lo está. Y la sección nueva abre con «no reescribe las anteriores: **las cierra**», que es una marca de supersesión más débil que la que sí usa `traceability.md:309` («**supersede** a todas las anteriores»).
- **Impacto.** `AUD-H-10` levantó como hallazgo precisamente que la matriz afirmara algo factualmente falso sobre `SC-GOV-022`. Aquí el archivo es `claims.md` y el riesgo es el mismo.
- **Remediación.** Añadir en las líneas 44–46 un puntero explícito a `GD-30` y a la sección del 2026-09-22, **sin reescribir el texto histórico**, y usar en la sección nueva la misma palabra «supersede» que usa la matriz.

---

### `F-07` — **MENOR** — La síntesis rotula mal el segundo contraste de H

- **Ubicación.** `docs/research/scientific-closure-synthesis-2026-09-22.md:290–293`.
- **Reproducción.** Calculé los dos contrastes desde `track_simulated.json`:
  - `refit_no_corrections − frozen` = **+0,056971 / −0,043723 / +0,002619 / +0,056470 / +0,005467**
  - `refit_with_corrections − frozen` = +0,023034 / −0,035372 / +0,009711 / +0,060857 / +0,004195
- **Observado.** La síntesis publica el **primer** conjunto y lo describe como «El contraste que **mezcla la actualización temporal con las correcciones**». El primer conjunto es `refit_no_corrections − frozen`, que por construcción **no contiene ninguna corrección**: es la actualización temporal pura. El artefacto de origen lo nombra correctamente `delta_temporal_update_mcc` (`execution-record.json:92–143`), aunque el `review.json` de H usa la etiqueta ambigua `delta_combining_temporal_update` y da la definición explícita al lado.
- **Impacto.** Los números son exactos; el rótulo es falso. La dirección importa: atribuye a las correcciones una contribución (+0,056971 en la semilla 0) que **no tienen**. No llega a afirmar beneficio —el párrafo anterior ya publicó el contraste que aísla correcciones y su signo mixto, y la sección 11 niega expresamente la mejora atribuible al feedback— pero es un enunciado inexacto en el documento declarado canónico.
- **Remediación.** Reescribir como «el contraste que mide la **actualización temporal sin correcciones**», o publicar los dos conjuntos con sus nombres.

---

### `F-08` — **PRECISIÓN** — La tabla de C imprime «—» para dos métricas de la persistencia que la evidencia sí publica

- **Ubicación.** `docs/research/scientific-closure-synthesis-2026-09-22.md:192–193`.
- **Observado.** ROC-AUC y `episode_recall` de la persistencia figuran como «—». `C/metrics.json` publica `baseline_persistence.roc_auc = 0,7867188` y `operational.episode_recall = 0,5`.
- **Impacto.** La dirección es conservadora: ambos valores favorecen al candidato (0,939 contra 0,787; 0,900 contra 0,500), de modo que omitirlos **no** infla nada. Pero «—» se lee como «no disponible», y no lo está. En un documento cuya virtud es que nunca sustituye un valor ausente, conviene distinguir «no existe» de «no lo imprimo».
- **Remediación.** Imprimir los dos valores, o marcar «no se contrasta» en vez de «—».

---

### `F-09` — **PRECISIÓN** — El encargo describe el diff como de 12 archivos; son 13

- **Reproducción.** `git diff --name-status 1c33aad 7e63d1c | wc -l` → 13. Seis añadidos, siete modificados.
- **Impacto.** Nulo sobre el contenido; lo registro para que quien reproduzca el snapshot no lo lea como un archivo faltante. **No es un defecto del artefacto auditado**, sino del enunciado del encargo.

---

## 5. `sufficiency_of_GD12_and_RNS`

**Mi juicio: los tres `review.json` justifican `NOT_REQUIRED` de verdad. No son una racionalización.** Y lo digo tras intentar tratarlos como tales.

**Anterioridad, comprobada en git y no en el documento.** `git log -S 'GD-12'` sitúa la decisión en `a0d8bf7`, 2026-09-19T08:23:14Z: **dos días antes** de la campaña. Extraje el texto de la fila en los tres commits en que el archivo cambió (`a0d8bf7`, `495555c`, HEAD) y son **idénticos carácter por carácter**: el contenido de fondo no fue retocado después de ver resultados. Esto es lo único que hacía falta comprobar, y es independiente de cualquier artefacto escrito hoy. `GD-30` lo dice y es cierto.

**R — `SC-GOV-021`.** La condición normativa es una conjunción: «si se pretende sostener desempeño sobre humedad continua **y** la evidencia existente no lo cubre». Verifiqué el primer término por mi cuenta: el contrato congelado define un objetivo **binario** (`p20`, horizonte 3) y las métricas de decisión son MCC, F1, `episode_recall` y `onset`; no existe **ningún** artefacto con MAE ni RMSE en m³/m³ en toda la campaña. `claims.md:15` (CL-05) y `:123` delimitan la afirmación exactamente así. Y el criterio de aceptación **del propio requisito** dice literalmente «`NOT_REQUIRED` para sola clasificación P20». No es una interpretación favorable: es el texto congelado aplicado a un hecho que comprobé. **Suficiente.**

**N — `SC-GOV-023`.** El primer término —«si se afirmará detección reservada de corrupciones»— es falso y lo verifiqué: `claims.md:17`, `:125` y la sección 11 de la síntesis lo prohíben expresamente, y ningún artefacto de v4 contiene una matriz de confusión de detección. Lo que me hizo cambiar de opinión sobre este artefacto es que **identifica por sí solo la trampa no obvia**: H inyecta corrupciones de etiqueta y publica un 0/4 humano contra un 4/4 del oráculo, y un lector podría leer eso como detección de anomalías. El `review.json` lo anticipa, lo rechaza en ambas direcciones («ni cubierto ni refutado») y prohíbe el traslado; `claims.md:125` y la matriz lo repiten. Un artefacto que va a buscar la objeción más fuerte contra sí mismo no es una racionalización. **Suficiente.**

**S — `SC-GOV-024`.** CL-08 (`claims.md:18`) limita la robustez a etiquetas escasas y ruido de v3 y **excluye** sensores o mediciones ausentes. El criterio de aceptación del requisito dice, con esas palabras, «escasez de etiquetas no equivale a sensores ausentes», y el artefacto construye su argumento sobre esa distinción en lugar de eludirla. Añade además, por iniciativa propia, que la imputación causal de entradas de v4 es una **regla de causalidad** (`SC-GOV-010`) y no un ensayo de robustez, cerrando el otro atajo disponible. **Suficiente.**

**H — `SC-GOV-022`.** `REQUIRED`, ejecutado, auditado. Fuera de discusión aquí.

**Tres debilidades que exijo que queden registradas, porque las encontré yo y el expediente no las enuncia todas:**

1. Los tres argumentos son, por construcción, **argumentos sobre lo que no se afirma**. Su validez es por tanto **contingente a que la memoria técnica no amplíe las afirmaciones**. Hoy esa línea la sostienen las reglas de redacción de `thesis-traceability.md` y la lista «No demostrado, enunciado de frente» de `claims.md:137–151`. Si el texto de la tesis la cruza, `NOT_REQUIRED` caduca. Los tres artefactos lo dicen en su campo `reversibility` y está bien que lo digan: **no es una exención permanente**.
2. Ninguno evalúa el segundo término de la conjunción, y los tres lo declaran abiertamente («NO EVALUADO; la condición es una conjunción y el primer conjunto es falso»). Es lógicamente correcto y está bien enunciado. Lo registro para que nadie lea después que la evidencia existente «cubre» la humedad continua, la detección reservada o la robustez ante mediciones ausentes: **no la cubre, y no hace falta que la cubra**.
3. `GD-30` concede que crítica y auditoría de `GD-12` las ejecuta **el mismo lector en una sola pasada**, por instrucción del responsable. **Lo confirmo: soy un solo lector.** No fueron dos revisiones independientes y no debe presentarse como si lo fueran. `GD-35` lo registra como limitación de procedimiento no subsanada y la fila `SC-GOV-008` la hereda; eso es correcto y debe permanecer.

**Conclusión.** `GD-12` queda **criticada y auditada de forma independiente por mí, con resultado favorable en el fondo**: R `NOT_REQUIRED`, N `NOT_REQUIRED`, S `NOT_REQUIRED`, H `REQUIRED`. El retorno de `SC-GOV-021`, `023` y `024` de `BLOCKED` a `NOT_APPLICABLE` es procedente **una vez que este informe esté registrado y los campos `independent_review` completados** (`F-02`), y no antes.

---

## 6. `governance_states`

**El recuento no cierra: `F-03`.** El real es 12 / 10 / 3, no 11 / 11 / 3.

**Fila por fila, las transiciones sí están justificadas, con una excepción.** Las examiné una a una contra la evidencia:

| Transición | Mi juicio |
| --- | --- |
| `003` PASS → PWL | **Correcta y verificada por mí.** `git diff a6570147 HEAD` vacío en las seis rutas; única diferencia en `src/` el archivo nuevo de H; `origin/main` avanzó a `2079d03` y no es ancestro. Enunciar la propiedad contra un commit inmutable en vez de contra una referencia móvil es un acierto metodológico, no un tecnicismo |
| `005` PWL → PASS | **Correcta**, sus dos causas declaradas están resueltas. Con una salvedad: su justificación invoca que `GD-12` «queda además criticada y auditada», lo que en el snapshot es `F-02`. Con este informe, se sostiene |
| `008` PASS → PWL | **Correcta.** La pasada única de revisión es una limitación real y está bien ubicada |
| `016` «cambia de base, no de estado» | **La fila es correcta; el párrafo de recuento y `GD-34` la contradicen** (`F-04`) |
| `018` PASS → PWL | **Correcta.** `AUD-H-02` —resultados sin ancla en git, manifiesto alojado en el mismo montaje escribible— es una limitación viva y su sitio es esta fila |
| `021`/`023`/`024` BLOCKED → `NOT_APPLICABLE` | **Correcta en el fondo**, por lo que expongo en §5; **prematura en el snapshot**, por `F-02` |
| `022` PWL sin cambio | **Correcta.** Ya lo había fijado la sección del complemento H |
| `025` BLOCKED → PWL | **Correcta en el fondo; inadmisible tal como está fundada**, por `F-01` |

**Los cuatro descensos deliberados hablan a favor del expediente.** Bajar `003`, `008`, `016` y `018` en la misma sesión en que se cierran cinco bloqueos es exactamente lo que impide que el cierre se lea como una mejora uniforme, y `GD-34` lo declara con esas palabras. Lo verifiqué: los cuatro tienen limitaciones reales que estaban registradas en otros documentos y no en su fila. Es la clase de gesto que un expediente que quisiera maquillarse no haría.

**La asimetría «requisito `NOT_APPLICABLE` / change `BLOCKED`» (`GD-31`) es defendible. No es un truco.** Cuatro razones, todas comprobadas:

1. Son **objetos distintos**. El estado del requisito describe si una obligación **condicional** aplica al alcance aprobado; el del change describe si se **implementó y ejecutó**. Un complemento no ejecutado no puede tener un change cerrado, y una obligación cuya condición no se da no puede estar «pendiente» para siempre.
2. El registro de estado de los tres changes **ya decía desde el 2026-09-19** que una decisión `NOT_REQUIRED` auditada no equivale a ejecución ni cierre individual del change. No es una racionalización escrita hoy.
3. **Decisivo: no tocaron el checker.** Bastaba añadir una arista `BLOCKED → NOT_APPLICABLE` a la máquina de estados. Corrí `scripts/check_scientific_closure.py` y las 48 pruebas: el checker está **sin modificar** y da exit 0 con la asimetría intacta. Relajar la herramienta para que acepte el estado deseado es la forma exacta de fallo que este sistema existe para impedir, y no se cometió. Esa abstención, pudiendo hacerlo, es la mejor prueba de que la asimetría no es un artificio.
4. **Está declarada en una sección propia** en lugar de disimulada.

**`changes.json` es consistente con el checker y con la matriz, y es el lugar más honesto del expediente.** Lo verifiqué: `sc-01`…`sc-05` y `sc-08` en `PASS` con auditoría; `sc-07`, `sc-09`, `sc-10` en `BLOCKED`; y **`sc-06` en `REVIEW` con `audit: null`**, con un `state_event` que dice literalmente que el informe del lector independiente está «pendiente en este snapshot» y que «El change **NO** se cierra con tests verdes». Eso es correcto y es la razón por la que `F-01` y `F-02` son subsanables en vez de fatales: **la capa verificable mecánicamente no mintió; mintió la prosa de la matriz.**

---

## 7. `overclaiming_scan`

Intenté refutar cada garantía con los datos que el propio artefacto publica. Éste es el registro de lo que **no** logré y de lo que **sí**.

**Lo que intenté y no logré refutar:**

- **(a) ¿Se infla C a superioridad general?** No. El intervalo que excluye el cero aparece siempre en el mismo bloque que ~24 unidades efectivas, la ausencia de corrección por multiplicidad, la serie única, la calibración degradada con sus cinco bins, los 75 días de falso aviso y los dos episodios no detectados. La frase «**no** sostiene una afirmación de superioridad general» es explícita (`synthesis:244`), se repite en `claims.md:121`, en `thesis-traceability.md` R.3 y en la regla de redacción 1. Verifiqué los cinco bins uno a uno: **exactos**. No pude construir una lectura en la que C aparezca como superioridad general.
- **(b) ¿Insinúa H un beneficio?** No. Los deltas que aíslan correcciones se publican con su signo mixto, se declara que **no hay intervalos porque el diseño congelado no predeclara bootstrap**, se declara que **no existe agregado entre semillas**, y «Mejora causada por el feedback humano» encabeza la lista de lo no demostrado (`claims.md:145`, `synthesis:479`). Barrí las palabras prohibidas en los dos documentos nuevos: **todas las apariciones están en negaciones o en listas de prohibición**. Lo único que hallé es el rótulo equivocado de `F-07`, que no llega a afirmar beneficio.
- **(c) ¿Está enunciado el 0/4, o sólo sus insumos?** **Enunciado, y en cinco lugares**: `synthesis:322`, `claims.md:94` y `:146`, `traceability.md:301` y `:342`, `thesis-traceability.md` R.8 y regla de redacción 5. Era el hallazgo `AUD-H-04` —el insumo publicado sin la conclusión— y está cerrado. Además lo **recomputé yo desde el paquete crudo** y coincide: cuatro divergentes, veinte ACEPTAR, 0 de 4.
- **(d) ¿Difiere alguna cifra de la evidencia?** Contrasté alrededor de **sesenta valores** de A, B, C y H contra los artefactos que los publican —MCC, F1, precisión, recall, Brier, ROC-AUC, `episode_recall`, matrices de confusión, deltas, intervalos, bins de calibración, episodios, rachas, prevalencias, P20, semillas, réplicas, hashes, identidades—. **Cero discrepancias numéricas.** Los redondeos son correctos en todos los casos que revisé. Recalculé por mi cuenta los tres deltas de A, los dos contrastes de H, las tres prevalencias, el conjunto de equivalencia de la sensibilidad y la concordancia 16/20 desde los datos crudos. Todo cuadra.
- **(e) ¿Se afirma validación agronómica, eficacia de campo o mejora causada por el feedback?** No, en ninguno de los documentos nuevos. Las cuatro están en la lista de lo no demostrado y en la tabla de trabajo futuro con la evidencia que cada una exigiría.
- **Intentos adicionales, todos fallidos:** que el verde del checker o de las pruebas se presente como cierre científico (negado expresamente en la fila `SC-GOV-020`, en `thesis-traceability` 3.9 y en la nota del gate); que la corrida de sensibilidad 7–28 cm se lea como mejor modelo (`depth_role = sensitivity_only_no_selection_effect` verificado, y la advertencia del registro transcrita literal); que la prevalencia 2024/2025 se infiera (se declara expresamente que no existe artefacto que la desagregue y **no se infiere**, con la abstención razonada en `CE-11`); que un `null` se sustituya por cero (las cinco razones literales verificadas en los artefactos).

**Dónde sí lo logré, y es lo que define el veredicto.** Los tres hallazgos materiales —`F-01`, `F-02`, `F-03`— **son sobreafirmaciones en el registro**: acreditar un artefacto que no existe, declarar auditado lo que los propios artefactos marcan `PENDING`, y publicar un recuento que la propia tabla desmiente. Es exactamente el modo de fallo que este proyecto tiene documentado y que ya se corrigió dos veces (`AUD-F-01` el 2026-09-20, `EV-02` el 2026-09-21). **Los números resistieron; el registro no.**

---

## 8. `GF_and_SC_GOV_025`

**Mi veredicto de fondo: `PASS_WITH_LIMITATIONS` para ambos es el estado correcto.** Ni `BLOCKED`, ni `PASS` pleno. **Condicionado a la corrección de `F-01`, `F-02` y `F-03`.**

Evalúo los cinco conjuntos del criterio de aceptación uno por uno, con mi propio juicio.

### Conjunto 1 — «Todas las afirmaciones tienen evidencia o limitación aceptada»

**SATISFECHO.** Rehíce yo el recuento. CL-01 a CL-03: cubiertas por A, B y C ejecutadas, cuyos resultados verifiqué numéricamente y cuya integridad comprobé (91/91). CL-04, CL-05, CL-07, CL-08: cubiertas por limitación aceptada, y las tres últimas ahora con artefacto propio. CL-06: cubierta con limitaciones por H, auditado. CL-09: verifiqué que `metrics.json` de A, B y C contiene `onset` con `anticipated/same_day/late/missed/censored`, la mediana de adelanto con signo y los falsos avisos, y que `onset` y `episode_recall` se publican **por separado**, como exige `SC-GOV-016`. CL-10: su propio texto exige «Terminal A/B/C auditado, H auditado, trazabilidad y límites»; los cuatro términos existen hoy, incluida la trazabilidad, que es el artefacto que faltaba. **10 de 10.** La circularidad de CL-10 —se cierra con documentos producidos hoy— es admisible porque su criterio es, por diseño, documental.

### Conjunto 2 — «Terminal negativo válido documentado»

**SATISFECHO.** Los tres terminales negativos están documentados **como resultados válidos y no como defectos**, y verifiqué los tres en origen: `SIN_GANADOR_ESTABLE` en `A/selection_decision.json`; la no inferioridad de B con su intervalo que incluye el cero en `B/decision.json` y `B/bootstrap.json`; y `NO_RECALIBRATION` en `track_human.json`, predeclarado como desenlace admisible en el contrato anclado en git **antes** de que el operador viera nada. La síntesis dice «No es un defecto de software ni un fracaso experimental» y la regla final de `claims.md` lo repite. **La ausencia de mejora general no es un error a corregir, y el expediente no la trata como tal.**

### Conjunto 3 — «Complementos justificados»

**SATISFECHO EN EL FONDO, NO EN EL SNAPSHOT.** Por lo que expongo en §5: las condiciones de activación de R, N y S no se dan, lo verifiqué contra el texto literal de los requisitos y contra la evidencia, y H es el único `REQUIRED`, ejecutado y auditado. **Pero en el snapshot `7e63d1c` los cuatro artefactos declaran `independent_review: PENDING`** (`F-02`). Se satisface **cuando este informe quede registrado en ellos**, no antes. Ésta era la causa exacta de `RB-03` y de `GD-23`, y queda resuelta por este informe.

### Conjunto 4 — «Memoria caps. 2/3 trazada»

**SATISFECHO.** Leí `thesis-traceability.md` entero. Es un artefacto sustantivo, no un gesto: veintiún filas con evidencia fuente, resultado utilizable, **afirmación permitida redactada**, limitación obligatoria, figura recomendada y ajuste pendiente; ocho reglas de redacción que prohíben nominalmente las sobreafirmaciones de este proyecto; y cinco ajustes pendientes con responsable. **Permite sólo afirmaciones respaldadas**: cada fila lleva su límite en la misma fila, R.4 declara obligatoria la curva de calibración si la memoria muestra ROC-AUC, y R.8 ordena que el 0/4 no se presente como fracaso del operador sino como alcance de la pista. Le reconozco además dos virtudes que no estaba obligado a tener: declara el conflicto entre `AGENTS.md` (resultados en cap. 2) y la plantilla TTFA (resultados en cap. 4) en vez de resolverlo por su cuenta, y lo eleva como `AJ-01` al responsable; y prohíbe copiar números desde sí mismo, remitiendo a la síntesis canónica. `RB-06` queda cerrado.

### Conjunto 5 — «Ningún obligatorio sin resolver»

**SATISFECHO CON LIMITACIONES.** Cero requisitos `BLOCKED`, una vez procedente el retorno de `021/023/024` a `NOT_APPLICABLE`. Diez conservan limitaciones declaradas. Verifiqué que **ninguna de las diez requiere evidencia científica nueva** y que ninguna se atenúa: la sustitución de perfiles de rol (`RK-10`, abierto y materializado), los dos push de preparación (`RK-14`, «registrado, no subsanado», que además reproduje en el reflog de la rama anterior: `dc0d3f5` y `b9fefbf` figuran como `update by push`), la condición 2 de ADR-0011 `PENDING_CONFIRMATION`, los resultados sin ancla en git, la multiplicidad sin corregir, la revisión de pasada única y las limitaciones vivas de H. Están donde deben estar: **en su propia fila**.

### Veredicto sobre `SC-GOV-025`

**`PASS_WITH_LIMITATIONS`, procedente tras corregir `F-01`, `F-02` y `F-03`.** Las seis causas que el auditor de H enumeró para mantenerlo `BLOCKED` están resueltas: la síntesis de resultados existe y la verifiqué cifra por cifra; `GD-12` está criticada y auditada por este informe; la trazabilidad a la memoria existe; la matriz se actualizó; CL-10 está cubierta; y la auditoría final requisito por requisito sobre el snapshot posterior a la campaña **es este documento**. Mantener `BLOCKED` sería sostener un bloqueo cuya causa se resolvió, y el responsable ha sido explícito en que eso no corresponde. Forzar `PASS` pleno sería falso: diez requisitos conservan limitaciones materiales.

### Veredicto sobre el gate `GF`

**`PASS_WITH_LIMITATIONS`, con la misma condición.** Su condición de avance es «Auditor final PASS sobre suficiencia del alcance completo». **La emito, con limitaciones y para el alcance aprobado de HU7/HU8**: la evidencia de A→B→C está completa, auditada, respaldada e íntegra —lo comprobé—, el único complemento `REQUIRED` está ejecutado y auditado, los tres `NOT_REQUIRED` están justificados y ahora auditados, las afirmaciones están trazadas a los capítulos de la memoria y los límites están declarados. La salida exigida —«afirmaciones trazadas, límites y pendientes, memoria; no sólo software verde»— se cumple.

**Y lo digo con la advertencia que este expediente merece:** no acepto como cierre científico que el checker dé exit 0, que las 48 pruebas pasen, que OpenSpec valide 11/11 ni que la suite dé verde. Corrí las cuatro cosas y las cuatro dan bien, y **ninguna de ellas es suficiencia científica**. Lo que sostiene mi `PASS_WITH_LIMITATIONS` es haber recomputado los números desde la evidencia y haber comprobado que el alcance está honestamente delimitado, no el color de las pruebas.

**`GF` no certifica HU1 ni el Trabajo Final completo.** Sólo el alcance aprobado de HU7/HU8.

---

## 9. `limitations_that_must_remain_declared`

Exijo que estas limitaciones se conserven, sin atenuar y en el lugar donde un lector encuentre el número:

1. **Etapa A: `SIN_GANADOR_ESTABLE`.** El modelo evaluado **no** es el de mejor MCC nominal —lo fue `soft_voting`, a 0,0101— sino el más simple de un conjunto de equivalencia de cuatro familias, fijado por una **convención predeclarada**, no por desempeño. Un empate práctico no demuestra equivalencia: demuestra que el soporte no separa.
2. **Etapa B: no inferioridad, no superioridad.** El intervalo pareado **incluye el cero** ([−0,014553; 0,209198]). Y la precisión del candidato (0,667) es **inferior** a la de la persistencia (0,723): la ventaja en MCC y en `episode_recall` se paga con más falsos avisos.
3. **Etapa C: resultado favorable, no superioridad general.** El intervalo excluye el cero por +0,0227, con **~24 unidades efectivamente independientes**, sin corrección por multiplicidad, sin calibración de cobertura y sobre una sola serie.
4. **Calibración degradada en C, invisible en las métricas agregadas.** Cuando el modelo dice 96 %, acierta 66 % (n=83). **Ni el Brier (0,0975) ni el ROC-AUC (0,9390) revelan el defecto.** Si la interfaz muestra probabilidades al productor, no pueden presentarse como frecuencias esperadas.
5. **Falsos avisos y episodios no detectados.** En C: 75 días de falso aviso en 26 rachas, 3,09 cada 30 días, precisión de alerta 0,603, dos episodios no detectados y uno censurado. En B: 45 días en 19 rachas y dos no detectados.
6. **Deriva de prevalencia 33,3 % → 26,5 % → 17,6 %.** Las métricas dependientes de prevalencia no son comparables entre etapas. **No existe** artefacto que desagregue 2024 y 2025 y no debe inferirse.
7. **H, detección humana 0 de 4.** Sobre la única tarea determinable, el operador aceptó las cuatro etiquetas corrompidas, que son exactamente las cuatro que el oráculo simulado corrigió sobre los mismos eventos. Lo recomputé. **Debe aparecer junto a cualquier mención del circuito de retroalimentación**, y no debe presentarse como fracaso del operador: fija el alcance real de la pista.
8. **H, sólo aceptación.** Corrección y recalibración quedan demostradas **únicamente** por la pista simulada. **Rechazo y recalibración sucesiva no fueron ejercitados por ninguna pista científica**: sólo por la suite con fixtures, que por contrato no es evidencia científica **y que sigue sin verificación independiente** (`RB-07`/`AUD-H-09`, que yo tampoco pude verificar).
9. **H, cegamiento parcial y nominal.** El paquete mostraba la observación madurada y el P20; la etiqueta correcta era determinable y las instrucciones enunciaban la regla. El operador es además autor del código y del generador de corrupción. La pista prueba el **cumplimiento de un procedimiento dictado**, no criterio propio, pericia ni juicio bajo incertidumbre.
10. **H, sin intervalos y sin mejora atribuible.** Un operador, veinte eventos, cinco semillas que no son cinco poblaciones, deltas puntuales sin intervalo porque el diseño congelado no predeclara bootstrap, sin agregado entre semillas. La corrupción simulada es un **modelo de error artificial**, no una medición de la tasa de error de un revisor real.
11. **Sin agrónomo ni validación de campo.** Ningún documento vigente la exige para cerrar H, HU5 ni `GF` —lo verificó el auditor de H contra cuatro fuentes y `GD-29` ya retiró la quinta cita, que era falsa—. Es **limitación y trabajo futuro**, declarada por el propio operador.
12. **Los resultados científicos no tienen ancla en git** y viven en un montaje escribible protegido por manifiestos alojados en ese mismo montaje. El ensayo de recuperación acredita integridad y recuperabilidad de la copia, **no** resistencia a edición deliberada con privilegios. Exposición estructural preexistente, idéntica en A/B/C y en H.
13. **Condición 2 de ADR-0011 `PENDING_CONFIRMATION`** en el manifiesto de procedencia; fecha de adquisición efectiva `UNKNOWN`; `downloaded_service_version` de NASA POWER `UNKNOWN`.
14. **Los dos `git push` de la preparación del 2026-09-20 permanecen como desviación reconocida y no subsanada** (`RK-14`). Lo verifiqué en el reflog: `dc0d3f5` y `b9fefbf` figuran como `update by push`. No existe artefacto que lo cure.
15. **Sustitución de los perfiles de rol declarada y no subsanada** (`RK-10`): los cinco perfiles `.codex/agents` no son cargables en este runtime. Se documenta la sustitución; **no** se la presenta como equivalencia.
16. **Esta sesión ejecutó una sola revisión independiente** en lugar de la secuencia checker → crítico → auditor (`GD-35`). Soy un solo lector. Crítica y auditoría de `GD-12` y del cierre documental van en una sola pasada.
17. **Validez externa estrecha.** Un solo sitio, reanálisis y no sensores propios, P20 como proxy y no fisiología, métricas retrospectivas y no operativas, tres años de ventana, sin ensayo con usuarios. HU5 y HU6 son **evidencia técnica**, que nunca es eficacia científica.
18. **`NOT_REQUIRED` de R, N y S limita la afirmación; no elimina el requisito de tesis** ni convierte la ausencia de evidencia en evidencia de ausencia. Caduca si la memoria amplía las afirmaciones.
19. **Dos puntos que yo no pude verificar** y que no deben presentarse como auditados por este informe: los 75 originales ilegibles de `evidence/{A,B,C}` (verificados sólo vía respaldo) y la imagen `sha256:55bc923e…`, no inspeccionable desde esta distro.

---

## 10. `remaining_blockers`

**Bloqueos científicos: ninguno.** No queda ninguna pregunta científica sin responder dentro del alcance aprobado, ninguna afirmación sin evidencia o sin límite aceptado, y ningún obligatorio irresuelto. **Nada de lo que sigue exige reabrir el holdout, reejecutar A, B, C ni H, ni producir evidencia científica nueva.**

**Bloqueos documentales, que son los que sostienen el `FAIL`:**

| ID | Bloquea | Qué falta |
| --- | --- | --- |
| **AF-01** | `SC-GOV-025`, `GF`, el registro de `sc-06-scientific-synthesis` | Corregir `F-01`: emitir `scientific-closure-audit.json` **a partir de** este informe y reescribir `traceability.md:348` y `:404` para que citen el informe real por su ubicación, en vez de acreditar un artefacto inexistente. Es la recurrencia de `AUD-F-01` y no puede quedar sin corregir |
| **AF-02** | `SC-GOV-021`, `023`, `024`, conjunto 3 de `SC-GOV-025` | Corregir `F-02`: completar `independent_review` en los tres `auxiliary/{R,N,S}/review.json` y en `claim-evidence-review.json` con el veredicto de este informe y su ubicación. Hasta entonces los propios artefactos dicen que **no** cierran su requisito |
| **AF-03** | La matriz final como artefacto canónico | Corregir `F-03`: el recuento es **12 / 10 / 3 / 0**, no 11 / 11 / 3 / 0, y rehacer la enumeración de transiciones (`F-04`) |
| **AF-04** | Nada por sí solo; deben corregirse | `F-05` (unificar «diez, nueve de ellos distintos de `SC-GOV-025`»), `F-06` (marca de supersesión en `claims.md:44–46`), `F-07` (rótulo del segundo contraste de H), `F-08` (dos métricas de persistencia impresas como «—») |
| **AF-05** | Nada; debe quedar declarado | `RB-07` heredado: `INV-10` y la reproducción estricta 18/18 siguen sin verificación independiente, y yo tampoco pude verificarlos. **`BLOCKED` por punto**, no `PASS` por confianza |
| **AF-06** | Nada; debe quedar declarado | `CK-B1` y `CK-B2`: 75 originales de A/B/C ilegibles para mí, verificados sólo vía respaldo; imagen no inspeccionada. **`BLOCKED` por punto** |

Corregidos `AF-01`, `AF-02` y `AF-03`, y declarados `AF-05` y `AF-06`, el estado que sostengo para el snapshot resultante es el que el implementador propone: **`SC-GOV-025` y `GF` en `PASS_WITH_LIMITATIONS`**.

---

## 11. Lo esencial, en prosa

Verifiqué la ciencia por mi cuenta y se sostiene. Recomputé las MCC de las cuatro familias en A, los seis intervalos pareados, las catorce métricas de B y sus quince de C, los cinco bins de calibración, las quince MCC de H y los dos contrastes, las tres prevalencias y el conjunto de equivalencia de la sensibilidad. **Cero discrepancias numéricas en cerca de sesenta valores.** Recomputé desde el paquete crudo la concordancia 16/20 y las cuatro etiquetas corrompidas, y el 0 de 4 humano es real. Comprobé 91/91 hashes de A/B/C y 100/100 de H, abrí los ledgers en modo `ro` y confirmé que el holdout sigue `CONFIRMADA`, con un solo registro y sin un solo archivo de evidencia tocado después de la campaña. `GD-12` es anterior a la ejecución: está en git desde el 2026-09-19, dos días antes, y su texto es idéntico en los tres commits.

La síntesis no sobreafirma. Intenté inflar C a superioridad, insinuar beneficio en H y encontrar el 0/4 escondido entre sus insumos, y fracasé en los tres intentos: el expediente publica el hecho desfavorable junto al favorable, en el mismo bloque, cada vez. La decisión de suficiencia sobre R, N y S no es una racionalización: los tres artefactos aplican el texto literal del criterio a hechos que comprobé, y el de N va a buscar por sí mismo la objeción más fuerte que existía contra él. La asimetría entre requisito y change no es un truco, y la mejor prueba es que **pudiendo añadir una arista al checker para evitarla, no la añadieron**.

Y sin embargo el snapshot no es registrable. La matriz final —el documento que se declara a sí mismo canónico— acredita como existente la auditoría que usted me encargó **antes de que yo la hiciera**, y fija el estado de `SC-GOV-025` sobre esa base. Ése es, palabra por palabra, el hallazgo `AUD-F-01` que ese mismo archivo condena 172 líneas más arriba, en esa misma fila. Declara «criticada y auditada» una revisión que sus propios artefactos marcan `PENDING`. Y publica un recuento, 11/11/3, que su propia tabla desmiente: es 12/10/3. Tres afirmaciones falsas en el artefacto que debía ser el más exacto de todos.

Por eso `FAIL`, y por eso `FAIL` de tres ediciones. No hay nada que reejecutar, nada que reabrir, nada que medir de nuevo. La campaña está hecha y es sólida. Lo que falló es, otra vez, lo único que falla acá: afirmar en el registro más de lo verificado. Corregido eso, `GF` y `SC-GOV-025` son `PASS_WITH_LIMITATIONS` y lo sostengo yo, con las diecinueve limitaciones intactas y sin certificar HU1 ni la tesis completa.
