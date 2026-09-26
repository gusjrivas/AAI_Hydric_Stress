# Arranque local reproducible: UI de productor contra el recorrido real de Pergamino

Mecanismo documentado para levantar backend + frontend con los artefactos reales
ya preparados (Hito 2, PR #219/#220), sin hardcodear rutas de una máquina
particular en código versionado, y sin sustituir insumos faltantes por
fixtures. Corresponde a la corrección de PR #221, sección 5.

## Qué NO es esto

- **No** es `docker-compose.producer-preview.yml` (si existe en el
  repositorio): ese flujo prepara datos **sintéticos**, nunca sirve como
  evidencia del recorrido real de Pergamino.
- **No** toca `historical_replay`/`replay_packages/`: es un sistema
  distinto, con su propio contrato de un solo escalar.
- **No** reentrena, recalibra ni prepara nuevas emisiones: solo sirve lo
  que ya está persistido.

## 1. Directorios externos requeridos

| Variable | Contenido esperado | Nunca |
| --- | --- | --- |
| `PRODUCER_DATA_DIR` | Catálogo, lecturas (`sensor__<sensor_id>.parquet`) y emisiones ya preparadas (`ui_metadata/operational_v2__<sensor_id>.json`) del recorrido real ya ejecutado (PR #219/#220). | `data/` del repositorio; `replay_packages/`. |
| `PRODUCER_BUNDLE_ROOT` | Los 9 bundles reales del ensamble (3 familias × 3 horizontes) de la ejecución real autorizada (PR #219). | Un directorio con bundles de prueba/sintéticos. |

Ambos son externos al repositorio (nunca se versionan). Los valores reales
usados en la verificación de PR #221 se documentaron aparte, fuera de
archivos versionados (ver la descripción del PR).

## 2. Backend

```bash
# bash
PRODUCER_DATA_DIR=<tu directorio con catálogo/lecturas/emisiones reales> \
PRODUCER_BUNDLE_ROOT=<tu directorio con los 9 bundles reales> \
    python scripts/run_producer_preview_backend.py
```

```powershell
# PowerShell
$env:PRODUCER_DATA_DIR = "<tu directorio con catálogo/lecturas/emisiones reales>"
$env:PRODUCER_BUNDLE_ROOT = "<tu directorio con los 9 bundles reales>"
python scripts/run_producer_preview_backend.py
```

`scripts/run_producer_preview_backend.py`:

- Valida que `PRODUCER_DATA_DIR` tenga al menos una lectura
  (`sensor__*.parquet`) y al menos una emisión preparada
  (`ui_metadata/operational_v2__*.json`) — si falta cualquiera, falla con
  un mensaje concreto explicando exactamente qué falta, nunca arranca en
  un estado a medias ni sustituye con datos inventados.
- Valida que `PRODUCER_BUNDLE_ROOT` tenga al menos un
  `ensemble_manifest.json` en algún subdirectorio.
- Habilita `PRODUCER_V2_ENABLED=true` y sirve en `http://127.0.0.1:8000`
  (configurable con `PRODUCER_PREVIEW_HOST`/`PRODUCER_PREVIEW_PORT`).
- El feedback de la demostración (`HistoricalReviewStore`,
  `src/human_feedback/historical_review_store.py`) queda aislado
  automáticamente dentro del mismo `PRODUCER_DATA_DIR`, en su propio
  subdirectorio (`historical_feedback/<sensor_id>.json`) — nunca en
  `ui_metadata/operational_v2__<sensor_id>.json`, que sigue siendo
  exclusivo de las revisiones operativas reales.

Si el puerto TCP 8000 (IPv4 o IPv6) ya está en uso por otro servicio en la
máquina (por ejemplo, un túnel de WSL escuchando en `[::1]:8000`), usar
`PRODUCER_PREVIEW_PORT` para elegir otro puerto explícito, y apuntar el
frontend a `http://127.0.0.1:<ese puerto>` (ver sección 3) — nunca asumir
que "localhost" resuelve al backend recién levantado.

## 3. Frontend

En `frontend/.env.development.local` (gitignored, nunca versionado):

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

(ajustar el puerto si se usó `PRODUCER_PREVIEW_PORT`). Luego:

```bash
cd frontend
npm run dev
```

`backend/app/main.py` ya permite el origen `http://localhost:5173` por
defecto; si Vite eligió otro puerto (por ejemplo porque el 5173 estaba
ocupado), agregar `CORS_EXTRA_ORIGINS=http://localhost:<puerto>` a las
variables de entorno del backend antes de levantarlo.

## 4. Verificación mínima de que apunta a datos reales

```bash
curl http://127.0.0.1:8000/api/v2/sensors
curl http://127.0.0.1:8000/api/v2/sensors/<sensor_id>/historical/<fecha-ya-preparada>/forecasts
```

La segunda llamada debe devolver `score_kind: "ensemble_mean_of_calibrated_components"`
y un objeto `ensemble` con 3 `components` — si devuelve
`batch_not_prepared`, la fecha no fue preparada en ese `PRODUCER_DATA_DIR`
(no es un error del mecanismo de arranque).

## 5. Detener / reiniciar

- Backend: `Ctrl+C` en la terminal donde corre
  `run_producer_preview_backend.py` (o cerrar el proceso `uvicorn`).
- Frontend: `Ctrl+C` en la terminal donde corre `npm run dev`.
- Reiniciar: repetir los pasos 2 y 3. El script vuelve a validar los
  directorios en cada arranque; no persiste estado propio.
