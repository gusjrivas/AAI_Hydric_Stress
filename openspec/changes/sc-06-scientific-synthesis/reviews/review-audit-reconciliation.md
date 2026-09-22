# Auditoría final independiente de la reconciliación RB-03/04/05/06

- **Rol:** `scientific_auditor` (auditor final independiente de esta reconciliación).
- **Snapshot auditado:** `e822f6f313625083ef43996244e149990c714d12` (HEAD de `feat/scientific-closure`), árbol limpio (`git status --porcelain` vacío).
- **Línea base de comparación:** `65ca852` (cierre de RB-03 con `PASS` de su propio auditor).
- **Sesión:** separada de la del implementador/orquestador. Solo lectura. No escribí, edité, creé ni borré ningún archivo. No ejecuté ningún runner científico, no abrí datasets, no toqué ledgers ni el holdout.
- **Runtime efectivo:** Claude Code CLI, modelo Opus 5. Coincide con `model_requested: "opus"` declarado en `reconciliation-2026-09-22/session-identity.json`. Sandbox de solo lectura **instruido, no forzado por el harness** (`sandbox_mode_effective: INSTRUCTED_ONLY`); lo que este informe acredita es mi conducta declarada, no una restricción impuesta por la herramienta.

## Qué NO verifiqué, por instrucción y no por limitación

Por instrucción expresa del responsable, transmitida por el orquestador, **no** reabrí ni reaudité: el contenido de RB-03 (dossier GD-12, `auxiliary/{R,N,S}/review.json`, crítica y auditoría de `sc-07/09/10`); los 91/91 y 100/100 hashes recomputados por las dos rondas de `f355272`; las 72 métricas del complemento H. Mi verificación sobre RB-03 se limitó, como se me indicó, a comprobar que `e822f6f` lo dejó intacto.

**Limitación decisiva de alcance, que condiciona todo lo que sigue:** mi mandato fueron seis ítems acotados. **No realicé la auditoría final requisito por requisito** que exige `SC-GOV-025`/T25. Por lo tanto este informe, cualquiera sea su veredicto, **no puede descargar RB-05**. Lo digo aquí, antes del veredicto, para que no se lo lea como lo que no es.

---

## Verificación punto por punto

### Ítem 1 — RB-03 sigue conforme al `PASS` de su propio auditor: **VERIFICADO**

**Comando:**
```
git diff --name-status 65ca852 e822f6f -- \
  'openspec/scientific-closure/sufficiency-review-2026-09-22/*' \
  'openspec/changes/sc-07*/reviews/*' 'openspec/changes/sc-09*/reviews/*' 'openspec/changes/sc-10*/reviews/*'
```
Resultado: **vacío**. Ningún archivo de la superficie RB-03 aparece en el diff.

**Verificación independiente por hash de árbol Git** (más fuerte que el diff, porque no depende de que yo acierte el pathspec):

| Ruta | `65ca852` | `e822f6f` | |
| --- | --- | --- | --- |
| `sufficiency-review-2026-09-22/` | `6ee5e143…` | `6ee5e143…` | IDÉNTICO |
| `sc-07-aux-regression/` (change completo) | `a3950a19…` | `a3950a19…` | IDÉNTICO |
| `sc-09-aux-anomalies/` (change completo) | `61e8502b…` | `61e8502b…` | IDÉNTICO |
| `sc-10-aux-robustness/` (change completo) | `d4be99c7…` | `d4be99c7…` | IDÉNTICO |

Los tres directorios `reviews/` comparten el árbol `1dbc6931…` en ambos commits. Se conservan `README.md`, `review-audit-gd12.md` y `review-critic-gd12.md` en cada uno.

**Archivos compartidos entre ambas líneas** (donde un toque a RB-03 sería posible sin aparecer como ruta nueva):

