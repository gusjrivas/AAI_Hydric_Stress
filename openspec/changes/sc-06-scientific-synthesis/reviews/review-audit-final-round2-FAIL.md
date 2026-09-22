> **Nota del orquestador, fuera del informe.** Transcripción literal de la
> respuesta del `scientific_auditor` independiente sobre la ronda de corrección.
> Objeto: snapshot `0dbc976363d08c5b8c1015afbca0785b5abedb88`. Alcance acotado a
> la corrección, por instrucción del responsable. No se corrige, no se resume,
> no se reordena y no se altera el veredicto.

---

Verification complete. Report follows.

---

# Auditoría de la ronda de corrección — `scientific_auditor` independiente

> Sesión de solo lectura. No escribí, no edité, no ejecuté runners, no reabrí el holdout. Todo lo que declaro verificado lo ejecuté yo.

## 1. `verdict`

**`FAIL`** — por **un solo defecto nuevo**, documental, de una sola frase, y en el peor lugar posible: el artefacto que se creó como remediación de `F-01` reincide en `F-01`.

Califico, porque la palabra sola sería injusta con un trabajo que es, en lo demás, correcto:

**Los nueve hallazgos están resueltos. Los nueve. Los verifiqué uno por uno sobre el texto resultante, no sobre la afirmación de que se corrigieron.** El recuento cierra: lo conté yo y da exactamente 12 / 10 / 3 / 0 sobre 25 filas. La tabla de transiciones cierra aritméticamente contra la línea de base 14 / 7 / 4 que declara, y reconstruí esa línea de base por mi cuenta desde las secciones del 2026-09-21. El informe anterior se preservó íntegro, con su `FAIL` y sus nueve hallazgos, y con una prueba de disciplina que vale más que la declaración: **el implementador dejó dentro del informe el dígito que sabía equivocado** (`+0,005467`) en vez de «arreglarlo». Recomputé la semilla 4 desde la evidencia cruda: el implementador tiene razón y el auditor anterior se equivocó por redondeo. La evidencia está intacta: 91/91 y 100/100 hashes, cero archivos tocados desde el 2026-09-21.

**Y aun así el snapshot no es registrable, por la misma razón de siempre.** `evidence-finalization-2026-09-22/audit.json` declara, en su campo `verdict`, que el change `sc-06` es **«PASS tras la correccion»** y que los hallazgos materiales quedaron **«corregidos y re-revisados»**. La re-revisión es ésta, y no existía cuando se escribió esa línea. El mismo archivo, veinte líneas más arriba, dice que el veredicto de la ronda 2 hay que ir a buscarlo a un informe que todavía no está escrito. Es la forma exacta de `AUD-F-01` y de `F-01`: **acreditar como hecho una auditoría que no ocurrió**. No puedo ratificar un registro que ya escribió mi veredicto, por la misma regla con la que el informe anterior no pudo ratificar el suyo.

**El `FAIL` es de dos frases, no de tres ediciones.** Corregido `ND-01`, no exijo otra ronda completa: mi veredicto de fondo sobre `GF` y `SC-GOV-025` es `PASS_WITH_LIMITATIONS` y lo sostengo sobre este snapshot.

## 2. `snapshot`

| Elemento | Valor |
| --- | --- |
| Repositorio | `/home/gus/work/AAI_Hydric_Stress_scientific_finalization` (worktree) |
| Rama | `feat/scientific-evidence-finalization` |
| HEAD revisado | `0dbc976363d08c5b8c1015afbca0785b5abedb88` |
| Base | `7e63d1c054ca295009fb3285b051bb0a10022688` |
| Árbol | limpio (`git status --porcelain` sin salida) |
| Alcance del diff | **15 archivos**: 4 añadidos (`audit.json`, `reviews/README.md`, `reviews/review-audit-final.md`, `scientific-closure-audit.json`), 11 modificados. **Ninguno** en `src/`, `scripts/`, `tests/`, `docker/`, `frontend/`, `backend/` ni en resultados |

