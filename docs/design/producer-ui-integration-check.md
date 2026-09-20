# Verificación de integración: UI productor (frontend) contra backend v2 real

Fecha: 2026-09-20. Frontend: `C:\Repo\AAI_Hydric_Stress`,
`feat/hu6-ui-productor-integracion`, commit entregado `aac3362` (más un fix de
esta verificación, ver Correcciones). Backend: `C:\Repo\AAI_Hydric_Stress_backend_ui`,
`feat/hu6-backend-soporte-ui` (worktree limpio, sin cambios; no se tocó).

Trazabilidad: HU6; capacidades `alerting-ui` (presentación) y
`architecture-integration` (consumo de la fachada v2); CRISP-DM despliegue e
integración. No afecta HU7/HU8, `controlled_daily_v3`, hipótesis, alcance ni
arquitectura. No se agregó funcionalidad nueva; solo se verificó la entrega
existente y se corrigió un fallo de integración demostrado (ver abajo).

## Resumen

**La integración frontend↔backend v2 pasa.** El catálogo, la selección de
sector/sensor, los períodos 7/30, el gráfico, la tabla, las unidades, la
procedencia, los faltantes y los estados vacíos funcionan contra un backend
v2 real (contenedor aislado, `PRODUCER_V2_ENABLED=true`), con peticiones
confirmadas en el panel de red del navegador. Se encontró y corrigió un
fallo real: las unidades se mostraban con el código crudo del backend
(`degC`, `mm/day`) en vez de una unidad legible para un productor sin
conocimientos técnicos.

## 1. Checkout limpio del frontend (detectar dependencias de archivos sin commit)

```
git clone --no-hardlinks --quiet <worktree> <tmp>/frontend_clean_check
cd <tmp>/frontend_clean_check && git checkout --quiet aac3362
cd frontend && npm install --no-audit --no-fund
npx oxlint && npx tsc -b && npx vite build && npx vitest run
```

Resultado: build y lint limpios; **102/102 tests** en 17 archivos (el
checkout limpio no incluye los 4 tests de `HistoryPanel` que siguen sin
commitear en el worktree real — correcto, esos son del cambio previo de otra
persona, no de esta entrega). Ningún import roto ni archivo faltante: la
entrega `aac3362` **no depende de ningún archivo sin commitear** del
worktree (en particular, `ProducerHistoryPanel.css` es propio del feature,
no una copia de `../summary/HistoryPanel.css` sin commitear, según ya se
había resuelto en la entrega original).

## 2. Backend v2 aislado

Se generó un lanzador externo (fuera del repo, en el scratchpad de la
sesión) para el backend, sin tocar el worktree `feat/hu6-backend-soporte-ui`:

```
docker build -f backend/Dockerfile -t producer-v2-check-backend:latest .   # build context: el worktree backend_ui
docker run -d --name producer-v2-check -p 127.0.0.1:8020:8000 \
  -e PRODUCER_V2_ENABLED=true producer-v2-check-backend:latest
```

El `Dockerfile` del proyecto copia `data/` a la imagen y no monta volúmenes:
toda escritura de la API durante la verificación (catálogo, lecturas) ocurre
en el filesystem efímero del contenedor y se descarta con `docker rm`. No se
escribió nada en el `data/` real de ningún worktree.

Datos de prueba (sintéticos, vía la API real, no manipulación directa de
archivos):

- `POST /api/v2/sectors` × 2 (`Huerta norte (verificación)`,
  `Huerta sur (verificación)`) + un tercero (`Prueba café`, usado solo para
  verificar codificación UTF-8).
- `POST /api/v2/sensors` × 3: `check-sensor-a` (real, sector norte, con
  lecturas), `check-sensor-b` (`synthetic`, sector sur, **sin** lecturas —
  para probar el estado vacío), `check-sensor-c` (`unknown`, sin sector —
  para probar "Todos los sectores").
- `PATCH /api/v2/sectors/{norte}` → `primary_sensor_id=check-sensor-a`.
- `POST /sensors/check-sensor-a/readings` × 9 (legacy, `procedencia:
  "sintetico"`), fechas 2026-01-01..10 saltando el 01-03 (fecha faltante) y
  con `soil_moisture: null` el 01-05 (fila presente, valor faltante).

Verificado por `curl` directo contra el contenedor antes de tocar el
frontend: catálogo, `GET .../readings` con `status=ready`/`no_readings`,
`missing_dates`, `units`, `last_reading_date`, `data_age_days`, `provenance`,
sensor desconocido → 404 con cuerpo `{error:{code:"sensor_not_found",...}}`.
Se verificó explícitamente que no hay corrupción de UTF-8 de punta a punta
(`"Prueba café"` viaja y vuelve con los bytes `c3 a9` intactos); una lectura
inicial que parecía mostrar tildes rotas era un artefacto de la codificación
de la consola de la herramienta de shell usada para inspeccionar, no del
backend ni de los datos — se descartó comparando bytes crudos con un
archivo, no con la salida de terminal.