- **`changes.json`** — comparación canónica entrada por entrada (`json.dumps(sort_keys=True)` + SHA-256): de las diez entradas, **sólo `sc-06-scientific-synthesis` cambió**. `sc-07-aux-regression`, `sc-09-aux-anomalies` y `sc-10-aux-robustness` son byte-idénticas y siguen en `BLOCKED` con su `applicability_decision`. `schema_version` sin cambios.
- **`traceability.md`, `decisions.md`, `claims.md`, `plan.md`, `README.md`, `hu8-…md`, `proposal.md`** — recuento de líneas eliminadas por archivo: **`-0` en los siete**. Son adiciones puras (`traceability.md` `+37`, `decisions.md` `+7`, `claims.md` `+84`, `plan.md` `+21`, `README.md` `+9`, `hu8` `+17`, `proposal.md` `+3`). Ninguna sección de RB-03 fue reescrita.
- La sección RB-03 de `traceability.md` (filas `SC-GOV-021/023/024` = `NOT_APPLICABLE`, líneas 316-318) está intacta; la nueva sección se añade a partir de la línea 345 y declara expresamente «La sección RB-03 inmediatamente anterior **no cambia**».
- `decisions.md` conserva GD-30/GD-31/GD-32 sin tocar; GD-33..GD-36 se añaden en una tabla nueva.

**Observación registrada, verificada y considerada aceptable:** `claims.md` recibe una inserción de 12 líneas (línea 45+) que marca como *superseded* un párrafo previo cuya afirmación en presente («esta decisión permanece pendiente de crítica y auditoría independiente») dejó de ser cierta. Es **anotación aditiva, con cero eliminaciones**: no reescribe el párrafo original, que se conserva literal, y es factualmente correcta —los artefactos que cita (`review-critic-gd12.md`, `review-audit-gd12.md`, los tres `review.json`) existen en las rutas indicadas, verificado por `ls`—. No altera el veredicto de RB-03 ni ninguno de sus artefactos. Cumple GD-30 («el registro no se reescribe»).

**Conclusión del ítem 1:** RB-03 está intacto. No lo reaudité.

### Ítem 2 — RB-04, RB-05 y RB-06 realmente cubiertos: **VERIFICADO, con un hallazgo material (F-01)**

**Existencia de los entregables portados:**
- `docs/research/scientific-closure-synthesis-2026-09-22.md` (30 877 bytes) — RB-04.
- `openspec/scientific-closure/reconciliation-2026-09-22/thesis-traceability.md` (19 622 bytes) — RB-06.
- `openspec/scientific-closure/reconciliation-2026-09-22/{reconciliation-table.md, session-identity.json}`.
- `openspec/changes/sc-06-scientific-synthesis/reviews/{README.md, review-audit-final-round1-FAIL.md, review-audit-final-round2-FAIL.md}`.

**Fidelidad del porte, contrastada contra `f355272` (alcanzable localmente, verificado con `git cat-file -t`):**

| Archivo | Fuente en `f355272` | Diferencia |
| --- | --- | --- |
| `review-audit-final-round1-FAIL.md` | `evidence-finalization-2026-09-22/reviews/review-audit-final.md` | **0 líneas** — verbatim exacto |
| `review-audit-final-round2-FAIL.md` | `…/review-audit-final-correction.md` | **0 líneas** — verbatim exacto |
| `scientific-closure-synthesis-2026-09-22.md` | misma ruta | sólo la nota de reconciliación (cabecera) y el ítem **(e)** de §5 |
| `thesis-traceability.md` | `evidence-finalization-2026-09-22/thesis-traceability.md` | sólo la nota de reconciliación y la fila **2.12** |

La preservación verbatim de los dos `FAIL` es literal, no aproximada. Las dos únicas adiciones son exactamente las que `reconciliation-table.md` declara.

**Las tres correcciones que `reconciliation-table.md` dice haber aplicado a `claims.md`, verificadas contra el original de `f355272`:**

