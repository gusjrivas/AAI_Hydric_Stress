# PASO 0 — Verificación final acotada

Fecha: 2026-09-22
Alcance: comprobación final acotada, complementaria a `paso0-relevamiento.md` y
`paso0-ampliacion.md`, que se conservan sin modificar. Exclusivamente
inspección y documentación. No se implementó código, no se entrenó ni
ejecutó ningún modelo nuevo, no se generó ninguna predicción nueva, no se
recalcularon métricas, no se accedió a la ventana C / holdout Pergamino
2024–2025, no se instaló ninguna dependencia, no se hizo commit, push, PR ni
merge.

## Estado del entorno antes de esta pasada

- Rama `feat/causal-historical-replay`, worktree
  `C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Verificado antes de
  empezar: único cambio en el árbol eran los dos informes previos ya
  entregados (uno staged, uno sin trackear). Se preservaron intactos; no se
  cambió de rama ni se modificó la base.

## 1. Corrección de criterio aplicada en esta pasada

Se adopta explícitamente la corrección indicada: **no se exige feedback
histórico ya existente**. El feedback puede ser una entidad nueva a registrar
durante una demostración futura, vinculada a la predicción original sin
alterarla. La ausencia de `feedback__<sensor>.parquet` con contenido útil
**no** se interpreta como ausencia de predicciones científicas archivadas —
se buscaron las predicciones en sí, en las salidas de las corridas
científicas (Etapa A / Etapa B / protocolo v3), no solo en el store operativo
de feedback humano.

## 2. Resolución del bloqueo de lectura de parquet

En las dos pasadas anteriores, la ausencia de intérprete Python en este
worktree obligó a inspeccionar los `.parquet` por extracción de tokens ASCII
imprimibles, que no permite leer valores numéricos ni fechas reales. En esta
pasada se resolvió sin instalar nada:

- Se verificó que WSL (Ubuntu) está disponible, pero sin `pandas` instalado
  — no se instaló nada ahí.
- Se usó el contenedor Docker `aai-hydric-stress-backend-1`, que **ya estaba
  corriendo** (parte de la arquitectura real declarada en ADR-0004, "Up 2
  days" al momento de la verificación — no se levantó ningún servicio nuevo),
  con `pandas 2.3.3` y `pyarrow 19.0.1` ya instalados. La lectura se hizo
  **por pipe de stdin** (`docker exec -i ... python -c "..." < archivo.parquet`),
  sin `docker cp`, sin escribir nada dentro del contenedor, sin instalar
  dependencias adicionales. Método de solo lectura verificado.

Resultados de lectura real (reemplazan la inspección por tokens de las
pasadas anteriores donde aplica):

- **`data/melchor_romero_2024_consolidado.parquet`**: 366 filas,
  2024-01-01 → 2024-12-31 (confirmado por rango real de la columna de fecha,
  no por nombre de archivo). Columna `origen` con **único valor `'real'`**
  para las 366 filas — confirma dato real, no inferido del nombre. `soil_moisture`
  con 88 valores nulos (huecos de cobertura reales). Columnas agronómicas
  presentes en el esquema (`et0`, `canopy_temperature`, `ndvi`,
  `stomatal_conductance`, `leaf_water_potential`) están **100% nulas
  (366/366)** — el dataset real solo tiene meteorología y humedad de suelo;
  las variables agronómicas que sí aparecen pobladas en los `sensor__demo-*`
  sintéticos no existen en este dataset real. Esto refuerza, con evidencia
  numérica directa, la distinción ya hecha en `paso0-ampliacion.md` entre el
  pipeline científico real y la simulación de demo.
- **`data/feedback_ui.parquet`**: confirmado con lectura real, 71 filas,
  columnas exactas `['fecha', 'alerta_generada', 'estado_validacion',
  'etiqueta_corregida', 'observacion']` — sin `model_version`,
  `target_timestamp` ni `y_proba`. Confirma numéricamente la corrección ya
  hecha en la ampliación anterior (no es un candidato de evidencia de
  procedencia temporal).
- **`data/feedback__demo-139b36b992.parquet`**: 2 filas, `fecha`
  2026-02-01/02, `target_timestamp` 2026-02-04/05, `model_version` con
  valores tipo hash, `issued_at` = 2026-09-18. Fechas de 2026, no de un
  período histórico real de 2024 — confirma que el ciclo demo simula una
  ejecución reciente, no un recorrido histórico real.

## 3. Inventario de predicciones científicas fuera del store de feedback

**Hallazgo central de esta pasada.** El servidor MLflow real (arquitectura
Postgres+MinIO+Docker de ADR-0004, puerto 5000, ya corriendo — no se levantó
nada nuevo) expone dos experimentos del **protocolo v3**:
`hu7-controlled-daily-v3-formal` (id 4) y `hu7-controlled-daily-v3` (id 3).
Se consultó exclusivamente vía API HTTP de solo lectura de MLflow
(`experiments/search`, `runs/search`, `artifacts/list`, `get-artifact`); no se
deserializó ningún modelo ni se ejecutó inferencia.

Antes de inspeccionar cualquier run, se listaron **todos** los experimentos
disponibles en ambos servidores MLflow accesibles (puertos 5000 y 5001):
ninguno se llama `v4`, `pergamino`, `holdout` ni `C`. No se accedió a ningún
artefacto de la ventana C / holdout Pergamino 2024–2025 en esta pasada.

Cada run del experimento v3 (ejemplo inspeccionado: config `base-seed4`,
`run_id 1157696b7bb941e394c5af530c762b07`, status `FINISHED`) tiene un
artefacto **`predictions.json`** con filas del tipo:

```json
{"timestamp":"2024-10-19T00:00:00.000","target_timestamp":"2024-10-22T00:00:00.000",
 "target_observed": true, "y_true": 1.0, "y_proba": 0.44, "y_pred": 0,
 "persistence": 1, "majority_class": 0, "always_stress": 1}
