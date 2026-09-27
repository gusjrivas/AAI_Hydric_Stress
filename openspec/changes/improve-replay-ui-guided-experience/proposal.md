# Change: Mejorar la presentación e interacción del recorrido de reproducción histórica

## Estado de este documento

**Implementado (frontend, sin cambios en backend ni en contratos).** Esta
entrega mejora la presentación y la interacción de la capacidad
`historical-replay` ya especificada e implementada
(`openspec/changes/add-causal-historical-replay/`), sobre la evidencia y el
filtrado de causalidad ya existentes en el backend. No entrena, no infiere,
no recalcula métricas, no cambia el candidato autorizado ni los contratos de
la API de solo lectura.

## Trazabilidad

- **Épica:** 4. Evaluación experimental (con superficie en Épica 3,
  integración de arquitectura, por el retoque de navegación).
- **Historia de usuario:** HU8 (demostración retrospectiva para memoria y
  defensa) y HU6 (`architecture-integration`, por la integración de esta
  vista en la navegación principal de la interfaz).
- **Capacidades OpenSpec afectadas:** `historical-replay` (comportamiento de
  presentación e interacción, sin tocar RH-01…RH-13 del backend, que ya
  garantizan la causalidad) y `alerting-ui` (la navegación pasa de cinco a
  seis destinos).
- **Fase CRISP-DM:** Evaluación (presentación de evidencia ya generada), no
  modelado ni despliegue nuevo.
- **Configuración experimental afectada:** ninguna. No se modifica
  `controlled_daily_v3`, el candidato `base-seed4`
  (`run_id 1157696b7bb941e394c5af530c762b07`), datasets, manifiestos, hashes
  ni resultados científicos históricos. No se ejecuta A/B/C ni se abre
  ningún holdout.
- **Impacto sobre hipótesis, propósito, alcance o arquitectura:** ninguno.

## Why

El relevamiento dirigido (ver `design.md`) confirmó que la implementación
previa (PR #214, `f17fe65`) ya resolvía correctamente el filtrado causal en
el backend, pero la presentación no permitía a una persona sin conocimiento
de la implementación seguir el recorrido **datos disponibles → predicción
archivada → revelación de observaciones → explicación del resultado** sin
explicación oral:

- El origen de la predicción y el reloj simulado eran selecciones
  independientes; cambiar el origen no reubicaba el reloj ni ocultaba el
  resultado anterior, lo que podía leerse como una alerta persistente de un
  caso ya abandonado.
- El gráfico mostraba humedad histórica por índice de fila (no por escala
  temporal real) y no integraba el umbral, el origen, el objetivo ni el
  resultado en una sola lectura.
- La comparación se expresaba como "Coincide/Discrepa", sin distinguir las
  cuatro categorías de resultado (alerta correcta / falsa alerta / omisión /
  ausencia correcta) ni la distancia física al umbral.
- El acceso a la vista vivía en un enlace aparte, fuera de la navegación
  principal de cinco destinos, sin estado activo.

## What Changes

- **Navegación:** "Explorar una predicción" pasa a ser un destino más de
  `useHashRoute`/`DestinationNav` (antes un enlace aparte sin
  `aria-current`), preservando los cinco destinos y anchors existentes.
- **Selección temporal comprensible:** origen y reloj dejan de ser
  independientes — cambiar el origen reubica el reloj en él y oculta de
  inmediato cualquier resultado anterior; se distingue explícitamente la
  fecha de los datos usados para predecir, la fecha alcanzada por la
  reproducción y la fecha objetivo; "Volver al inicio de este caso" ahora
  conserva el origen (antes lo reiniciaba al primero disponible); se agrega
  la acción principal "Ver qué ocurrió el [fecha objetivo]".
- **Gráfico principal integrado:** reescritura de `MoistureHistoryChart` con
  escala temporal real (incluye días ausentes por completo, no solo valores
  nulos), marcadores de origen/objetivo, línea de umbral con sombreado,
  intervalo futuro todavía oculto explícito, estilo distinto para
  observaciones reveladas, ventana inicial de ~30 días con ampliación
  explícita, y una banda separada del eje numérico para la clase predicha
  (nunca una curva de humedad pronosticada).
- **Predicción explicada en palabras** (`ReplayPredictionSummary`) y
  **comparación explicativa** (`ReplayComparisonCard`, con las cuatro
  categorías y la distancia con signo al umbral, denominada explícitamente
  "distancia física", nunca "error del modelo").
- **Estados explícitos** para cargando / predicción no disponible /
  resultado todavía oculto / observación no disponible / revelado / error de
  consulta, sin convertir ausencia o error en "sin alerta".
- Sin cambios en `backend/app/routers/replay.py`,
  `backend/app/schemas_replay.py`, ni `src/historical_replay/`: se reutilizan
  los contratos existentes en su totalidad.

## Impact

- **Specs afectadas:** `historical-replay` (delta de comportamiento de
  presentación/interacción, ver `specs/historical-replay/spec.md`) y
  `alerting-ui` (delta de navegación, ver `specs/alerting-ui/spec.md`).
- **Specs consumidas sin cambios:** contratos RH-01…RH-13 del backend
  (`add-causal-historical-replay`), `human-feedback`.
- **Fuera de alcance:** cualquier cambio de backend, entrenamiento,
  recalibración, holdout, o candidato/horizonte distinto de `base` +3 días.
- **Impacto sobre memoria técnica:** ninguno declarado en este *change*; la
  mejora de presentación puede citarse como evidencia de usabilidad en el
  capítulo 3, sin modificar su contenido en este PR.

## Verificación

Ver `tasks.md` para el desglose y `docs/adr` no aplica (no hay decisión
arquitectónica nueva, solo de presentación). Pruebas: `frontend/src/features/historical-replay/*.test.{ts,tsx}`
y `frontend/src/App.test.tsx` (ver reporte de verificación en la descripción
del PR).
