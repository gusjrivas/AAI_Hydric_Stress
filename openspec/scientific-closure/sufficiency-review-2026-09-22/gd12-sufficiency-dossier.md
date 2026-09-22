# Dossier de suficiencia GD-12 — complementos R, N y S

Sesión `sufficiency-review-2026-09-22`. Snapshot de entrada
`1c33aad8cbee765e2968bd164b5d4890743eea0a`, árbol limpio, rama
`feat/scientific-closure`. Autorización `AUTH-SUFF-2026-09-22`.

**Versión 2, corregida tras la primera crítica independiente.** La versión 1
(snapshot `2185ed4`) recibió quince hallazgos, **siete materiales**. El informe
del crítico se conserva verbatim y sin editar en
`openspec/changes/sc-0{7,9,10}-*/reviews/review-critic-gd12.md`; la resolución
de cada hallazgo está en `findings-resolution.json`. Los tres veredictos de
clasificación de la versión 1 fueron confirmados; lo que la crítica refutó fue
la **estructura del argumento**, la **exactitud de cuatro citas** y la
**gobernanza** de las transiciones de estado. Las tres cosas se corrigen aquí, y
las correcciones están marcadas en línea.

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

## 1. La regla de decisión, y por qué no es la misma para los tres

**Corrección tras el hallazgo C-01.** La versión 1 de esta sección se titulaba
«tomada de la norma y no construida aquí» y afirmaba que las tres normas tienen
«la misma forma condicional». **Es falso**, y el crítico lo demostró leyendo el
texto exacto de la especificación:

| Requisito | Norma verbatim | Forma lógica |
| --- | --- | --- |
| `SC-GOV-021` | «R DEBE activarse **solo si** se pretende sostener desempeño sobre humedad continua **y** la evidencia existente no lo cubre.» | Condición **necesaria**: la conjunción es requisito de la activación |
| `SC-GOV-023` | «N DEBE activarse **si** se afirmará detección reservada de corrupciones **y** la demostración disponible es insuficiente.» | Condición **suficiente**: fija cuándo hay que activar, no cuándo no |
| `SC-GOV-024` | «S DEBE activarse **si** se sostendrá robustez ante ausencia de mediciones/ruido **más allá de** evidencia ya válida.» | Condición **suficiente** |

La diferencia no es de estilo y cambia la carga de la prueba:

- **Para R**, la norma hace el trabajo sola. «Solo si» convierte la conjunción
  en necesaria: si no se pretende sostener desempeño sobre humedad continua, la
  activación no está permitida. `NOT_REQUIRED` no es una interpretación
  favorable, es lo que la norma impone.
- **Para N y para S**, la norma dice cuándo hay que activarlos y **calla sobre
  el caso negativo**. Inferir `NOT_REQUIRED` de que el antecedente no se cumple
  sería **negar el antecedente**, que es una falacia. La versión 1 incurría en
  ella.

**Cómo se sostienen entonces N y S.** No por la norma que los gobierna, sino
por una demostración positiva, que es la que hace la sección 6: **ninguna fuente
de obligación del trabajo —hipótesis canónica, propósito y alcance de
`project.md`, criterios de aceptación de HU7/HU8, criterios de aceptación de los
propios requisitos— exige una afirmación que sólo N o S podrían sostener**. Esa
demostración debe apoyarse en fuentes **independientes de la decisión**, no en
`claims.md`, por la razón que da la sección 6.

Tres consecuencias que este dossier se obliga a respetar:

1. **El disparador es la afirmación, no el hueco de evidencia.** Que falte
   evidencia de regresión no hace `REQUIRED` a R; lo haría querer afirmar
   desempeño sobre humedad continua.
2. **El precio de `NOT_REQUIRED` es una limitación declarada, no un silencio.**
   Cada complemento no activado deja una zona sobre la que el cierre **no puede
   afirmar nada**, y esa zona debe quedar escrita, no omitida.
3. **`NOT_REQUIRED` no puede usarse para achicar una afirmación que el plan
   obliga a sostener.** Si la afirmación es obligatoria, lo que corresponde es
   ejecutar el complemento, no recortar la afirmación.

---

## 2. Evidencia de partida

