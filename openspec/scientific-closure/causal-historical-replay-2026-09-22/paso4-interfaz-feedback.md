# PASO 4 — Interfaz de reproducción histórica y feedback de demostración

Fecha: 2026-09-23.
Rama `feat/causal-historical-replay`, worktree
`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`. Continúa
`paso3-api-lectura.md`. No se agregaron escenarios sintéticos, +1/+2, otros
modelos, entrenamiento, inferencia, recalibración ni métricas científicas.
No se accedió al holdout v4. No se hizo commit, push, PR ni merge.

## 1. Cierre de la incertidumbre de regresión

El informe del Paso 3 dejó dos hallazgos sin resolver de forma concluyente
(atribuidos al entorno sin comparación directa). Esta pasada los cerró:

### 1.1 `test_forecast.py::test_run_forecast_returns_verdicts`

**No atribuido al entorno solo porque el archivo no fue modificado** — se
investigó la causa real:

- `git diff <base-de-la-rama> -- backend/app/pipeline.py backend/app/routers/forecast.py src/predictive_modeling/ src/architecture_integration/ src/data_quality/ src/data_ingestion/ data/melchor_romero_2024_consolidado.parquet backend/tests/test_forecast.py` → **diff vacío** en todos los archivos: ni el código de la pipeline, ni el dataset, ni el test mismo cambiaron respecto de la base de esta rama. Cualquier fallo de este test bajo condiciones equivalentes ya existiría en la base, no lo introdujo este *change*.
- Reproducido el fallo de forma aislada: `execute_configured_pipeline` devolvía `train_rows=94`, `test_rows=0` (se esperaba `test_rows=67`, el mismo valor ya confirmado para `base-seed4` en el Paso 1).
- Diagnóstico dirigido (sin abrir una auditoría general): se llamó `run_end_to_end_pipeline` directamente con los mismos argumentos que usa `execute_configured_pipeline` → **`train=199, test=67`, correcto**. La diferencia solo aparecía al pasar por `execute_configured_pipeline`, que antes de entrenar consulta `load_latest_recalibrated_model("sensor-a", ...)` contra el MLflow del entorno.
- Se consultó el registro de modelos del contenedor compartido `aai-hydric-stress-backend-1` (`mlflow.MlflowClient().search_registered_models()`, solo lectura): **ya existía** `alerting_ui_recalibrated_model__sensor-a` (versión 1, `trained_through=2026-09-13`) — de actividad real y ajena a esta tarea (el contenedor lleva "Up 2 days"). Con ese predictor cacheado, `skip_fit=True` y `test = test[test.timestamp > trained_through]` queda vacío para un dataset que termina en 2024-12-31.
- **Comparación bajo condiciones equivalentes**, como pide la consigna: mismo código, mismo test, mismo dataset — con `MLFLOW_TRACKING_URI=sqlite:////tmp/....db` (tracking aislado, un `.db` nuevo, mismo patrón que ya usa `test_lineage.py`), **el test pasa** (4/4 en `test_forecast.py`). Con el registro ambiental preexistente del contenedor compartido, falla. Es una dependencia de aislamiento de MLflow ya ausente en `test_forecast.py` (a diferencia de `test_lineage.py`, que sí aísla), expuesta por el estado real de un contenedor de larga vida — **no una regresión de este *change***.
- No se corrigió el test en sí (pertenece a otro alcance, "no modificar componentes ajenos"); se documenta la causa y la comparación que la demuestra.

### 1.2 `test_producer_v2_emission.py`

Repuestas únicamente las dos dependencias locales que el propio archivo
importa y que faltaban en el entorno aislado (`tests/test_operational_inference.py`,
`tests/test_operational_run.py` — no todo `tests/`, solo esas dos). Con
ambas repuestas y el mismo tracking aislado: **7/7 pasan**.

### 1.3 Verificación final

```
MLFLOW_TRACKING_URI=sqlite:////tmp/....db python -m pytest backend/tests -q
```

