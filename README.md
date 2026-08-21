# AAI_Hydric_Stress

Prototipo experimental de la arquitectura de inteligencia artificial para detección temprana de estrés hídrico en cultivos hortícolas — Trabajo Final, Maestría en Inteligencia Artificial (FIUBA).

Ver [`docs/adr/`](docs/adr/) para las decisiones de arquitectura y stack técnico, y [`openspec/project.md`](openspec/project.md) para el contexto, alcance y convenciones del proyecto.

## Estado del proyecto

Ver [`docs/seguimiento-tareas.md`](docs/seguimiento-tareas.md) para la auditoría detallada, tarea por tarea, con evidencia verificable. Resumen por historia de usuario:

| HU | Capacidad | Estado |
|----|-----------|--------|
| HU1 | Estado del arte y comprensión del dominio | 🟡 Parcial (búsqueda dirigida; falta protocolo sistemático en bases institucionales) |
| HU2 | `data-ingestion` — preparación del conjunto experimental de datos | 🟡 Parcial (NASA POWER + ESA CCI consolidados; falta 1 fuente) |
| HU3 | `data-quality` — calidad, anomalías y datos sintéticos | ✅ Completa |
| HU4 | `predictive-modeling` — modelado predictivo y alertas tempranas | ✅ Completa |
| HU5 | `human-feedback` — retroalimentación humana y recalibración | ✅ Completa |
| HU6 | `architecture-integration` — integración de la arquitectura | ✅ Completa |
| HU7 | `experiment-runner` — diseño y ejecución del plan experimental | ✅ Completa |
| HU8 | Análisis de resultados y contrastación de la hipótesis | ✅ Completa |

Además de las HU del backlog de tesis, el repo incluye una interfaz de usuario (`backend/` + `frontend/`, ver sección siguiente) que expone HU5+HU6 y cierra el loop de recalibración manual disparada desde la UI (ver `docs/adr/0006-recalibracion-disparada-desde-la-ui.md`).

## Estructura del código

- `src/data_ingestion/`: esquema del contrato de datos, conectores (NASA POWER, ESA CCI Soil Moisture) y consolidación de fuentes.
- `src/data_quality/`: limpieza, detección de anomalías (Isolation Forest), generación de datos sintéticos y pipeline integrado.
- `src/predictive_modeling/`: etiquetado, ingeniería de variables, modelos (persistencia, regresión logística, Random Forest), evaluación y alertas.
- `src/human_feedback/`: esquema y registro de retroalimentación humana sobre alertas, e integración con predicciones para recalibración supervisada.
- `src/architecture_integration/`: orquestador de punta a punta que encadena las cuatro capacidades anteriores.
- `src/experiment_runner/`: ejecución del plan experimental (escenarios de escasez/ruido, aumentación sintética, registro de corridas en MLflow).
- `scripts/`: puntos de entrada de línea de comandos para correr cada pipeline sobre un dataset real (`run_data_quality_pipeline.py`, `run_end_to_end_pipeline.py`, conectores de ingesta).
- `backend/`: API FastAPI de la interfaz de usuario (alerting-ui) — fachada delgada que orquesta el pipeline y expone `POST /forecast/run`, `GET /feedback` + confirmar/rechazar, y `POST /recalibrate`.
- `frontend/`: aplicación React + TypeScript (Vite) que consume esa API — pronóstico, validación humana de alertas y disparo manual de recalibración.
- `openspec/specs/`: especificación viva de cada capacidad (requisitos, escenarios, verificación con datos reales, limitaciones conocidas). `openspec/changes/`: historial de decisiones de diseño por *change*.
- `docs/adr/`: decisiones de arquitectura, desde el stack técnico del PoC (ADR-0001/0002) hasta el stack web, MLflow/MinIO y la dockerización de backend/frontend (ADR-0003 a ADR-0006).

## Interfaz de usuario (alerting-ui)

Backend y frontend dockerizados que exponen el pipeline completo (HU6) y la retroalimentación humana (HU5), incluyendo recalibración manual del modelo desde un botón en la UI (ver `docs/seguimiento-tareas.md`, sección "Interfaz de usuario").

Para levantar el stack completo (Postgres + MinIO + MLflow + backend + frontend):

```bash
cp .env.example .env   # ajustar si hace falta
docker compose up -d --build
```

- Frontend: http://localhost:5173
- Backend (FastAPI): http://localhost:8000
- MLflow Tracking UI: http://localhost:5000

## Desarrollo y tests

Se recomienda ejecutar el proyecto dentro del devcontainer/Docker incluido, para evitar restricciones de políticas de Control de Aplicaciones de Windows sobre las DLL nativas de pandas/pyarrow en algunos equipos:

```bash
docker build -t aai-hydric-stress-test .
docker run --rm aai-hydric-stress-test
```

También puede abrirse la carpeta en VS Code con la extensión Dev Containers (`.devcontainer/devcontainer.json`).

Si el entorno local no tiene esa restricción, alternativamente:

```bash
pip install -e ".[dev,backend]"
pytest -q                    # tests de src/ (núcleo)
pytest backend/tests -q      # tests del backend de alerting-ui
```

Para los tests del frontend:

```bash
cd frontend
npm install
npm run test
```
