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
| 16 | Pausa/reanudación de la demo acelerada | Una respuesta vieja no deshace una pausa | Solo pruebas automatizadas (`useDemoSession.race.test.tsx`); **el controlador no se levantó en este ensayo** | vitest |

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
- **Demo acelerada no ensayada en Docker.** El controlador (`demo-control`,
  perfil `demo` de Compose) no se levantó; la carrera de respuestas está cubierta
  solo por pruebas automatizadas de hook, no por ensayo en navegador.
- **Fallos inyectados.** El error de ingesta se provocó deteniendo el contenedor
  del backend del laboratorio (acción externa); la interfaz no contiene botones
  ni funciones de inyección. El caso `period_end=null` en D queda cubierto solo
  por prueba automatizada.
- **Melchor Romero.** Se reutilizó una copia de los artefactos de una
  preparación previa (2026-09-27, anterior a la corrección del #228); no existe
  un hash fijado en el repositorio para ellos, por lo que su verificación se
  limita a haber comprobado que las copias no cambiaron durante el ensayo. Solo
  se ensayó la carga de las pantallas de ambos sitios, no el registro de
  revisiones en el productor.
- Los pronósticos del laboratorio fueron «Sin alerta» en todas las emisiones
  observadas; el guion no depende de una alerta positiva.
- La revisión de objetivos usa el día UTC del navegador para decidir qué
  acciones ofrecer; el backend sigue siendo la autoridad y su rechazo 409 sigue
  mostrándose.
- La conexión con un sensor físico, MQTT, WebSockets y la validación en campo no
  existen; están presentadas como trabajo futuro.
