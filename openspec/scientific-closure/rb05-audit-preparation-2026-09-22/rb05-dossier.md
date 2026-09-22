# Dossier RB-05 — preparación de la auditoría final requisito por requisito

Sesión `rb05-audit-preparation-2026-09-22`. Snapshot de entrada `22da0dd`,
rama `feat/scientific-closure-final-main`, árbol limpio. HEAD contiene
`origin/main` (`2079d03`) y `origin/feat/scientific-closure` (`0ebd5bc`).
Autoridad: instrucción explícita del responsable, sesión del 2026-09-22.

**Versión 2, corregida tras la auditoría independiente Codex sobre `88ced62`
(round 1, veredicto `FAIL`, informe verbatim en
`reviews/review-audit-codex-round1-FAIL.md`).** La versión 1 de este
documento (commit `88ced62`) proponía PASS/PASS_WITH_LIMITATIONS para los 25
requisitos sin hallazgos materiales pendientes. La auditoría encontró cuatro
hallazgos materiales (M-01..M-04); el §3 de abajo incorpora las
correcciones, marcadas en línea, sin borrar lo que la versión 1 decía sobre
cada fila — se preserva la versión 1 leyendo el commit `88ced62`. **El más
severo, M-01, es un incumplimiento histórico verificado y no reparable
documentalmente** en la secuencia de gates A→B→C (`decisions.md` GD-38,
`risks.md` RK-20): éste, y no la falta de auditoría, es ahora la razón por la
que `SC-GOV-025` y `GF` siguen `PENDIENTE`.

**Qué es este documento.** La preparación del dossier que la sección
"Auditoría independiente única solicitada" de
`traceability.md:389-396` pide para RB-05: la auditoría final **requisito por
requisito sobre los 25 SC-GOV**, que a esta fecha nunca ocurrió sobre el
snapshot posterior a la campaña (las dos auditorías disponibles con ese
alcance, sobre `f355272`, terminaron en `FAIL`, ver
`openspec/changes/sc-06-scientific-synthesis/reviews/review-audit-final-round{1,2}-FAIL.md`).
Reúne, para cada uno de los 25 requisitos, el estado documental vigente y su
evidencia exacta, walking a través de las cuatro capas de actualización que
`traceability.md` fue acumulando el 2026-09-21 y el 2026-09-22, sin duplicar
una quinta tabla independiente de las que ya existen.

**Qué NO es este documento.**

- No es la auditoría final independiente. Es su insumo. El veredicto
  PASS/FAIL/BLOCKED sobre RB-05 lo emite el auditor externo (Codex), no esta
  sesión.
- No cambia `SC-GOV-025` ni el gate `GF`, que siguen `PENDIENTE` exactamente
  como los dejó la reconciliación (`traceability.md:368-369`, `plan.md:90`).
- No transiciona `sc-06-scientific-synthesis` en `changes.json`.
- No reabre ni reaudita RB-03 (`sufficiency-review-2026-09-22/`), RB-04
  (`docs/research/scientific-closure-synthesis-2026-09-22.md`) ni RB-06
  (`reconciliation-2026-09-22/thesis-traceability.md`). Se citan como
  evidencia intocada.
- No ejecuta A, B, C, H, R, N ni S. No abre el holdout. No recomputa hashes ni
  métricas: reutiliza íntegramente lo ya verificado por las auditorías
  preservadas.

## 1. Método

Fuente jerárquica, de más antigua a más reciente, en `traceability.md`: (a)
tabla base y sección "Estado por requisito — 2026-09-21 (CAMPAÑA A → B → C
EJECUTADA)" (líneas 46-88) — **es la más reciente para SC-GOV-001..020**, ver
§2 sobre por qué no la desplaza la sección "Actualización por integración de
`origin/main`" que aparece más abajo en el archivo; (b) "Estado por requisito
— 2026-09-21, complemento H" (líneas 259-305), que supersede 022 y 025; (c)
"Estado por requisito — 2026-09-22, decisión de suficiencia GD-12 (RB-03)"
(líneas 307-347), que supersede 021, 023 y 024; (d) "Estado por requisito —
2026-09-22, reconciliación RB-04/05/06" (líneas 349-397), que supersede 016,
025 y el gate GF. Cada fila de la tabla del §3 cita la capa que efectivamente
la fija hoy, no la primera que menciona el requisito.

## 2. Discrepancia documental resuelta: orden de las secciones fechadas 2026-09-21

`traceability.md` contiene, en este orden de lectura, dos secciones con
estados aparentemente contradictorios para `SC-GOV-002`, `SC-GOV-003` y
`SC-GOV-009`:

- Línea 46: "Estado por requisito — 2026-09-21 (CAMPAÑA A → B → C
  EJECUTADA)", que da PASS a los tres.
- Línea 222: "Actualización por integración de `origin/main` — 2026-09-21",
  que dice "SC-GOV-002 sigue `BLOCKED`", "SC-GOV-003 sigue
  `PASS_WITH_LIMITATIONS`" y "SC-GOV-009 sigue `BLOCKED`".

**Resolución, con evidencia, no por orden de lectura del archivo.** La
sección de la línea 222 anota explícitamente que corrige hechos de "las filas
anteriores" y que "no cambia el estado de ningún requisito" — es decir,
describe el estado que esas filas tenían **antes** de que la campaña se
ejecutara, en el momento en que sólo se había integrado `origin/main` (PR
#206) y la campaña todavía no corría. La prueba más directa está en la propia
sección: se autodescribe diciendo "No se ejecutó A, B ni C, no se abrió el
holdout 2024–2025 y no se inicializó el ledger definitivo"
(`traceability.md:256`), lo que es incompatible con haber sido escrita
después de la campaña. Esto es consistente con `next-session.txt`, que
preserva como texto histórico superseded la versión del 2026-09-21 anterior
a la campaña, y que declara expresamente: "el merge de integración no movió
ningún estado de requisito ni de change". La resolución real de
`SC-GOV-009` (identidad ejecutable, GD-25/RK-09) está documentada con
detalle **sólo** en `current-execution-checkpoint.md:43-55`, que se declara
a sí mismo vigente y que **explícitamente nombra y supersede** "la de
«2026-09-21, integración de `origin/main`»" como registro histórico. La
sección de la línea 46 de `traceability.md`, que ya da PASS a los tres
requisitos citando esa misma resolución de GD-25/RK-09 e identidad
`214735e`/`37eed42`, es por tanto la que refleja el estado **posterior** a la
campaña, pese a aparecer antes en el archivo. La reconciliación de
`reconciliation-2026-09-22/reconciliation-table.md:48` confirma esta lectura
para el resto de la matriz: dice que las filas `SC-GOV-001..020` (salvo 016)
"ya están en la sección vigente de `65ca852` (posterior a H, 2026-09-21) con
los mismos valores" — es decir, la de la línea 46 de `traceability.md`, no la
de la línea 222.

**Corrección tras la crítica independiente (hallazgo material M-01).** La
versión anterior de este párrafo atribuía la frase de
`reconciliation-table.md:48` a `traceability.md:349` ("la sección
RB-04/05/06"), que no contiene esa frase ni la cadena `65ca852`. Es el mismo
defecto de cita mal atribuida que `F-01`/`AUD-F-01` documentaron en sesiones
anteriores. La conclusión no cambia — se sostiene con evidencia
independiente, incluida la autodescripción de `traceability.md:256` citada
arriba, que el crítico verificó por su cuenta — pero la cita se corrige a su
fuente real.

**Conclusión operativa:** `SC-GOV-002`, `SC-GOV-003` y `SC-GOV-009` son
`PASS`, con la sección de línea 46 y `current-execution-checkpoint.md:33-55`
como evidencia primaria; la sección de línea 222 se cita únicamente como
historia superseded. El auditor único debería confirmar esta lectura por su
cuenta, no aceptarla sobre la palabra de este dossier.

## 3. Los 25 requisitos SC-GOV

| ID | Estado | Evidencia exacta | Limitación / nota |
| --- | --- | --- | --- |
| SC-GOV-001 | PASS | `traceability.md:57` | — |
| SC-GOV-002 | PASS | `traceability.md:58`; ver §2 para la sección superseded | Condiciones 1 (parcial), 2 (parcial) y 3 de ADR-0011 no cambian (`traceability.md:236`) |
| SC-GOV-003 | ~~PASS~~ **PASS_WITH_LIMITATIONS (corregido, M-04)** | `traceability.md:59`; `current-execution-checkpoint.md:33-55`; ver §2. **Corrección:** `traceability.md`, sección 2026-09-22 (M-01..M-04), fila `SC-GOV-003`; `decisions.md` GD-39 | `src/` es byte-idéntico a `origin/main`, no a `214735e` directamente; la distinción identidad ejecutable/documental está declarada, no oculta. **Agregado:** el criterio textual incluye «no push ... sin encargo futuro explícito»; `RK-14` (dos pushes de preparación) sigue abierto y no subsanado, mismo tratamiento que ya tenía `SC-GOV-019` |
| SC-GOV-004 | PASS | `traceability.md:60` | — |
| SC-GOV-005 | PASS_WITH_LIMITATIONS | `traceability.md:61`; reconfirmado por `claims.md:113` "Clasificación final de afirmaciones — 2026-09-22", filas CL-06 (`claims.md:88`) y CL-10 (`claims.md:92,157`) | CL-10 declara su último término ("trazabilidad y límites") cubierto por RB-06, y queda **pendiente de esta misma auditoría RB-05** para el término "H auditado" + terminal — es decir, RB-05 es simultáneamente objeto y, en parte, insumo de esta fila; no se cierra el círculo aquí |
| SC-GOV-006 | PASS_WITH_LIMITATIONS | `traceability.md:62`; `decisions.md` GD-17 (sustitución `.codex/agents` declarada) | Perfiles nominales no cargables en este runtime; sustitución documentada, no presentada como equivalencia |
| SC-GOV-007 | ~~PASS~~ **No sostenido (M-01)**, pendiente de decisión del responsable | `traceability.md:63`. **Corrección:** sección 2026-09-22 (M-01..M-04); `decisions.md` GD-38; `risks.md` RK-20 | `changes.json` acredita, para `sc-04`/`sc-05`, autorizaciones que citan el `PASS` de la etapa previa antes de que ese `PASS` existiera en el propio registro — verificado por dos fuentes primarias independientes (contenido de `changes.json` y marcas de tiempo de sistema de archivos de los `gate-review.json`) |
| SC-GOV-008 | ~~PASS~~ **No sostenido (M-02)**, pendiente de remediación | `traceability.md:64`. **Corrección:** `sc-06-scientific-synthesis/tasks.md` T08, desmarcada 2026-09-22 | La cadena de revisión independiente que debía acreditar T08 no cubre el hallazgo M-01 |
| SC-GOV-009 | PASS | `traceability.md:65`; `current-execution-checkpoint.md:43-55` (resolución explícita GD-25/RK-09, dos auditores independientes); ver §2 | `RK-19` (docstring falso en `controlled_daily_v4/__init__.py`) sigue abierto como riesgo menor, remitido a un change propio (`next-session.txt`); no afecta esta identidad porque no es uno de los siete archivos con delta numérico-neutro clasificado |
| SC-GOV-010 | PASS | `traceability.md:66` | — |
| SC-GOV-011 | PASS | `traceability.md:67` | `SIN_GANADOR_ESTABLE`, desempate por simplicidad; no se presenta como superioridad |
| SC-GOV-012 | Resultado científico sostenido; **secuencia de gate no sostenida (M-01)** | `traceability.md:68`. **Corrección:** sección 2026-09-22 (M-01..M-04) | `CANDIDATE_VALIDATED` por no inferioridad, el IC pareado incluye el cero — esto se sostiene. Lo que no se sostiene: el criterio exige «tras gate A», y B se ejecutó (`03:51:13`) antes de que el veredicto de auditoría de A existiera en disco (`04:23:00`) |
| SC-GOV-013 | PASS | `traceability.md:69` | — |
| SC-GOV-014 | Resultado científico sostenido; **secuencia de gate no sostenida (M-01)** | `traceability.md:70`. **Corrección:** sección 2026-09-22 (M-01..M-04) | Apertura única, nominal e irreversible del holdout 2024-2025; no se reabre — esto se sostiene. Lo que no se sostiene: el criterio exige que C «requiera B validada», y C se ejecutó (`04:06:10`) antes de que el veredicto de auditoría de B existiera en disco (`04:23:35`) |
| SC-GOV-015 | PASS_WITH_LIMITATIONS | `traceability.md:71` | Sin corrección por multiplicidad; ~24 unidades efectivas en C |
| SC-GOV-016 | PASS_WITH_LIMITATIONS | `traceability.md:364` (capa RB-04/05/06, supersede la fila `:72`) | Revisión documental de la síntesis contra `claims.md` y métricas ya recomputadas; no recomputa métricas nuevas; pendiente de verificación por esta misma auditoría única |
| SC-GOV-017 | PASS_WITH_LIMITATIONS | `traceability.md:73` | Condición 2 de ADR-0011 (licencia NASA POWER) sigue `PENDING_CONFIRMATION`, aceptada como limitación vía GD-13; fecha de adquisición `UNKNOWN`, no inventada |
| SC-GOV-018 | PASS | `traceability.md:74` | — |
| SC-GOV-019 | PASS_WITH_LIMITATIONS | `traceability.md:75`; `decisions.md` GD-19; `risks.md` RK-14 | ADR-0011 declara expresamente que la ratificación de RK-14 **no subsana** el incumplimiento de los dos push en preparación; no existe artefacto que lo cure, por lo que no puede declararse PASS pleno |
| SC-GOV-020 | PASS | `traceability.md:76` | — |
| SC-GOV-021 | NOT_APPLICABLE | `traceability.md:316` (capa RB-03) | Límites permanentes de afirmación (no MAE/RMSE, no valor continuo de humedad); `sc-07-aux-regression` permanece `BLOCKED` con `applicability_decision`, no se reabre |
| SC-GOV-022 | PASS_WITH_LIMITATIONS | `traceability.md:267` (capa complemento H, supersede la fila `BLOCKED` original) | RECHAZO y recalibración sucesiva no ejercitados; cegamiento parcial declarado; `INV-10` y la reproducción estricta 18/18 no verificados de forma independiente por ninguna auditoría a la fecha |
| SC-GOV-023 | NOT_APPLICABLE | `traceability.md:317` (capa RB-03) | Prohibido afirmar detección reservada de corrupciones con cifra alguna; `sc-09-aux-anomalies` permanece `BLOCKED`, no se reabre |
| SC-GOV-024 | NOT_APPLICABLE bajo el límite expreso de CL-08 | `traceability.md:318` (capa RB-03) | **Cláusula de reapertura vinculante:** S vuelve a `REQUIRED` si la síntesis (RB-04) enuncia cualquier resultado de robustez. Verificado en esta sesión (§4): la síntesis y la reconciliación tratan el ~24 % de imputación `causal_ffill` explícitamente como amenaza a la validez, no como evidencia de robustez (`traceability.md:371-387`, `decisions.md` GD-35); la cláusula **no se activa** |
| SC-GOV-025 | PENDIENTE — no se declara PASS_WITH_LIMITATIONS ni BLOCKED | `traceability.md:368` (capa RB-04/05/06) | De los cinco términos de aceptación, cuatro cubiertos; "ningún obligatorio sin resolver" exige el PASS formal de RB-05, que este dossier prepara pero no otorga. **No se toca en esta sesión** |

**RB-05 en sí (el entregable, no una fila SC-GOV):** no cubierto como PASS
formal. Dos rondas de auditoría sobre el snapshot `f355272` terminaron en
`FAIL` documental (defectos de sobreafirmación, no numéricos); la renuncia
del auditor de la ronda 2 a una tercera ronda no se trata como PASS
(`traceability.md:367`, `decisions.md` GD-34). **Esta versión 2 del dossier
sí recibió su auditoría única, sobre `88ced62`, y también terminó en `FAIL`**
(`reviews/review-audit-codex-round1-FAIL.md`), esta vez por una contradicción
cronológica comprobada (M-01), no por sobreafirmación documental.

**Gate GF:** `PENDIENTE`, no evaluable como PASS (`plan.md:90`,
`traceability.md:369`). El hallazgo M-01 no exige reabrir el holdout ni
reejecutar A, B, C, H, R, N o S — es un defecto de gobernanza del proceso de
gates, no de los resultados científicos que ese proceso produjo.

## 4. Verificación de la cláusula de reapertura de SC-GOV-024

La decisión RB-03 (`traceability.md:318`) condiciona `SC-GOV-024` a que la
síntesis científica (RB-04) no enuncie "ningún resultado de robustez". Se
verificó contra la reconciliación RB-04/05/06 (`traceability.md:371-387`),
que declara explícitamente: "**No** se afirma que S se haya ejecutado ni que
exista evidencia de robustez ante mediciones ausentes; la campaña A/B/C/H
(Pergamino, no Melchor Romero) **no imputa**". Esta declaración es la
corrección introducida por el hallazgo `F-01` de la auditoría de
reconciliación (`decisions.md` GD-37) y fue verificada por ese auditor por
contraste directo con el código fuente. No se detectó, en las secciones de
`traceability.md` citadas en este dossier ni en `decisions.md` GD-33..GD-37,
ninguna otra afirmación de robustez que la síntesis introduzca. Esta
verificación no sustituye una lectura línea por línea de las 552 líneas de
`docs/research/scientific-closure-synthesis-2026-09-22.md`; el auditor único
puede considerar necesario hacerla.

## 5. Recuento

**Recuento de la versión 1 (commit `88ced62`, antes de esta auditoría): PASS
14, PASS_WITH_LIMITATIONS 7, NOT_APPLICABLE 3, PENDIENTE 1 (SC-GOV-025) = 25.**
Reconstrucción, no una tabla nueva independiente: la base post-campaña da
14/6/5/0 (`traceability.md:83`); el complemento H mueve `SC-GOV-022` de
`BLOCKED` a `PASS_WITH_LIMITATIONS` → 14/7/4/0; RB-03 mueve `SC-GOV-021`,
`SC-GOV-023` y `SC-GOV-024` de `BLOCKED` a `NOT_APPLICABLE` → 14/7/1/3, donde
el 1 `BLOCKED` remanente es `SC-GOV-025`; la reconciliación RB-04/05/06
relabela ese remanente de `BLOCKED` a `PENDIENTE` (no lo resuelve, sólo
corrige la causa citada) sin mover `SC-GOV-016`, que sigue
`PASS_WITH_LIMITATIONS` con nueva base documental. Este recuento reproduce el
que reconstruyó por su cuenta el auditor de la ronda 2 de `f355272`
(`review-audit-final-round2-FAIL.md`, §3 F-04: "14/7/4 ... 12/10/3/0"), con
una diferencia deliberada: aquella ronda avanzó `SC-GOV-025` a
`PASS_WITH_LIMITATIONS` (de ahí su 12/10), lo que esta reconciliación
descartó explícitamente por `GD-34`. El recuento de este dossier usa
`PENDIENTE`, no `PASS_WITH_LIMITATIONS`, para esa única fila.

**Recuento tras la auditoría Codex round 1 (M-01..M-04):** de las 25 filas,
21 no cambian de categoría (aunque una, `SC-GOV-003`, cambia de subcategoría
dentro de "sostenido", ver M-04). Cuatro dejan de estar sostenidas sin
limitación: `SC-GOV-007` y `SC-GOV-008` (M-01/M-02, sin PASS ni
PASS_WITH_LIMITATIONS hasta que se remedien) y `SC-GOV-012`/`SC-GOV-014`
(resultado científico sostenido, secuencia de gate no sostenida). El auditor
de Codex, contando con su propia metodología (sostenido/no sostenido en vez
de los cuatro estados de la matriz), llegó a 18 sostenidos + 6 no sostenidos
+ 1 bloqueado = 25 sobre el mismo snapshot; la diferencia con el detalle de
este dossier es de granularidad de categorías, no de qué filas están en
disputa — los seis "no sostenidos" que declaró (`003, 007, 008, 012, 014,
019`) coinciden con los que este dossier señala como afectados por M-01/M-04,
salvo que este dossier mantiene `SC-GOV-019` en `PASS_WITH_LIMITATIONS` (ya
lo estaba, sin cambio) en vez de "no sostenido", porque su fila ya declaraba
la limitación exacta que el criterio exige antes de esta auditoría.

## 6. Inconsistencias documentales abiertas, no corregidas aquí

- `claims.md` tiene una inconsistencia de recuento ya señalada y diferida a
  RB-04 por `traceability.md:346-347`: su prosa dice "9 de 10" en una sección
  y su tabla de la sección "Clasificación final" marca diez filas
  `CUBIERTA`. No se toca en este dossier porque corregirla sería reabrir
  RB-04, fuera del alcance autorizado de esta sesión.
- `SC-GOV-024` queda `NOT_APPLICABLE` bajo una condición viva (la cláusula de
  reapertura de §4), no un estado terminal incondicional; cualquier revisión
  futura de la síntesis debe volver a verificarla.

## 7. Qué necesita la auditoría única (alcance sugerido, no vinculante)

Mismo alcance que pidió la reconciliación (`traceability.md:389-396`),
extendido explícitamente a los 25 requisitos por ser éste el objeto de RB-05:

1. Verificar, requisito por requisito, que el estado de la tabla del §3 se
   sostiene contra la evidencia citada — en particular la resolución de §2
   (orden de las secciones del 2026-09-21) y la verificación de §4 (cláusula
   de reapertura de `SC-GOV-024`), que son las dos únicas lecturas donde este
   dossier ejerce juicio en vez de transcribir un estado ya escrito.
2. Confirmar que RB-03 sigue conforme al `PASS` de su propio auditor, sin
   reabrirlo.
3. Confirmar que no hay sobreafirmaciones nuevas introducidas por este
   dossier — en particular, que ninguna fila del §3 declara un estado más
   favorable que el que su evidencia citada sostiene.
4. Decidir si el estado que se propone para `SC-GOV-025` y `GF` se deriva de
   evidencia vigente, una vez completo el recorrido de los 25 requisitos.
5. Confirmar que ningún `FAIL` histórico (rondas 1 y 2 de `f355272`) se
   presenta aquí como `PASS`.
6. No repite recómputo de hashes, métricas ni suites completas salvo que
   encuentre una razón concreta para dudar de un valor citado.