1. **Rutas de `auxiliary/{R,N,S}/review.json`** — `f355272` escribía `auxiliary/R/review.json` a secas (líneas 134, 136, 137 de su `claims.md`); `e822f6f` escribe `sufficiency-review-2026-09-22/auxiliary/R/review.json` en CL-05, CL-07 y CL-08. **Corrección aplicada y apuntando a artefactos que existen.**
2. **Limitación de imputación causal en CL-04 y CL-08** — ausente en `f355272`, presente en `e822f6f`. **Aplicada.**
3. **CL-10 degradada** — `f355272`: `DEMOSTRADA **para su alcance exacto**`; `e822f6f`: `RESPALDADA CON LIMITACIONES, **pendiente de la auditoría única del snapshot reconciliado (RB-05)**`, y su columna de evidencia pierde la referencia a la «matriz final» y gana la declaración explícita de los dos `FAIL`. **Aplicada.**

**Contraste de citas puntuales contra sus fuentes** (cuatro comprobaciones):

- **75,96 % de cobertura** → `docs/seguimiento-tareas.md:92`: «100% en las 5 variables climáticas, **75.96% en humedad de suelo** (gaps reales del producto satelital…)». **Verificada en la fuente primaria.** También en el dossier GD-12 (líneas 113, 299, 307). ✓
- **Cifras estructurales de A/B/C** → contra `sc-03-stage-a/temporal-contract-check.json`: 2913 filas de A, 362 de B, 728 de C, P20 de C `0.300275`, P20 congelado `0.30266…`. Todas coinciden con la síntesis (líneas 78, 150, 199, 277). ✓
- **Métricas de la Etapa C** → contra `sc-05-stage-c/holdout-review.json` (lectura del registro de revisión, no del holdout): `delta_point_estimate = 0.09133252934788794` e IC `[0.0227; 0.17841825864767943]`, citados como «Δ MCC 0,0913 con IC [0,0227; 0,1784]». **Coinciden.** ✓
- **«imputación causal sólo sobre entradas y target nunca imputado (`temporal-contract-check.json`)»** → **NO se sostiene tal como está citada.** Ver hallazgo **F-01**.

**Cobertura de RB-05:** `traceability.md:367` la declara **NO CUBIERTA como `PASS` formal**, con los dos precedentes `FAIL` nombrados y la renuncia a la tercera ronda descrita sin eufemismo. Es la declaración correcta. No se acredita RB-05 en ningún lado.

### Ítem 3 — No existen sobreafirmaciones: **VERIFICADO**

**Búsqueda A** (`grep -rn "renunci"` sobre todo `openspec/` y los dos documentos de `docs/research/` tocados): siete apariciones, todas en contexto de negación explícita. Las dos más cargadas:

- `reviews/README.md:31-35`: «…declaró por escrito un veredicto de fondo `PASS_WITH_LIMITATIONS` … y **renunció expresamente a una tercera ronda** — pero ninguna tercera ronda verificó la corrección de `ND-01`/`ND-02`/`ND-03` sobre el snapshot final `f355272`. Esta reconciliación trata esa renuncia como lo que es —una limitación declarada por el propio auditor— y no como un tercer `PASS`.»
- `decisions.md` GD-34: «Presentar esa renuncia como sustituto de un `PASS`, o presentar un `FAIL` como aprobación, es precisamente lo que el responsable prohibió.»

**Búsqueda B** (`grep` de `PASS_WITH_LIMITATIONS` aplicado a `SC-GOV-025`/`GF` en todo el snapshot): las únicas apariciones que asocian ese valor a esos dos identificadores son **descripciones del estado de `f355272` que se declara descartado** (`reconciliation-table.md:47`, `decisions.md` GD-34). Ninguna lo afirma como estado vigente.

No encontré un solo pasaje que presente los `FAIL` como aprobación, ni la renuncia como `PASS`.

### Ítem 4 — El estado `PENDIENTE` de `GF`/`SC-GOV-025` se deriva de evidencia vigente: **VERIFICADO**

