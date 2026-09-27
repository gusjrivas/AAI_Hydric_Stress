# Frontend — demo de arquitectura de IA (alerting-ui)

## Recorrido histórico de defensa: Pergamino

Abrir `http://localhost:5173/#defensa-pergamino`. La pantalla consulta emisiones y
lecturas **ya persistidas** por las rutas `GET /api/v2/sensors/pergamino-ensemble-demo/historical/...`;
no emite nuevas predicciones. Hay cinco emisiones navegables, del **13 al 17 de
junio de 2023**. El reloj puede avanzar hasta el 20 de junio; una lectura ausente
permanece marcada como dato faltante. Las revisiones de la demo se guardan en el
`HistoricalReviewStore` aislado del almacenamiento operativo.

Arranque local en PowerShell desde la raíz del repositorio, con Python y Node
instalados y los artefactos reales ya disponibles fuera del checkout:

```powershell
$env:PRODUCER_SOURCE_DATA_DIR = '<directorio externo con sensor__pergamino-ensemble-demo.parquet y ui_metadata/operational_v2__pergamino-ensemble-demo.json>'
$env:PRODUCER_BUNDLE_ROOT = '<directorio externo que contiene pergamino-ensemble-demo/horizon_1..3>'
.\scripts\prepare_defense_data.ps1 -SourceDataDir $env:PRODUCER_SOURCE_DATA_DIR -DemoDataDir '.demo-defense-data\session-1'
$env:PRODUCER_DATA_DIR = (Resolve-Path '.demo-defense-data\session-1').Path
python scripts/run_producer_preview_backend.py
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

El backend escucha en `127.0.0.1:8000` y el frontend usa ese origen por
defecto. Si se cambia el puerto o host, configurar `VITE_API_BASE_URL` y
`CORS_EXTRA_ORIGINS` según los scripts existentes. `prepare_defense_data.ps1`
rechaza un destino existente para conservar cada sesión, verifica los SHA-256
de ambos insumos persistidos y nunca copia revisiones previas. La ruta
`POST /forecasts` no forma parte de este recorrido.

La evaluación agregada se sirve desde `public/retrospective-2023.json`, una
proyección versionada de los artefactos canónicos `ui_summary.json` y
`metrics.json`, sin predicciones fechadas ni bundles. Para verificarla:

```powershell
node scripts/check_retrospective_projection.mjs
# Con los artefactos canónicos disponibles, verifica también sus hashes:
node scripts/check_retrospective_projection.mjs '<directorio de salida canónica>'
# Solo si se dispone de la salida canónica y se necesita reproducir la proyección:
node scripts/project_retrospective_ui.mjs '<directorio de salida canónica>' frontend/public/retrospective-2023.json
```

### Guion de demostración (unos cinco minutos)

1. Abrir el recorrido y señalar Pergamino, ERA5-Land/NASA POWER, la calidad de datos y las **cinco** fechas de emisión disponibles.
2. Elegir `2023-06-13`. Comparar las tarjetas +1/+2/+3, fechas objetivo y el acuerdo de los tres modelos; abrir los scores. `as_of_date` es la emisión, `target_date` el objetivo.
3. Avanzar el reloj al `2023-06-14`. Mostrar la observación posterior de +1 y que +2/+3 todavía no están disponibles según el reloj.
4. Confirmar o rechazar +1 y guardar un comentario marcado como prueba técnica. Recargar y consultar la revisión persistida. Volver al `2023-06-13` para mostrar que el reloj oculta la revisión y la observación futuras.
5. Navegar a `2023-06-14` y volver a `2023-06-13`; abrir el panel agregado 2023 y sus tablas. Explicar el carácter exploratorio no independiente, la desviación de ejecución duplicada y el FAIL de gobernanza.

La disponibilidad del paso 3 depende de las lecturas persistidas del directorio
externo elegido; no se inventan observaciones ni se cubre todo 2023 con emisiones
navegables. Se comprobaron las cinco emisiones, el reloj y una revisión aislada
mediante HTTP contra el backend real. La inspección en navegador y las capturas
siguen pendientes porque una preferencia guardada bloquea `127.0.0.1:5174` en
la herramienta de navegador de este entorno.

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