Toda la evidencia citada es **preexistente y congelada**. Esta sesión no
recomputó ninguna métrica, no abrió ningún dataset y no tocó ningún ledger.

| Fuente | Qué aporta |
| --- | --- |
| `docs/research/reference-v3-formal-results.json` y `reference-v3-formal-table.md` (EV-01) | Las **8 configuraciones formales de `controlled_daily_v3`**: `base`, `sinteticos`, `anomalias`, `completa`, `coverage_fraction_0.5`, `recent_fraction_0.5`, `noise_test_only_0.3`, `noise_both_0.3`, con F1, MCC y AP por configuración |
| `docs/research/hu8-resultados-discusion-conclusiones.md`, §7, §8 y la sección de **erratas** de la tercera auditoría | La contrastación vigente de la hipótesis y, sobre todo, **qué conclusiones previas fueron retractadas** |
| `docs/research/hu8-auditoria-revalidacion.md`, CA1–CA4 | Los criterios de aceptación reales de HU8 y su estado |
| `docs/research/scientific-closure-decisions.md`, §R, §N, §S | Los **diseños congelados** de los tres complementos |
| `docs/research/scientific-closure-preexecution-audit.md`, riesgos SC08/SC10/SC11 | El registro preejecución que declaró estas tres brechas |
| `openspec/specs/scientific-closure/spec.md`, SC-GOV-021/023/024/025 | Normas y criterios de aceptación verbatim |
| `openspec/project.md` | Título, propósito, alcance e inclusiones/exclusiones |
| Evidencia de A, B, C (2026-09-21) y H (2026-09-21) | Lo efectivamente obtenido: clasificación P20 a t+3 y el complemento HITL |

**Hecho negativo verificado, no inferido.** Una búsqueda de `MAE`/`RMSE` sobre
`docs/research/reference-v3-formal-results.json` devuelve **0 ocurrencias**, y
no existe ningún artefacto de regresión en la evidencia de A, B, C ni H. El
crítico independiente lo reverificó por su cuenta y lo encontró **más fuerte**
de lo declarado: sobre los 89 archivos de la raíz de evidencia, ningún archivo
contiene claves `mae`, `rmse`, `r2`, `mean_absolute_error` ni
`root_mean_squared_error`, y el único nombre con «regres» es
`oof_predictions_logistic_regression.csv`, que es un clasificador.

**Hecho incómodo incorporado tras el hallazgo C-11, ausente en la versión 1.**
El dataset de la evidencia formal v3, `melchor_romero_2024_consolidado`, tiene
**75,96 % de cobertura en humedad de suelo**: aproximadamente **un 24 % de los
días son huecos reales del producto satelital**, imputados por el contrato con
`causal_ffill`. La tercera auditoría de HU8 registra además que «cuatro de esas
71 etiquetas provenían de humedad imputada». Esto vale para **las ocho
configuraciones formales**, y tiene consecuencia directa sobre S (sección 5).

---

## 3. R — regresión de humedad continua: `NOT_REQUIRED`

**Qué afirmaría R.** Desempeño sobre humedad de suelo 0–7 cm observada a t+3 en
m³/m³: MAE y RMSE, deltas pareados contra persistencia y contra la media de
train, con bootstrap de bloques de 30 días. Es una escala **distinta** de la
clasificación, y el propio diseño congelado lo dice: «no equivale a
clasificación P20».

**La norma resuelve el caso.** `SC-GOV-021` usa «solo si», de modo que la
activación exige que se pretenda sostener desempeño sobre humedad continua. No
se pretende. Y el **criterio de aceptación del propio requisito**, que es fuente
normativa independiente de `claims.md`, lo dice con todas las letras:
«`NOT_REQUIRED` para sola clasificación P20». El alcance ejecutado es
exclusivamente clasificación binaria P20 a t+3.

**Por qué la exclusión no es un recorte oportunista.** El objeto aprobado del
trabajo es **detección temprana**, no estimación de humedad:

- El título del Trabajo Final es «Arquitectura de inteligencia artificial para
  **detección temprana** de estrés hídrico en cultivos hortícolas bajo
  escenarios de escasez y variabilidad de datos».
