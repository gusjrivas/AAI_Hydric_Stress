# Demostración dinámica acelerada (HU6)

Reproduce un período pasado sintético, un día calendario por paso, contra los
endpoints reales de ingesta y pronóstico (`alerting-ui`), para mostrar cómo
crecen el historial y los pronósticos registrados en el tiempo. Ver
[`openspec/changes/add-accelerated-sensor-demo/`](../../openspec/changes/add-accelerated-sensor-demo/)
para el diseño completo y el estado de tareas.

**Alcance de esta entrega (1 de 4):** solo `prepare` y `run` por línea de
comandos, ejecutados de punta a punta en el propio proceso de la CLI. Todavía
no existen: lock de proceso ni pausa/continuación persistente, adaptador HTTP
de control, UI ni perfil Docker (entregas 2-4).

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
`blocked` y no reintenta automáticamente — la recuperación conservadora es
la entrega 2 de este change.

## Ver el estado de una sesión

```
python -m scripts.demo_simulation status --id demo-xxxxxxxxxx
```

Imprime el manifiesto completo (`demo_sessions/<id>/manifest.json`): estado,
cursor, fases por día, hashes de payload y veredictos confirmados.

## Verificación de esta entrega

- `pytest tests/demo_simulation` (37 tests): contra un backend real
  (`app.main.app` servido por `uvicorn` en un hilo, HTTP real — no
  `TestClient`) y un registro MLflow aislado en sqlite temporal. Incluye
  cinco pasos consecutivos, causalidad temporal, no publicación de días
  futuros, bloqueo sin reintento ante fallos de ingesta/pronóstico, y
  preservación de archivos de sensores ajenos.
- `ruff check scripts/demo_simulation tests/demo_simulation` y
  `black --check scripts/demo_simulation tests/demo_simulation`.

## Limitaciones declaradas

- El generador (`data_ingestion.mock_sensor`) es un random walk acotado, no
  un modelo físico de cultivo: no garantiza estacionalidad, balance hídrico
  ni escenarios de secado/lluvia realistas (queda para un change posterior).
- No hay garantía de ejecución única del modelo o del pronóstico ante una
  pérdida de respuesta HTTP; el requisito de esta entrega es no duplicar
  registros ni avanzar sin confirmación, no una transacción exactamente-una-vez.
- No excluye a otros clientes HTTP del mismo sensor ni impide dos workers
  simultáneos (lock de proceso: entrega 2).
