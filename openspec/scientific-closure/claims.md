# Afirmaciones y suficiencia

Ninguna fila afirma resultados futuros. La evaluación documental de
`sc-01-evidence-scope` fija qué evidencia hace falta antes de observar A/B/C o
complementos. El alcance conserva todas las hipótesis y componentes, pero no
exige mejora positiva. `PENDING` describe evidencia científica futura; no vuelve
`UNRESOLVED` la decisión de necesidad ya tomada.

| ID | Afirmación y límite aprobado | Evidencia existente | Brecha / evidencia futura | Decisión sobre complementos |
| --- | --- | --- | --- | --- |
| CL-01 | Comparación retrospectiva P20 entre familias en Pergamino; exploratoria, no superioridad general | Protocolo v4 y diseños preejecución `REFERENCED` | A íntegra, soporte y selección conforme protocolo: `PENDING` | R/N/S `NOT_REQUIRED`; H no aporta a esta afirmación |
| CL-02 | Validación temporal del candidato congelado; un gate negativo solo permite afirmar que no validó | Contrato B `REFERENCED` | B única, solo si A entrega candidato admisible: `PENDING` | Sin complemento requerido |
| CL-03 | Desempeño temporal final 2024–2025; no afirmar si C no se abre | Contrato C `REFERENCED` | C única, solo con B `CANDIDATE_VALIDATED`, auditor B PASS y sin decisiones adaptativas: `PENDING` | Sin complemento requerido |
| CL-04 | Aporte de sintéticos/anomalías como predictores en la referencia v3, limitado a su diseño y sitio | Resultados formales v3 `REFERENCED`, preservados y no recalculados | Mantener límites y trazabilidad; no convertirlos en resultado v4 | N `NOT_REQUIRED`: esta afirmación no es detección reservada ni fallas reales |
| CL-05 | Error continuo de humedad t+3 permanece registrado, pero no se sostiene como afirmación de la campaña P20 | Diseño R `REFERENCED`; sin ejecución científica nueva | Si se ampliara el alcance a regresión, harían falta MAE/RMSE y baselines auditados | R `NOT_REQUIRED` para clasificación P20; ampliar la afirmación exigiría nueva decisión |
| CL-06 | Aporte cuantitativo de correcciones supervisadas simuladas; nunca beneficio de una persona real | Diseño H `REFERENCED`; integración HU5 no demuestra efecto | Comparación predeclarada y auditada de tres brazos: `PENDING` | H `REQUIRED`; evidencia humana prospectiva externa sería necesaria para afirmar beneficio humano real |
| CL-07 | Detección de corrupciones reservadas permanece explícita, pero no se sostiene en el cierre limitado | Diseño N `REFERENCED`; no hay evaluación reservada autorizada | Fit train y evaluación reservada serían necesarios para ampliar la afirmación | N `NOT_REQUIRED`; no afirmar detección reservada, anomalías reales ni fallas reales |
| CL-08 | Robustez se limita a etiquetas escasas y ruido históricamente documentados en v3; excluye sensores o mediciones ausentes | Referencia v3 `REFERENCED`; diseño S preservado | Máscaras/ruido predeclarados serían necesarios para ampliar a mediciones ausentes | S `NOT_REQUIRED` bajo este límite; no extrapolar a sensores ausentes |
| CL-09 | Anticipación retrospectiva de episodios P20 t+3, sin anticipación operativa o agronómica | Definición v4 `REFERENCED` | Métricas onset, censura, falsos avisos y soporte: `PENDING`; onset puede quedar indefinido si el soporte no alcanza | Sin complemento requerido |
| CL-10 | Suficiencia del alcance HU7/HU8, sin certificar HU1 ni la tesis completa por sí sola | Fuentes de alcance, v3 `REFERENCED` y criterios preejecución | Terminal A/B/C auditado, H auditado, trazabilidad y límites: `PENDING` | Criterio fijado; R/N/S `NOT_REQUIRED`, H `REQUIRED` |

CL-10 se satisface con un terminal válido del protocolo auditado, incluso un
resultado negativo en A/B o soporte insuficiente; evidencia histórica v3
`REFERENCED` con sus límites; H auditado; y afirmaciones trazadas a capítulos
2/3 con limitaciones explícitas. No exige abrir C si un gate negativo detiene la
secuencia ni definir onset cuando el soporte no lo permite. Tampoco certifica
HU1 o el cierre total de la tesis sin evidencia propia de esos entregables.