Resultado: **123 passed, 0 failed** (creció de 117 a 123 porque esta misma
pasada agregó los tests nuevos de `/replay/predictions` y feedback,
incluidos en `backend/tests`). No hay ninguna regresión introducida por
este *change*; ambos hallazgos del Paso 3 eran ambientales.

## 2. Implementación realizada

### 2.1 Backend — API ampliada

- `GET /replay/predictions` (`list_origins`): metadatos mínimos de los
  orígenes disponibles (`{"timestamp_origen": ...}`, nada más) — permite
  elegir otro origen real sin inventar fechas faltantes.
- `ReplayEvidenceCard` en `GET /replay/candidate`: `package_id`, nombre del
  dataset, `commit_sha`, corte de entrenamiento (`split_date`), convención
  de fecha, supuesto de disponibilidad diaria — campos explícitos tomados
  del manifiesto ya verificado, nunca el manifiesto completo.
- `src/historical_replay/feedback.py` (RH-07): `ReplayFeedbackStore`
  (JSON-lines, un archivo por `package_id`, en `replay_feedback/` — nunca
  `data/feedback__<sensor_id>.parquet`, nunca dentro de `replay_packages/`),
  `register_feedback` (valida identidad de la predicción, contenido, y que
  la observación ya haya sido revelada — `FeedbackNotYetRevealedError` si
  no), `visible_feedback_for` (oculta el feedback si se retrocede el reloj,
  sin borrarlo).
- `POST /replay/predictions/{origen}/feedback`, `GET .../feedback`: el
  servidor nunca confía en que el cliente haya esperado a la revelación —
  revalida contra el registro interno del paquete.

### 2.2 Frontend — pantalla "Reproducción histórica"

`frontend/src/features/historical-replay/`: `api.ts`, `HistoricalReplayPage.tsx`,
`MoistureHistoryChart.tsx`, `ReplayEvidenceCard.tsx`, `ReplayFeedbackForm.tsx`,
`dateUtils.ts`. Ruta `#reproduccion-historica` (enlace en `App.tsx`, mismo
patrón que el enlace de "Demostración" ya existente).

- Selección determinística inicial: primer origen de `GET /replay/predictions`.
- Reloj simulado visible, con "Avanzar"/"Retroceder"/"Reiniciar"; el origen
  seleccionado se mantiene fijo en el estado de React al avanzar el reloj —
  nunca se sustituye por la predicción del nuevo día.
- Selector de otros orígenes realmente disponibles.
- Historial de humedad (`MoistureHistoryChart`) limitado al reloj simulado;
  los huecos se cortan el trazo en vez de unirse.
- Estados de carga, error, "no disponible" (backend con el feature apagado),
  predicción no encontrada y observación no disponible.
- Un contador de solicitud por `(origen, fecha simulada)` descarta cualquier
  respuesta HTTP que llegue tarde para un corte que ya no es el vigente
  (`HistoricalReplayPage.tsx`, `latestRequestKey`).
- Lenguaje: mensaje fijo de "reproducción retrospectiva", proxy estadístico
  relativo, utilidad agronómica no demostrada. `y_proba` nunca se muestra
  (ni con advertencia): decisión ya tomada en el Paso 3 y mantenida aquí.
- Ficha de trazabilidad expandible (`<details>`), con los campos pedidos.
- Formulario de feedback (`ReplayFeedbackForm`), habilitado solo cuando la
  predicción ya reveló observación; muestra el feedback ya registrado
  (`registered_at`/`simulated_at` por separado) en vez de permitir uno
  nuevo.

## 3. Resultados y límites de verificación

### 3.1 Pruebas ejecutadas

```
# Backend (entorno aislado, sin copiar código al contenedor compartido)
MLFLOW_TRACKING_URI=sqlite:////tmp/....db python -m pytest backend/tests -q
# → 123 passed

# historical_replay + constructor
python -m pytest tests -q
# → incluye 7 tests nuevos de tests/test_historical_replay_feedback.py

# Frontend
npx vitest run
# → 22 archivos, 147 passed (incluye 4 de HistoricalReplayPage.test.tsx)
npx tsc -b       # sin errores
npx oxlint ...   # 1 advertencia de estilo (set-state-in-effect), no bloqueante
```