- **`changes.json`**: `sc-06-scientific-synthesis` = `"IN_PROGRESS"`, **no** `PASS`; `"audit": null`. Su `gate_evaluation` concluye textualmente: «Gate satisfecho para HABILITAR el trabajo documental. **No implica PASS del change**: SC-GOV-025 exige además "ningún obligatorio sin resolver", y RB-05 … no tiene todavía un veredicto formal PASS sobre ningún snapshot.»
- **`traceability.md:368`**: `SC-GOV-025` = **`PENDIENTE`**, con el desglose de sus cinco términos de aceptación y la identificación precisa del único incumplido («ningún obligatorio sin resolver»). **No** dice `PASS_WITH_LIMITATIONS`.
- **`traceability.md:369`**: gate `GF` = **`PENDIENTE, no evaluable como PASS todavía`**.
- **`plan.md:90`**: `GF Cierre` = **`PENDIENTE`**.
- **`claims.md:157`**: `CL-10` = `RESPALDADA CON LIMITACIONES, pendiente de la auditoría única`. **No** `DEMOSTRADA`.
- **`README.md:37`**: «**`SC-GOV-025` y `GF` siguen `PENDIENTE`**».

El fundamento del `PENDIENTE` es verificable y verdadero: la inexistencia de un `PASS` formal de RB-05, que comprobé de forma independiente leyendo los veredictos de los dos informes preservados y constatando que no existe un tercero.

**Comprobación adicional de coherencia con la gobernanza del repositorio:** `e822f6f` **no está publicado** (`git branch -r --contains e822f6f` vacío; `origin/feat/scientific-closure` sigue en `1c33aad`). Consistente con `session-identity.json` y con la regla «sin push» de `AGENTS.md`.

### Ítem 5 — Limitación de imputación causal (~24 %) declarada donde corresponde: **VERIFICADO en los cuatro lugares; la aclaración sobre A/B/C/H tiene el defecto F-01**

| Ubicación declarada | Verificación |
| --- | --- |
| `hu8-resultados-discusion-conclusiones.md` §8.4 | Líneas 213-228: bloque «Adición 2026-09-22 (amenaza a la validez incorporada, no un hallazgo nuevo)», con 75,96 %, ~24 %, `causal_ffill`, «atraviesa las ocho configuraciones formales por igual, sin control experimental» ✓ |
| `claims.md` CL-04 | Línea 151, columna de prohibiciones: «citar cualquier configuración de esa referencia sin declarar que ~24 % de sus días de humedad son huecos imputados con `causal_ffill`» ✓ |
| `claims.md` CL-08 | Línea 155: «presentar la referencia v3 como un régimen "limpio" de mediciones: ~24 % de sus días de humedad están imputados con `causal_ffill`, sin caracterizar» ✓ |
| Síntesis `scientific-closure-synthesis-2026-09-22.md` | §5, ítem **(e)**, líneas 254-266 ✓ |
| `thesis-traceability.md` fila **2.12** | Línea 61, con fuente, resultado utilizable, afirmación permitida y límite obligatorio ✓ |

**Las dos aclaraciones negativas exigidas, verificadas:**
- **No se declara que S se ejecutó ni que existe evidencia de robustez.** `hu8` §8.4: «No se afirma por este hecho que exista evidencia de robustez ante sensores ausentes, ni que el complemento S se haya ejecutado: **no se ejecutó**.» `traceability.md:379-381` y la fila 2.12 repiten la negación. ✓
- **Se aclara que no afecta a la campaña A/B/C/H (Pergamino).** Presente en síntesis §5(e), `traceability.md:379-381` y `decisions.md` GD-35. **La aclaración es sustantivamente correcta —y de hecho conservadora— pero su cita es defectuosa: ver F-01.**

### Ítem 6 — Ningún `FAIL` presentado como `PASS`: **VERIFICADO, con dos búsquedas distintas**

**Búsqueda 1 — etiquetado de los informes.** Los nombres de archivo llevan el veredicto (`…-round1-FAIL.md`, `…-round2-FAIL.md`). La tabla de `reviews/README.md` los consigna en una columna «Veredicto» como `FAIL` — tres hallazgos materiales en la ronda 1, uno nuevo introducido por la propia corrección en la ronda 2 — y antepone una «Advertencia expresa»: «Estos dos `FAIL` **no se presentan aquí, ni en ningún artefacto de esta rama, como aprobación independiente**.»

