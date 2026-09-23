# Paso 4.1 — Cierre funcional de la demo y preparación de capturas

HU7/HU8, capacidad OpenSpec `historical-replay` (change
`add-causal-historical-replay`), fase CRISP-DM: evaluación/despliegue de la
demostración (no modeling ni entrenamiento). No hay impacto sobre hipótesis,
alcance ni arquitectura del Trabajo Final; no hay impacto sobre la
configuración experimental (`controlled_daily_v3`, protocolo v3): este paso
no toca el paquete científico ni recalcula ninguna métrica, solo corrige la
interfaz de solo lectura y su feedback de demostración.

Continuación directa de `paso4-interfaz-feedback.md`, sobre los mismos
archivos, en la misma rama (`feat/causal-historical-replay`) y el mismo
worktree (`C:\Repo\AAI_Hydric_Stress_causal_historical_replay`). No se
realizaron `commit`, `push`, `PR` ni `merge`. No se entrenó, no se infirió,
no se recalibró, no se recalcularon métricas científicas ni se accedió al
holdout v4.

## 1. Aislamiento del estado de cada consulta

**Defecto real identificado en el Paso 4:** `latestRequestKey` era una
cadena de texto `origen|fecha`. Esa clave se **repite** en una navegación
A→B→A: la segunda consulta a "A" y la primera comparten exactamente la
misma clave. Si la respuesta de la primera consulta (ya obsoleta) llegaba
después de que la segunda consulta a "A" hubiera sido disparada pero antes
de que resolviera, el guardado `latestRequestKey.current !== requestKey`
**no la habría descartado**, porque ambas comparten la misma cadena.

**Corrección:** `HistoricalReplayPage.tsx` reemplaza la clave de texto por
un contador de generación monotónico (`generationRef`, `useRef<number>(0)`),
incrementado en cada efecto de `(selectedOrigin, simulatedDate)`. Cada
consulta (predicción, historial, feedback) y cada envío de feedback capturan
la generación vigente en el momento de dispararse; solo se aplica su
resultado si `generationRef.current` sigue siendo esa misma generación al
resolver. Un envío de feedback iniciado para A que resuelve después de
navegar a B ya no puede poblar B (probado explícitamente).

Además, el estado anterior ya no espera a la nueva respuesta para
desaparecer: al cambiar de selección, `predictionState`/`historyState`/
`feedbackState` se resetean a `"loading"` de forma **síncrona**, en el mismo
efecto que dispara las nuevas consultas — antes, el resultado del corte
previo permanecía visible durante toda la carga del nuevo (visible incluso
en la transición previa al primer render posterior al cambio).

El formulario de feedback se remonta con `key={origen|fecha}` al cambiar de
predicción (reinicia su borrador interno).

**Defecto real de habilitación del formulario:** la condición previa era
`predictionStatus === "ready" && prediction?.target_observed !== undefined`,
que es `true` también cuando `target_observed === false` (el objetivo nunca
maduró en este run) — el formulario podía mostrarse sin que hubiera
observación real con la que comparar. Corregido a
`prediction?.target_observed === true`.

## 2. Errores explícitos

`historyState`/`feedbackState` distinguen ahora tres estados
(`loading`/`error`/`ready`) en vez de dos (antes, cualquier fallo HTTP en
`getHistory`/`getFeedback` se convertía, en el `catch`, en el mismo estado
que una respuesta vacía exitosa). Un error al consultar el feedback
existente ya **no** habilita silenciosamente el formulario de alta como si
se hubiera confirmado la ausencia de un registro previo — se muestra un
mensaje de error explícito y el formulario no se ofrece.

## 3. Semántica y presentación

- **Lenguaje de clase**, verificado antes de escribirse: `manifest.label_rule.rule
  == "observed_value_at_t_plus_h_less_than_frozen_threshold"` (leído en
  `replay_packages/base-seed4-1157696b7b-v2/manifest.json`) — clase 1
  significa "el valor observado en el horizonte está por debajo del umbral
  congelado", clase 0 lo contrario. Se reemplazó "Estrés (1)/Sin estrés (0)"
  por "Por debajo del umbral de humedad (1)" / "No inferior al umbral de
  humedad (0)" en toda la interfaz (predicción, observación revelada,
  formulario). La regla se expone ahora por la API
  (`ReplayCandidateInfo.regla_etiqueta`: `variable`, `unidad`, `operador`,
  `umbral`, `percentil`) — si el manifiesto declarara una regla no
  reconocida, el backend responde 500 en vez de inventar un texto genérico
  (`_LABEL_RULE_OPERATORS` en `backend/app/routers/replay.py`).
