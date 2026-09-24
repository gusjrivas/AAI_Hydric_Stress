# PASO 1 — Especificación de la reproducción histórica v3

Fecha: 2026-09-23. Actualizado el mismo día tras la revisión dirigida (ver
`paso1-revision-dirigida.md`, que corrige y completa lo que sigue).
Alcance: exclusivamente documentación e inspección en modo lectura sobre
servicios y dependencias ya disponibles (API MLflow, git, contenedor Docker
en ejecución). No se implementó código de aplicación, no se entrenaron ni
ejecutaron modelos, no se generó ninguna predicción nueva, no se
recalcularon métricas científicas, no se accedió a la ventana C / holdout
Pergamino 2024–2025, no se instaló ninguna dependencia, no se hizo commit,
push, PR ni merge.

## Continuidad

Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Se preservaron intactos,
sin modificar, los tres informes de Paso 0
(`paso0-relevamiento.md`, `paso0-ampliacion.md`, `paso0-verificacion-final.md`),
en el mismo directorio. Este documento no repite ese relevamiento; lo cita y
continúa desde su resultado.

## Candidato verificado

`paso0-verificacion-final.md`, sección "Resultado": experimento
`hu7-controlled-daily-v3-formal` (MLflow `experiment_id=4`), run hijo
`FINISHED` `1157696b7bb941e394c5af530c762b07` (`base-seed4`), anidado bajo el
run padre `6d516bb9f778450f8fbe2e5492818e57` (`base`). No se extendieron
conclusiones a otros runs del mismo experimento (96 runs totales, no
inspeccionados uno por uno — no bloquea este paso por instrucción explícita,
ver `design.md` §8).

## Qué produce este paso

La especificación completa quedó redactada como un *change* de OpenSpec,
siguiendo la convención del repositorio, en
`openspec/changes/add-causal-historical-replay/` (`proposal.md`,
`design.md`, `specs/historical-replay/spec.md` con 13 requisitos
`RH-01`..`RH-13`, `tasks.md`, `traceability.md`). Este documento no duplica
ese contenido; remite a él como fuente.

## Comprobaciones del candidato: resultado actualizado

La primera versión de este paso dejó pendientes, sin intentar resolverlas,
las comprobaciones de procedencia, temporalidad, perturbación e
interpretación de la salida. La revisión dirigida las completó consultando
en modo lectura la API real de MLflow (puerto 5000), el contenedor Docker en
ejecución de la arquitectura ADR-0004, y el historial de git del commit
exacto que produjo el run (`2a40ee68c52d2eb5e2040a36b1029f756f9c048a`,
ancestro verificado del `HEAD` actual, árbol de trabajo limpio en el momento
de la ejecución). Resultado (evidencia exacta y fuentes en
`paso1-revision-dirigida.md` y `design.md` §2–§3):

- **Procedencia:** **resuelta**. `dataset_sha256` capturado por la propia
  canalización en el momento de la ejecución (2026-09-05), corroborado hoy
  contra el archivo real en el contenedor en ejecución — vinculación
  verificada por hash de ejecución, no por coincidencia de fechas.
- **Temporalidad y modelo fijo:** **resuelta**. Código confirma un único
  modelo fijo (`RandomForestClassifier`, sin folds) entrenado una vez;
  entrenamiento purgado por fecha objetivo (`target_timestamp < cutoff`),
  con valores concretos consistentes (última fecha de entrenamiento
  `2024-10-15`, corte `2024-10-19`).
- **Perturbaciones:** **resuelta**. `noise_std_ratio` nunca se pasa para la
  configuración `base` en el script que produjo este run — sin perturbación
  aplicada en ninguna partición, confirmado por trayectoria de código, no por
  el nombre de la configuración.
- **Separación de umbrales:** **resuelta**. Umbral de humedad que define
  `y_true` (0.31678178906440735 m3/m3, percentil 20 del entrenamiento
  limpio) y regla de decisión del clasificador que produce `y_pred`
  (`alert_threshold=0.5`, fijo) son valores distintos, confirmados por
  separado — no se asumió que fueran iguales ni se inventó un valor.
