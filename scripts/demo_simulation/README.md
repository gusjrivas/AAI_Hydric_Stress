# Demostración dinámica acelerada (HU6)

Reproduce un período pasado sintético, un día calendario por paso, contra los
endpoints reales de ingesta y pronóstico (`alerting-ui`), para mostrar cómo
crecen el historial y los pronósticos registrados en el tiempo. Ver
[`openspec/changes/add-accelerated-sensor-demo/`](../../openspec/changes/add-accelerated-sensor-demo/)
para el diseño completo y el estado de tareas.

**Alcance de las entregas implementadas (1 y 2 de 4):** `prepare`, `run` y
`status` por línea de comandos (entrega 1); lock de proceso, máquina de
estados persistida, adaptador HTTP local de control (`serve`,
inicio/pausa/continuación) y perfil Docker opcional `demo` (entrega 2).
Todavía no existe: la UI de demostración (entrega 3) ni la verificación
integrada final (entrega 4).

## Requisitos

- Backend real corriendo y accesible (por defecto `http://localhost:8000`):

  ```
  cd backend && uvicorn app.main:app --reload
  ```

## Preparar una sesión

```
python -m scripts.demo_simulation prepare --start 2026-01-01 --days 5 \
    --history-days 120 --seed 42
```

- `--start`: primer día calendario a reproducir (debe ser pasado; el período
  completo, incluido el horizonte de pronóstico vigente, también debe serlo).
- `--days`: cantidad de días a reproducir.
- `--history-days`: días de historial sintético previo a `--start` (no se
  publica ningún día de reproducción por adelantado).
- `--seed`: semilla base del generador (`data_ingestion.mock_sensor`), fija
  antes de ver ningún resultado — no se elige por las alertas que produce.
- Opcionales: `--backend-url`, `--interval-seconds` (1-60, default 5),
  `--sessions-dir` (default `demo_sessions/` en la raíz del repo),
  `--data-dir` (default `data/`, el mismo que usa el backend).

`prepare` asigna un sensor nuevo `demo-<id>` (no elegible por quien ejecuta el
comando) y rechaza la preparación si esa sesión, su dataset o su feedback log
ya existen — nunca sobrescribe. La salida incluye el identificador de sesión
y el comando siguiente.

## Ejecutar la sesión

```
python -m scripts.demo_simulation run --id demo-xxxxxxxxxx
```

Ejecuta todos los pasos pendientes (o `--steps N` para una cantidad fija),
esperando `interval_seconds` entre pasos exitosos. Cada paso: genera y
persiste el payload del día → `POST /sensors/{sensor_id}/readings` → verifica
por `GET /quality/{sensor_id}` que no hay días posteriores → `POST
/forecast/{sensor_id}/run` → confirma por `GET /feedback/{sensor_id}`.

Ante cualquier fallo o resultado que no pueda confirmarse (incluido un
timeout, que nunca se interpreta como cancelación), la sesión queda
`blocked` y no reintenta automáticamente. `run` sostiene el mismo lock de
proceso que usa el adaptador HTTP de control (`scripts.demo_simulation.lock`):
no puede correr al mismo tiempo que `serve` sobre la misma sesión.

## Ver el estado de una sesión

```
python -m scripts.demo_simulation status --id demo-xxxxxxxxxx
```

Imprime el manifiesto completo (`demo_sessions/<id>/manifest.json`): estado,
cursor, fases por día, hashes de payload y veredictos confirmados.

## Adaptador HTTP local de control (entrega 2)

Controla una sesión ya preparada por `prepare` (no crea sesiones nuevas):
inicio, pausa y continuación explícita, con exclusión de proceso y
deduplicación de órdenes repetidas. Es un servicio local, pensado para uso
propio o desde una UI de demostración (entrega 3), nunca para exposición
pública.

```
python -m scripts.demo_simulation serve --id demo-xxxxxxxxxx
```

