# Paso 4.1.1 — Cierre de dos pendientes concretos del Paso 4.1

HU7/HU8, capacidad OpenSpec `historical-replay` (change
`add-causal-historical-replay`), fase CRISP-DM: evaluación/despliegue de la
demostración. Sin impacto sobre hipótesis, alcance, arquitectura ni
configuración experimental. Continuación directa de `paso4-1-cierre-demo.md`,
misma rama (`feat/causal-historical-replay`), mismo worktree. No se realizó
`commit`, `push`, `PR` ni `merge`. No se entrenó, no se infirió, no se
recalibró, no se recalcularon métricas ni se accedió al holdout v4.

## 1. Garantía durante el render

**Defecto señalado, real:** `HistoricalReplayPage.tsx` limpiaba el estado
(`predictionState`/`historyState`/`feedbackState` a `"loading"`) e
incrementaba la generación **dentro de un `useEffect`**. Un `useEffect` corre
después del render (efecto pasivo): el informe anterior describía esa
limpieza como si fuera una garantía síncrona previa al render, lo cual es
incorrecto — el primer render posterior a un cambio de selección podía, en
principio, seguir mostrando el estado comprometido de la selección anterior,
antes de que el efecto llegara a ejecutarse.

**Corrección real:** se introdujo `selectionScope.ts`, un módulo puro sin
ninguna dependencia de temporización de React:

- `taggedFor(origin, date, value)` etiqueta cada resultado con el
  `(origen, fecha simulada)` para el que se pidió.
- `visibleFor(tagged, selectedOrigin, simulatedDate, fallback)` devuelve
  `tagged.value` **solo si** `tagged.origin === selectedOrigin && tagged.date
  === simulatedDate`; si no, devuelve `fallback` (el estado `loading`).

`HistoricalReplayPage.tsx` ahora guarda `predictionState`/`historyState`/
`feedbackState` ya etiquetados (`ForSelection<...>`), y en cada render
calcula `predictionVisible`/`historyVisible`/`feedbackVisible` con
`visibleFor` **antes** de decidir qué renderizar. Esto es una comparación
pura evaluada en el cuerpo del componente, no en un efecto: es verdadera en
todo render, incluido el primero posterior a un cambio de selección,
independientemente de si el `useEffect` ya corrió. El contador de
generación (`generationRef`) se conserva, pero su responsabilidad quedó
acotada a lo que sí depende de temporización: resolver qué promesa asíncrona
puede escribir estado al resolver (la carrera A→B→A entre respuestas que
llegan fuera de orden para el mismo `(origen, fecha)`), **no** evitar que se
muestre un dato viejo en el render — de eso se encarga el etiquetado.

Se agregó además limpieza real al desmontar (`mountedRef`), ausente en la
versión anterior.

**Defecto encontrado al implementar la limpieza al desmontar, real y
distinto del anterior:** la primera versión de `mountedRef` ponía
`mountedRef.current = false` únicamente en la función de limpieza del efecto,
sin reafirmar `true` en el propio montaje. Este proyecto activa `StrictMode`
en `main.tsx`; en desarrollo, React invoca deliberadamente
montaje→limpieza→montaje una segunda vez para exponer errores de este tipo.
Con esa primera versión, tras el doble montaje, `mountedRef.current` quedaba
en `false` para siempre — bloqueando cualquier actualización de estado real,
aunque las promesas resolvieran correctamente. **Este defecto no lo detectó
ningún test** (ninguno usaba `StrictMode`) — se encontró recién al verificar
el arranque en un navegador real (sección 2 de este informe), exactamente
el tipo de comprobación que el Paso 4.1.1 pedía no saltear. Corregido
reafirmando `mountedRef.current = true` al inicio del efecto de montaje.

**Pruebas nuevas** (`HistoricalReplayPage.test.tsx`):

- `selectionScope.test.ts` (5 pruebas): prueba pura y directa de la garantía
  — incluye un caso explícito con un resultado etiquetado para la selección
  B, comprobado contra una selección vigente A, sin que medie ningún efecto
  ni promesa.
- `never renders origin A's prediction/history/feedback under origin B's
  selection, not even immediately after switching`: deja las promesas de B
  colgadas para siempre (nunca resuelven) y comprueba, inmediatamente
  después de cambiar de selección, que ningún dato de A permanece visible —
  la garantía no depende de que la promesa de B haya resuelto.
- `still shows real data under StrictMode's dev mount→cleanup→mount
  double-invoke`: regresión específica del defecto de `mountedRef`
  encontrado en el navegador; se verificó deliberadamente en RED (revirtiendo
  la reafirmación de `mountedRef.current = true` y confirmando que la
  prueba falla exactamente por "Cargando predicción…" nunca resuelto) antes
  de restaurar la corrección.

