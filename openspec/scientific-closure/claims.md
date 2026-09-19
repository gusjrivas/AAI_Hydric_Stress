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