## 3. Frontend limpio contra el backend real

Bloqueo encontrado y cómo se resolvió: el backend fija
`allow_origins=["http://localhost:5173"]` en `CORSMiddleware` (sin
regex, sin wildcard). El puerto `5173` ya estaba ocupado por un proceso
ajeno y preexistente (`node.exe`, escuchando en `[::1]:5173`, resolución
IPv6 preferida por Windows/Chrome para el hostname `localhost`), que se
preservó sin tocar. Server otro puerto para el checkout limpio habría hecho
que el navegador enviara un `Origin` distinto de `http://localhost:5173` y
el backend real habría rechazado la petición por CORS (esto se confirmó:
apuntar a `http://localhost:5173` desde el navegador servía, de hecho, la
respuesta del proceso ajeno, no la del checkout limpio — se verificó por
ausencia de peticiones en el log del servidor propio).

Solución sin tocar el proceso ajeno ni el CORS del backend: se sirvió el
checkout limpio en `127.0.0.1:5174` con un proxy de desarrollo de Vite
(`server.proxy` en `vite.config.ts`, **solo en el checkout temporal, no
commiteado**) hacia `http://127.0.0.1:8020`, de forma que el navegador ve
peticiones same-origin (`http://127.0.0.1:5174/api/v2/...`) y Vite las
reenvía server-side al backend aislado. Esto no reemplaza la verificación
por un mock: las peticiones HTTP reales llegan al backend real; solo se
evita la restricción de CORS del navegador para poder inspeccionar la
integración completa en un navegador de verdad.

```
VITE_API_BASE_URL=  # cadena vacía: baseUrl.ts arma rutas relativas /api/v2/...
npx vite --host 127.0.0.1 --port 5174 --strictPort
```

## 4. Verificación funcional (navegador real, Chrome vía la extensión)

Todo lo siguiente se confirmó con capturas de pantalla y con el panel de red
del navegador (`read_network_requests`), no con mocks:

- **Catálogo real**: el selector "Tu sector" lista los 3 sectores creados
  por la API (incluido `Prueba café`, tildes correctas en el DOM real).
- **Selección de sector → sensor**: al elegir "Huerta norte" se dispara
  `GET /api/v2/sensors?sector_id=...` (200) y se auto-selecciona el sensor
  primario del sector (`check-sensor-a`, configurado vía `PATCH`).
- **Sector sin primario, un solo sensor**: "Huerta sur" auto-selecciona su
  único sensor (`check-sensor-b`), que además está marcado `synthetic` →
  aparece la etiqueta "Simulado" en el `<option>` y el chip "Datos
  simulados" junto al nombre.
- **"Todos los sectores"**: lista los 3 sensores, incluido
  `check-sensor-c` (sin sector) con la etiqueta "Procedencia sin declarar"
  (`source_kind: unknown`).