Prohibido afirmar sin respaldo: superioridad general de IA/ensambles, beneficio
obligatorio de sintéticos o HITL, estrés fisiológico validado, ahorro de agua,
eficacia agronómica, latencia operativa, generalización geográfica, R/H/N/S como
confirmación independiente (usan 2015–2022), seeds como cinco poblaciones,
v4 como réplica directa v3 o un cambio atribuible exclusivamente al sitio.
No seleccionar modelos, umbrales, hipótesis narrativas ni conclusiones favorables
mirando C. C solo contrasta el objeto previamente fijado.

Decisión por complemento: REQUIRED / NOT_REQUIRED / UNRESOLVED. Registrar
afirmación, fuente de alcance, evidencia existente, brecha, justificación,
autor/responsable y revisión crítica. NOT_REQUIRED no elimina requisitos de
tesis: limita la afirmación explícitamente y requiere compatibilidad con alcance.
Resultados negativos, persistencia superior o SIN_GANADOR_ESTABLE son admisibles.
NO_VALID_SELECTION por soporte informa insuficiencia, no prueba equivalencia.

Decisión vigente previa a ejecución: R `NOT_REQUIRED`, H `REQUIRED`, N
`NOT_REQUIRED`, S `NOT_REQUIRED`. Esta decisión permanece pendiente de crítica
y auditoría independiente; no autoriza ejecutar H, A, B, C ni abrir holdouts.

> **Superseded el 2026-09-22 (RB-03, decisiones GD-30/GD-31/GD-32).** El
> párrafo anterior se conserva **sin reescribir** como registro de su momento,
> pero su afirmación en presente dejó de ser cierta: la decisión GD-12 **ya no**
> está pendiente de crítica y auditoría independiente. Fue criticada
> (`openspec/changes/sc-07-aux-regression/reviews/review-critic-gd12.md`, 7
> hallazgos materiales, todos remediados) y auditada (`review-audit-gd12.md`,
> `PASS` sobre el bloqueo RB-03), en el snapshot `2185ed4` → `6878184` →
> `65ca852`. Los tres artefactos `auxiliary/{R,N,S}/review.json` existen en
> `openspec/scientific-closure/sufficiency-review-2026-09-22/auxiliary/`. El
> estado vigente lo fija la sección «Clasificación final de afirmaciones —
> 2026-09-22» de este archivo y la matriz de `traceability.md`.

**Consecuencia registrada el 2026-09-20 (hallazgo C-09, decisión GD-23).**
Mientras esa auditoría independiente no exista, los requisitos SC-GOV-021,
SC-GOV-023 y SC-GOV-024 **no** pueden figurar como `NOT_APPLICABLE`, porque ese
estado es terminal para el checker normativo, tan definitivo como `PASS`, y su
única base sería esta decisión autodeclarada no auditada. Los tres figuran
`BLOCKED` en la matriz de trazabilidad. La decisión de fondo —R, N y S
`NOT_REQUIRED` para el alcance aprobado— **no** se revierte: lo que se revierte
es atribuirle un estado terminal. Los artefactos `auxiliary/R/review.json`,
`auxiliary/N/review.json` y `auxiliary/S/review.json` no existen, y esa ausencia
se declara aquí en lugar de omitirse.

## Estado de las afirmaciones tras la campaña A→B→C y el complemento H — 2026-09-21

Esta sección **no reescribe** la tabla anterior: registra cómo quedaron sus
`PENDING` una vez ejecutados A, B, C y H. El recuento lo rehizo el auditor final
independiente del complemento H, no el orquestador.

**9 de 10** afirmaciones tienen hoy evidencia o limitación aceptada, frente a
**4 de 10** el 2026-09-20. `PENDING` designaba evidencia futura faltante, no un
límite aceptado; esa era la razón del recuento anterior.