- `--host`/`--port`: por defecto `127.0.0.1:8010` (loopback; nunca `0.0.0.0`
  fuera del perfil Docker, ver más abajo).
- `--allowed-origin` (repetible) o la variable de entorno
  `DEMO_CONTROL_ALLOWED_ORIGIN` (lista separada por comas): origins
  autorizados para CORS y para la validación explícita de `Origin` en cada
  mutación. Por defecto `http://localhost:5173`.

Contrato HTTP (cuerpo JSON `{"session_id", "expected_revision", "request_id"}`
en cada orden de control):

| Endpoint | Efecto |
|---|---|
| `GET /demo/session` | Estado actual; nunca crea recursos, nunca inicia el worker, nunca avanza la sesión. |
| `POST /demo/session/start` | Inicia una sesión `prepared`. |
| `POST /demo/session/pause` | Solicita pausa: el paso en curso termina igual, nunca se cancela un POST en vuelo; el siguiente paso no arranca. |
| `POST /demo/session/resume` | Continúa una sesión `paused`, o intenta reconciliar y despejar una `blocked` antes de continuar. Nunca es automático: siempre requiere esta orden explícita, incluso después de un reinicio del proceso `serve`. |

Reglas de las órdenes de control: un `request_id` repetido devuelve el mismo
resultado ya registrado, sin iniciar un segundo worker; un
`expected_revision` desactualizado se rechaza con 409 (nunca se aplica en
silencio); una transición no válida desde el estado vigente también se
rechaza con 409. El backend de destino queda fijado en el manifiesto desde
`prepare`; ningún campo de la orden HTTP puede cambiarlo.

### Diagnosticar una sesión bloqueada

`GET /demo/session` (o `status` por CLI) incluye `error` con el motivo. Las
causas posibles en esta entrega:

- **Incertidumbre sobre un pronóstico:** el proceso se reinició o perdió la
  respuesta de `POST /forecast/{sensor_id}/run` sin poder confirmar, por
  `GET /feedback/{sensor_id}`, si el backend llegó a registrarlo. No se
  reintenta solo: `resume` vuelve a intentar la reconciliación por lectura
  antes de decidir si continúa o si el bloqueo persiste.
- **Cambio externo del dataset:** el estado de `GET /quality/{sensor_id}` no
  coincide ni con el último paso confirmado por esta sesión ni con su propio
  paso pendiente. No se sobrescribe ni se borra nada; requiere revisión
  manual del sensor de demostración.
- **Fallo de ingesta o pronóstico reportado por el backend** (por ejemplo,
  422 sin historial entrenable): igual que en la entrega 1, se conserva lo ya
  aceptado y se detiene el avance.

Una sesión bloqueada nunca se repara borrando o sobrescribiendo el dataset o
el manifiesto: `resume` es el único camino, y solo avanza si la
reconciliación es satisfactoria.

## Perfil Docker opcional `demo`

Servicio `demo-control` en `docker-compose.yml`, bajo el perfil `demo`: no se
construye ni se levanta con `docker compose up` normal, y no modifica
`docker-compose.override.yml`. Reutiliza el entorno Python del proyecto
(`docker/demo-control/Dockerfile`) sin copiar `data/`: el worker de control
accede al estado del backend únicamente vía HTTP (`GET /quality`,
`GET /feedback`), nunca por lectura directa de archivos.

1. Levantar el backend habitual (`docker compose up -d backend mlflow ...`).
2. Preparar la sesión apuntando al backend de la red de Compose (no a
   `localhost`, que no resuelve dentro del contenedor de control):

   ```
   docker compose --profile demo run --rm demo-control \
       prepare --start 2026-01-01 --days 5 --history-days 120 --seed 42 \
       --backend-url http://backend:8000
   ```

   El manifiesto queda en `./demo_sessions/` (montado como volumen); tomar
   nota del `session_id` impreso (`demo-<id>`).
