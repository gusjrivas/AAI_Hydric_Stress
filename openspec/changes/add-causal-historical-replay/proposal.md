# Change: Add causal historical replay (demostración de reproducción histórica)

## Estado de este documento

**Candidato habilitado para implementación, con limitaciones documentadas y
no bloqueantes.** Revisión dirigida (`paso1-revision-dirigida.md`) completó,
en modo lectura sobre servicios ya disponibles (API MLflow, git, contenedor
Docker en ejecución), las comprobaciones de procedencia, temporalidad,
perturbación e interpretación de los datos que la versión anterior de este
documento dejaba pendientes. No quedan bloqueos materiales sobre el candidato
`base-seed4` (`design.md` §2–§3); persisten dos limitaciones no bloqueantes,
correctamente disclosables (ausencia de evidencia de calibración de
`y_proba`; marcador de imputación del historial pre-corte no persistido en
los artefactos del run, aunque el mecanismo que lo produce sí existe y es
determinístico — ver `design.md` §9). Este estado no autoriza todavía commit
de código, ejecución de modelos, ni acceso a la ventana C / holdout Pergamino
2024–2025: sigue siendo una especificación, no una implementación.

## Trazabilidad

- **Épica:** 4. Evaluación experimental.
- **Historia de usuario:** HU8 — análisis de resultados (demostración
  retrospectiva para memoria/defensa), apoyada en capacidades ya implementadas
  de HU5 (`human-feedback`) y HU7 (`experiment-runner`), sin modificarlas.
- **Fase de CRISP-DM:** Evaluación (lectura de evidencia ya generada), no
  modelado ni despliegue nuevo.
- **Configuración experimental afectada:** ninguna. No modifica `controlled_daily_v3`,
  grillas, semillas, hipótesis, propósito ni arquitectura. Lee, sin recalcular,
  un run `FINISHED` ya persistido del protocolo v3.
- **Insumo de diseño:**
  [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md)
  (contrato de retroalimentación, reutilizado sin alterar),
  [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md)
  (contrato de registro en MLflow de las corridas v3),
  `docs/research/protocolo-experimental-v3.md` (definición del experimento,
  contrato del modelo, ruido, escasez),
  `openspec/scientific-closure/causal-historical-replay-2026-09-22/` (los tres
  informes de relevamiento que preceden esta propuesta).

## Why

El Trabajo Final necesita una demostración defendible, con datos reales, de
que el sistema respeta causalidad temporal estricta entre predicción y
observación: mostrar una fecha histórica, ocultar el futuro no revelado,
emitir/exhibir la predicción archivada, avanzar el reloj, y solo entonces
revelar la observación real y registrar retroalimentación nueva. Ningún
componente actual arma ese recorrido como una vista unificada — hoy son piezas
separadas (`forecast`, `feedback`, `lineage`, corridas de `experiment-runner`)
sin una capa de "replay". El relevamiento de Paso 0 (tres informes en
`openspec/scientific-closure/causal-historical-replay-2026-09-22/`) identificó
un candidato acreditado con datos reales para especificar ese recorrido: un
run `FINISHED` del experimento `hu7-controlled-daily-v3-formal`, config
`base-seed4`, `run_id 1157696b7bb941e394c5af530c762b07`.

## What Changes

- **Nueva capacidad `historical-replay`**, de solo lectura sobre evidencia ya
  persistida: no entrena, no infiere, no recalcula métricas, no genera
  predicciones nuevas.
- **Entidades nuevas** (ver `design.md` §4): predicción histórica identificable,
  la proyección pública que la muestra según el reloj vigente,
  observación/etiqueta posterior, estado del reloj de reproducción, feedback
  de demostración — aisladas del entrenamiento y de la recalibración
  automática.
- **Filtrado de causalidad en el backend** (no solo en el frontend): ninguna
  respuesta expone `y_true`/`target_observed`/baselines de una fecha objetivo
  todavía no alcanzada por el reloj simulado.
- **Reutilización sin modificación** del contrato `human_feedback/*`
  (`schema.py`) para registrar feedback de demostración, separando su fecha
  real de registro de la fecha simulada, sin disparar recalibración ni tocar
  el `feedback_log` operativo de ningún sensor real.