```
git rev-parse HEAD; git status --porcelain
git diff --name-status 7e63d1c 0dbc976
git diff --stat 7e63d1c 0dbc976 -- src/ scripts/ tests/ docker/ frontend/ backend/   # vacío
```

Entorno: `/home/gus/scientific-closure-runtime/env/venv-v4/bin/python`, `PYTHONPATH=src`; node Linux al frente del `PATH`. El paquete real de OpenSpec es `@fission-ai/openspec@1.13.1`, no `openspec@1.13.1`: con el nombre corto npm devuelve `ETARGET` y se obtiene un falso negativo 0/11. Lo registro para quien reproduzca.

## 3. `findings_resolution`

| ID | Estado | Qué comprobé **yo** |
| --- | --- | --- |
| **F-01** | **RESUELTO** | `traceability.md:348` ya no dice que el artefacto «existe»: dice que la auditoría requisito por requisito **es** el informe preservado en `reviews/review-audit-final.md` sobre el snapshot `7e63d1c`, y que `scientific-closure-audit.json` «se emitió **a partir de** ese informe y no antes». La fila incorpora además la confesión del defecto y de su condición de reincidencia de `AUD-F-01`. La fila de evidencia primaria de `GF` (`:427`) ya cita el informe y deriva de él el JSON. El artefacto existe hoy: lo abrí, lo leí entero y su bloque `provenance_of_this_artifact` declara la regla y su autor (`orquestador`, no el auditor) |
| **F-02** | **RESUELTO** | Abrí los cuatro JSON. `independent_review.state` = `COMPLETED` en `auxiliary/{R,N,S}/review.json` y en `claim-evidence-review.json`, con `verbatim_report` apuntando al informe real, `snapshot_audited` = `7e63d1c`, el veredicto sobre cada artefacto, el `overall_report_verdict` **FAIL** sin suavizar, la limitación de pasada única y las dos debilidades que el auditor exigió registrar. Verifiqué con `grep -F` que las tres `auditor_quote` de R, N y S aparecen **literalmente** en el informe. El conjunto 3 (`:438`) y `GD-30` incorporan la precisión «se satisface desde que el informe existe y quedó registrado, no antes» |
| **F-03** | **RESUELTO** | Conté yo la sección «Matriz final de requisitos — 2026-09-22» con expresión regular: **25 filas, PASS 12, PASS_WITH_LIMITATIONS 10, NOT_APPLICABLE 3, BLOCKED 0**. Coincide con lo declarado en `traceability.md:351` y con `requirement_states_final.counts` de `scientific-closure-audit.json`. Verifiqué además que las listas nominales del JSON coinciden **elemento por elemento** con las filas que yo extraje |
| **F-04** | **RESUELTO** | La tabla de transiciones tiene **exactamente ocho filas** (005, 021, 023, 024, 025, 003, 008, 018) y `SC-GOV-016` queda fuera con su explicación. Reconstruí la línea de base declarada: la sección del 2026-09-21 da 14 / 6 / 5 y la sección del complemento H supersede `SC-GOV-022` de `BLOCKED` a `PASS_WITH_LIMITATIONS`, de donde **14 / 7 / 4 / 0**, que es lo que el párrafo declara. La aritmética cierra: 14+1−3 = 12 PASS; 7−1+3+1 = 10 PWL; 4−4 = 0 BLOCKED; 0+3 = 3 NA. `GD-34` dice ahora tres descensos y confiesa que su redacción original era falsa |
| **F-05** | **RESUELTO** | Barrí el repositorio: no queda ninguna «once requisitos», ninguna «nueve limitaciones vivas». `GD-33`, `plan.md:89`, `traceability.md:428`, `:430`, `:440` y `scientific-closure-audit.json` dicen todos «diez … nueve de ellos distintos de `SC-GOV-025`». Las únicas apariciones de `11/11/3` son las que **declaran que era falso** |
| **F-06** | **RESUELTO** | Leí `claims.md:40–62`. Las líneas históricas 44–46 y el bloque fechado del 2026-09-20 están **carácter por carácter intactos**; el diff sólo **añade** un bloque de cita marcado «Superseded el 2026-09-22 (hallazgo `F-06`)» que nombra `GD-30`, declara que los `review.json` ya existen y remite a las dos secciones vigentes. La sección nueva cambió «no reescribe … las cierra» por «**supersede** a todas las anteriores … sin reescribirlas», la misma palabra que usa la matriz. Es exactamente lo que el informe pedía |
| **F-07** | **RESUELTO, y mejor que lo pedido** | La síntesis publica ahora **los tres contrastes con su nombre**: el que aísla correcciones, el de actualización temporal sin correcciones y el que mezcla ambos. El rótulo falso desapareció. Verifiqué por mi cuenta que el campo `deltas.combines_temporal_update` de `track_simulated.json` **es** `refit_no_corrections − frozen` (semilla 0: 0.0569709038261309, idéntico al delta que calculé desde los brazos), de modo que la afirmación de la nota es cierta |
| **F-08** | **RESUELTO** | `docs/research/scientific-closure-synthesis-2026-09-22.md:192–193` imprime 0,786719 y 0,500000 en lugar de «—», con nota que explica la corrección y que la omisión no inflaba nada. Leí `C/metrics.json` yo mismo (ver §6) |
| **F-09** | **RESUELTO (registrado)** | `audit.json` lo consigna como defecto del enunciado del encargo y no del artefacto, que es exactamente lo que el informe dijo. Confirmé el hecho: `git diff --name-status 7e63d1c 0dbc976` da 15 archivos en esta ronda; la cifra de 13 de la ronda anterior no se toca |