3. Levantar el servicio de control con ese identificador:

   ```
   DEMO_SESSION_ID=demo-<id> docker compose --profile demo up demo-control
   ```

   Variables de entorno relevantes: `DEMO_SESSION_ID` (obligatoria para que
   el contenedor sirva algo; sin ella, la CLI rechaza `--id ""` con un
   mensaje diagnosticable, en vez de romper `docker compose` para el resto
   del proyecto), `DEMO_CONTROL_PORT` (por defecto `8010`, enlazado a
   `127.0.0.1` del host), `DEMO_CONTROL_ALLOWED_ORIGIN`.
4. Controlar la sesión desde el host: `curl http://127.0.0.1:8010/demo/session`,
   y las órdenes `POST` descritas arriba.

## Verificación de esta entrega

- `pytest tests/demo_simulation` (56 tests, 1 marcado `skip` por una
  condición de temporización no determinística documentada en el propio
  test — ver limitaciones): contra un backend real (`app.main.app` servido
  por `uvicorn` en un hilo, HTTP real) y un registro MLflow aislado en
  sqlite temporal. `tests/demo_simulation/test_control.py` cubre lock de
  proceso, deduplicación de órdenes, revisión obsoleta, transición inválida,
  pausa durante un paso en curso, continuación explícita, reconciliación de
  una respuesta perdida (sin reenvío del pronóstico), bloqueo por
  incertidumbre y detección de un cambio externo al dataset.
  `tests/demo_simulation/test_service.py` cubre el contrato HTTP con
  `fastapi.testclient.TestClient` (in-process, sin backend real de por
  medio en el transporte): pureza de `GET`, deduplicación e invalidación de
  revisión sobre HTTP, validación de `Origin` y que el `backend_url` del
  manifiesto no puede reconfigurarse desde una orden.
- `ruff check scripts/demo_simulation tests/demo_simulation` y
  `black --check scripts/demo_simulation tests/demo_simulation`.
- `docker build -f docker/demo-control/Dockerfile .` y
  `docker compose --profile demo config` verificados manualmente; el
  servicio no aparece en `docker compose config --services` sin el perfil.

## Limitaciones declaradas

- El generador (`data_ingestion.mock_sensor`) es un random walk acotado, no
  un modelo físico de cultivo: no garantiza estacionalidad, balance hídrico
  ni escenarios de secado/lluvia realistas (queda para un change posterior).
- No hay garantía de ejecución única del modelo o del pronóstico ante una
  pérdida de respuesta HTTP: el backend/MLflow subyacentes no ofrecen una
  clave de idempotencia. El requisito de esta entrega es no duplicar
  registros ni avanzar sin confirmación (recuperación conservadora, con
  bloqueo explícito ante incertidumbre), nunca una garantía
  exactamente-una-vez sobre la ejecución interna del modelo.
- La exclusión de proceso (`SessionLock`) protege contra dos workers de esta
  herramienta (CLI directa o adaptador HTTP) sobre la misma sesión; no
  excluye a otros clientes HTTP externos que operen directamente contra el
  backend con el mismo `sensor_id` de demostración.
- Un test de pausa (`test_pause_completes_current_step_before_stopping`) se
  omite (`skip`) en el caso de borde en que, en un entorno particularmente
  rápido, la sesión de dos pasos completa antes de que la orden de pausa
  llegue a aplicarse; el resto de la aserción de "la pausa nunca cancela un
  paso en curso" queda cubierto igual por
  `test_recovery_reconciles_confirmed_forecast_without_reposting` y
  `test_resume_continues_from_first_incomplete_step`.
- El perfil Docker `demo` no fue verificado con el stack de Compose completo
  corriendo end-to-end (postgres/minio/mlflow/backend reales en contenedores
  más `demo-control` controlando una sesión); se verificó la construcción de
  la imagen, la validez de la configuración de Compose (con y sin el
  perfil) y el comportamiento de error ante `--id` vacío. La verificación de
  extremo a extremo queda pendiente para cuando exista la UI (entrega 3) o
  se documente explícitamente como parte del cierre de esta entrega.