- **Diseño (no implementación) de un paquete de lectura reproducible** para la
  defensa, con artefactos y hashes, que evite depender de una consulta viva a
  MLflow durante la exposición.
- Este *change* **no** incluye código, tests, ni el paquete de lectura
  exportado — ver `tasks.md` para el desglose y su estado (`[ ]` = no
  iniciado).

## Impact

- **Specs afectadas:** nueva capacidad `historical-replay` (`ADDED
  Requirements`, ver `specs/historical-replay/spec.md`).
- **Specs consumidas sin cambios:** `human-feedback` (contrato de
  retroalimentación), `experiment-runner` (artefactos `predictions.json` /
  `effective_configuration.json` del protocolo v3).
- **Código futuro (fuera de este change):** un módulo nuevo de lectura de
  runs v3 + reloj de reproducción; posible endpoint de solo lectura análogo a
  `GET /lineage/{sensor_id}`; reutilización de
  `src/human_feedback/schema.py` para el feedback de demostración.
- **Fuera de alcance de este change:** implementación de backend/frontend,
  exportación del paquete de lectura, cualquier ejecución A/B/C, apertura de
  holdout, entrenamiento o recalibración real, y todo lo referido a `+1`/`+2`
  días u otros runs/experimentos fuera de `base-seed4` (ver `design.md` §8
  sobre por qué no se generaliza a los 96 runs del experimento).
- **Impacto sobre hipótesis, propósito, alcance o arquitectura:** ninguno.
  Impacto sobre memoria técnica: capítulo 2 (evaluación retrospectiva vs.
  utilidad agronómica no demostrada, ver `design.md` §10) y capítulo 3
  (custodia/reproducibilidad de la demostración, capturas previstas en
  `design.md` §10). No se propone ninguna modificación al capítulo 2, ya
  corregido.
- **Impacto sobre cronograma/entregables:** ninguno declarado con precisión
  nueva; se mantiene la referencia de 600 horas del plan de tesis sin
  desagregar por instrucción explícita de no inventar estimaciones de
  esfuerzo.

## Alternativas consideradas

- **Usar `demo_sessions/*` (datos sintéticos de la demo del productor) en vez
  de un run real de v3**: descartada para esta primera entrega porque el
  pedido exige datos reales; `demo_sessions` está confirmado como sintético
  sin ambigüedad (`paso0-ampliacion.md` §2.2). Queda disponible como base para
  una demo *no* causal-histórica (ya cubierta por `demo-simulation`).
- **Usar el holdout Pergamino 2024–2025 (`controlled_daily_v4`, Etapa C) como
  candidato**: descartada, prohibida por gobernanza vigente (protocolo v4 §16,
  apertura única e irreversible del holdout, `scientific-closure/README.md`).
- **Exigir el ciclo completo predicción→feedback humano ya registrado
  históricamente antes de aceptar un candidato**: descartada tras la
  corrección de criterio de `paso0-verificacion-final.md` §1 — el feedback
  puede ser una entidad nueva a registrar durante la demostración, vinculada a
  la predicción original sin alterarla; exigir feedback histórico ya
  registrado habría dejado sin candidato viable (`paso0-ampliacion.md` §5).
- **Reabrir/ampliar el relevamiento a los 96 runs del experimento v3 antes de
  especificar**: descartada para esta primera entrega por instrucción
  explícita de no exigir varios modelos para aceptar el primer recorrido; se
  documenta como límite de generalización, no como bloqueo (`design.md` §8).

## Estado: especificación, candidato habilitado (no implementado)

Ver `tasks.md` para el desglose de tareas pendientes, ordenado (paquete y
lector → validaciones → API → interfaz → feedback → verificación del
recorrido y capturas), y `traceability.md` para la matriz requisito → prueba
prevista → evidencia, incluidas las nuevas pruebas de elegibilidad temporal
(RH-11), vinculación cruzada (RH-12) y separación de umbrales (RH-13). Ningún
ítem de este *change* tiene código, test ni evidencia de ejecución todavía.
