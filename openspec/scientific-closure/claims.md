# Afirmaciones y suficiencia

Ninguna fila afirma resultados futuros. El change sc-01-evidence-scope debe
contrastar evidencia existente permitida antes de decidir nuevas ejecuciones.
El alcance de project.md incluye evaluar contribuciones de componentes, pero
no exige demostrar una mejora positiva. No retirar componentes de la hipótesis
para poder declarar cierre. Si faltan criterios de suficiencia aprobados,
UNRESOLVED bloquea el cierre global, no impone cuatro runners automáticamente.

| ID | Afirmación susceptible de sostenerse | Evidencia mínima / límite | Necesidad del complemento |
| --- | --- | --- | --- |
| CL-01 | Comparación retrospectiva P20 entre familias en Pergamino | A íntegra, soporte y selección conforme protocolo; exploratoria | R/H/N/S no necesarios para esta afirmación |
| CL-02 | Validación temporal de candidato congelado | B única; si no valida, solo afirmar que no superó el gate | Sin complemento |
| CL-03 | Desempeño temporal final 2024–2025 | C autorizada después de B validada; sin selección | Sin complemento; no afirmar si C no se abre |
| CL-04 | Aporte de sintéticos/anomalías como predictores en referencia v3 | Evidencia formal v3 con límites originales, preservada | N no es necesario para repetir fielmente esta afirmación limitada |
| CL-05 | Error de predicción de humedad continua t+3 | Evaluación de regresión con MAE/RMSE y baselines, no clasificación | R solo si se incorpora/sostiene esta afirmación; fuera del objetivo P20 principal |
| CL-06 | Aporte cuantitativo de correcciones supervisadas | Comparación prospectiva de tres brazos; no basta integración HU5 | H u otra evidencia equivalente válida si la afirmación se sostiene; insuficiencia actual documentada |
| CL-07 | Detección de corrupciones reservadas | Fit train, referencia de corrupción y evaluación reservada | N si se sostiene esa afirmación; no implica detectar anomalías reales |
| CL-08 | Robustez ante ausencia de mediciones y ruido hipotético | Máscaras/ruido predeclarados, target limpio, mismas fechas | S si la evidencia previa no cubre la afirmación; etiquetas escasas no bastan |
| CL-09 | Anticipación al inicio de episodios retrospectivos | Onset con t+3, censuras, falsos avisos y soporte | Métricas v4; no anticipación operativa demostrada |
| CL-10 | Cierre del alcance de tesis | Mapeo hipótesis/componentes a evidencia y límites explícitos | Decisión de suficiencia global pendiente, no derivada de CL-01 solamente |

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
