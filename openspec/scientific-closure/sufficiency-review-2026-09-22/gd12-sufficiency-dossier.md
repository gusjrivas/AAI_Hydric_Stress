# Dossier de suficiencia GD-12 — complementos R, N y S

Sesión `sufficiency-review-2026-09-22`. Snapshot de entrada
`1c33aad8cbee765e2968bd164b5d4890743eea0a`, árbol limpio, rama
`feat/scientific-closure`. Autorización `AUTH-SUFF-2026-09-22`.

**Qué decide este documento.** Si los complementos condicionales **R**
(`auxiliary_soil_regression_v1`), **N** (`auxiliary_anomalies_v1`) y **S**
(`auxiliary_robustness_v1`) deben implementarse y ejecutarse para cerrar el
alcance científico aprobado, o si pueden clasificarse `NOT_REQUIRED` sin dejar
ninguna afirmación obligatoria sin respaldo.

**Qué NO decide.** No decide si los complementos son científicamente
interesantes —los tres lo son—, ni si sus diseños congelados son correctos —no
se revisan aquí—, ni si el trabajo futuro debería ejecutarlos. No produce
ningún resultado experimental. La ausencia de ejecución de R, N y S **no es** y
no puede presentarse como un hallazgo, un resultado negativo ni una conclusión
sobre regresión, detección de anomalías o robustez.

**Por qué existe.** Es el bloqueo **RB-03** que levantó la auditoría final
independiente del complemento H el 2026-09-21: la decisión de suficiencia GD-12
—que declara R, N y S `NOT_REQUIRED`— nunca fue criticada ni auditada por nadie
independiente, y los artefactos `auxiliary/{R,N,S}/review.json` no existían. Por
esa causa `GD-23` degradó `SC-GOV-021`, `SC-GOV-023` y `SC-GOV-024` de
`NOT_APPLICABLE` a `BLOCKED` el 2026-09-20, y por esa causa el criterio
«complementos justificados» de `SC-GOV-025` sigue incumplido.

---

## 1. La regla de decisión, tomada de la norma y no construida aquí

Las tres normas de la especificación tienen **la misma forma condicional**, y
esa forma es la regla de decisión. Se transcriben literales:

| Requisito | Norma |
| --- | --- |
| `SC-GOV-021` | «R **DEBE** activarse **solo si** se pretende sostener desempeño sobre humedad continua **y** la evidencia existente no lo cubre.» |
| `SC-GOV-023` | «N **DEBE** activarse **si** se afirmará detección reservada de corrupciones **y** la demostración disponible es insuficiente.» |
| `SC-GOV-024` | «S **DEBE** activarse **si** se sostendrá robustez ante ausencia de mediciones/ruido **más allá de** evidencia ya válida.» |

Cada norma tiene dos términos: **(i)** una intención de afirmar algo, y
**(ii)** una insuficiencia de la evidencia disponible para afirmarlo. El
complemento es `REQUIRED` cuando **ambos** se cumplen. Es `NOT_REQUIRED` cuando
falla el primero: cuando **ninguna afirmación del alcance aprobado sostiene esa
cosa**.

Tres consecuencias que este dossier se obliga a respetar:

1. **El disparador es la afirmación, no el hueco de evidencia.** Que falte
   evidencia de regresión no hace REQUIRED a R; lo haría querer afirmar
   desempeño sobre humedad continua.
2. **El precio de `NOT_REQUIRED` es una limitación declarada, no un silencio.**
   Cada complemento no activado deja una zona sobre la que el cierre **no puede
   afirmar nada**, y esa zona debe quedar escrita, no omitida.
3. **`NOT_REQUIRED` no puede usarse para achicar una afirmación que el plan
   obliga a sostener.** Si la afirmación es obligatoria, lo que corresponde es
   ejecutar el complemento, no recortar la afirmación. La verificación de esto
   es la sección 6, y es la parte de este dossier que más expuesta está a
   refutación.

---

## 2. Evidencia de partida

Toda la evidencia citada es **preexistente y congelada**. Esta sesión no
recomputó ninguna métrica, no abrió ningún dataset y no tocó ningún ledger.