- HU4 es «modelado predictivo y generación de **alertas tempranas**»; la salida
  del sistema es una alerta, no un valor de humedad.
- El protocolo v4 y las tres etapas ejecutadas (A, B, C) son, íntegramente, un
  problema de **clasificación binaria P20 a t+3 con MCC como métrica primaria**.
- La auditoría preejecución fijó la jerarquía: «MCC primaria; MAE/RMSE
  pertenecen al **auxiliar continuo**».

`CL-05` registra esta misma exclusión, pero **no se la invoca como prueba**: por
la razón de la sección 6, `claims.md` no puede ser el fundamento.

**El contraargumento más fuerte, y su respuesta.** La auditoría preejecución
registró el riesgo **SC08 — «MAE/RMSE ausentes — alta para cierre final»**, sin
condicionar esa severidad a nada.

**Corrección tras el hallazgo C-09.** La versión 1 afirmaba que «la columna de
mitigación del propio SC08 lo dice». **No lo dice**: la celda de mitigación dice
«Diseño R completo; runner/evaluación/evidencia pendientes, separado de
clasificación», y la de severidad dice «alta para cierre final», sin condicionar.
La condicionalidad es **una inferencia de este dossier**, y se presenta como tal:
un riesgo enunciado sobre la ausencia de una métrica es alto **para un cierre que
pretenda usarla**, y este cierre no la usa y lo declara. Lo que SC08 prohíbe es
la tercera vía —cerrar en silencio, dejando que el lector suponga que el sistema
estima humedad— y esa vía queda cerrada por los límites de abajo. SC08 **no se
declara resuelto**: queda como limitación viva.

**Límites que quedan obligatorios y permanentes.** Mientras R no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar que el sistema predice, estima o pronostica el **valor** de humedad de
  suelo a ningún horizonte;
- reportar MAE, RMSE o R² **como desempeño predictivo de humedad de la campaña
  P20 o de la arquitectura de detección temprana**;
- traducir MCC, AP, Brier o F1 a exactitud sobre humedad;
- presentar la ausencia de estos números como evidencia de que la regresión
  funcionaría, o de que no funcionaría. **No se sabe**: no se midió.

**Corrección tras el hallazgo C-13.** La versión 1 prohibía reportar MAE/RMSE
«de ninguna procedencia». Era insostenible: la spec de `data-quality` (HU3), que
está dentro del alcance aprobado, **ya reporta** MAE 0.02312 / 0.02323 al medir
la utilidad predictiva del **generador sintético** con una regresión lineal
simple. Ese resultado es preexistente, válido en su propio alcance y **no se
suprime**. El límite correcto es el acotado de arriba: lo prohibido es presentar
cualquier MAE/RMSE como desempeño de humedad de la campaña P20 o de la
arquitectura de detección temprana, no la existencia de errores continuos en
otras evaluaciones con su propio alcance declarado.

**Estado propuesto.** R `NOT_REQUIRED`; `SC-GOV-021` `NOT_APPLICABLE` con la
limitación anterior declarada; `sc-07-aux-regression` **permanece `BLOCKED`**
(ver sección 7).

---

## 4. N — detección reservada de corrupciones: `NOT_REQUIRED`

**Qué afirmaría N.** Que un `IsolationForest` ajustado **solo** sobre entradas
2015–2020 **detecta** corrupciones inyectadas en una reserva 2022 que no
intervino en el ajuste: TP/FP/TN/FN, precisión, recall y tasa de falsas
alarmas, por tipo de corrupción (`spikes` de ±3σ en 5 % de fechas; bloques
`stuck` de 3 días hasta 5 % de fechas).

**Dos afirmaciones distintas, y el cierre sostiene una sola.**

- El **aporte de las anomalías como variable predictora**. Esta sí se sostiene,
  y su evidencia existe: las configuraciones `anomalias` y `completa` de las 8
  formales de v3.
- La **detección reservada** de corrupciones. Ésta no se hace.

**Corrección tras los hallazgos C-02 y C-03, ambos materiales.** La versión 1
sostenía el primer punto citando una comparación de HU8 §7 (F1 0.7309 de `base`
contra 0.7278 de `+anomalías`) y atribuyéndola a las 8 configuraciones
formales. Eran **dos errores encadenados**: esa comparación es evidencia
**pre-formal**, y en la tabla formal la dirección es **la inversa**. Los números
correctos de la evidencia vigente son:

| Configuración | F1 | MCC | AP |
| --- | ---: | ---: | ---: |
| `base` | 0.5592 | −0.0135 | 0.5816 |
| `anomalias` | 0.5689 | 0.0110 | 0.5672 |

Es decir: F1 y MCC favorecen **levemente** a `anomalias`, y AP favorece a
`base`. La lectura vigente es la de la matriz de contrastación de HU8 §8.2:
«**Evidencia mixta** (F1/MCC débil-positivo, AP negativo en 5/5 semillas)», con
alcance «este dataset» y limitación «compromiso entre métricas sin resolver».

La versión 1 concluía además que «no hay evidencia de un efecto real, positivo
ni negativo». Esa formulación fue **retractada por la tercera auditoría del
propio documento**, cuya errata dice: «Diferencias de signo mixto entre cinco
semillas **no demuestran ausencia de efecto**. La conclusión defendible es
**ausencia de mejora consistente** en la evidencia reunida». Se adopta la
formulación corregida. El resultado sigue siendo un negativo válido y no una
brecha: lo que no hay es mejora consistente, no una demostración de que no haya
efecto.

**El contraargumento más fuerte, y su respuesta.** El propósito del proyecto
nombra explícitamente «la **detección de anomalías**» como uno de los cuatro
componentes cuyo aporte hay que evaluar. Si el plan obliga a evaluar ese
componente, ¿no obliga a evaluar su detección?

No, y la distinción es de fondo. Lo que las fuentes de obligación piden es el
**aporte del componente**, no el desempeño del detector como clasificador de
corrupciones:

- **CA2 de HU8**, verbatim: «Se analiza el **aporte** de los componentes
  incorporados a la arquitectura». Aporte, no detección.
- La lista «**Incluye**» de `openspec/project.md` enumera como plan
  experimental obligatorio «un plan experimental que compare configuraciones
  (base, base+sintéticos, base+anomalías, completa)» — las cuatro que v3
  ejecutó, y nada más.
- `hu8-auditoria-revalidacion.md` cierra CA1–CA4 como «CUMPLE CON LIMITACIÓN»
  declarando que «ninguno de los gaps identificados es un defecto técnico ni
  **exige nueva evidencia experimental**».

El riesgo preejecución **SC10 — «Anomalías evaluadas sin reserva independiente
— alta»** queda como **limitación viva, no resuelta**: su propia mitigación dice
«Diseño N separado; la demostración previa **queda limitada**».

**Límites que quedan obligatorios y permanentes.** Mientras N no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar que el sistema **detecta** anomalías, corrupciones, fallas de sensor
  o mediciones erróneas, con ninguna cifra de detección;
- reportar precisión, recall, tasa de falsas alarmas ni matriz de confusión del
  detector;
- presentar la demostración funcional de HU3 como evaluación científica de
  detección: es funcional, y así debe llamarse;
- interpretar las anomalías **simuladas** de v3 como fallas reales de sensores;
- afirmar, en sentido inverso, que el detector **no** detecta: tampoco eso se
  midió sobre una reserva independiente;
- presentar el aporte como «mejora»: la lectura vigente es evidencia **mixta**
  con compromiso entre métricas sin resolver.

**Estado propuesto.** N `NOT_REQUIRED`; `SC-GOV-023` `NOT_APPLICABLE` con esas
limitaciones; `sc-09-aux-anomalies` **permanece `BLOCKED`** (ver sección 7).

---

## 5. S — robustez ante escasez, ruido y ausencia de mediciones: `NOT_REQUIRED`, con la frontera más fina de las tres

**Qué afirmaría S.** Cuatro condiciones × cinco semillas: base; etiquetas al
50 % por coverage estratificado; **mediciones enmascaradas** en bloques de 3
días hasta el 10 % de los días de test; y ruido gaussiano σ=0.3·σ_train sobre
entradas de test.