- **Selector operativo separado:** el formulario de "Punto de medición
  (sensor)" (operativo, gobierna la ruta `#resumen`/`#productor`, no esta
  demo) se oculta ahora explícitamente en la ruta `#reproduccion-historica`
  (`App.tsx`: `route !== "productor" && !isHistoricalReplayRoute`).
- **Ejes legibles:** `MoistureHistoryChart.tsx` agrega ejes con marcas de
  fecha (primera/última) y humedad en m³/m³ (mínimo/máximo), además de la
  leyenda textual ya existente. Los huecos siguen sin interpolarse.
- **Corte de partición vs. fecha máxima de entrenamiento:** el manifiesto
  real declara `split_date=2024-10-19` mientras que
  `effective_configuration.json::training_dates` tiene como máximo
  `2024-10-15` — **cuatro días antes**, no la misma fecha. La ficha de
  trazabilidad anterior solo mostraba `split_date` bajo "Corte de
  entrenamiento", lo que invitaba a leerla como si fuera la última fecha
  usada para entrenar. Se agregó `ReplayEvidenceCard.training_max_date`
  (`backend/app/schemas_replay.py`), derivado de
  `LoadedReplayPackage.effective_configuration["training_dates"]` (nuevo
  campo del loader, `src/historical_replay/package_loader.py`), y la
  interfaz ahora muestra ambas fechas por separado, etiquetadas "Corte de
  partición (train/test)" y "Última fecha realmente usada para entrenar".
- Identidad del modelo acreditado (experimento/run/config/semilla) ya se
  mostraba y se sigue mostrando sin cambios.

## 4. Arranque repetible

`scripts/demo_replay_up.sh` / `scripts/demo_replay_down.sh`:

- Puertos configurables por variable de entorno
  (`DEMO_REPLAY_BACKEND_PORT`/`DEMO_REPLAY_FRONTEND_PORT`, por defecto
  `8100`/`5180`, distintos de los operativos `8000`/`5173`).
- CORS configurado por `CORS_EXTRA_ORIGINS` (variable de entorno agregada a
  `backend/app/main.py`), nunca editando `allow_origins` a mano en cada
  sesión.
- No sobrescribe ningún `.env`: solo exporta variables al proceso de la
  sesión.
- `HISTORICAL_REPLAY_PACKAGE_DIR` apunta al paquete existente sin copiarlo
  ni modificarlo — el backend nunca escribe ahí.
- `HISTORICAL_REPLAY_FEEDBACK_DIR` es un directorio nuevo por sesión
  (`replay_feedback/demo-session-<id>/`); las sesiones anteriores no se
  tocan.
- Los PID de los procesos arrancados se guardan por sesión
  (`.demo_replay_sessions/<id>/*.pid`); `demo_replay_down.sh <id>` detiene
  únicamente esos procesos.

No regenera el paquete ni recalcula nada.

## 5. Pruebas dirigidas

**Frontend** (`frontend/src/features/historical-replay/HistoricalReplayPage.test.tsx`,
promesas controladas manualmente, sin temporizadores reales) — 8 pruebas
nuevas, además de las 4 ya existentes del Paso 4 (adaptadas al nuevo
lenguaje de clase y a los campos nuevos de `ReplayCandidateInfo`):

1. `does not show origin A's feedback while origin B's own query is still pending` — cambio A→B con feedback previo de A: mientras la consulta de B está en vuelo no se sigue mostrando el feedback de A.
2. `does not let a feedback POST started for A populate B after navigating away` — POST de feedback de A que resuelve después de navegar a B no puebla B.
3. `shows the saved feedback entry after a successful POST, replacing the empty state` — el registro exitoso reemplaza el estado vacío (regresión básica sobre el flujo de guardado).
4. `keeps the correct state after out-of-order A→B→A navigation` — navegación A→B→A con respuestas que resuelven fuera de orden: solo la última generación de cada origen puede escribir estado.
5. `shows no future result while a retreat is loading` — retroceso: mientras la consulta está en vuelo no se muestra el resultado posterior ya revelado.
6. `does not show the feedback form when target_observed is false` — cubre directamente el defecto de habilitación corregido en §1.
7. `distinguishes a history fetch error from an empty history` — error de historial ≠ historial vacío.
8. `distinguishes a feedback fetch error from an empty feedback list, and does not silently enable the form` — error de feedback ≠ feedback vacío, y no habilita el alta.