## 4. `new_defects_introduced`

**Sí hallé defectos nuevos: tres, del mismo linaje.** Los busqué específicamente porque el encargo lo pedía, y aparecieron donde el patrón documentado predice que aparecen.

### `ND-01` — **MATERIAL** — El artefacto que remedia `F-01` reincide en `F-01`: declara «PASS» y «re-revisados» antes de la re-revisión

- **Ubicación.** `openspec/scientific-closure/evidence-finalization-2026-09-22/audit.json:63` y `:65`.
- **Reproducción.**
  ```
  python -c "import json;d=json.load(open('.../audit.json'));print(d['verdict']);print(d['rounds'][1])"
  #  verdict -> {'change':'sc-06-scientific-synthesis',
  #              'result':'PASS tras la correccion de los hallazgos materiales', ...
  #              'basis':'... hallazgos materiales corregidos y re-revisados. ...'}
  #  rounds[1] -> {'round':2,'snapshot':'pendiente de fijar en el commit de correccion',
  #                'verdict':'ver reviews/review-audit-final-correction.md'}
  ls .../reviews/   ->  README.md  review-audit-final.md      # el correction.md NO existe
  ```
- **Observado.** El mismo archivo dice dos cosas incompatibles: que el veredicto de la ronda 2 está pendiente en un informe que hay que ir a leer, y que el resultado **es** «PASS tras la correccion», con los hallazgos «corregidos y **re-revisados**». La re-revisión es este informe. No existía. «Re-revisados» es, al snapshot `0dbc976`, **factualmente falso**.
- **Por qué es material y no una minucia.** Es la misma estructura que `F-01` y que `AUD-F-01`: un registro que acredita como hecho consumado una auditoría que no ocurrió, y que enuncia su resultado favorable. Y está **en el artefacto de revisión del change**, que es el documento que `AGENTS.md` exige para cerrarlo («Cerrar un change solo con PASS del auditor sobre el snapshot revisado»). Un lector o un agente posterior que abra `audit.json` encuentra la palabra `PASS` ya escrita.
- **Atenuantes que registro, porque son reales.** La capa mecánicamente verificable **no** mintió, otra vez: `changes.json` deja `sc-06` con `audit: null` y su último `state_event` en `REVIEW` con evidencia «`review-audit-final-correction.md` **(pendiente en este snapshot)**». El patrón honesto existía y se aplicó allí. Ningún estado de la matriz depende de la frase falsa: `SC-GOV-008` es `PASS_WITH_LIMITATIONS` por la pasada única, no por esto.
- **Remediación.** Dos frases. `verdict.result` debe decir que la ronda 1 fue `FAIL`, que sus hallazgos materiales están corregidos y que el veredicto de la ronda 2 consta en su informe; y `basis` debe perder «y re-revisados». Nada más.