| ID | Estado | Qué lo cambió |
| --- | --- | --- |
| CL-01 | CUBIERTA | Etapa A ejecutada. `SIN_GANADOR_ESTABLE` con desempate por simplicidad predeclarada, soporte 3/3 folds y 5000/5000 réplicas. Resultado negativo válido, no defecto |
| CL-02 | CUBIERTA | Etapa B ejecutada. `CANDIDATE_VALIDATED` por **no inferioridad**: el intervalo pareado incluye el cero y no demuestra superioridad |
| CL-03 | CUBIERTA | Etapa C abierta **una sola vez**, ledger `CONFIRMADA` |
| CL-04 | CUBIERTA por limitación aceptada | v3 `REFERENCED`, preservada y no recalculada |
| CL-05 | CUBIERTA por limitación aceptada | La afirmación de regresión no se sostiene en esta campaña; la brecha es condicional a ampliar el alcance |
| **CL-06** | **CUBIERTA CON LIMITACIONES** | **Es la que movió el complemento H.** Comparación predeclarada y auditada de los tres brazos, con el contrato anclado en git **antes** de ejecutar. Reporta el aporte cuantitativo de correcciones supervisadas **simuladas** sin afirmar beneficio y sin intervalos, y **nunca** beneficio de una persona real, como exige la propia redacción de CL-06. La pista humana controlada **no** sostiene ninguna afirmación cuantitativa |
| CL-07 | CUBIERTA por limitación aceptada | No se afirma detección reservada |
| CL-08 | CUBIERTA por limitación aceptada | Robustez limitada a lo documentado en v3, sin extrapolar a sensores ausentes |
| CL-09 | CUBIERTA | Métricas de onset, episodios, censura y soporte presentes en la evidencia de A, B y C |
| **CL-10** | **CUBIERTA** al registrarse la auditoría de H | Exige «Terminal A/B/C auditado, H auditado, trazabilidad y límites». Los cuatro términos se cumplen: la trazabilidad la provee la sección del 2026-09-21 de `traceability.md`, que supersede la fila obsoleta de SC-GOV-022 |

**Lo que sigue sin cubrir, y no depende de las afirmaciones.** `SC-GOV-025`
permanece `BLOCKED` y el gate `GF` no es evaluable como PASS. El auditor fue
explícito: la cobertura de afirmaciones es **uno solo** de los cinco conjuntos
del criterio de aceptación de `SC-GOV-025`. Faltan la auditoría final requisito
por requisito sobre el snapshot posterior a la campaña, la síntesis científica
de los resultados efectivamente obtenidos, la crítica y auditoría
independientes de la decisión de suficiencia GD-12 sobre R/N/S —que mantiene
`SC-GOV-021`, `023` y `024` en `BLOCKED`— y la trazabilidad a los capítulos 2 y
3 de la memoria.

**Límite que debe acompañar a CL-06 en cualquier lectura.** La intervención
humana controlada demostró el mecanismo en su camino de **aceptación**, con
cegamiento **parcial** y declarado, y el operador **no detectó ninguna** de las
cuatro etiquetas corrompidas que se le presentaron. La corrección y la
recalibración quedan demostradas por la pista **simulada**; el rechazo y la
recalibración sucesiva, por **ninguna** pista científica. No hubo intervención
de un agrónomo ni validación agronómica de campo: es trabajo futuro, declarado
por el propio operador.

## Clasificación final de afirmaciones — 2026-09-22

**Nota de reconciliación.** Sección redactada originalmente en
`feat/scientific-evidence-finalization` (commit `7e63d1c`) e incorporada aquí
como entregable de **RB-04/RB-06**, con tres correcciones: (1) las rutas de
`auxiliary/{R,N,S}/review.json` apuntan a
`openspec/scientific-closure/sufficiency-review-2026-09-22/auxiliary/`, los
artefactos que la crítica y la auditoría independientes de **RB-03**
(`2185ed4` → `65ca852`) efectivamente revisaron y aprobaron — no a los de la
otra rama, que quedan como historia en `f355272`; (2) CL-04 y CL-08 incorporan
la limitación de imputación causal en la evidencia v3 (~24 % de días,
`causal_ffill`); (3) CL-10 no se declara `DEMOSTRADA` hasta que la auditoría
única del snapshot reconciliado (que esta misma sesión solicita) emita
veredicto, porque la auditoría final requisito por requisito sobre el snapshot
posterior a la campaña (RB-05) tuvo dos rondas con veredicto formal `FAIL`, y
ese `FAIL` no se sustituye por un `PASS` de facto.

Esta sección **supersede** a todas las anteriores de este archivo para el
estado de las afirmaciones, sin reescribirlas: se conservan íntegras como
registro histórico. Clasifica cada
afirmación del cierre en una de cuatro categorías y fija qué puede decirse en la
memoria técnica y qué no. Producida sin ejecutar A, B, C ni H, sin abrir el
holdout y sin evidencia científica nueva.

Categorías: **DEMOSTRADA** (evidencia propia, suficiente y auditada para el
enunciado exacto); **RESPALDADA CON LIMITACIONES** (evidencia propia que sostiene
un enunciado más débil que el intuitivo, con límites que deben acompañarla
siempre); **NO DEMOSTRADA** (no hay evidencia propia; el enunciado no se sostiene
y no se insinúa); **TRABAJO FUTURO** (haría falta evidencia nueva, y se declara
cuál).