**Búsqueda 2 — lenguaje de aprobación** (`grep -rni "aprobad|ratific|avalad|convalidad|auditoría favorable|validado por la auditoría|superó la auditoría"` sobre todos los archivos tocados, excluidos los dos informes preservados): **ninguna** de las coincidencias aplica lenguaje de aprobación a `f355272`. Todas son usos ajenos («alcance aprobado», «imagen aprobada», «fixtures aprobados», «hipótesis aprobada»).

**Búsqueda 3 — cada mención de `f355272` y su calificativo** (23 apariciones): todas van acompañadas de «descartar», «historia», «dos rondas … `FAIL`», «no se presenta como aprobación», o son referencias neutras de procedencia del porte. Ninguna lo presenta como validación.

Adicionalmente, `tasks.md` mantiene **T25 sin marcar** con la nota: «Las dos rondas … terminaron en veredicto formal `FAIL`; ninguna tercera ronda verificó la corrección final, y esta reconciliación **no** trata la renuncia del auditor a esa tercera ronda como un `PASS`.»

### Comprobaciones mecánicas (no sustituyen el juicio de suficiencia — `SC-GOV-020`)

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src …/venv-v4/bin/python -m pytest \
  tests/test_scientific_closure_governance.py tests/test_scientific_closure_checker.py -q -p no:cacheprovider
→ 48 passed, 14 subtests passed in 1.42s

