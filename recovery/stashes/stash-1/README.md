# stash@{1}

- Origen: `On feat/hu6-ui-productor-integracion: !!GitHub_Desktop<feat/hu6-ui-productor-integracion>`
- Commit del stash: `a78c25c01a4390110846990858a91c961fa94237`
- Base: `a250a9e8d6af7a33f746031345a369a8059890b1` (`feat(HU6): consulta de pronósticos y revisión humana en Mi cultivo`, 2026-09-20 18:17:23 -0300; ancestro de `origin/main`)
- Fecha del stash: 2026-09-22 19:18:18 -0300

## Contenido

32 archivos (1290 inserciones, 3 eliminaciones), listados en `files.txt`; copias de los archivos completos en `files/`; `stash-1.patch` es el patch completo con `--binary`. Grupos principales:

- Cambio OpenSpec `add-measurement-history-overview` (proposal, spec delta, tasks) y delta de `openspec/specs/alerting-ui/spec.md`.
- Backend: endpoint de solo lectura `GET /sensors/{sensor_id}/history` (`backend/app/routers/sensors.py`, `schemas.py`, `backend/tests/test_sensor_history.py`).
- Frontend: `HistoryPanel`, `historyApi.ts`, ajustes de `ResumenView` y tests.
- `docker-compose.override.yml`, `docs/seguimiento-tareas.md`.
- Datos de prueba de sensor: `data/feedback__sensor-a.parquet`, `data/sensor__sensor-a.parquet` (binarios; están en `files/`; no se leyeron ni ejecutaron).
- Directorios `work/backend-specs-staging/` y `work/ui-mock/`: scripts y maquetas HTML/`.cjs`/`.ps1` de trabajo. Se conservan sin ejecutar.

## Relevancia aparente

Trabajo de UI/backend (HU6, alerting-ui) de historial de mediciones, anterior a la integración posterior de la UI de productor. Sin impacto sobre configuración experimental ni sobre el estado científico.

## Equivalente en main

Equivalencia exacta: no. Ninguno de `HistoryPanel.tsx`, `historyApi.ts`, `test_sensor_history.py`, `docker-compose.override.yml` ni la carpeta `add-measurement-history-overview` existe en `origin/main`. `origin/main` tiene una funcionalidad de historial distinta (`ProducerHistoryPanel`, `/replay/history`), por lo que podría haber superposición funcional parcial, no verificada.

## Decisión provisional

Preservado íntegro. Probablemente superado por el desarrollo posterior de la UI de productor, pero no se comprobó; no incorporar a main.
