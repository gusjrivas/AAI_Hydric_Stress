# Guía de defensa del laboratorio de sensor simulado

Trazabilidad: HU5/HU6 (revisión humana e integración) y HU7 solo como
contexto de demostración (`demo-simulation`), capacidad `alerting-ui` (más
`demo-simulation` para la corrección de la demo acelerada). CRISP-DM:
despliegue/comunicación. Sin cambio de hipótesis, alcance, arquitectura ni
configuración experimental; no se tocó ningún experimento A/B/C/H, holdout,
bundle, métrica ni predicción archivada, y no se reentrenó Pergamino ni
Melchor Romero.

## 1. Qué se ensayó

- **Código ensayado (SHA):** `d47f74a1db3cb9ca470d655d282d9e9ea1237b93`
  (rama `fix/sensor-demo-defense-closure`, partida de `origin/main` `faabf1b`,
  que incluye el PR #229). El ensayo Docker usó ese árbol de código más el
  archivo `docker/defense-rehearsal/compose.yml` (agregado después, sin
  cambiar el código del frontend ni del backend).
- **Entorno:** Windows 11 solo como anfitrión de Docker Desktop (Docker
  Engine 29.5.2) y del navegador (Chrome con la extensión de automatización).
  Backend y frontend corrieron **dentro de contenedores**; no se usaron
  servicios nativos ni venvs de Windows.
- **Servicios del ensayo** (proyecto Compose aislado `aai-defense-rehearsal`):
  `lab-backend` (endpoints planos, `:18299`), `producer-backend`
  (`producer_v2`, Pergamino/Melchor Romero, `:18199`) y `frontend` (Vite,
  `:15199`, con `VITE_API_BASE_URL` → laboratorio y
  `VITE_PRODUCER_API_BASE_URL` → productor, la separación del #229).
- **Datos y volúmenes aislados:** el laboratorio escribe en el volumen
  nombrado `aai-defense-rehearsal_lab_data` (eliminado al terminar con
  `down -v`, solo el de este proyecto). El productor sirvió **copias** de los
  artefactos verificados de Pergamino (lectura y emisión con SHA-256 iguales a
  los fijados en `scripts/prepare_defense_data.ps1`; bundles del ensamble) y
  de Melchor Romero (copia de artefactos de una preparación previa; ver
  limitaciones), sin `historical_feedback`. Los contenedores y volúmenes
  ajenos (MLflow, MinIO, Postgres, `aai-producer-*`) no se detuvieron ni se
  modificaron.

### Comandos exactos

```powershell
# Preparación de copias (rutas locales del ensayo; nunca los originales)
#   producer-data/   sensor__pergamino-ensemble-demo.parquet, sensor__melchor-romero-demo.parquet,
#                    ui_metadata/operational_v2__*.json
#   producer-bundles/ pergamino-ensemble-demo/, melchor-romero-demo/, run_manifest*.json
$env:REHEARSAL_PRODUCER_DATA    = "<copia de producer-data>"
$env:REHEARSAL_PRODUCER_BUNDLES = "<copia de producer-bundles>"
docker compose -f docker/defense-rehearsal/compose.yml build
docker compose -f docker/defense-rehearsal/compose.yml up -d
docker compose -f docker/defense-rehearsal/compose.yml ps
curl http://127.0.0.1:18299/openapi.json        # laboratorio: 200
curl http://127.0.0.1:18199/api/v2/sensors      # productor: 200 (2 sensores)
curl http://127.0.0.1:15199/                    # frontend: 200
docker compose -f docker/defense-rehearsal/compose.yml stop   # parada
docker compose -f docker/defense-rehearsal/compose.yml up -d  # reinicio
docker compose -f docker/defense-rehearsal/compose.yml down -v # limpieza (solo este proyecto)
```

Nota de entorno: al comenzar, el motor Docker de esta máquina estaba
detenido; se reinició Docker Desktop (no había contenedores en ejecución) y,
al volver, sus contenedores con política de reinicio se levantaron solos. No se
tocaron.

Pruebas automatizadas (frontend, `cd frontend`): `npx vitest run` → 245
pruebas verdes; `npx tsc -b`, `npm run build` sin errores; `npm run lint` sin
advertencias nuevas. No cambió el backend, por lo que no se reejecutó `pytest`.

## 2. Tabla de pruebas

Evidencia = salida observada en el navegador real contra los contenedores
(DOM y respuestas HTTP) y registros de los contenedores. **No se pudieron
capturar imágenes** (ver limitaciones).

| # | Acción | Resultado esperado | Resultado observado | Evidencia |
| --- | --- | --- | --- | --- |
| 1 | Abrir el laboratorio | Rótulo permanente, título e id `lab-*` | Rótulo «SIMULACIÓN · Datos sintéticos · Sin sensor físico conectado», A habilitado, B–D deshabilitados | DOM |
| 2 | A | 120 lecturas guardadas, calidad confirmada, pronóstico solicitado | 120 filas (2026-05-27 → 2026-09-23); pronóstico «Sin alerta» con objetivo 2026-09-26 | DOM; log `POST /sensors/lab-*/readings` ×120 y `POST /forecast/.../run` |
| 3 | B | Temperatura 85 °C marcada por control de calidad | Marcada `out_of_range.temperature` (2026-09-24), texto aclara que no es alerta hídrica | DOM (registro de sesión) |
| 4 | C | Reloj +4 días, sin lecturas nuevas, sin pronóstico nuevo | Reloj 2026-09-28; última lectura guardada 2026-09-24 (121 filas); aviso «Verificar sensor y cultivo» | DOM |
| 5 | D | Lecturas para fechas pendientes y nuevo pronóstico | 125 filas hasta 2026-09-28; pronóstico «Sin alerta», objetivo 2026-10-01 | DOM |
| 6 | Revisión sobre objetivo vencido (2026-09-26) | Confirmar/Corregir habilitados; guardado | Confirmar guardó «Coincide con lo observado»; `POST /feedback/.../confirm` 200 | DOM; log del contenedor |
| 7 | Revisión sobre objetivo no vencido (2026-10-01) | Botones deshabilitados y texto «Disponible cuando termine el día objetivo: 2026-10-01 (UTC).» | Ambos deshabilitados con ese texto | DOM |
| 8 | Salir del laboratorio durante A | No se envían más lecturas ni pronóstico | Conteo de filas del sensor estable (83 → 83 → 83 en 12 s); sin pronóstico | consultas `GET /quality/lab-*` |
| 9 | «Iniciar una sesión nueva» con A en curso | Sesión anterior se detiene; la nueva parte limpia | Anterior estable en 86 filas; nueva sin datos (404), estado «Sin iniciar», A habilitado | consultas `GET /quality/lab-*` |
| 10 | Error de ingesta real (se detuvo el contenedor del backend del laboratorio durante A) | Estado de error, A–D deshabilitados, mensaje y «sesión nueva» disponible | «Failed to fetch» + «Este paso no pudo completarse. Para evitar modificar lecturas ya guardadas, iniciá una sesión nueva. Los datos de la sesión anterior se conservan.»; A–D deshabilitados | DOM |
| 11 | Reiniciar backend y sesión nueva | Datos previos conservados; nueva sesión completa A | Sesión fallida conservó sus 71 filas; sesión nueva `lab-2cbc81018b` cargó 120 | `GET /quality` |
| 12 | Pergamino y Melchor Romero en el entorno combinado | Se cargan desde el backend productor | Ambas pantallas cargaron; `GET /api/v2/sensors/.../historical/.../readings` y `/forecasts` 200 | DOM; log productor |
| 13 | Separación productor/laboratorio | Lab no escribe en el directorio del productor | 0 solicitudes `lab-*` al productor; los 4 archivos del productor con SHA-256 idénticos a antes del ensayo; archivos `lab-*` solo en el volumen del laboratorio | logs; `sha256sum` |
| 14 | Parada y reinicio | Servicios vuelven sanos, datos del volumen persisten | 3 servicios saludables; `lab-2cbc81018b` con 120 filas tras reiniciar | `docker compose ps`, HTTP |
| 15 | D con `period_end=null` y error de consulta en D | Error controlado, sin ingesta/pronóstico | Solo prueba automatizada (`useSensorLabScenarios.test.tsx`); no hay forma legítima de provocarlo en el backend real y no se dejó un control de fallos en la interfaz | vitest |
| 16 | Pausa/reanudación de la demo acelerada | Una respuesta vieja no deshace una pausa | Ronda 1: solo pruebas automatizadas (`useDemoSession.race.test.tsx`). Ronda 2: ensayada con el controlador real (sección 6) | vitest; navegador |

Las pruebas de regresión fallan contra el código anterior: las tres de orden de
respuestas de `useDemoSession.race.test.tsx` fallan contra `origin/main`.

## 3. Guion de 3–4 minutos

1. **Propósito (30 s).** «Este laboratorio no recibe datos de un cultivo: un
   generador produce lecturas de prueba para mostrar cómo responde la
   aplicación.» Señalar el rótulo permanente y los bloques «Qué simulamos» y
   «Qué funciona realmente».
2. **A (45 s).** «Generar historial de prueba»: 120 días sintéticos. Mostrar en
   Calidad las 120 filas y el pronóstico emitido. Explicar el resultado
   observado, aunque sea «Sin alerta»: la señal del modelo va de 0 a 1 y no es
   un porcentaje de certeza. No se fuerza una alerta positiva.
3. **B (30 s).** «Introducir una lectura anómala» (85 °C). El control de calidad
   la marca fuera de rango. **Es una anomalía de medición, no una alerta de
   estrés hídrico.**
4. **C (30 s).** «Simular una interrupción»: no se desconectó ningún
   dispositivo; se suspendió el envío del generador. Los resultados anteriores
   siguen visibles pero no describen una situación actualizada; el reloj de la
   pantalla no cambia la fecha real del servidor.
5. **D (30 s).** «Simular la recuperación»: se generan lecturas de prueba para
   las fechas pendientes (no se recuperan mediciones de un dispositivo) y se
   vuelve a pedir un pronóstico.
6. **Revisión (30 s).** Elegir una fila cuyo objetivo ya terminó (UTC) y
   confirmarla; mostrar que las filas con objetivo de hoy o futuro están
   bloqueadas. Declarar que esta revisión es un ejercicio sintético, no una
   observación de campo.
7. **Conexión física futura (30 s).** Abrir «¿Cómo se conectaría un sensor
   real?»: cuatro pasos, trabajo futuro; un único sensor de humedad no
   reemplaza todas las variables del predictor.

## 4. Qué distinguir ante el tribunal

- **Control de calidad vs. alerta predictiva.** La calidad describe si el dato
  es plausible (rango, faltantes, duplicados). La alerta es una señal del
  predictor sobre una posible falta de agua a futuro. Una lectura anómala puede
  ser ruido de medición y no implica estrés hídrico.
- **Funcionamiento técnico vs. validación científica.** Se demuestra que el
  recorrido (ingesta → calidad → predictor → revisión humana) funciona de
  punta a punta con datos sintéticos. No se demuestra precisión en campo ni se
  agrega evidencia científica: el predictor operativo puede entrenarse o
  actualizarse con las lecturas sintéticas de la sesión, y sus resultados solo
  ilustran el funcionamiento del sistema.

## 5. Limitaciones reales

- **No hay capturas de pantalla ni verificación a 390 px.** La pestaña del
  navegador de automatización permaneció con visibilidad «hidden»: el pedido de
  captura expiró (`Page.captureScreenshot`) y el cambio de tamaño de ventana no
  modificó el ancho efectivo (`innerWidth` siguió en 1225). Todo lo observado se
  leyó del DOM y de las respuestas reales; el diseño a 390 px y las capturas
  quedan **pendientes**.
- **Demo acelerada:** ensayada en la segunda ronda (sección 6).
- **Fallos inyectados.** El error de ingesta se provocó deteniendo el contenedor
  del backend del laboratorio (acción externa); la interfaz no contiene botones
  ni funciones de inyección. El caso `period_end=null` en D queda cubierto solo
  por prueba automatizada.
- **Melchor Romero:** la primera ronda usó artefactos anteriores al #228; queda reemplazada por la revalidación de la sección 7.
- Los pronósticos del laboratorio fueron «Sin alerta» en todas las emisiones
  observadas; el guion no depende de una alerta positiva.
- La revisión de objetivos usa el día UTC del navegador para decidir qué
  acciones ofrecer; el backend sigue siendo la autoridad y su rechazo 409 sigue
  mostrándose.
- La conexión con un sensor físico, MQTT, WebSockets y la validación en campo no
  existen; están presentadas como trabajo futuro.

## 6. Segunda ronda: bloqueo de feedback y demo acelerada en Docker

- **SHA del código ensayado:** `50e1d3dd21b05841cdc1530ec8cacc64dbdf804d`
  (frontend con el bloqueo de feedback completado, más el perfil `demo` del
  Compose de ensayo). Pruebas, `tsc`, build y lint corridos **dentro de Docker**
  sobre la imagen `aai-defense-rehearsal-frontend` construida con ese código:
  `docker run --rm aai-defense-rehearsal-frontend sh -c "npx tsc -b && npx vitest run && npm run build && npm run lint"`
  → 33 archivos, 247 pruebas verdes, build correcto, 0 errores de lint.
- **Bloqueo de feedback al guardar (automatizado, vitest):** una única función
  decide si una fila es revisable (fecha objetivo contra el día UTC real y, si
  existe, `demoGate.isRowReviewable`) y se aplica antes de `confirm`/`reject`
  y dentro del manejador de guardado (no solo por el atributo `disabled`).
  `CorrectionForm` recibe `blockedReasons` (distinto de `saving`): con la fila
  bloqueada, «Guardar corrección» queda deshabilitado con el motivo visible,
  «Cancelar» sigue disponible y lo escrito se conserva; al volver a permitirse
  la fila puede guardarse. Pruebas: `ForecastPage.targetMaturity.test.tsx`
  (a–e del encargo, más un gate que cambia sin re-render). No se ensayó en
  navegador (el gate solo bloquea durante una demo en curso; cubierto por
  pruebas de componente).

### Compose y comandos

`docker/defense-rehearsal/compose.yml` agrega el servicio opcional
`demo-control` (perfil `demo`, imagen `docker/demo-control/Dockerfile` sin
cambios, comandos de `scripts/demo_simulation` sin cambios) y
`VITE_DEMO_CONTROL_BASE_URL` en el frontend, conservando `VITE_API_BASE_URL`
(laboratorio) y `VITE_PRODUCER_API_BASE_URL` (productor). El controlador apunta a
`http://lab-backend:8000`; `prepare` escribe el historial en el volumen aislado
`lab_data` (el mismo del backend de laboratorio) y el manifiesto en el volumen
propio `demo_sessions`. No se usó ningún volumen científico ni el backend
productor.

```powershell
docker compose -f docker/defense-rehearsal/compose.yml build
docker compose -f docker/defense-rehearsal/compose.yml up -d
docker compose -f docker/defense-rehearsal/compose.yml --profile demo run --rm --no-deps demo-control `
    prepare --start 2026-09-10 --days 5 --history-days 120 --seed 42 --backend-url http://lab-backend:8000
$env:DEMO_SESSION_ID = "demo-a749b73ee1"
docker compose -f docker/defense-rehearsal/compose.yml --profile demo up -d demo-control
# ... recorrido en el navegador ...
docker compose -f docker/defense-rehearsal/compose.yml --profile demo down -v   # solo este proyecto
```

Sesión usada: `demo-a749b73ee1` (preparada de cero, semilla 42, 120 días de
historial 2026-05-13 → 2026-09-09, reproducción 2026-09-10 → 2026-09-14). No se
reutilizó ninguna sesión parcial.

### Resultados del recorrido acelerado (navegador real + API del controlador)

| Comprobación | Esperado | Observado | Tipo de evidencia |
| --- | --- | --- | --- |
| a. Sesión preparada | Identidad y estado | «Demostración con datos simulados», sensor `demo-a749b73ee1`, «Preparada, sin iniciar», 0 de 5 | DOM |
| b. Iniciar | Avanzan lecturas y pronósticos | Cursor 0→1 con `last_ingested_date`=`last_forecast_date`=2026-09-10 | API `GET /demo/session` |
| c–d. Pausa durante la ejecución | `pausing` y luego `paused` confirmado | Rev. 7 `pausing` (UI «Pausa solicitada — terminando el paso actual») → rev. 8 `paused` (UI «Pausada») | API + DOM |
| e. Sin avance en pausa | Cursor fijo | 20 s con cursor 1 y rev. 8; solo «Continuar» habilitado | API + DOM |
| f. Reanudar | Sigue del paso pendiente | Cursor 1→2 (2026-09-11) sin repetir el 10 | API |
| g. Completar | 5 de 5 | `completed`, rev. 25, UI «Completada», «5 de 5» | API + DOM |
| h. Fechas y duplicados | 5 ingestas, 5 pronósticos, sin duplicados | Lecturas 2026-09-10…14; `total_rows` 125, 0 fechas repetidas; log: `POST /sensors/demo-…/readings` ×5 y `POST /forecast/demo-…/run` ×5, todos 200; controlador: 1 start, 1 pausa, 1 reanudación | API + logs |
| i. Productor sin escrituras | Archivos idénticos | SHA-256 del directorio del productor idénticos antes y después; 0 solicitudes `demo-*` al productor | `sha256sum`, logs |

Observación honesta: durante el recorrido la interfaz mostró por momentos un
estado atrasado respecto de la API (por ejemplo «En ejecución, 1 de 5» con la
sesión ya completada) y se puso al día segundos después. Con el navegador de
automatización la pestaña permanece oculta, lo que limita sus temporizadores y
espacia la consulta periódica (cada 2 s); al estabilizarse coincidió con la API.
No se pudo distinguir con certeza si es solo esa limitación del navegador; no se
observó un retroceso a un estado anterior. La carrera de respuestas reordenadas
sigue cubierta solo por las pruebas automatizadas.

## 7. Segunda ronda: revalidación de Melchor Romero (paquete posterior al #228)

### Identificación del paquete

- Los informes del repositorio (guía de arranque, `docs/seguimiento-tareas.md`)
  describen los datos de Melchor Romero como «preparados desde cero en un
  directorio temporal» pero **no fijan rutas ni hashes**. El paquete se identificó
  por evidencia, no por nombre ni fecha:
  1. Preparado el 2026-09-29 11:25, posterior a las pruebas del #228
     (09:26–09:50), en el directorio de trabajo de la sesión que verificó el
     arranque del #229: `melchor-rehearsal-data` + `melchor-rehearsal-bundles`.
  2. Una segunda copia independiente (`combined-rehearsal-data` /
     `-bundles`, 13:22, usada en el ensayo del arranque combinado) contiene la
     **misma** emisión (`operational_v2__melchor-romero-demo.json`) y el **mismo**
     conjunto de bundles de Melchor (huella de árbol idéntica).
  3. Los valores verificados en el #229 (25/10 = 36,3 % real; 26/10 = 36,3 %
     imputado; 27/10 = 33,0 %) coinciden con lo observado abajo.
- Otras preparaciones existentes (2026-09-27, `mr_demo_*`, `mrdemo_*`,
  `melchor_verify`) tienen el **mismo** parquet de lecturas
  (`391cdb31…`, con columnas `*_imputado`) pero emisiones y bundles distintos
  (reentrenados en cada preparación); no son el paquete del #229 y no se usaron.
- **Limitación:** la identificación se apoya en marcas de tiempo, identidad de
  contenido entre dos copias y lo narrado en los informes; ningún documento del
  repositorio fija estos hashes.

### Origen y SHA-256 (copia de trabajo nueva)

Origen: `combined-rehearsal-data` y `combined-rehearsal-bundles`. Copiados
(sin `.lock`) a un directorio nuevo y verificados contra el origen (copia == origen).

| Archivo | SHA-256 |
| --- | --- |
| `sensor__melchor-romero-demo.parquet` | `391cdb31433d3f8bb2ecc1cc0ea52e6ac218a2c2fe60353ce55d32ee0d2e7342` |
| `ui_metadata/operational_v2__melchor-romero-demo.json` | `111fb155ecd1a7f5a71cfb265619c5ba495fc0adde56f060290fd98340235a18` |
| `sensor__pergamino-ensemble-demo.parquet` | `f6f9e19ae19c0835d6da57cfda490de4e81d84f0657ed0118d609f3a9da3f98c` (igual al fijado en `prepare_defense_data.ps1`) |
| `ui_metadata/operational_v2__pergamino-ensemble-demo.json` | `fcd7ac529b6ce300905eba805e4655ab8bafaf1e63cbe7b2e7316d37bf535dcd` (igual al fijado) |
| Bundles (78 archivos) | huella de árbol `melchor-romero-demo` = `52a94333ebc9…` |

Procedencia en los datos: el parquet trae `soil_moisture_imputado`,
`relative_humidity_imputado`, `solar_radiation_imputado` y `origen`; consulta directa
(pandas dentro del contenedor): 2024-10-25 = 0,363274 (`imputado=False`),
2024-10-26 = 0,363274 (`imputado=True`), 2024-10-27 = 0,329569 (`imputado=False`).
No se generó ni modificó ningún flag; no se ejecutó ningún preparador ni entrenamiento.

### Resultados en navegador real (contenedores, misma pila de la sección 6)

| Comprobación | Esperado | Observado |
| --- | --- | --- |
| a. Emisión 23/10, +3, objetivo 26/10 | Disponible | «+3 · Objetivo: 26 de oct de 2024», «Sin alerta prevista» |
| b. 25/10 | 36,3 % real | «36.3 % · Fuente real» |
| c. 26/10 | 36,3 % imputado con advertencia | «36.3 % · Valor imputado (completado a partir del último dato disponible, sin dato propio en la fuente para esta fecha). No es una observación independiente para contrastar con el pronóstico.»; tabla: «Fuente real · Imputado (sin dato propio este día)» |
| d. 27/10 | 33,0 % propio | «33.0 % Fuente real» |
| e. Reloj adelante/atrás | Sin observaciones futuras | Con reloj en 24, 25 y 26/10 la tabla llega exactamente a esa fecha; +2 y +3 muestran «Todavía no disponible según el reloj» hasta que corresponde; con 27/10 «Nunca se revelan observaciones posteriores a esta fecha» |
| **f. Objetivo imputado no habilita revisión independiente** | Revisión bloqueada | **DISCREPANCIA:** con el reloj en 27/10, «Confirmar resultado» y «Rechazar resultado» de +3 (objetivo imputado) están **habilitados**. La elegibilidad del historial la decide el backend solo por tiempo (`reviewable = now >= review_open_at`); no considera la procedencia imputada. No se modificó ninguna regla ni se forzó la prueba. La interfaz sí advierte que el valor no es una observación independiente. |
| g. Feedback con observación real | Persistencia | +1 (objetivo 24/10, 35,0 % real): «Confirmar resultado» → «Guardar opinión» → `POST …/historical/2024-10-27/forecasts/fc_…/reviews` **201**; tras recargar la página: «Revisión: Confirmado por vos» |
| h. Predicciones archivadas intactas | Sin cambios | Comparando SHA-256 antes/después: lecturas, emisiones de ambos sitios y los 78 archivos de bundles idénticos. Únicos archivos nuevos: `historical_feedback/melchor-romero-demo.json` y su `.lock`, escritos por el `POST` de revisión (verificado en el registro) |
| i. Pergamino y separación | Sin mezcla | Pergamino carga sus 5 emisiones (2023-06-13…17) y no menciona Melchor; 0 solicitudes `lab-*`/`demo-*` al productor y 0 solicitudes a rutas de productor en el backend de laboratorio; en el volumen del laboratorio solo existen archivos `demo-*` |

## 8. Pendientes reales (segunda ronda)

- Discrepancia (f) de Melchor Romero: el contrato actual no bloquea la revisión de
  un objetivo cuya observación es imputada. Decisión pendiente (fuera de este alcance).
- Identificación del paquete de Melchor Romero sin hashes fijados en el repositorio.
- El bloqueo de feedback por `demoGate` con el formulario abierto solo está
  cubierto por pruebas de componente, no por navegador.
- La carrera de respuestas reordenadas de la demo acelerada solo tiene pruebas
  automatizadas; el estado atrasado transitorio de la interfaz con la pestaña
  oculta no se distinguió de una limitación del navegador de automatización.
- Sin capturas ni verificación a 390 px (fuera de este encargo).