PYTHONPATH=src …/venv-v4/bin/python scripts/check_scientific_closure.py
→ scientific-closure checker: PASS (estructura; runtime no verificado)
```
**No los tomo como evidencia de suficiencia.** Sólo acreditan que la transición de `sc-06` a `IN_PROGRESS` es admisible para la tabla de transiciones y que la estructura OpenSpec es válida.

---

## Hallazgos

### F-01 — MATERIAL — Cita atribuye a `temporal-contract-check.json` una verificación que ese artefacto no contiene, y traslada a v4 una propiedad de contrato que es de v3

- **Ubicaciones:**
  - `docs/research/scientific-closure-synthesis-2026-09-22.md:254-258` (§5, ítem (e)) — **introducida por esta reconciliación**, es la única adición propia a la síntesis.
  - `openspec/scientific-closure/decisions.md`, GD-35 — «el contrato de A/B/C/H declara imputación causal sólo sobre entradas y target nunca imputado, **verificado en `temporal-contract-check.json`**». Formulación más fuerte y la menos sostenida.
  - `openspec/scientific-closure/reconciliation-2026-09-22/thesis-traceability.md:51`, fila 2.2 — **heredada verbatim de `f355272`**, no introducida aquí.
  - `openspec/scientific-closure/traceability.md:379-381` — misma afirmación sin cita.

- **Esperado:** que el artefacto citado contenga la verificación que se le atribuye («imputación causal sólo sobre entradas», «target observado a t+3 no imputado»).

- **Observado:** volqué el artefacto completo (2 686 bytes, `sc-03-stage-a/temporal-contract-check.json`). **No contiene ningún campo ni comprobación sobre imputación.** Su contenido es: `feature_contract` (ocho variables, lags, ventanas, `verified_identical: true`), `stage_windows`, `nested_cv`, `p20_by_stage`, cinco `leakage_checks` y `verdict: PASS`. Los cinco `leakage_checks` cubren (1) ninguna fecha ≥ 2023-01-01 en A, (2) ninguna fecha de 2024-25 en B, (3) P20 de C no contaminado, (4) invariante causal `max(target_train) < min(feature_validation)`, (5) horizonte t+3 constante en las 728 filas de C. **Ninguno es un control de imputación.**

  Dos matices que registro en favor del texto auditado: el artefacto declara `requirement_ids: ["SC-GOV-010"]` con `verdict: PASS`, y la **norma** de `SC-GOV-010` (`requirements.json:97`) sí dice «…target observado t+3, P20 train, **imputación causal solo de entradas** y fit fold-local». Pero el **criterio de aceptación** del propio `SC-GOV-010` omite la imputación («No se agregan ni generan features fuera de etapa autorizada; max target train < min emisión validación; ocho features iguales entre candidatos»), y el artefacto no itemiza esa comprobación. La cita convierte una **norma declarada** en una **verificación registrada**, que es una inferencia que completa evidencia faltante.

  Además, contrasté el sustrato en el código: `"imputation": "causal_ffill"` vive en `src/predictive_modeling/contract.py:71`, cuyo `PIPELINE_VERSION = "controlled_daily_v3"` — **es el contrato de v3**. El runner de v4 (`src/experiment_runner/controlled_daily_v4/`) **no declara ningún campo `imputation`** (grep sin resultados) y, lejos de imputar, **aborta**: `features.py:143` — «Nunca repara ni imputa: reporta y aborta con un diagnóstico preciso»; `ingestion.py:118` — «No imputa días con menos de 24 observaciones». `validate_continuous_daily_calendar` lanza `CalendarIntegrityError` ante cualquier hueco del calendario diario.

- **Dirección del error y por qué no lo clasifico como sobreafirmación:** el defecto es **conservador**. La garantía real de v4 (exigir calendario diario completo y abortar) es **más fuerte** que la enunciada («imputación causal sólo sobre entradas»). La conclusión que la frase sostiene —que el ~24 % de imputación de v3 **no contamina** A/B/C/H— es **correcta y está mejor respaldada de lo que el texto dice**. No infla ningún resultado, no toca ningún estado de compuerta y no habilita ninguna afirmación adicional. Por eso **no** activa los ítems 3 ni 6 de mi alcance.

- **Por qué aun así es material:** `AGENTS.md` prohíbe «completar evidencia faltante mediante inferencias», y este repositorio ya sancionó con dos `FAIL` el mismo **género** de defecto —el registro afirma lo que el artefacto citado no dice—. La diferencia de **especie** es la que me impide llevarlo a `FAIL`: allá la afirmación era falsa, autointeresada y fijaba `SC-GOV-025` sobre una auditoría inexistente; acá es verdadera en sustancia, conservadora en dirección y no sostiene ningún estado.

- **Remediación propuesta (documental, sin recómputo):** sustituir la cita por la fuente que sí lo sostiene. Por ejemplo, en §5(e) y en GD-35: «la campaña A/B/C/H **no imputa**: el runner de v4 exige calendario diario completo y aborta ante huecos (`controlled_daily_v4/features.py::validate_continuous_daily_calendar`, `ingestion.py::aggregate_era5_daily`); `causal_ffill` es una propiedad del contrato de **v3** (`predictive_modeling/contract.py`, `PIPELINE_VERSION = controlled_daily_v3`)». Corregir en la fila 2.2 de `thesis-traceability.md` el reparto entre lo que `temporal-contract-check.json` verifica (contrato de ocho features, ventanas, P20 en train, cinco controles de fuga) y lo que sólo está **declarado** en la norma de `SC-GOV-010`. **Esta corrección es obligatoria antes de que `SC-GOV-025` o `GF` se muevan de `PENDIENTE`.**

### OBS-01 — MENOR — `reviews/README.md` tabula un informe que todavía no existe

- **Ubicación:** `openspec/changes/sc-06-scientific-synthesis/reviews/README.md:44`.
- **Observado:** la tabla «Auditoría de esta reconciliación» lista `review-audit-reconciliation.md`, archivo **ausente** del directorio en este snapshot (`ls` muestra sólo `README.md` y los dos `…-FAIL.md`).
- **Por qué NO reincide en el defecto que causó el primer `FAIL` de `f355272`:** la columna «Veredicto» dice «**Ver el archivo**», no prejuzga resultado alguno, y **ningún estado se fija sobre esa base** (`SC-GOV-025` y `GF` siguen `PENDIENTE`). Lo señalo porque, en este snapshot, la fila nombra un archivo inexistente sin marcarlo como pendiente.
- **Remediación:** añadir «(pendiente al 2026-09-22)» en la fila, o dejar que se resuelva sola al preservarse este informe en esa ruta. **Se autoextingue.**

### OBS-02 — MENOR — T08 y T16 marcadas `[x]` con su artefacto de evidencia declarado inexistente

- **Ubicación:** `openspec/changes/sc-06-scientific-synthesis/tasks.md`, líneas 8-9.
- **Observado:** T08 declara evidencia `audit.json` y T16 declara `claim-evidence-review.json`. Ninguno de los dos existe para `sc-06`. Las notas al pie **lo dicen explícitamente** («No hay `audit.json` propio de `sc-06`: la evidencia vive distribuida en esas rutas»; «No hay `claim-evidence-review.json` separado en esta reconciliación»).
- **Valoración:** la divulgación es honesta y desactiva el riesgo de lectura engañosa; el preámbulo del archivo advierte además que «Marcar una tarea **no** acredita suficiencia científica». Aun así, la casilla marcada dice más que la nota que la matiza, para quien lea sólo la lista.
- **Remediación:** trasladar el calificativo a la propia casilla (p. ej. `[x] T08 … (evidencia distribuida; sin audit.json propio)`), o producir los dos artefactos.

### OBS-03 — PROCESO — Intervengo como REVIEW-5 sin que REVIEW-3 ni REVIEW-4 hayan corrido sobre este snapshot

- **Ubicación:** `tasks.md`, líneas 13-14 (`[ ] REVIEW-3 evidence_checker`, `[ ] REVIEW-4 scientific_critic`).
- **Observado:** el propio `tasks.md` declara que «REVIEW-3 y REVIEW-4 no corrieron como pasadas separadas en ninguna de las dos ramas de origen», y que REVIEW-1/REVIEW-2 los ejecutó el orquestador «sin rol separado».
- **Norma aplicable:** `AGENTS.md` — «scientific_critic intenta refutar criterios sin modificar el cambio» y «**scientific_auditor independiente interviene después de superar las críticas**».
- **Consecuencia:** el snapshot reconciliado **no pasó por una crítica adversarial independiente**. Yo soy el primer lector independiente que lo mira, y mi alcance fue acotado a seis ítems. Esto es una desviación declarada del orden de revisión, no un defecto oculto, pero **limita lo que mi veredicto puede descargar** y es una de las razones por las que no recomiendo `PASS` de change. Contrasta, para peor, con RB-03, que sí tuvo crítica (7 hallazgos materiales) **y** auditoría en sesiones separadas.

---

## VEREDICTO

# **PASS**

**Sobre qué recae este `PASS`, literalmente:** sobre los **seis ítems del alcance que se me fijó**. Verifiqué que `e822f6f` deja RB-03 intacto; que RB-04 y RB-06 están cubiertos por entregables que existen, portados con fidelidad verificada y con las tres correcciones declaradas efectivamente aplicadas; que RB-05 se declara **no cubierto**; que `SC-GOV-025`, `GF`, `sc-06` y `CL-10` no se sobredeclaran; que no hay una sola sobreafirmación ni un solo `FAIL` presentado como aprobación; y que la limitación de imputación causal está declarada en los cuatro lugares comprometidos, con sus dos negaciones expresas. La reconciliación hace lo que su tabla dice que hace.

**Sobre qué NO recae, y no puede recaer:**

1. **No descarga RB-05 ni T25.** No realicé una auditoría requisito por requisito sobre los 25 requisitos: eso quedó fuera de mi alcance por instrucción. Un `PASS` de alcance acotado **no es** la auditoría final que exige `SC-GOV-025`.
2. **No es cierre científico.** `SC-GOV-020` es explícito: ningún `PASS` estructural equivale a cierre científico. Los 48 tests verdes y el checker en `PASS` no aportan nada a esta conclusión y así los traté.
3. **No ratifica el contenido de RB-03** —no lo reabrí— **ni los hashes y métricas de A/B/C/H** —no los recomputé—.
4. **Queda condicionado a la corrección de F-01**, que es obligatoria antes de cualquier movimiento de `SC-GOV-025` o `GF`.

### Estados que recomiendo

| Objeto | Estado recomendado | Fundamento |
| --- | --- | --- |
| **`SC-GOV-025`** | **`PENDIENTE`** — sin cambio | Su quinto término de aceptación, «ningún obligatorio sin resolver», **sigue incumplido**: T25 está sin marcar y mi auditoría, por alcance instruido, no fue requisito por requisito. El `PENDIENTE` que el snapshot propone es correcto y **confirmo que se deriva de evidencia vigente y verificable**. |
| **Gate `GF`** | **`PENDIENTE`** — sin cambio | Su condición de avance es el `PASS` de un auditor final sobre la suficiencia del alcance **completo**. Este informe no lo es. |
| **`sc-06-scientific-synthesis`** | **`IN_PROGRESS`** — **no `PASS`** | Tres razones acumulativas: (a) T25 sigue abierta y mi alcance no la descarga; (b) REVIEW-3 y REVIEW-4 nunca corrieron sobre este snapshot (OBS-03), y `AGENTS.md` sitúa al auditor *después* de las críticas; (c) F-01 pendiente de corrección. `CLOSE` exige `PASS` y `PASS` no existe. |
| **`sc-07` / `sc-09` / `sc-10`** | **`BLOCKED`** — sin cambio | Verificado byte-idénticos. No se tocan. |
| **`CL-10`** | `RESPALDADA CON LIMITACIONES` — sin cambio | Correcta mientras RB-05 siga sin `PASS`. |

**Camino más corto hacia un `GF` legítimo, si se quiere recorrer:** corregir F-01 (documental, sin recómputo); correr una pasada de `scientific_critic` sobre el snapshot corregido; y encargar entonces una auditoría final **requisito por requisito** sobre los 25 requisitos, que es la única que puede descargar `SC-GOV-025`. Ninguno de los tres pasos exige reabrir el holdout ni reejecutar A, B, C, H, R, N o S.

---

## Limitaciones de esta revisión

1. **Degradación de rol.** Los perfiles de `.codex/agents` no son cargables en este runtime; actué como subagente de Claude Code (Opus 5) en contexto separado, sustitución ya registrada en `session-identity.json`. El modo de solo lectura fue **instruido, no impuesto por el harness**: mi cumplimiento es declarado, no forzado.
2. **Alcance acotado por instrucción.** Seis ítems. No auditoría requisito por requisito. No recomputé hashes, ni las 72 métricas de H, ni el contenido de RB-03. Un defecto que viva exclusivamente en esas zonas **no habría sido detectado por mí**.
3. **Contraste de citas por muestreo, no exhaustivo.** Verifiqué cuatro citas (75,96 %; cifras estructurales de A/B/C; métricas de la Etapa C; el contrato temporal). La cuarta falló, lo que sugiere que un contraste exhaustivo de la síntesis y de `thesis-traceability.md` —536 y 132 líneas— podría revelar más defectos del mismo género. **No afirmo que F-01 sea el único.**
4. **Verificación de intactitud, no de corrección, sobre RB-03.** Acredito que no fue tocado. No acredito que sea correcto: eso lo acredita su propio auditor, cuyo informe no revisé.
5. **`f355272` comparado desde el repositorio local.** El commit es alcanzable localmente (`git cat-file -t` → commit) y los diffs se hicieron contra él. No verifiqué contra la copia remota de GitHub del PR #211.
6. **Conclusión que no extraigo.** Que la evidencia sea científicamente suficiente para HU7/HU8. No me fue preguntado, no lo evalué, y este informe no debe citarse en ese sentido.