| Fuente | Qué aporta |
| --- | --- |
| `docs/research/reference-v3-formal-results.json` y `reference-v3-formal-table.md` (EV-01) | Las **8 configuraciones formales de `controlled_daily_v3`**: `base`, `sinteticos`, `anomalias`, `completa`, `coverage_fraction_0.5`, `recent_fraction_0.5`, `noise_test_only_0.3`, `noise_both_0.3`, con F1, MCC y AP por configuración |
| `docs/research/hu8-resultados-discusion-conclusiones.md`, §7 y §8 | La contrastación vigente de la hipótesis sobre esa evidencia, con sus resultados mixtos y negativos preservados |
| `docs/research/scientific-closure-decisions.md`, §R, §N, §S | Los **diseños congelados** de los tres complementos, con sus métricas e invariantes |
| `docs/research/scientific-closure-preexecution-audit.md`, riesgos SC08/SC10/SC11 y tabla de diseños | El registro preejecución que declaró estas tres brechas y sus mitigaciones |
| `openspec/scientific-closure/claims.md`, CL-04, CL-05, CL-07, CL-08, CL-10 | El alcance exacto de lo que el cierre afirma y de lo que se niega a afirmar |
| Evidencia de A, B, C (2026-09-21) y H (2026-09-21) | Lo efectivamente obtenido: clasificación P20 a t+3 y el complemento HITL |
| `openspec/project.md` | Propósito, alcance e inclusiones/exclusiones del Trabajo Final |

**Hecho negativo verificado, no inferido.** Una búsqueda de `MAE`/`RMSE` sobre
`docs/research/reference-v3-formal-results.json` devuelve **0 ocurrencias**, y
no existe ningún artefacto de regresión en la evidencia de A, B, C ni H. Es
decir: si alguna afirmación del cierre necesitara error continuo en m³/m³, **no
habría con qué sostenerla** y R sería `REQUIRED`. La decisión de esta sección no
descansa en suponer que la evidencia existe, sino en constatar que **ninguna
afirmación la pide**.

---

## 3. R — regresión de humedad continua: `NOT_REQUIRED`

**Qué afirmaría R.** Desempeño sobre humedad de suelo 0–7 cm observada a t+3 en
m³/m³: MAE y RMSE, deltas pareados contra persistencia y contra la media de
train, con bootstrap de bloques de 30 días. Es una escala **distinta** de la
clasificación, y el propio diseño congelado lo dice: «no equivale a
clasificación P20».

**Qué afirma el cierre, y qué no.** `CL-05` es explícita: «Error continuo de
humedad t+3 permanece registrado, pero **no se sostiene como afirmación de la
campaña P20**», y su columna de brecha dice que sostenerlo «exigiría MAE/RMSE y
baselines auditados» — es decir, la brecha está **enunciada y condicionada a
una ampliación de alcance que no ocurrió**.

**Por qué la exclusión no es un recorte oportunista.** El objeto aprobado del
trabajo es **detección temprana**, no estimación de humedad:

- `openspec/project.md` define el propósito como investigar cómo los cuatro
  componentes «contribuyen a la **detección temprana de estrés hídrico**».
- HU4 es «modelado predictivo y generación de **alertas tempranas**»; la salida
  del sistema es una alerta, no un valor de humedad.
- El protocolo v4 y las tres etapas ejecutadas (A, B, C) son, íntegramente, un
  problema de **clasificación binaria P20 a t+3 con MCC como métrica primaria**.
- La auditoría preejecución ya había fijado la jerarquía: «MCC primaria;
  MAE/RMSE pertenecen al **auxiliar continuo**».

Ninguna de las diez afirmaciones `CL-01..CL-10` requiere un número en m³/m³.

**El contraargumento más fuerte, y su respuesta.** La auditoría preejecución
registró el riesgo **SC08 — «MAE/RMSE ausentes — alta para cierre final»**. Una
lectura razonable diría: si el propio registro califica la ausencia como «alta
para cierre final», declarar R `NOT_REQUIRED` contradice ese registro.

La respuesta no es que SC08 esté mal, sino que su severidad es **condicional a
la misma intención que la norma exige**, y la columna de mitigación del propio
SC08 lo dice: «Diseño R completo; runner/evaluación/evidencia pendientes,
**separado de clasificación**». SC08 es alto **para un cierre que pretenda
sostener desempeño sobre humedad continua**. Este cierre no lo pretende, y lo
declara. Lo que SC08 prohíbe es la tercera vía: cerrar en silencio, dejando que
el lector suponga que el sistema estima humedad. Este dossier la cierra
expresamente en el punto siguiente.

**Límites que quedan obligatorios y permanentes.** Mientras R no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar que el sistema predice, estima o pronostica el **valor** de humedad de
  suelo;
- reportar error en m³/m³, ni MAE, ni RMSE, ni R², de ninguna procedencia;
- traducir MCC, AP, Brier o F1 a exactitud sobre humedad;
- presentar la ausencia de estos números como evidencia de que la regresión
  funcionaría, o de que no funcionaría. **No se sabe**: no se midió.

