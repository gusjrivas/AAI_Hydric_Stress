# Frontend — demo de arquitectura de IA (alerting-ui)

React + TypeScript + Vite, sin router ni librería de estado global (ver
`docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md`). Consume la API del
backend (`../backend/`) por HTTP; no accede a `src/`, `data/` ni MLflow
directamente.

## Ejecutar en desarrollo

```bash
npm install
npm run dev
```

Por defecto apunta a `http://localhost:8000`. Para apuntar a otro backend,
configurar `VITE_API_BASE_URL` (ver `.env.example`):

```bash
cp .env.example .env   # editar VITE_API_BASE_URL si hace falta
```

## Tests, lint y build

```bash
npm test
npm run lint
npm run build
```

## Estructura

Una sola página (`App.tsx`), organizada por *feature* en `src/features/`:

- `architecture-flow/`: guía visual de las etapas de la arquitectura, con anclas a cada sección.
- `quality/`: panel de calidad y anomalías (`GET /quality/{sensor_id}`).
- `forecast/`: pronóstico, alerta, feedback humano y recalibración (flujo existente desde HU5/HU6, más el predictor activo vía `GET /models/{sensor_id}/active`).
- `lineage/`: reconstrucción de la cadena de recalibraciones A→B→C (`GET /lineage/{sensor_id}`).
- `evidence/`: panel estático de evidencia científica formal (`controlled_daily_v3`), sin llamadas HTTP.