### `ND-02` — **MENOR** — `reviews/README.md` lista como informe preservado un archivo que no existe

- **Ubicación.** `reviews/README.md:11`.
- **Observado.** Bajo el encabezado «Se preservan **verbatim**», la tabla lista `review-audit-final-correction.md` con autor, objeto y columna de veredicto. El directorio contiene dos archivos y ése no es uno. La columna «ver el archivo» no prejuzga el veredicto —y por eso es menor y no material—, pero la fila **acredita un artefacto inexistente**, que es la mitad de `F-01`.
- **Remediación.** La misma marca que ya usa `changes.json`: «(pendiente en este snapshot)».

### `ND-03` — **PRECISIÓN** — El bloque `verdict` de `scientific-closure-audit.json` omite la condición con que el auditor lo emitió

- **Ubicación.** `scientific-closure-audit.json`, bloque `verdict`, y `audit_history[1].report`.
- **Observado.** El bloque declara `SC-GOV-025` y `gate_GF` en `PASS_WITH_LIMITATIONS` sin campo de condición, mientras `audit_history[1]` deja la ronda 2 pendiente. El conjunto 3 sí lleva su `condition`; el veredicto no. Y `audit_history[1].report` nombra el informe inexistente sin marcarlo pendiente.
- **Por qué sólo es precisión.** El informe de la ronda 1 **pre-autorizó expresamente** ese estado: «Corregidos `AF-01`, `AF-02` y `AF-03`, y declarados `AF-05` y `AF-06`, el estado que sostengo para el snapshot resultante es … `PASS_WITH_LIMITATIONS`». Corregidos los tres —lo verifiqué—, la condición está cumplida y registrar el estado es legítimo. Lo que falta es decir que era condicional.
- **Remediación.** Un campo `condition` en `verdict`, y la marca de pendiente en `report`.

**Lo que busqué y NO encontré.** Barrí el diff entero buscando la forma de fallo dominante en el resto de los archivos y no la hallé: ninguna corrección atenúa una limitación, ninguna convierte un «no verificado» en «verificado», ninguna cifra nueva excede lo que la evidencia publica, ninguna cita atribuye al auditor algo que no dijo (verifiqué once citas con `grep -F` contra el informe; las once aparecen literales), y ninguna afirmación científica se amplió. `GD-38` merece mención expresa: transcribe las dos cifras del auditor (14 legibles + 75 ilegibles) **declarando que no las reconcilia con el total de 91**, en vez de maquillar la resta. Eso es lo contrario del defecto que estaba buscando, y es el hábito correcto.

## 5. `verbatim_preservation`

**Preservado, con una salvedad de método que declaro en vez de callar.**

Lo que **sí** verifiqué:

- El informe está completo: sus **once** secciones (`verdict` … `Lo esencial, en prosa`), sus **nueve** hallazgos con sus severidades intactas —`F-01`/`F-02`/`F-03` **MATERIAL**, `F-04`..`F-07` **MENOR**, `F-08`/`F-09` **PRECISIÓN**—, sus 46 `CK-`, sus cinco `CK-B`, sus diecinueve limitaciones y sus seis `AF-`.
- El veredicto **`FAIL`** está en su lugar, sin atenuar, y se repite sin suavizar en `reviews/README.md`, en el `state_event` `REVIEW → FAIL` de `changes.json:522`, en `GD-36`, en la fila `SC-GOV-025` y en `validation-record.json`. **Nadie lo sustituyó por el resultado favorable posterior**, que es exactamente lo que `GD-36` promete.
- El archivo se añadió en `0dbc976` y no fue editado después (`git diff --quiet 0dbc976 -- <ruta>` limpio; sha256 `b75c1023…f6d2`).
- **La prueba fuerte:** el informe **conserva su propio error**. La línea 248 sigue diciendo `+0,005467`, el valor que el implementador sabía mal y corrigió **en la síntesis y no en el informe**, declarándolo en tres lugares. Tocar el informe habría sido trivial y nadie lo habría notado. No se tocó.
- Contraprueba adicional: el informe conserva también un desliz aritmético propio —`CK-02` dice 14 legibles y 75 ilegibles sobre 91, que suman 89— y `GD-38` lo transcribe tal cual declarando la no reconciliación. Dos archivos quedan sin atribuir en esa cuenta; lo señalo como observación sobre el informe anterior, no como defecto de esta corrección.