**Por qué la norma no se activa.** `SC-GOV-024` dispara «si **se sostendrá**
robustez ante ausencia de mediciones/ruido más allá de evidencia ya válida». El
cierre **no sostiene robustez de ninguna clase**: la conclusión científica
vigente, HU8 §8.3, declara que la evidencia «no permite sostener una mejora
general de la arquitectura para la detección temprana de estrés hídrico». No se
puede exceder una afirmación que no se hace.

**Qué cubre y qué no cubre la evidencia, corregido tras el hallazgo C-11.**

| Condición del diseño S | Evidencia formal v3 | Estado real de la evidencia |
| --- | --- | --- |
| Base | `base` | Condición controlada |
| Etiquetas escasas | `coverage_fraction_0.5`, `recent_fraction_0.5` | Condición controlada, **una sola fracción (0.5) por mecanismo** |
| Ruido en entradas | `noise_test_only_0.3`, `noise_both_0.3` | Condición controlada, intensidad única, **ruido no calibrado** |
| **Mediciones ausentes** | Ninguna condición controlada | **Presentes e imputadas en TODA la evidencia, sin control ni medición del efecto**: ~24 % de días de humedad son huecos reales del producto satelital, imputados con `causal_ffill` |

La versión 1 decía que la evidencia «no cubre» mediciones ausentes. **Es una
descripción falsa de los datos**, y el crítico la refutó: las mediciones
ausentes no están fuera de la evidencia, **están dentro y sin caracterizar**.
Las dos afirmaciones tienen consecuencias distintas, y la correcta es la
segunda: no hay una condición experimental de mediciones ausentes, pero tampoco
hay un régimen limpio con el que compararla, porque el 24 % de huecos atraviesa
las ocho configuraciones por igual. `CL-08` excluye la afirmación sobre sensores
ausentes, y esa exclusión sigue siendo correcta; lo que era incorrecto es el
motivo que este dossier daba.

**El contraargumento más fuerte, y sigue siéndolo.** La hipótesis canónica habla
de «contextos caracterizados por **disponibilidad limitada**, ruido y alta
variabilidad de datos», y el propósito de `project.md` dice, completo, que se
investiga cómo los componentes «contribuyen a la detección temprana de estrés
hídrico **en escenarios de disponibilidad limitada, ruido y alta variabilidad de
datos**» (la versión 1 truncaba la cita justo antes de esa cláusula — hallazgo
C-10). Si «disponibilidad limitada» debe leerse como **mediciones que faltan**,
la condición 3 de S es la única que la operacionaliza y S sería `REQUIRED`.

La respuesta, que sigue siendo la parte más refutable del documento:

1. **«Disponibilidad limitada» es una caracterización del contexto, no un
   tratamiento obligatorio.** El plan la operacionalizó de dos maneras
   declaradas, y la matriz de contrastación de HU8 §8.2 tiene fila propia para
   ella: evidencia `coverage_fraction_0.5` (mixta) y `recent_fraction_0.5`
   (**mejora consistente**), resultado «Mixto: depende del mecanismo», alcance
   «una fracción (0.5) por mecanismo», limitación «explicación causal de
   `recent` no demostrada». *(Corrección tras C-12: la versión 1 presentaba el
   alcance como si fuera la limitación, y omitía que `recent_fraction_0.5` es
   calificado de mejora consistente y, en §8.3, del «único efecto consistente y
   de mayor magnitud» del estudio.)*
2. **La norma manda distinguir, no unificar.** El criterio de aceptación de
   `SC-GOV-024` dice «escasez de etiquetas **no equivale** a sensores ausentes»,
   y el diseño congelado de S ordena «no confundir … coverage/recent históricos
   con falta de mediciones». Distinguirlas es cumplir la norma, no eludirla.
3. **Las exclusiones de alcance son anteriores a los resultados.**
   `project.md` excluye hardware IoT propio y despliegue en explotaciones
   reales, que es el contexto donde la caída de un sensor sería la amenaza
   dominante.
4. **Si un revisor independiente sostiene la lectura contraria**, la conclusión
   correcta **no** es recortar `CL-08`: es declarar S `REQUIRED`, detener y
   reportar el conflicto al responsable, conforme a la condición de parada de
   `AUTH-SUFF-2026-09-22`.