**Estado propuesto.** R `NOT_REQUIRED`; `SC-GOV-021` `NOT_APPLICABLE` con la
limitación anterior declarada; `sc-07-aux-regression` cerrado por decisión
motivada, sin implementación, conforme a su propio criterio de aceptación
(«Si NOT_REQUIRED: solo decisión motivada, sin implementación»).

---

## 4. N — detección reservada de corrupciones: `NOT_REQUIRED`

**Qué afirmaría N.** Que un `IsolationForest` ajustado **solo** sobre entradas
2015–2020 **detecta** corrupciones inyectadas en una reserva 2022 que no
intervino en el ajuste: TP/FP/TN/FN, precisión, recall y tasa de falsas
alarmas, por tipo de corrupción (`spikes` de ±3σ en 5 % de fechas; bloques
`stuck` de 3 días hasta 5 % de fechas).

**Qué afirma el cierre, y qué no.** Hay dos afirmaciones distintas sobre
anomalías y **el cierre sostiene una sola**:

- `CL-04` — el **aporte de las anomalías como variable predictora** en la
  referencia v3. Esta sí se sostiene, y su evidencia existe: las
  configuraciones `anomalias` y `completa` de las 8 formales de v3, con
  resultados **preservados tal como quedaron**. HU8 §7 los reporta sin
  suavizar: tras la purga de frontera de horizonte, `base` supera a
  `+anomalías` en F1 y MCC, las diferencias por semilla tienen signo mixto
  (`[+0.0122, +0.0158, −0.0396, +0.0210, −0.0250]`), y la conclusión correcta
  es que **no hay evidencia de un efecto real, positivo ni negativo**. Es un
  resultado negativo válido, no una brecha.
- `CL-07` — la **detección reservada** de corrupciones. Esta el cierre se niega
  a sostenerla: «Detección de corrupciones reservadas permanece explícita, pero
  **no se sostiene** en el cierre limitado», y su columna de brecha dice que
  afirmarla exigiría «fit train y evaluación reservada», que es exactamente el
  diseño N.

La primera afirmación tiene evidencia; la segunda no se hace. La norma de
`SC-GOV-023` no se activa.

**El contraargumento más fuerte, y su respuesta.** El propósito del proyecto
nombra explícitamente «la **detección de anomalías**» como uno de los cuatro
componentes cuyo aporte hay que evaluar. Si el plan obliga a evaluar ese
componente, ¿no obliga a evaluar su detección?

No, y la distinción es de fondo, no verbal. Lo que el propósito obliga a
evaluar es la **contribución del componente a la detección temprana de estrés
hídrico**, que es lo que las configuraciones `base → anomalias` y
`+sintéticos → completa` de v3 midieron, y lo que la matriz de contrastación de
HU8 §8.2 registra como «evidencia mixta». El desempeño del **detector como
clasificador de corrupciones** es una pregunta distinta, que ni la hipótesis ni
los criterios de aceptación de HU7/HU8 formulan. El registro lo dice con sus
palabras al cerrar HU8: «Ninguna de estas acciones es necesaria para sostener
el cierre de HU8: la evidencia formal ya existente es válida y suficiente para
los criterios de aceptación reales».

El riesgo preejecución **SC10 — «Anomalías evaluadas sin reserva independiente
— alta»** se responde igual que SC08: su propia mitigación dice «Diseño N
separado; **la demostración previa queda limitada**». Queda limitada, no
invalidada, y la limitación se declara abajo.

**Límites que quedan obligatorios y permanentes.** Mientras N no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar que el sistema **detecta** anomalías, corrupciones, fallas de sensor
  o mediciones erróneas, con ninguna cifra de detección;
- reportar precisión, recall, tasa de falsas alarmas ni matriz de confusión del
  detector;
- presentar la demostración funcional de HU3 como evaluación científica: es
  funcional, y así debe llamarse;
- interpretar las anomalías **simuladas** de v3 como fallas reales de sensores;
- afirmar, en sentido inverso, que el detector **no** detecta: tampoco eso se
  midió sobre una reserva independiente.

**Estado propuesto.** N `NOT_REQUIRED`; `SC-GOV-023` `NOT_APPLICABLE` con esas
limitaciones; `sc-09-aux-anomalies` cerrado por decisión motivada, sin
implementación.

---

## 5. S — robustez ante escasez, ruido y ausencia de mediciones: `NOT_REQUIRED`, con la frontera más fina de las tres