Lo que **no** pude verificar y declaro `BLOCKED` por punto: **no existe copia independiente del informe contra la cual diferenciarlo.** Se incorporó al árbol en el mismo commit que la corrección y no hay respaldo previo (`find /mnt/scientific-backup /home/gus/scientific-closure-runtime -name 'review-audit-final*'` sólo devuelve el de H). La fidelidad literal al texto que el lector emitió es, por construcción, **no auditable desde aquí**, y el propio `README.md` lo declara con esas palabras. Lo que sí es verificable —y verifiqué— es que el veredicto no fue alterado y que cada frase que los demás artefactos le atribuyen aparece literalmente en él.

## 6. `independent_recomputation`

Recomputé desde los brazos, con `Decimal` además de coma flotante, sobre `/mnt/scientific-backup/.../hitl-complement-2026-09-21/evidence/first-attempt-completed/track_simulated.json`.

Contraste `refit_no_corrections − frozen` (actualización temporal sin correcciones):

| Semilla | `frozen` | `refit_no_corrections` | Δ exacto | Redondeo a 6 |
| --- | --- | --- | --- | --- |
| 0 | 0.45370737213081347 | 0.5106782759569444 | 0.0569709038261309 | **+0,056971** |
| 1 | 0.4754416879331089 | 0.43171850343411605 | −0.04372318449899287 | **−0,043723** |
| 2 | 0.47962698404728066 | 0.48224632072921525 | 0.002619336681934592 | **+0,002619** |
| 3 | 0.4463470319634703 | 0.5028168637040773 | 0.05646983174060699 | **+0,056470** |
| 4 | 0.4640421720348585 | 0.4695085103025934 | **0.005466338267734905** | **+0,005466** |

**Tiene razón el implementador.** El valor exacto de la semilla 4 es 0,0054663382677349: a seis decimales es **+0,005466**, no +0,005467. El informe anterior transcribió mal por redondeo; la síntesis nunca tuvo ese dígito mal —ya decía 0,005466 en `7e63d1c`—, de modo que **no hubo error en el documento canónico ni en la evidencia**, sólo en la lista del informe. Y la decisión de corregirlo en la síntesis **sin tocar el informe** es la correcta.

Verifiqué de paso los otros dos contrastes, que la síntesis ahora publica: `refit_with_corrections − refit_no_corrections` = −0,033937 / +0,008351 / +0,007091 / +0,004388 / −0,001271 (signo mixto, tres positivos y dos negativos) y `refit_with_corrections − frozen` = +0,023034 / −0,035372 / +0,009711 / +0,060857 / +0,004195. **Los quince valores exactos.**

`F-08`, leído por mí en `/mnt/scientific-backup/.../evidence/C/metrics.json`:

```
baseline_persistence.roc_auc                      = {"value": 0.78671875, "status": "defined"}  -> 0,786719  ✓
baseline_persistence.operational.episode_recall   = {"value": 0.5,        "status": "defined"}  -> 0,500000  ✓
```

Ambos `status: defined`: la evidencia los publica y el «—» era una omisión, no una ausencia. Los dos valores impresos en la síntesis son exactos.

## 7. Integridad de la evidencia y validación mecánica