El riesgo preejecución **SC11 — «Escasez de etiquetas confundida con sensores —
alta»** queda como **limitación viva**, atendida por declaración y no por
evidencia.

**Límites que quedan obligatorios y permanentes.** Mientras S no se ejecute, el
cierre científico y la memoria **no pueden**:

- afirmar robustez, tolerancia ni degradación graceful ante **ausencia de
  mediciones**, caída de sensores, huecos de datos o interrupciones de
  telemetría;
- extrapolar `coverage_fraction`/`recent_fraction` a falta de mediciones: son
  mecanismos distintos, y la norma manda distinguirlos;
- presentar el ruido gaussiano de v3 como ruido real de sensor: HU8 §8.2 lo
  declara «no representativo de ruido real de sensor»;
- presentar cualquier resultado de v3 sin declarar que **el ~24 % de los días
  de humedad del dataset son huecos imputados**, en todas las configuraciones,
  sin caracterización de su efecto;
- afirmar, en sentido inverso, que el sistema **no** tolera mediciones
  ausentes. No se midió.

**Corrección tras el hallazgo C-03.** La versión 1 anclaba una limitación de S
en que el escenario de escasez tenía «el MCC más negativo de todo el estudio
(−0.1103, peor incluso que persistencia)». La tercera auditoría **retractó esa
frase por escrito**: «−0.1103 es mayor (menos negativo) que −0.1113: la escasez
**no** tiene el peor MCC si se incluye ese baseline. Además, los escenarios **no
compartían el mismo target**». La cifra además pertenece a `train_fraction=0.5`,
un escenario **pre-formal** que no integra las 8 configuraciones formales. La
limitación se retira y se reemplaza por la vigente: los resultados de escasez de
v3 son mixtos, dependen del mecanismo, cubren una sola fracción y su explicación
causal no está demostrada.

**Estado propuesto.** S `NOT_REQUIRED` **bajo el límite de `CL-08`**;
`SC-GOV-024` `NOT_APPLICABLE` con esas limitaciones; `sc-10-aux-robustness`
**permanece `BLOCKED`** (ver sección 7).

---

## 6. Condición de parada: ¿queda alguna afirmación obligatoria sin respaldo?

**Corrección tras el hallazgo C-04, material.** La versión 1 apoyaba esta
verificación en una tabla cuya fila decisiva era `claims.md`. Es circular:
`git log` muestra que **GD-12 y la redacción limitante de CL-04, CL-05, CL-07 y
CL-08 entraron en el mismo commit `a0d8bf7` (2026-09-19)**, del mismo autor, y
la quinta columna de esa tabla se llama literalmente «Decisión sobre
complementos» y ya dice «R/N/S `NOT_REQUIRED`». `claims.md` **no es una fuente
independiente**: es el registro de la misma decisión que aquí se evalúa. La
verificación se rehace contra fuentes que no fueron redactadas con GD-12.

| Fuente de obligación, independiente de GD-12 | Qué obliga | ¿Cubierto sin R/N/S? |
| --- | --- | --- |
| Título y propósito de `openspec/project.md` | Detección temprana de estrés hídrico bajo escenarios de escasez y variabilidad; investigar cómo los cuatro componentes contribuyen a esa detección **en escenarios de disponibilidad limitada, ruido y alta variabilidad de datos** | **Sí.** El objeto es detección, no estimación de humedad (R). Los contextos de escasez y ruido tienen condiciones controladas en v3 (S), con la limitación de la sección 5 declarada |
| Lista «**Incluye**» de `openspec/project.md` | «un plan experimental que compare configuraciones (base, base+sintéticos, base+anomalías, completa)» | **Sí.** Son exactamente las cuatro que v3 ejecutó. No enumera detección reservada (N), regresión (R) ni una matriz de robustez (S) |
| Hipótesis canónica de ADR-0001, citada en HU8 §8.1 | Si la combinación de los cuatro componentes mejora la detección temprana, en contextos de disponibilidad limitada, ruido y alta variabilidad | **Sí.** Los cuatro componentes y los contextos tienen fila propia en la matriz de contrastación de HU8 §8.2; el cuarto (HITL) se cubrió además con el complemento H el 2026-09-21 |
| Criterios de aceptación reales de HU8, CA1–CA4 | CA2 pide «el **aporte** de los componentes incorporados a la arquitectura»; CA4 pide **contrastar**, no confirmar | **Sí.** «Aporte» no es «desempeño del detector» (N). `hu8-auditoria-revalidacion.md` cierra CA1–CA4 como CUMPLE CON LIMITACIÓN y declara que ningún gap «exige nueva evidencia experimental» |
| Criterios de aceptación verbatim de `SC-GOV-021/023/024` | El de `SC-GOV-021` dice «`NOT_REQUIRED` para sola clasificación P20»; los de `SC-GOV-023` y `SC-GOV-024` describen la rama REQUIRED y una prohibición que rige siempre | **Sí.** Las prohibiciones («no convertir anomalías simuladas en fallas reales»; «escasez de etiquetas no equivale a sensores ausentes») se cumplen por declaración, y así se registran |
| `SC-GOV-025` | Cierre científico: afirmaciones con evidencia o limitación aceptada, terminal negativo válido documentado, **complementos justificados**, memoria caps. 2/3 trazada, ningún obligatorio sin resolver | **Parcialmente.** Este dossier atiende exactamente el término «complementos justificados». Los otros cuatro siguen abiertos y **no** los toca esta sesión (RB-04, RB-05, RB-06) |