No se afirma cobertura de casos no ejercitados: por ejemplo, no se probó
concurrencia entre **dos** POST de feedback simultáneos para la misma
predicción (el backend ya lo cubre a nivel de archivo con
`ReplayFeedbackStore`, ver Paso 4, pero no se agregó un test de carrera de
UI para ese caso específico, que no fue señalado como defecto).

**Backend** — 2 pruebas nuevas dirigidas al lenguaje/evidencia:

- `tests/test_historical_replay_package_loader.py::test_load_valid_package_succeeds`
  (extendida): `LoadedReplayPackage.effective_configuration` expone
  `training_dates`.
- `backend/tests/test_replay.py::test_candidate_includes_expandable_evidence_card`
  (extendida): `training_max_date` presente y distinto de `split_date`.
- `backend/tests/test_replay.py::test_candidate_exposes_the_verified_label_rule`
  (nueva): `regla_etiqueta` expone `variable`/`unidad`/`operador`/`umbral`
  verificados contra el manifiesto real.

### Resultados de ejecución

- `tests/test_historical_replay_package_loader.py` + `tests/test_build_replay_package.py`: **20 passed**.
- `backend/tests/test_replay.py`: **18 passed**.
- `backend/tests/` (suite completa): **124 passed, 0 failed** (creció de 123 a 124 por la prueba nueva del backend).
- `frontend`: **155 passed** en 22 archivos (147 previos + 8 nuevos), `tsc --noEmit` sin errores.
- No se corrió la suite completa de `tests/` (fuera de `historical_replay`) hasta el final: incluye conectores de ingesta con dependencias de red (NASA POWER, ESA CCI) ajenos a este *change*; se detuvo tras superar el 50% sin fallos observados, para no consumir tiempo en pruebas de red no relacionadas con esta tarea. No se afirma que esa porción restante haya pasado.

Todas las ejecuciones se realizaron dentro de una instancia Docker
desechable de la imagen `aai-hydric-stress-backend` (`docker run --rm`, con
este worktree montado en `/tmp/hr_workspace`, `PYTHONPATH` apuntando a la
copia del worktree) — nunca en el contenedor compartido
`aai-hydric-stress-backend-1`, ni escribiendo en `/workspace/src` de ningún
contenedor en ejecución.

## 6. Verificación en navegador

Recorrido real ejecutado con dos instancias Docker desechables
(`docker run -d --rm`, sin `--name` reutilizado de ninguna sesión anterior,
eliminadas al finalizar):

- Backend: imagen `aai-hydric-stress-backend`, worktree montado en
  `/tmp/hr_workspace`, publicado en el puerto de host `8100`,
  `HISTORICAL_REPLAY_FEEDBACK_DIR` apuntando a
  `replay_feedback/demo-session-browsercheck/` (directorio nuevo, exclusivo
  de esta verificación).
- Frontend: imagen `aai-hydric-stress-frontend`, con `frontend/src` e
  `index.html` del worktree montados sobre el `/app` baked de la imagen
  (conserva el `node_modules` de la imagen), publicado en el puerto de host
  `5190`, `VITE_API_BASE_URL=http://localhost:8100`.
- Ninguna de las dos tocó el contenedor compartido ni otro worktree.

Recorrido (Chrome, extensión `claude-in-chrome`):