**Qué afirmaría S.** Cuatro condiciones × cinco semillas: base; etiquetas al
50 % por coverage estratificado; **mediciones enmascaradas** en bloques de 3
días hasta el 10 % de los días de test; y ruido gaussiano σ=0.3·σ_train sobre
entradas de test.

**Qué afirma el cierre, y qué no.** `CL-08` traza la frontera con precisión
inusual: «Robustez se limita a **etiquetas escasas y ruido** históricamente
documentados en v3; **excluye sensores o mediciones ausentes**».

Y esa frontera coincide con lo que la evidencia congelada cubre y no cubre:

| Condición del diseño S | ¿Evidencia formal v3? | ¿Afirmada por CL-08? |
| --- | --- | --- |
| Base | Sí — configuración `base` | Sí |
| Etiquetas escasas | Sí — `coverage_fraction_0.5` y `recent_fraction_0.5` | Sí, con límites |
| Ruido en entradas | Sí — `noise_test_only_0.3` y `noise_both_0.3` | Sí, con límites |
| **Mediciones enmascaradas / sensores ausentes** | **No. Ninguna.** | **No — excluida expresamente** |

Las dos primeras filas con evidencia tienen, además, sus resultados
**preservados sin armonizar**, incluido el más incómodo: HU8 §7 registra que el
escenario de escasez `train_fraction=0.5`, antes reportado como mejora de F1,
tiene «el **MCC más negativo de todo el estudio** (−0.1103, peor incluso que
persistencia)». Ese hallazgo no se toca aquí y no se reinterpreta.

**El contraargumento más fuerte, y es el más fuerte de los tres.** La hipótesis
canónica del trabajo habla de «contextos caracterizados por **disponibilidad
limitada**, ruido y alta variabilidad de datos». «Disponibilidad limitada» se
puede leer de dos maneras: como **menos etiquetas/menos historia** —lo que v3
operacionalizó con `coverage_fraction` y `recent_fraction`— o como **mediciones
que faltan**, que es justamente la condición 3 de S, la única sin evidencia. Si
la segunda lectura es la que el plan obliga a sostener, entonces S es
`REQUIRED` y esta decisión es incorrecta.

La respuesta de este dossier, ofrecida como **la parte más refutable de todo el
documento**, es triple:

1. El plan **ya operacionalizó** «disponibilidad limitada» y lo hizo de dos
   maneras, no de ninguna: la matriz de contrastación de HU8 §8.2 tiene una
   fila «Disponibilidad limitada» cuya evidencia son `coverage_fraction_0.5` y
   `recent_fraction_0.5`, con resultado «Mixto: depende del mecanismo» y
   limitación «una fracción (0.5) por mecanismo». La dimensión de la hipótesis
   **está evaluada**, con su operacionalización declarada y sus límites.
2. La lectura «mediciones ausentes» **no queda tapada**: `CL-08` la excluye
   **por escrito** del alcance de la afirmación, y `openspec/project.md`
   excluye del alcance el hardware IoT propio y el despliegue en explotaciones
   reales, que es el contexto donde la caída de un sensor sería la amenaza
   dominante. La exclusión es anterior a los resultados y no se inventa aquí.
3. Aun así, esta es la clasificación con **mayor probabilidad de ser revertida
   por un revisor independiente**, y se registra como tal. Si el crítico o el
   auditor sostienen que «disponibilidad limitada» obliga la lectura de
   mediciones ausentes, la conclusión correcta **no** es recortar `CL-08`: es
   declarar S `REQUIRED`, detener esta línea de trabajo y reportar el conflicto
   al responsable, conforme a la condición de parada de `AUTH-SUFF-2026-09-22`.

El riesgo preejecución **SC11 — «Escasez de etiquetas confundida con sensores
— alta»** apunta exactamente a esta confusión, y su mitigación es «Diseño S
distingue etiquetas, mediciones y ruido». Esa distinción se preserva aquí en la
única forma disponible sin ejecutar S: **declarando** que la evidencia cubre
etiquetas y ruido y **no** cubre mediciones ausentes.

**Límites que quedan obligatorios y permanentes.** Mientras S no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar robustez, tolerancia o degradación graceful ante **ausencia de
  mediciones**, caída de sensores, huecos de datos o interrupciones de
  telemetría;
- extrapolar los resultados de `coverage_fraction`/`recent_fraction` a falta de
  mediciones: son mecanismos distintos, y el propio registro lo advierte;
- presentar el ruido gaussiano de v3 como ruido real de sensor: «no
  representativo de ruido real de sensor», dice HU8 §8.2;
- presentar los resultados de escasez de v3 como favorables sin acompañarlos
  del hallazgo de MCC −0.1103.