**Precedente análogo, con su referente declarado.** `hu8-auditoria-revalidacion.md`
resolvió una situación de la misma forma para **HITL**: ante ausencia de
evaluación cuantitativa formal, concluyó que «esta ausencia **no obliga a
reabrir HU7/HU8**: ni los criterios de aceptación reales de HU7 ni los de HU8
exigen esa evaluación cuantitativa, y la limitación ya está documentada
explícitamente, sin ocultarse». Se cita como **precedente de método, no como
pronunciamiento sobre R, N o S**: su referente es H y no estos complementos.
*(Precisión sobre la propia crítica independiente: su verificación V-11 cita esa
línea correctamente, pero al listarla junto a las fuentes sobre N puede leerse
como si hablara de N. No habla de N.)*

**Resultado de la verificación: no se identifica ninguna afirmación obligatoria
que quede sin respaldo por no ejecutar R, N o S.** La condición de parada **no**
se activa. El punto con margen real de discrepancia sigue siendo el de la
sección 5, y se somete a la auditoría independiente en lugar de resolverse por
autoridad del orquestador.

*(Nota sobre el recuento de afirmaciones, hallazgo C-14: la versión 1 repetía
«nueve de diez están cubiertas o limitadas», mientras la tabla post-campaña de
`claims.md` marca las **diez** filas como CUBIERTA y su prosa dice 9 de 10. La
inconsistencia es preexistente, no se creó ni se resuelve aquí, y se señala en
lugar de propagarse: corresponde a `RB-02`/`RB-04`, no a este dossier.
Nota sobre la hipótesis, hallazgo C-15: la hipótesis nombra **tres** términos de
contexto —disponibilidad limitada, ruido y alta variabilidad—; la matriz §8.2
fusiona ruido y variabilidad en una fila. Se cita la hipótesis por sus tres
términos.)*

---

## 7. Consecuencia normativa: qué estado recibe cada cosa

**Corrección tras los hallazgos C-05, C-06 y C-08, los tres materiales.** La
versión 1 movió los tres changes de `BLOCKED` a `APPROVED` y a `IN_PROGRESS`, y
propuso cerrarlos como `PASS` de change. Estaba mal, por tres razones que el
crítico documentó y que se verificaron contra las fuentes:

- **`plan.md` es explícito**: «sc-07..10 requieren sc-01+sc-02 **y condición
  REQUIRED**» y «Cambios dependientes **no se ejecutan si gate negativo**». La
  condición REQUIRED no se cumple **y no puede cumplirse**, porque la decisión
  es justamente la contraria.
- **`operations.md` es explícito**: «APPROVED → IN_PROGRESS requiere
  dependencias PASS, **extra_gate** y permisos» y «Un campo faltante o
  indeterminado **bloquea**». El propio bloque `gate_evaluation` que la versión
  1 escribió declaraba dos de cinco cláusulas **no satisfechas**, y la
  transición se hizo igual. Escribir la prosa honesta al lado no repara el acto.