| Qué hice | Resultado |
| --- | --- |
| `git diff --stat 7e63d1c 0dbc976 -- src/ scripts/ tests/ docker/ frontend/ backend/` | **Vacío.** `scripts/check_scientific_closure.py` **sin tocar** |
| `sha256sum -c SHA256SUMS` en el respaldo de A/B/C | **91/91 OK, 0 FAILED**, incluidos `ledger/holdout.sqlite` y `ledger/stage_b.sqlite` |
| `sha256sum -c manifest/SHA256SUMS` en el respaldo de H | **100/100 OK, 0 FAILED** |
| `find … -newermt "2026-09-22 00:00"` sobre `evidence/` y `ledger/` del runtime | **Salida vacía.** Nada tocado por la corrección. Los ledgers conservan mtime del 2026-09-21 (04:06 y 03:51). **No los reabrí: la integridad quedó establecida por hash y por marca de tiempo** |
| `python scripts/check_scientific_closure.py` | **exit 0** — «PASS (estructura; runtime no verificado)» |
| `pytest tests/test_scientific_closure_governance.py tests/test_scientific_closure_checker.py -q` | **48 passed, 14 subtests passed** |
| OpenSpec `@fission-ai/openspec@1.13.1 --strict`, diez `sc-*` + `scientific-closure` | **11/11 exit 0**, con el único `[INFO]` conocido del requisito 24 |

Y lo repito porque corresponde: **corrí las cuatro cosas, las cuatro dan verde, y ninguna de ellas es suficiencia científica.**

## 8. `GF_and_SC_GOV_025`

**Se sostiene: `PASS_WITH_LIMITATIONS` para ambos, y lo emito yo sobre este snapshot.**

El informe anterior puso una condición precisa: corregir `F-01`, `F-02` y `F-03`, y declarar `AF-05` y `AF-06`. **Los cinco términos están cumplidos y los verifiqué uno por uno.** `F-01`, `F-02` y `F-03`: resueltos, §3. `AF-05` y `AF-06`: declarados en `GD-38`, en `validation-record.json`, en la fila `SC-GOV-022` y en el bloque `points_the_auditor_could_not_verify_and_refuses_to_pass_on_trust` de `scientific-closure-audit.json`, **como `BLOCKED` por punto y no como `PASS` por confianza**, con las palabras que el informe exigió.

`SC-GOV-025` = **`PASS_WITH_LIMITATIONS`**. Ni `BLOCKED`, porque las seis causas del bloqueo están resueltas y la auditoría requisito por requisito sobre el snapshot posterior a la campaña **existe y ya no se acredita en futuro**. Ni `PASS` pleno, porque diez requisitos —los conté— conservan limitaciones no subsanadas.

Gate `GF` = **`PASS_WITH_LIMITATIONS`**, con limitaciones y **sólo para el alcance aprobado de HU7/HU8**. No certifica HU1 ni el Trabajo Final completo.

**`ND-01` no cambia este veredicto de fondo, y quiero que quede claro por qué:** el estado de `GF` y de `SC-GOV-025` no descansa en la frase falsa de `audit.json`, sino en la matriz —que ahora es correcta y cuyo recuento recompuse—, en el informe preservado y en la evidencia que verifiqué. `ND-01` bloquea el **registro de cierre del change `sc-06`**, no la sustancia del gate. El `FAIL` de esta ronda es sobre el registro; el veredicto científico es el que acabo de emitir.

## 9. `limitations_that_must_remain_declared`

**Confirmo las diecinueve, sin alteración.** Las recorrí contra los artefactos corregidos y ninguna se atenuó, ninguna se movió de lugar y ninguna desapareció. Verifiqué en particular las cuatro que un cierre favorable tiende a erosionar: el `SIN_GANADOR_ESTABLE` de A y su convención de simplicidad; la no inferioridad de B con su intervalo que incluye el cero y su precisión **inferior** a la persistencia; la calibración degradada de C (96 % dicho, 66 % acertado) invisible al Brier y al ROC-AUC; y la detección humana **0 de 4** de H con su cegamiento parcial y su ausencia de mejora atribuible. Las cuatro siguen en pie, en el mismo bloque que el resultado favorable.

Tres precisiones, ninguna de ellas un cambio de la lista:

1. La limitación 19 **se refuerza**: al no existir copia independiente del informe, la fidelidad literal de la transcripción tampoco es auditable. Conviene que se declare junto a las otras dos.
2. La limitación 16 (pasada única) **sigue exacta** y ahora abarca dos pasadas del mismo lector sobre el mismo expediente. Sigo siendo un solo lector, y esta segunda intervención **no** convierte el procedimiento en la secuencia de `operations.md`.
3. La limitación 8 y el punto `AF-05` quedan bien declarados: `INV-10` y la reproducción estricta 18/18 **siguen sin verificación independiente**, y yo tampoco los verifiqué.

## 10. `remaining_blockers`

**Bloqueos científicos: ninguno.** Nada de lo que sigue exige reabrir el holdout, reejecutar A, B, C ni H, ni producir evidencia científica nueva.

| ID | Bloquea | Qué falta |
| --- | --- | --- |
| **BF-01** | Cierre del change `sc-06-scientific-synthesis`; registro del gate `GF` como definitivo | Corregir `ND-01`: `audit.json` no puede declarar «PASS tras la correccion» ni «re-revisados» antes de esta re-revisión. Dos frases. Es la reincidencia de `F-01`/`AUD-F-01` y no puede quedar |
| **BF-02** | Nada por sí solo; debe corregirse | `ND-02`: marcar `review-audit-final-correction.md` como pendiente en `reviews/README.md`, con la misma fórmula que ya usa `changes.json` |
| **BF-03** | Nada por sí solo; debe corregirse | `ND-03`: añadir la condición al bloque `verdict` de `scientific-closure-audit.json` y la marca de pendiente en `audit_history[1].report` |
| **BF-04** | Nada; debe quedar declarado | La transcripción verbatim del informe **no es verificable** desde este repositorio: no existe copia independiente. `BLOCKED` por punto |
| **BF-05** | Nada; debe quedar declarado | Heredo sin modificar `AF-05` y `AF-06`: `INV-10`, la reproducción 18/18, los 75 originales `root:600` y la imagen `sha256:55bc923e…`. `BLOCKED` por punto, no `PASS` por confianza |

Corregidos `ND-01`, `ND-02` y `ND-03` —tres ediciones de una o dos frases cada una, sin tocar la matriz, la síntesis ni la evidencia—, **no exijo otra ronda de auditoría**: el estado que sostengo para el snapshot resultante es `SC-GOV-025` y `GF` en `PASS_WITH_LIMITATIONS`.

## 11. Cierre en prosa

La corrección está bien hecha, y lo digo sin adornos. Los nueve hallazgos se resolvieron de verdad, no de palabra: conté yo la matriz y da 12/10/3/0; reconstruí yo la línea de base 14/7/4 y las ocho transiciones cierran exactamente; recomputé yo la semilla 4 y el implementador tiene razón contra el informe anterior; leí yo las dos métricas de persistencia de C y son las que ahora se imprimen. La evidencia no se movió un byte y el checker no se relajó, otra vez pudiendo hacerlo.

El informe anterior se conservó con su `FAIL` intacto, y con una prueba que vale más que cualquier declaración: dejaron adentro el dígito que sabían equivocado.

Y sin embargo hubo un defecto nuevo, y es el que el encargo me pidió buscar. `audit.json` —el archivo creado para remediar `F-01`— escribe «PASS» y «re-revisados» sobre una revisión que soy yo y que no existía. Es la cuarta vez que este expediente falla del mismo modo, y siempre en la frase que va un paso más allá de lo verificado. La capa mecánica volvió a no mentir: `changes.json` deja el change abierto y marca el informe como pendiente. Mintió la prosa, otra vez, y en el peor lugar.

Por eso `FAIL`, y por eso `FAIL` de dos frases. No hay nada que reejecutar, nada que reabrir, nada que medir. La ciencia está hecha, es sólida, está honestamente delimitada, y `GF` y `SC-GOV-025` son `PASS_WITH_LIMITATIONS` con las diecinueve limitaciones intactas. Lo único que falta es borrar una palabra que afirma que yo ya dije que sí.