- **Estado vacío real**: `check-sensor-b` (sin lecturas) muestra "Todavía no
  hay mediciones para este punto..." — respuesta real `status:
  no_readings`, no simulada.
- **Historial con datos reales** (`check-sensor-a`): procedencia
  "Datos simulados · Solo para demostración" (de las lecturas, no del
  catálogo — correcto, la declaración del catálogo no debe pisar la
  procedencia real de las lecturas), "Última lectura: 10 de ene de 2026.
  Antigüedad: 253 días.", "21 fechas faltan en este período." (ventana de
  30 días), gráfico con el hueco del 01-03 sin unir y el 01-05 sin punto
  (`soil_moisture: null`), tabla con las 9 filas, fila del 01-05 con
  "Sin medición", fila del 01-08 con la lluvia sembrada (`2.0 mm`).
- **Períodos 7/30 reales**: cambiar a "Últimos 7 días" dispara
  `GET .../readings?days=7` (200); con 7 días no hay fechas dentro de la
  ventana totalmente ausentes (solo el 01-05 con valor nulo), y el mensaje
  de fechas faltantes correctamente no aparece.
- **Peticiones confirmadas en el panel de red**: `GET /api/v2/sensors`,
  `GET /api/v2/sensors?sector_id=...`, `GET
  /api/v2/sensors/{id}/readings?days=30|7`, todas `200` contra el backend
  real (no interceptadas ni mockeadas).
- **Teclado**: `Tab` desde "Aplicar" (control legacy) alcanza "Tu sector" y
  luego "Punto de medición" en orden lógico, con anillo de foco visible en
  ambos controles nuevos.
- Nota de desarrollo, no un bug: cada cambio de sensor/período dispara la
  petición de lecturas **dos veces** en el panel de red. Es
  `React.StrictMode` (activo en `main.tsx`, ya presente antes de esta
  entrega) invocando los efectos dos veces en desarrollo para detectar
  efectos no idempotentes; no ocurre en producción y no duplica pedidos
  reales fuera del modo desarrollo.

## 5. Verificación visual/dispositivo — pendiente explícito

**Viewport móvil real: no se pudo verificar.** `resize_window` no cambió la
resolución real renderizada por el navegador de esta sesión (se mantuvo en
1512×797 pese a pedir 390×844) — la misma limitación ya documentada en este
repo para otras entregas de HU6 con la misma herramienta de automatización
(ver `openspec/specs/alerting-ui/spec.md`, sección "Limitaciones
conocidas"). No se intentó una aproximación por CSS (contenedor angosto
inyectado) porque no sería una emulación de dispositivo real y ya está
señalado como límite conocido de la herramienta, no del frontend. Queda
pendiente una verificación en un dispositivo o navegador con redimensionado
genuino.

Lo que sí se verificó en escritorio con el navegador real: layout sin
solapamientos con datos reales de longitud variable (nombres largos con
tildes, tablas de 7 columnas + origen), foco de teclado visible, ausencia
de diálogos bloqueantes, sin errores de consola relevantes durante el
recorrido.

## 6. Correcciones aplicadas (solo frontend, fallos demostrados)

**Unidades sin traducir (bug real, confirmado en el navegador contra datos
reales del backend v2).** `formatReadingValue` en
`frontend/src/features/producer/readingsApi.ts` armaba el sufijo de unidad
concatenando literalmente el código que devuelve el contrato v2
(`degC`, `mm/day`, `MJ/m2/day`, ...), pensado para máquinas, no para
mostrarlo a un productor sin conocimientos técnicos. Se agregó una tabla de
traducción de presentación (`UNIT_DISPLAY_LABELS`) que muestra `°C`, `mm`,
`MJ/m²/día`, etc., y conserva el código crudo como resguardo si apareciera
una unidad no mapeada (nunca oculta la unidad). Se agregó una prueba de
regresión en `ProducerHistoryPanel.test.tsx` que falla si vuelve a aparecer
`degC`/`mm/day` en el DOM. No se tocó ningún otro comportamiento (unidades
de humedad del suelo siguen expresándose como `%` vía conversión explícita,
sin cambios).

No se encontraron otros fallos de integración de origen frontend. No se
encontraron fallos de backend en este alcance (catálogo + históricos); ver
sección 7 para lo que quedó fuera de foco.

## 7. Fuera de alcance de esta verificación

- Pronósticos, revisiones y recalibración v2 (`api-contract.md` los define,
  pero la propia entrega backend documentada en
  `docs/design/backend-producer-ui-first-delivery.md` los deja fuera de la
  "primera entrega"; la UI productor tampoco los integra por diseño de esta
  entrega — ver el mensaje "Los pronósticos del catálogo v2 todavía no
  están integrados").
- Feedback v2, alta/edición de sensores desde la UI, backend en general: sin
  cambios, según lo pedido.

## Comandos usados (resumen)

```bash
# Checkout limpio
git clone --no-hardlinks --quiet C:/Repo/AAI_Hydric_Stress <tmp>/frontend_clean_check
cd <tmp>/frontend_clean_check && git checkout --quiet aac3362
cd frontend && npm install --no-audit --no-fund
npx oxlint && npx tsc -b && npx vite build && npx vitest run

# Backend aislado
cd C:/Repo/AAI_Hydric_Stress_backend_ui
docker build -f backend/Dockerfile -t producer-v2-check-backend:latest .
docker run -d --name producer-v2-check -p 127.0.0.1:8020:8000 \
  -e PRODUCER_V2_ENABLED=true producer-v2-check-backend:latest
python seed_v2.py http://127.0.0.1:8020   # sectores/sensores/lecturas sintéticos vía API real

# Frontend limpio + proxy de verificación (server.proxy en vite.config.ts,
# solo en el checkout temporal)
npx vite --host 127.0.0.1 --port 5174 --strictPort

# Cierre
docker stop producer-v2-check && docker rm producer-v2-check
docker rmi producer-v2-check-backend:latest
```

## Estado de los worktrees al finalizar

- Backend (`feat/hu6-backend-soporte-ui`): sin cambios (`git status` limpio).
  El contenedor y la imagen de verificación se eliminaron; ningún dato del
  worktree se escribió ni se leyó fuera de lo que ya estaba commiteado.
- Frontend (`feat/hu6-ui-productor-integracion`): se agregó el fix de
  unidades y su test (ver commit). Todos los cambios previos sin commitear
  (backend/, `docs/seguimiento-tareas.md`, `openspec/specs/alerting-ui/spec.md`,
  `frontend/src/features/summary/{HistoryPanel*,historyApi.ts}`,
  `ResumenView.*`, `openspec/changes/add-measurement-history-overview/`,
  `work/`, `docker-compose.override.yml`, datos de prueba en `data/`) se
  preservaron intactos y no se incluyeron en el commit de esta verificación.
- Procesos: se detuvieron únicamente los iniciados en esta verificación
  (contenedor `producer-v2-check`, Vite en `127.0.0.1:5174`). Los procesos
  y contenedores preexistentes del usuario (`aai-hydric-stress-*`, el
  proceso Node en `5173`) no se tocaron.