Las 4 pruebas A→B→A / POST tardío / retroceso del Paso 4.1 se conservaron
sin cambios de comportamiento y siguen pasando.

## 2. Un único arranque realmente probado

**Reescritura completa de `scripts/demo_replay_up.sh`/`demo_replay_down.sh`**,
ajustados al procedimiento Docker que ya se había verificado funcionando
(dos contenedores desechables de `aai-hydric-stress-backend`/
`aai-hydric-stress-frontend`), no a procesos locales de Python/Node
(no disponibles en este host fuera de Docker — la versión anterior de los
scripts nunca se había ejecutado de verdad, por eso no se detectaron sus
defectos hasta ahora):

- Código y paquete científico montados de solo lectura (`:ro`); el feedback
  de la sesión vive en un directorio nuevo, montado aparte con
  lectura/escritura.
- Un `session_id` ya usado se rechaza (`.demo_replay_sessions/<id>` o un
  contenedor con ese nombre ya existente) — nunca se sobrescribe.
- No se toca ningún `.env` ni servicio compartido; los contenedores tienen
  nombres derivados del `session_id` (`hr-demo-backend-<id>`,
  `hr-demo-frontend-<id>`), nunca los operativos.
- Antes de anunciar éxito, se comprueba que backend (`/openapi.json`) y
  frontend (`/`) respondan de verdad — no solo que el contenedor haya
  arrancado.
- Si el arranque falla en cualquier paso, se retiran únicamente los
  contenedores y el directorio de esa sesión (`fail()` centralizado).
- `demo_replay_down.sh` detiene por nombre de contenedor (derivado del
  `session_id`), nunca por PID.

**Defecto real encontrado al ejecutar los scripts por primera vez de
verdad:** el chequeo de disponibilidad usaba `curl -sf` y su código de
salida. En este entorno, `curl -f` reportó fallo de forma intermitente
**incluso habiendo recibido un 200 completo** (comprobado directamente:
`curl -sf -o /dev/null -w '%{http_code}'` imprimía `code=200` y aun así el
`if` no se cumplía) — aparentemente por un reset de conexión posterior a la
respuesta. Con un timeout de 30 intentos de 1 segundo, el arranque fallaba
igual y el script retiraba los recursos, aun con el backend respondiendo
bien. Corregido leyendo el código HTTP impreso por `-w` (`http_code()`),
ignorando el estado de salida de `curl`.

### Ejecución real (comandos tal cual, sin alternativas)

```
$ cd /c/Repo/AAI_Hydric_Stress_causal_historical_replay
$ bash scripts/demo_replay_up.sh sesion-a
Iniciando sesión 'sesion-a'...
Esperando a que el backend responda (http://localhost:8100/openapi.json)...
Esperando a que el frontend responda (http://localhost:5190/)...
Sesión 'sesion-a' lista:
  backend  -> http://localhost:8100 (contenedor hr-demo-backend-sesion-a)
  frontend -> http://localhost:5190/#reproduccion-historica (contenedor hr-demo-frontend-sesion-a)
  feedback (nuevo, exclusivo de esta sesión): .../replay_feedback/demo-session-sesion-a
Detenerla con: scripts/demo_replay_down.sh sesion-a

$ bash scripts/demo_replay_up.sh sesion-a   # rechazo de id repetido
La sesión 'sesion-a' ya existe (.../.demo_replay_sessions/sesion-a). Elegí otro session_id.
$ echo $?
1
```

Recorrido real en navegador (Chrome, extensión `claude-in-chrome`), contra
`sesion-a` (`http://localhost:5190`):

**a) Cambio entre dos orígenes reales.** Origen inicial `2024-10-19` con
reloj también en `2024-10-19`: mostró correctamente la predicción archivada
(visible desde su propio origen, RH-02) — no `hidden-before-origin`.
Cambiado el origen a `2024-10-20` **sin mover el reloj** (quedó en
`2024-10-19`, anterior al nuevo origen): pasó a mostrar correctamente
"todavía no fue emitida" (`hidden-before-origin`) para el origen
`2024-10-20`, no el resultado ya visible del origen anterior — verificado
releyendo la respuesta capturada de ese paso antes de escribir esta
corrección, no reconstruida de memoria.

**b) Registro de feedback en la sesión.** Avanzado el reloj a `2024-10-23`
(objetivo real de origen `2024-10-20`): discrepancia real (`y_pred=0` vs.
`y_true=1`, medición `0.295` m³/m³). Registrado feedback "No coincide" +
observación "Sesion A, verificacion Paso 4.1.1.". Verificado en disco:

```
$ cat replay_feedback/demo-session-sesion-a/base-seed4-1157696b7b-v2.jsonl
{"timestamp_origen": "2024-10-20", ..., "estado_validacion": "rechazada",
 "observacion": "Sesion A, verificacion Paso 4.1.1.",
 "registered_at": "2026-09-23T21:33:09.184712+00:00", "simulated_at": "2024-10-23"}
```

**c) Detener la sesión y arrancar otra vacía.**

```
$ bash scripts/demo_replay_down.sh sesion-a
Detenido hr-demo-backend-sesion-a.
Detenido hr-demo-frontend-sesion-a.
Sesión 'sesion-a' detenida. Feedback preservado en:
.../replay_feedback/demo-session-sesion-a

$ DEMO_REPLAY_BACKEND_PORT=8102 DEMO_REPLAY_FRONTEND_PORT=5192 \
  bash scripts/demo_replay_up.sh sesion-b
Iniciando sesión 'sesion-b'...
Esperando a que el backend responda (http://localhost:8102/openapi.json)...
Esperando a que el frontend responda (http://localhost:5192/)...
Sesión 'sesion-b' lista: ...
```

`replay_feedback/demo-session-sesion-b/` estaba vacío al arrancar
(comprobado con `ls` antes de abrir el navegador).

**d) Feedback anterior preservado y no visible en la sesión nueva.** En
`sesion-b`, el mismo origen `2024-10-20` avanzado hasta `2024-10-23`
muestra la misma predicción/discrepancia real (mismo paquete científico,
montado de solo lectura en ambas sesiones), pero la sección de feedback
muestra el **formulario de alta vacío**, no el registro de `sesion-a`.
Verificado en disco simultáneamente:

```
$ cat replay_feedback/demo-session-sesion-a/*.jsonl   # sigue intacto
{"timestamp_origen": "2024-10-20", ..., "observacion": "Sesion A, verificacion Paso 4.1.1.", ...}
$ ls replay_feedback/demo-session-sesion-b/            # vacío
```

Captura de `sesion-b` en ese estado:
`paso4-1-1-capturas/1-sesion-b-vacia-sin-feedback-de-sesion-a.jpg`.

Detenida al final con `bash scripts/demo_replay_down.sh sesion-b` (sin
errores); `docker ps -a --filter name=hr-demo` no lista ningún contenedor
al terminar.

## 3. Corrección de una afirmación no respaldada

`paso4-1-cierre-demo.md` (§8) afirmaba: *"no se probó concurrencia entre
dos POST de feedback simultáneos para la misma predicción (el backend ya lo
cubre a nivel de archivo con `ReplayFeedbackStore`...)"*. Esa segunda parte
es una garantía de concurrencia **no respaldada por ninguna prueba
específica** — se revisó `tests/test_historical_replay_feedback.py` y
`src/historical_replay/feedback.py`: no existe ningún test de escritura
concurrente ni mecanismo de bloqueo explícito verificado. **Se retracta esa
afirmación aquí.** Lo que sigue siendo cierto, sin ampliarlo: no se probó (ni
en este paso ni en el anterior) qué ocurre si dos procesos escriben feedback
para la misma predicción al mismo tiempo; no se afirma que esté cubierto,
resuelto, ni que sea seguro.

## 4. Resultados de ejecución (solo lo afectado)

- `frontend`: **162 passed** en 23 archivos (155 previos + 5 de
  `selectionScope.test.ts` + 2 de integración nuevas), `tsc --noEmit` sin
  errores. Comando: `npx vitest run` / `npx tsc --noEmit` desde
  `frontend/`.
- No se tocó ningún archivo de `backend/` ni de `src/historical_replay/` en
  este cierre — no se volvió a correr esa suite (124 tests, sin cambios
  desde `paso4-1-cierre-demo.md`) porque no está afectada.
- Verificación en navegador real descrita en la sección 2, con los scripts
  entregados ejecutados tal cual (sin comandos Docker manuales alternativos).

## 5. Pendientes / bloqueos

- Ninguno de los dos pendientes de este cierre quedó sin resolver.
- Sigue sin probarse: escritura concurrente de feedback para la misma
  predicción (ver sección 3 — ahora documentado como no probado, no como
  cubierto).
- Sigue pendiente lo ya señalado en pasos anteriores (memoria, exportación
  para defensa, distinción de estado por fila en `GET /replay/history`).

## 6. Entrega

- Capturas nuevas:
  `openspec/scientific-closure/causal-historical-replay-2026-09-22/paso4-1-1-capturas/`.
- ZIP de revisión: `paso4-1-1-revision-codigo.zip` (código modificado,
  pruebas, este informe, evidencia de las dos sesiones).

No se realizó `commit`, `push`, `PR` ni `merge`.