### 3.2 Comprobación real en navegador

**Sí fue posible y se realizó.** Aislamiento: se levantó una instancia
Docker **nueva y descartable** de la misma imagen del backend
(`aai-hydric-stress-backend:latest`), con este worktree montado
(`src/`, `backend/`, `data/`, `replay_packages/`, `replay_feedback/`) y
publicada en un puerto distinto (`8099`) — el contenedor compartido
`aai-hydric-stress-backend-1` no se tocó ni se reinició en ningún momento.
El frontend se sirvió con `npm run dev` (Node ya disponible en el host de
este worktree) apuntando a ese backend aislado vía `frontend/.env`
(gitignorado). El puerto 5173 ya estaba en uso por otro proceso (probablemente
otro worktree) — no se tocó; se permitió temporalmente `http://localhost:5174`
en el CORS de `backend/app/main.py` **solo para esta verificación**, y se
revirtió ese permiso apenas terminó (confirmado con `git diff` contra el
commit base: `main.py` solo difiere en el import y registro del router
`replay`, nada de CORS).

Recorrido verificado en Chrome real (`claude-in-chrome`), sobre el
candidato `base-seed4`, predicción con origen `2024-10-19`:

1. Carga inicial: candidato, selección determinística del primer origen,
   historial con 84 días sin medición correctamente cortados en el gráfico,
   predicción visible (`Sin estrés (0)`) sin ninguna observación.
2. Avance del reloj (3 clics en "Avanzar") hasta `2024-10-22`: observación
   revelada (`Estrés (1)`), coincidencia mostrada como **"Discrepa"**
   (`y_pred=0` vs. `y_true=1` — un caso real de discrepancia, no elegido
   por acertar), medición original `medida (0.279 m³/m³)`.
3. Feedback registrado desde el formulario ("No coincide" +
   observación) → confirmado en pantalla: `rechazada` — "Verificacion en
   navegador, Paso 4.", `Registrado el 2026-09-23T17:53:53.826800Z (reloj
   simulado en 2024-10-22)` — fecha real y fecha simulada correctamente
   separadas, sin atribución a un experto ni a la fecha histórica.
4. Retroceso del reloj a `2024-10-21`: la observación y el feedback
   desaparecen de la pantalla — el registro persiste (verificado
   directamente: `replay_feedback/base-seed4-1157696b7b-v2.jsonl` sigue
   conteniendo la fila).
5. Consola del navegador revisada tras una carga limpia: **sin errores**.

Este recorrido corresponde exactamente al pedido en la consigna ("antes de
revelar la observación, después y con feedback registrado"). Capturas reales
guardadas en
`openspec/scientific-closure/causal-historical-replay-2026-09-22/paso4-capturas/`
(`1-antes-de-revelar.jpg`, `2-observacion-revelada.jpg`,
`3-feedback-registrado.jpg`) — no fabricadas, tomadas directamente de la
sesión de Chrome descrita arriba.

### 3.3 Lo que quedó sin comprobar en navegador

- El selector de "otros orígenes disponibles" no se ejercitó manualmente en
  el navegador (sí está cubierto por tests de frontend y backend).
- El estado "predicción no encontrada"/"no disponible" (backend apagado) no
  se verificó visualmente en navegador — sí por test (`test_disabled_by_default_returns_not_found`
  a nivel API, y el test de frontend equivalente).
- No se verificó en un navegador distinto de Chrome, ni en viewport móvil.
- La instancia Docker de verificación fue descartada al finalizar (no queda
  un backend expuesto públicamente tras esta tarea).

## 4. Instrucciones reproducibles para abrir la demo

Requiere Docker y Node ya instalados (ambos ya presentes en este entorno).

```bash
# 1) Backend aislado, en un contenedor descartable (no el compartido)
mkdir -p replay_feedback
docker run -d --name hr-verify-backend \
  -p 127.0.0.1:8099:8000 \
  -v "$(pwd)/src:/workspace/src" \
  -v "$(pwd)/backend:/workspace/backend" \
  -v "$(pwd)/data:/workspace/data" \
  -v "$(pwd)/replay_packages:/workspace/replay_packages" \
  -v "$(pwd)/replay_feedback:/workspace/replay_feedback" \
  -e HISTORICAL_REPLAY_ENABLED=true \
  -e HISTORICAL_REPLAY_PACKAGE_DIR=/workspace/replay_packages/base-seed4-1157696b7b-v2 \
  -e HISTORICAL_REPLAY_FEEDBACK_DIR=/workspace/replay_feedback \
  -e MLFLOW_TRACKING_URI= \
  -w /workspace/backend \
  aai-hydric-stress-backend:latest \
  uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2) Frontend