- **`approved_for_implementation: true` era falso** como predicado. Es
  exactamente el que lee la cláusula «implementation approved» del `extra_gate`,
  y el mismo registro lo declaraba `satisfied: false` tres líneas más abajo. Un
  consumidor automático del registro quedaba inducido a error.

**Lo que corresponde, y es alcanzable sin forzar nada:**

| Objeto | Estado | Fundamento |
| --- | --- | --- |
| `SC-GOV-021`, `SC-GOV-023`, `SC-GOV-024` (**requisitos**) | `NOT_APPLICABLE`, sólo con auditoría independiente favorable | Es exactamente lo que `GD-23` degradó y prometió devolver «con auditoría independiente favorable de GD-12», y lo que `operations.md` reserva: «`NOT_APPLICABLE` se reserva a complementos `NOT_REQUIRED` con **decisión de suficiencia auditada**». Vive en `traceability.md` |
| `sc-07`, `sc-09`, `sc-10` (**changes**) | **`BLOCKED`, sin moverse** | Su `extra_gate` exige la condición REQUIRED, que no se cumple y no se cumplirá. Un change cuyo gate es negativo no se despacha. `BLOCKED` no es un defecto aquí: es la descripción correcta de un complemento que no hay que ejecutar |
| La decisión en sí | Registrada en el campo `applicability_decision` de cada change | Preserva en el registro legible por máquina la distinción que C-08 señalaba: un complemento **nunca implementado por innecesario** no se confunde con uno cuyo contrato se cumplió |

Los tres changes quedan en `BLOCKED` con su decisión de aplicabilidad registrada
y auditada. Ningún gate se consume, ningún permiso se otorga y ningún estado
terminal se atribuye a un experimento que no se ejecutó.

*(Hallazgo C-07: la cláusula 7 de `AUTH-SUFF-2026-09-22` dice «solo con
auditoría independiente favorable, actualizar `changes.json`…», y la versión 1
lo actualizó antes de cualquier veredicto. La corrección de esta sección
restituye el estado anterior de los tres changes y deja el registro conforme a
esa cláusula: lo único que se escribe antes de la auditoría son los eventos que
**documentan y revierten** la transición indebida, que no pueden borrarse porque
`operations.md` prohíbe borrar eventos.)*

---

## 8. Lo que esta decisión no afirma

- **No** afirma que R, N y S sean innecesarios para el problema científico. Son
  trabajo futuro pertinente y sus diseños congelados se preservan intactos.
- **No** afirma nada sobre los resultados que R, N o S habrían producido. No se
  ejecutaron; no hay resultado, ni positivo ni negativo, que reportar.
- **No** convierte la ausencia de ejecución en una conclusión experimental. Una
  brecha declarada es una brecha, no un hallazgo.
- **No** revierte, corrige ni reinterpreta ningún resultado de v3, de A, de B,
  de C ni de H.
- **No** resuelve los riesgos preejecución SC08, SC10 y SC11: los tres quedan
  como limitaciones vivas.
- **No** desbloquea `SC-GOV-025` ni el gate `GF`: `RB-04`, `RB-05` y `RB-06`
  siguen abiertos e intactos.
- **No** se apoya en el holdout 2024–2025 para nada.

## 9. Trabajo futuro condicional

Cada complemento vuelve a ser `REQUIRED`, y este dossier queda superado, en
cuanto se pretenda sostener la afirmación correspondiente:

| Complemento | Reabrir si se pretende afirmar |
| --- | --- |
| R | Desempeño sobre el **valor** de humedad de suelo (m³/m³) en cualquier horizonte |
| N | **Detección** de corrupciones, anomalías o fallas de sensor con cifras de detección sobre una reserva independiente |
| S | Robustez ante **ausencia de mediciones**, caída de sensores o huecos de telemetría — **y además**, por la observación del crítico independiente, en cuanto la síntesis científica pendiente (`RB-04`) enuncie **cualquier** resultado de robustez |

En los tres casos corresponde un change aprobado con su propia autorización,
runner validado y evidencia auditada; ninguno puede ejecutarse al amparo de
esta decisión.