### Afirmaciones de la campaña

| ID | Enunciado permitido, tal como puede escribirse | Clasificación | Evidencia primaria | Qué queda prohibido decir |
| --- | --- | --- | --- | --- |
| CL-01 | La comparación retrospectiva entre las cuatro familias autorizadas sobre 2015–2022 en Pergamino terminó en `SIN_GANADOR_ESTABLE`; el candidato se fijó por el desempate de simplicidad **predeclarado**, no por desempeño superior | RESPALDADA CON LIMITACIONES | Etapa A auditada: soporte 3/3 folds, 5000/5000 réplicas, `selection_decision.json`, `frozen_config.json` | Que la regresión logística sea mejor que las otras familias; que exista un ganador; que el empate pruebe equivalencia |
| CL-02 | El candidato congelado se validó una sola vez sobre 2023 y resultó **no inferior** a la persistencia causal dentro del margen práctico predeclarado; el intervalo pareado **incluye el cero** | RESPALDADA CON LIMITACIONES | Etapa B auditada: `decision.json`, custodia de intento único, `predictions_2023.csv` | Superioridad sobre persistencia; que `CANDIDATE_VALIDATED` signifique «mejor»; reutilizar B para elegir otro candidato |
| CL-03 | La evaluación final sobre el holdout 2024–2025, abierto **una única vez**, arrojó un resultado favorable frente a la persistencia en MCC, acompañado de calibración degradada, falsos avisos y episodios no detectados | RESPALDADA CON LIMITACIONES | Etapa C auditada: `outcome.json`, `metrics.json`, ledger `CONFIRMADA`, apertura única e irreversible | Desempeño operativo; anticipación agronómica; que el holdout pueda reabrirse o reinterpretarse; presentar el MCC sin la calibración degradada |
| CL-04 | Los sintéticos y las anomalías aportaron como predictores en la referencia histórica `controlled_daily_v3`, dentro de su propio diseño y sitio | RESPALDADA CON LIMITACIONES | `docs/research/reference-v3-formal-results.json`, `REFERENCED`, preservada y no recalculada | Convertir ese aporte en resultado de v4; extrapolarlo a Pergamino; presentarlo como detección; **citar cualquier configuración de esa referencia sin declarar que ~24 % de sus días de humedad son huecos imputados con `causal_ffill`** (§8.4 de `hu8-resultados-discusion-conclusiones.md`, añadido 2026-09-22) |
| CL-05 | El error continuo de humedad a t+3 **no** se midió en esta campaña | NO DEMOSTRADA | `sufficiency-review-2026-09-22/auxiliary/R/review.json`; R `NOT_REQUIRED` (GD-12, criticada y auditada por RB-03) | Cualquier afirmación de desempeño sobre humedad continua; presentar MCC como si acreditara error continuo |
| CL-06 | El mecanismo de corrección supervisada quedó técnicamente validado: las correcciones **simuladas** producen recalibración, con deltas de signo mixto entre semillas y **sin** intervalos | RESPALDADA CON LIMITACIONES | Complemento H auditado: tres brazos sobre las mismas filas de evaluación, 20 eventos por semilla, cinco semillas congeladas, estratificación verificada | Mejora atribuible al feedback; beneficio de una persona real; pericia, criterio propio o juicio humano bajo incertidumbre |
| CL-07 | La detección reservada de corrupciones **no** se evaluó | NO DEMOSTRADA | `sufficiency-review-2026-09-22/auxiliary/N/review.json`; N `NOT_REQUIRED` (GD-12, criticada y auditada por RB-03) | Detección reservada; anomalías reales; fallas reales de sensor; usar el 0/4 humano de H como tasa de detección |
| CL-08 | La robustez citable se limita a las etiquetas escasas y el ruido documentados en v3 | RESPALDADA CON LIMITACIONES | Referencia v3 `REFERENCED`; `sufficiency-review-2026-09-22/auxiliary/S/review.json`; S `NOT_REQUIRED` (GD-12, criticada y auditada por RB-03: `2185ed4`→`65ca852`) | Robustez ante sensores o mediciones ausentes; equiparar escasez de etiquetas con ausencia de mediciones; **presentar la referencia v3 como un régimen "limpio" de mediciones: ~24 % de sus días de humedad están imputados con `causal_ffill`, sin caracterizar** |
| CL-09 | Las métricas de anticipación retrospectiva de episodios P20 a t+3 —onset, censura, falsos avisos y soporte— están presentes en la evidencia de A, B y C, con sus indefiniciones declaradas | RESPALDADA CON LIMITACIONES | Evidencia de A, B y C; `statistical-review.json` | Anticipación operativa; anticipación agronómica; tratar un onset indefinido como si fuera cero |
| CL-10 | El conjunto de evidencia es suficiente para el alcance aprobado de HU7/HU8, con sus limitaciones declaradas | RESPALDADA CON LIMITACIONES, **pendiente de la auditoría única del snapshot reconciliado (RB-05)** | Terminal A/B/C auditado; H auditado (PASS_WITH_LIMITATIONS); GD-12 criticada y auditada (RB-03, PASS); síntesis 2026-09-22; trazabilidad a capítulos 2 y 3. **RB-05** (auditoría final requisito por requisito) tuvo dos rondas con veredicto formal `FAIL` por defectos documentales, sin una tercera ronda que las verificara: no se cita como PASS | Que certifique HU1; que certifique la tesis completa; que un PASS estructural equivalga a cierre científico; **que los dos `FAIL` de RB-05 se presenten como aprobación, o que la renuncia a una tercera ronda sustituya a un PASS** |