cd frontend
echo "VITE_API_BASE_URL=http://127.0.0.1:8099" > .env
npm install   # primera vez
npm run dev   # respetar el puerto que Vite elija; si no es 5173,
              # agregar ese origen a allow_origins en backend/app/main.py
              # temporalmente (revertir después)

# 3) Navegar a http://localhost:<puerto>/#reproduccion-historica

# 4) Al terminar:
docker rm -f hr-verify-backend
```

## 5. Recorrido breve para la defensa

1. Abrir `#reproduccion-historica` — se ve de inmediato el aviso de
   "reproducción histórica retrospectiva" y el disclaimer de proxy
   estadístico.
2. Mostrar el historial de humedad con huecos reales preservados (no
   interpolados).
3. Mostrar la predicción archivada, sin ninguna observación visible.
4. Avanzar el reloj día a día hasta la fecha objetivo — señalar que el
   origen seleccionado nunca cambia.
5. Mostrar la revelación (incluyendo, si se repite este mismo run, el caso
   real de discrepancia) y registrar feedback.
6. Retroceder el reloj y mostrar que la observación y el feedback
   desaparecen — abrir la ficha de trazabilidad para mostrar la
   procedencia exacta (commit, dataset, corte de entrenamiento).

## 6. Pendientes reales

- Extender `GET /replay/history` con el estado de medición por fila
  (`medida`/`imputada`/`no_determinado`) — hoy solo expone el valor o
  `null`.
- `prediccion_seleccionada_id` como concepto de API: no existe; la
  selección vive en el estado del cliente (decisión de diseño, no una
  laguna).
- Redacción de memoria (capítulo 3): no iniciada, fuera de alcance de este
  paso por instrucción explícita.
- Exportación del paquete de lectura para la defensa: requiere
  autorización explícita separada.
- El fallo ambiental de `test_forecast.py` bajo el `MLFLOW_TRACKING_URI`
  por defecto del contenedor compartido no se corrigió (no es de este
  *change*) — queda documentado como hallazgo operativo para quien
  mantenga ese contenedor: su registro de modelos tiene estado real de
  actividad ajena a esta tarea (`sensor-a`, `trained_through=2026-09-13`).

## Cierre

Diff de esta tarea: `backend/app/config.py`, `dependencies.py`, `main.py`
(router `replay` registrado, sin cambios de CORS); `backend/app/routers/replay.py`,
`schemas_replay.py` (endpoints nuevos); `backend/tests/test_replay.py`
(17 tests); `src/historical_replay/feedback.py` (nuevo);
`tests/test_historical_replay_feedback.py` (nuevo, 7 tests);
`frontend/src/features/historical-replay/` (nuevo, 6 archivos + test);
`frontend/src/App.tsx` (ruta nueva); `tasks.md`/`traceability.md`
actualizados; este informe; capturas reales en `paso4-capturas/`;
`replay_feedback/` (nuevo directorio, con el registro real de la
verificación en navegador). No se modificó ningún artefacto científico
original ni el paquete `replay_packages/base-seed4-1157696b7b-v2/`. No se
tocó el contenedor compartido `aai-hydric-stress-backend-1` ni ningún otro
worktree. No se instaló nada de forma persistente (el contenedor de
verificación fue descartable y se eliminó). No se hizo commit, push, PR ni
merge. Se detiene aquí para revisión.