- **`target_observed` y objetivos faltantes:** **resuelta como mecanismo**,
  con una limitación de cobertura: en este candidato, las 67 filas de
  `predictions.json` tienen `target_observed=true`; el caso
  `target_observed=false` existe en el contrato pero no está ejercitado por
  ningún ejemplo real de este run.
- **Marcador de imputación:** el mecanismo **existe** (`<columna>_imputado`
  en `interpolate_missing_causal`), contrario a lo que se creía pendiente;
  no está persistido en los artefactos de este run — queda como tarea de
  implementación concreta (recomputación determinística), no como incógnita.
- **`y_proba` sin evidencia de calibración:** limitación permanente,
  confirmada activamente (el único motor de calibración del repositorio no
  aplica a este run, por fecha de introducción y por alcance de capacidad).

Ninguna de estas conclusiones se completó por inferencia: cada una cita el
código, el parámetro de MLflow o el artefacto exacto que la sostiene.

## Recorrido funcional (corregido)

El recorrido corrige el contrato temporal de la primera versión: la
predicción es visible desde que el reloj alcanza su fecha de origen,
independientemente de si su observación ya fue revelada (antes se excluía la
fila completa por su fecha objetivo futura, lo cual era incorrecto). Detalle
completo, con la proyección pública separada del registro interno, en
`design.md` §4–§5.

## Contratos y aislamiento (ampliados)

Cinco entidades (`HistoricalPredictionRecord`, `ReplayPredictionView` —
nueva, la proyección pública—, `ReplayObservation`, `ReplayClockState` con
`prediccion_seleccionada_id` separado de la fecha simulada, y
`ReplayFeedbackRecord`), detalladas en `design.md` §4. El feedback de
demostración solo puede registrarse después de la revelación, y un
retroceso del reloj oculta también el feedback ya revelado sin alterar el
registro interno — corrección nueva respecto de la primera versión.

## Documentación para la memoria

Tabla completa en `design.md` §10. No se propone ninguna modificación al
capítulo 2 (ya corregido). Se distingue explícitamente que probar el
filtrado temporal de la interfaz (una propiedad de la implementación) no
prueba que los insumos crudos estaban disponibles ese día en un escenario
operativo real (una propiedad del dato, no verificada) — ambas afirmaciones
nunca se presentan una como si demostrara la otra.

## Impacto sobre alcance, riesgos, cronograma y entregables

- Hipótesis, propósito, alcance y arquitectura del Trabajo Final: sin impacto
  identificado.
- Riesgo principal: presentar este único run como si generalizara al
  experimento completo — mitigado por `RH-09` y por la tabla de memoria.
- Cronograma/entregables: se mantiene la referencia de 600 horas del plan de
  tesis sin desagregar; no se inventa ninguna estimación de esfuerzo nueva.

## Estado de cierre

**Candidato habilitado para implementación, con limitaciones documentadas y
no bloqueantes** (ver `proposal.md`, `traceability.md`). No quedan bloqueos
materiales de procedencia, temporalidad o perturbación sobre `base-seed4`.
Persisten dos limitaciones no bloqueantes que deben disclosarse siempre:
ausencia de evidencia de calibración de `y_proba`, y marcador de imputación
del historial pre-corte pendiente de una tarea de implementación
determinística (no de una comprobación de conocimiento). Este estado sigue
sin autorizar commit de código, ejecución de modelos, ni acceso al holdout C
— es una especificación, no una implementación.

No se entrenó, no se infirió, no se recalcularon métricas, no se accedió al
holdout C. No se modificó gobernanza ni evidencia científica. No se
implementó backend/frontend ni se exportó ningún paquete en este paso. No se
hizo commit, push, PR ni merge.

## Cierre

Este documento fue actualizado el 2026-09-23 junto con
`openspec/changes/add-causal-historical-replay/` (`proposal.md`, `design.md`,
`specs/historical-replay/spec.md`, `tasks.md`, `traceability.md`) y el nuevo
`paso1-revision-dirigida.md`, que contiene el detalle completo de la
revisión dirigida. No se modificaron `paso0-relevamiento.md`,
`paso0-ampliacion.md` ni `paso0-verificacion-final.md`. Se detiene aquí para
revisión.