### Afirmaciones de sistema, derivadas de HU5 y HU6

| Enunciado permitido | Clasificación | Evidencia primaria | Límite |
| --- | --- | --- | --- |
| El circuito de retroalimentación humana está implementado end-to-end y registra correcciones con su linaje temporal | DEMOSTRADA como **evidencia técnica** | HU5 integrada; pruebas del repositorio; complemento H ejecutado sobre él | Evidencia técnica **nunca** es eficacia científica. La implementación funcional no prueba beneficio |
| La arquitectura de integración y la interfaz del productor existen y son operables | DEMOSTRADA como **evidencia técnica** | HU6; `frontend/` idéntico a `main` | No se ensayó con usuarios finales; no hay medición de uso ni de latencia operativa |

### No demostrado, enunciado de frente

Ninguna de estas afirmaciones tiene evidencia propia en este trabajo y **ninguna
se insinúa** en la memoria:

1. Superioridad general de IA, ensambles o aprendizaje profundo sobre líneas de base.
2. Validación agronómica, eficacia de campo o ahorro de agua.
3. Estrés fisiológico de los cultivos: el objetivo es un proxy P20 sobre humedad de reanálisis.
4. Mejora causada por el feedback humano.
5. Detección humana de errores de etiqueta: fue **0 de 4** sobre las únicas cuatro determinables.
6. Generalización geográfica más allá de Pergamino; Balcarce no alimenta la comparación principal.
7. Anticipación operativa o latencia de alerta.
8. Robustez ante sensores caídos o mediciones ausentes.
9. Desempeño sobre humedad continua.
10. Detección reservada de corrupciones.

### Trabajo futuro, con la evidencia que cada ítem exigiría

| Trabajo futuro | Evidencia nueva que haría falta |
| --- | --- |
| Validación agronómica de campo | Campaña prospectiva multi-sitio con observación humana independiente de si las predicciones se corresponden con la realidad, declarada por el propio operador |
| Beneficio real del feedback humano | Protocolo prospectivo con revisores múltiples, cegamiento efectivo, rechazo y recalibración sucesiva ejercitados, y tamaño muestral que admita intervalos |
| Desempeño sobre humedad continua | Complemento R: diseño congelado, runner validado, MAE/RMSE en m³/m³ y comparación contra persistencia |
| Detección reservada de corrupciones | Complemento N: fit sólo sobre train, inyección reservada conocida, matriz de confusión y soporte |
| Robustez ante mediciones ausentes | Complemento S: cuatro condiciones fijas, cinco semillas, target limpio común, máscaras e imputación registradas |
| Generalización geográfica | Réplica del protocolo v4 en al menos un segundo sitio, con su propia procedencia y su propio holdout |
| Sensores propios en campo | Ingesta real, no reanálisis; procedencia, calibración y custodia propias |

### Regla que sobrevive al cierre

`NOT_REQUIRED` limita la afirmación; **no** elimina el requisito de la tesis ni
convierte la ausencia de evidencia en evidencia de ausencia. Resultados
negativos, persistencia superior, `SIN_GANADOR_ESTABLE` y `NO_RECALIBRATION` son
resultados válidos del protocolo, no defectos a corregir.