1. **Antes de revelar** (`2024-10-19`): selector operativo "sensor-a"
   ausente; ficha de trazabilidad expandida muestra `split_date=2024-10-19`
   y `training_max_date=2024-10-15` **por separado** ("anterior al corte de
   partición; no son la misma fecha"), y la regla de la clase proxy
   ("Proxy: soil_moisture observada en el horizonte por debajo de 0.317
   m3/m3 (percentil 20 del período de entrenamiento)"); gráfico con ejes de
   fecha y m³/m³; predicción archivada muestra "No inferior al umbral de
   humedad (0)"; sin observación ni formulario. Captura:
   `paso4-1-capturas/1-antes-de-revelar.jpg`.
2. **Avance de 3 días** (`Avanzar ▶` × 3, hasta `2024-10-22`, la fecha
   objetivo real): se revela una discrepancia real —
   "Observación revelada: Por debajo del umbral de humedad (1)",
   "Coincidencia con la predicción: Discrepa", "Medición original: medida
   (0.279 m³/m³)" — y aparece el formulario de feedback. Captura:
   `paso4-1-capturas/2-observacion-revelada.jpg`.
3. **Feedback registrado:** "No coincide" + observación
   "Verificacion en navegador, Paso 4.1." → "Registrar feedback de
   demostración". La sección pasa a mostrar el registro
   ("rechazada — "Verificacion en navegador, Paso 4.1."", con
   `registered_at`/`simulated_at` separados). Verificado también en el
   archivo persistido:
   `replay_feedback/demo-session-browsercheck/base-seed4-1157696b7b-v2.jsonl`.
   Captura: `paso4-1-capturas/3-feedback-registrado.jpg`.
4. **Retroceso** (`◀ Retroceder`, a `2024-10-21`): la observación revelada y
   la sección de feedback desaparecen de inmediato (vuelve a
   "Observación posterior: todavía no revelada en la fecha simulada."); el
   registro persistido **no se borra** (confirmado releyendo el archivo
   `.jsonl` después del retroceso: sigue teniendo la única línea
   registrada).

**No se ejecutó en este recorrido** (por acotar el tiempo de la
verificación manual, ya cubierto por las pruebas automatizadas de la
sección 5): cambiar de origen en el `<select>` dentro del navegador real
(el aislamiento A→B/A→B→A se verificó exhaustivamente por test, no de nuevo
a mano); reiniciar una sesión de demostración completa desde cero
(`demo_replay_up.sh` con un `SESSION_ID` nuevo) para confirmar que preserva
sesiones anteriores — se verificó por inspección del script y porque el
directorio `replay_feedback/demo-session-browsercheck/` en efecto no
interfirió con `replay_feedback/base-seed4-1157696b7b-v2.jsonl` (el
registro del Paso 4), que sigue intacto.

## 7. Arranque reproducible de la demo

```bash
# Desde la raíz del worktree, con Python (deps del backend) y Node
# disponibles, o dentro de un contenedor desechable de la misma imagen
# que aai-hydric-stress-backend:
scripts/demo_replay_up.sh
# Backend en http://localhost:8100, frontend en http://localhost:5180
# (o los puertos indicados por DEMO_REPLAY_BACKEND_PORT/DEMO_REPLAY_FRONTEND_PORT)

# Al terminar:
scripts/demo_replay_down.sh <session_id>   # id impreso por demo_replay_up.sh
```

## 8. Pendientes reales (no resueltos en este paso)

- Redacción de la memoria (capítulo 3): fuera de alcance explícito.
- Exportación del paquete de lectura para la defensa: requiere autorización
  separada.
- `GET /replay/history` sigue sin exponer `medida`/`imputada`/
  `no_determinado`/`sin_dato_en_fuente` por fila (ya señalado en el Paso 4;
  no bloqueante).
- No se probó una carrera de UI entre dos envíos de feedback simultáneos
  para la misma predicción (el backend la cubre a nivel de archivo).
- No se verificó en navegador real el cambio de origen ni el reinicio de
  sesión con preservación de feedback previo (cubierto por test/inspección,
  no por recorrido manual — ver §6).

## 9. Entrega

- `tasks.md` y `traceability.md` actualizados (sección 7 y "Cierre
  funcional de la demo (Paso 4.1)" respectivamente).
- Capturas nuevas en
  `openspec/scientific-closure/causal-historical-replay-2026-09-22/paso4-1-capturas/`
  (capturas previas del Paso 4 conservadas en `paso4-capturas/`, sin
  sobrescribir).
- ZIP de revisión: `paso4-1-revision-codigo.zip` (código, pruebas,
  este informe y las capturas nuevas — sin dataset, credenciales,
  `node_modules` ni artefactos pesados).

No se realizó `commit`, `push`, `PR` ni `merge`.