```

Registro por candidato (`base-seed4`, experimento v3):

| Campo pedido | Valor / evidencia |
|---|---|
| Ruta y campaña | MLflow experimento `hu7-controlled-daily-v3-formal` (id 4), run `1157696b7bb941e394c5af530c762b07`, config `base-seed4`; protocolo v3, **no v4/holdout** |
| Disponibilidad | Local, accesible vía servidor MLflow real ya corriendo (Postgres+MinIO+Docker), no un checkout de archivos sueltos |
| Procedencia de datos | `effective_configuration.json` del mismo run declara `training_dates` en 2024, fechas reales y discontinuas, consistentes con los huecos de cobertura ya confirmados en `melchor_romero_2024_consolidado.parquet` |
| Origen y fecha objetivo del pronóstico | `timestamp` (origen, ej. 2024-10-19) → `target_timestamp` (ej. 2024-10-22) en el mismo registro |
| Horizonte y unidad | +3 días, confirmado por la diferencia entre `timestamp` y `target_timestamp` en múltiples filas |
| Variable predicha | `y_proba`/`y_pred` de estrés hídrico (etiqueta binaria), con baselines de comparación en el mismo artefacto (`persistence`, `majority_class`, `always_stress`) |
| Identidad del modelo | `run_id` + `effective_configuration.json` (hiperparámetros, semillas, `contract.pipeline_version: "controlled_daily_v3"`) |
| Evidencia del corte de entrenamiento | `training_dates` explícito en `effective_configuration.json` del mismo run |
| Vínculo con observación posterior | `y_true` y `target_observed` **ya incluidos en el mismo artefacto** — no requiere feedback humano nuevo porque es un backtest retrospectivo, no un stream en producción |
| Restricciones y comprobaciones pendientes | Ver §5 |

Configuraciones disponibles en el mismo experimento: `base`, `completa`,
`anomalias`, `coverage_fraction_0.5`, `recent_fraction_0.5`,
`noise_test_only_0.3`, `noise_both_0.3`, `sinteticos`. `base`/`completa` son
los candidatos no perturbados por diseño declarado, pero no se verificó en
esta pasada si `base` aplica en la práctica algún ruido residual (ver §5).

No se generalizó a partir de este único run: se listaron todos los
experimentos antes de elegir uno, y se identificó la existencia de múltiples
configs y semillas dentro del mismo experimento v3, sin inspeccionar los 96
runs uno por uno (limitación explícita, ver §5).

**Naturaleza distinta de este vínculo predicción↔observación**: a diferencia
del ciclo `forecast.py`→`feedback__<sensor>.parquet` (predicción emitida,
feedback humano registrado después, ambos con timestamps de emisión/validación
separados), este mecanismo es un **backtest retrospectivo formal de v3**: la
observación (`y_true`) ya está resuelta en el mismo artefacto porque la
corrida evalúa un período ya cerrado, no una predicción emitida en producción
esperando validación humana. Debe presentarse como tal — evidencia de
evaluación retrospectiva formal de v3, no como un caso de "predicción emitida
en producción y luego validada por un humano".

## 4. Reconciliación de restricciones (con contexto completo)

**Cita del README, contexto completo**
(`openspec/scientific-closure/README.md`, líneas ~40-72): la frase "Excluye...
inspección de holdouts cerrados..." aparece dentro de una sección que
enumera el alcance de **una campaña específica**: el cierre de
`controlled_daily_v4` (gates A→B→C, dossier RB-05, RB-03), descrita en el
mismo documento inmediatamente antes. No es una regla de alcance para todo el
repositorio ni para todo experimento científico existente; es el alcance de
esa campaña de cierre puntual. El "holdout cerrado" al que se refiere es
específicamente Pergamino 2024–2025 (Etapa C de `controlled_daily_v4`).

**Protocolo v4 §16**: la prohibición de "analizar valores, clases ni métricas
de 2024–2025" es, por su propio texto y ubicación (protocolo de
`controlled_daily_v4`), específica de esa ventana temporal de esa campaña —
no se encontró, en esta ni en las pasadas anteriores, ninguna cláusula que
extienda esa prohibición a los experimentos v3 (`hu7-controlled-daily-v3` /
`hu7-controlled-daily-v3-formal`), cuyo período de entrenamiento/evaluación es
2024 pero **no** corresponde a la ventana de holdout de v4.

No se hallaron, en esta pasada, citas contradictorias entre sí sobre este
punto específico.

**Clasificación de las tres acciones pedidas:**

- **(i) Leer un resultado ya archivado y publicado de A/B/v3**: no alcanzado
  por la exclusión de "inspección de holdouts cerrados" (específica de la
  campaña v4/Pergamino, según el contexto completo de §4) ni por el FAIL de
  RB-05 (defecto de gobernanza de proceso de v4, ya establecido en
  `paso0-ampliacion.md`). Leer los `predictions.json` de runs `FINISHED` de
  v3 no encuentra, en esta pasada, ninguna prohibición textual aplicable.
- **(ii) Ejecutar una nueva evaluación**: sigue prohibido —
  `PREPARATION_ONLY` excluye explícitamente "ejecución científica durante
  preparación". No se ejecutó ninguna evaluación nueva en esta pasada; solo
  se leyeron artefactos ya persistidos de runs `FINISHED` preexistentes.
- **(iii) Usar datos para ajustar o seleccionar modelos**: no aplica a lo
  hecho en esta pasada; no se ajustó ni seleccionó nada.

Esta clasificación resuelve documentalmente el alcance de la prohibición
citada respecto de los runs v3 inspeccionados. No se asumió permiso para
inspeccionar C, y no se accedió a C.

## 5. Comprobaciones pendientes y limitaciones explícitas

- No se confirmó si la config `base`/`completa` aplica o no ruido/perturbación
  en la práctica (el esquema de `effective_configuration.json` de
  `base-seed4` incluye campos de semilla de ruido aunque el nombre de la
  config sugiera ausencia de perturbación). Antes de especificar el Paso 1
  sobre este run puntual, debe compararse explícitamente `y_proba`/features
  contra el dataset crudo para confirmar ausencia real de perturbación —
  pendiente, no resuelto en esta pasada por límite de tiempo.
- No se inspeccionaron los 96 runs del experimento uno por uno; no puede
  descartarse con certeza absoluta que alguno de ellos tenga una marca
  interna de asociación con la ventana Pergamino/holdout, aunque no se halló
  ninguna señal de eso en los experimentos listados ni en el run inspeccionado.
- Si el Paso 1 requiere demostrar específicamente el flujo de feedback humano
  post-hoc (no solo un backtest ya resuelto), el candidato de esta sección
  debe combinarse con el contrato de `human_feedback/*` sobre un
  `target_timestamp` real de este mismo run, registrando el feedback como
  entidad nueva sin alterar la predicción archivada — tal como habilita la
  corrección de criterio adoptada en §1. Esa combinación no fue construida ni
  probada en esta pasada; es una recomendación para el Paso 1, no un hecho
  verificado.
- No se afirma que no existan más candidatos fuera de lo inspeccionado en
  esta pasada acotada (por ejemplo, artefactos de Etapa A/B fuera de MLflow,
  en algún directorio `results/`/`artifacts/` no relevado); no se encontró
  ninguno de ese tipo en la búsqueda realizada, pero la búsqueda no fue
  exhaustiva sobre todo el árbol del repositorio.

## Resultado

**A — Candidato acreditado para especificar el recorrido.**

El caso concreto verificable: cualquier run `FINISHED` de los experimentos
`hu7-controlled-daily-v3-formal` / `hu7-controlled-daily-v3` en el servidor
MLflow real (puerto 5000), por ejemplo `base-seed4`
(`run_id 1157696b7bb941e394c5af530c762b07`) — dato real confirmado
(`origen='real'` en el parquet fuente, con lectura numérica directa),
predicción archivada real con `timestamp`/`target_timestamp`/`y_proba`,
horizonte +3 días confirmado, observación ya vinculada en el mismo artefacto
(`y_true`, `target_observed`), modelo identificable por `run_id` +
`effective_configuration.json`, corte de entrenamiento explícito
(`training_dates`). No se tocó, en la obtención de este candidato, ningún
artefacto de la ventana C / holdout Pergamino 2024–2025.

Este resultado corrige el veredicto de "ningún ejemplo completo acreditable"
que constaba en `paso0-ampliacion.md` (§5 de ese informe) — esa conclusión
era correcta bajo el criterio vigente en ese momento (que exigía feedback
histórico ya registrado y no contemplaba los backtests de v3 como fuente de
predicciones archivadas), pero queda superada por la corrección de criterio
adoptada en esta pasada (§1) y por el hallazgo de esta sección.

No obstante, este resultado A no habilita todavía redactar el Paso 1 sin más:
quedan pendientes las comprobaciones de §5 (perturbación real de la config
`base`, cobertura de los 96 runs, y la construcción — no verificación — del
enlace con `human_feedback/*` para el flujo de feedback post-hoc).

## Cierre

Diff de esta tarea: exclusivamente este archivo nuevo
(`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso0-verificacion-final.md`),
que convive con `paso0-relevamiento.md` y `paso0-ampliacion.md` sin
modificarlos, en la rama `feat/causal-historical-replay`. No se modificó
ningún archivo existente, no se ejecutó entrenamiento/inferencia/recálculo de
métricas, no se generó ninguna predicción nueva, no se accedió a la ventana C
/ holdout Pergamino 2024–2025, no se instaló ninguna dependencia, no se
levantó ningún servicio nuevo (el contenedor Docker usado ya estaba
corriendo), no se hizo commit, push, PR ni merge. Se detiene aquí para
revisión.