**Estado propuesto.** S `NOT_REQUIRED` **bajo el límite de `CL-08`**;
`SC-GOV-024` `NOT_APPLICABLE` con esas limitaciones; `sc-10-aux-robustness`
cerrado por decisión motivada, sin implementación.

---

## 6. Condición de parada: ¿queda alguna afirmación obligatoria sin respaldo?

La instrucción vigente obliga a detenerse y reportar el conflicto si algún
complemento resulta **necesario para una afirmación obligatoria del plan**. Esta
sección es la verificación explícita de esa condición, y se hace sobre las
fuentes que fijan qué es obligatorio.

| Fuente de obligación | Qué obliga | ¿Cubierto sin R/N/S? |
| --- | --- | --- |
| Hipótesis canónica (ADR-0001, citada en HU8 §8.1) | Evaluar si la combinación de sintéticos, detección de anomalías, modelado predictivo y retroalimentación humana mejora la detección temprana, en contextos de disponibilidad limitada, ruido y variabilidad | **Sí.** Los cuatro componentes y los dos contextos tienen fila propia en la matriz de contrastación de HU8 §8.2, con evidencia formal v3; el cuarto componente (HITL) se cubrió además con el complemento H el 2026-09-21 |
| `openspec/project.md`, propósito y alcance | Evaluar la contribución de los componentes; **no** incluye validación agronómica, hardware IoT propio ni despliegue real | **Sí**, y las exclusiones son anteriores a los resultados |
| `claims.md`, `CL-01..CL-10` | Las diez afirmaciones del cierre | **Sí.** Nueve están cubiertas o limitadas; ninguna de las diez requiere R, N ni S. `CL-10` fija el criterio de suficiencia y ya contiene «R/N/S `NOT_REQUIRED`, H `REQUIRED`» |
| Criterios de aceptación de HU7/HU8 | Cierre de la evaluación experimental | **Sí**, y el propio HU8 §8.5 lo declara: «Ninguna de estas acciones es necesaria para sostener el cierre de HU8» |
| `SC-GOV-025` | Cierre científico: afirmaciones con evidencia o limitación aceptada, terminal negativo válido documentado, **complementos justificados**, memoria caps. 2/3 trazada, ningún obligatorio sin resolver | **Parcialmente.** Este dossier atiende exactamente el término «complementos justificados». Los otros cuatro términos siguen abiertos y **no** los toca esta sesión (RB-04, RB-05, RB-06) |

**Resultado de la verificación: no se identifica ninguna afirmación obligatoria
que quede sin respaldo por no ejecutar R, N o S.** La condición de parada **no**
se activa. El punto con margen real de discrepancia es el de la sección 5
—«disponibilidad limitada» leída como mediciones ausentes— y se somete
deliberadamente a la crítica y a la auditoría independientes en lugar de
resolverse por autoridad del orquestador.

---

## 7. Lo que esta decisión no afirma

- **No** afirma que R, N y S sean innecesarios para el problema científico. Son
  trabajo futuro pertinente y sus diseños congelados se preservan intactos.
- **No** afirma nada sobre los resultados que R, N o S habrían producido. No se
  ejecutaron; no hay resultado, ni positivo ni negativo, que reportar.
- **No** convierte la ausencia de ejecución en una conclusión experimental. Una
  brecha declarada es una brecha, no un hallazgo.
- **No** revierte, corrige ni reinterpreta ningún resultado de v3, de A, de B,
  de C ni de H.
- **No** desbloquea `SC-GOV-025` ni el gate `GF`: `RB-04`, `RB-05` y `RB-06`
  siguen abiertos e intactos, y el criterio de `SC-GOV-025` tiene cinco
  términos de los que este dossier atiende uno.
- **No** se apoya en el holdout 2024–2025 para nada. Ninguna clasificación de
  suficiencia usa resultados de C.

## 8. Trabajo futuro condicional

Cada complemento vuelve a ser `REQUIRED`, y este dossier queda superado, en
cuanto se pretenda sostener la afirmación correspondiente:

| Complemento | Reabrir si se pretende afirmar |
| --- | --- |
| R | Desempeño sobre el **valor** de humedad de suelo (m³/m³) en cualquier horizonte |
| N | **Detección** de corrupciones, anomalías o fallas de sensor con cifras de detección sobre una reserva independiente |
| S | Robustez ante **ausencia de mediciones**, caída de sensores o huecos de telemetría |

En los tres casos corresponde un change aprobado con su propia autorización,
runner validado y evidencia auditada; ninguno puede ejecutarse al amparo de
esta decisión.
