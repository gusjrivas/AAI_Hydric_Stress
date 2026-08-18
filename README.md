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
| HU7 | `experiment-runner` — diseño y ejecución del plan experimental | ⬜ No iniciada |
| HU8 | Análisis de resultados y contrastación de la hipótesis | ⬜ No iniciada |

## Estructura del código

- `src/data_ingestion/`: esquema del contrato de datos, conectores (NASA POWER, ESA CCI Soil Moisture) y consolidación de fuentes.
- `src/data_quality/`: limpieza, detección de anomalías (Isolation Forest), generación de datos sintéticos y pipeline integrado.
- `src/predictive_modeling/`: etiquetado, ingeniería de variables, modelos (persistencia, regresión logística, Random Forest), evaluación y alertas.
- `src/human_feedback/`: esquema y registro de retroalimentación humana sobre alertas, e integración con predicciones para recalibración supervisada.
- `src/architecture_integration/`: orquestador de punta a punta que encadena las cuatro capacidades anteriores.
- `scripts/`: puntos de entrada de línea de comandos para correr cada pipeline sobre un dataset real (`run_data_quality_pipeline.py`, `run_end_to_end_pipeline.py`, conectores de ingesta).
- `openspec/specs/`: especificación viva de cada capacidad (requisitos, escenarios, verificación con datos reales, limitaciones conocidas). `openspec/changes/`: historial de decisiones de diseño por *change*.

## Desarrollo y tests

Se recomienda ejecutar el proyecto dentro del devcontainer/Docker incluido, para evitar restricciones de políticas de Control de Aplicaciones de Windows sobre las DLL nativas de pandas/pyarrow en algunos equipos:

```bash
docker build -t aai-hydric-stress-test .
docker run --rm aai-hydric-stress-test
```

También puede abrirse la carpeta en VS Code con la extensión Dev Containers (`.devcontainer/devcontainer.json`).

Si el entorno local no tiene esa restricción, alternativamente:

```bash
pip install -e ".[dev]"
pytest -q
```
