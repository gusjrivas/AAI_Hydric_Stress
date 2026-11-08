# AAI_Hydric_Stress

Prototipo experimental de la arquitectura de inteligencia artificial para detección temprana de estrés hídrico en cultivos hortícolas — Trabajo Final, Maestría en Inteligencia Artificial (FIUBA).

Ver [`docs/adr/`](docs/adr/) para las decisiones de arquitectura y stack técnico, y [`openspec/project.md`](openspec/project.md) para el contexto, alcance y convenciones del proyecto.

## Cómo levantar el proyecto

Requisitos: Docker con contenedores Linux (camino recomendado); para desarrollo sin Docker, Python 3.10 o superior y Node.js con npm.

**1. Stack completo (Postgres, MinIO, MLflow, backend y frontend):**

```bash
cp .env.example .env   # valores de desarrollo local, no credenciales de producción
docker compose up -d --build
```

| Servicio | URL |
|----------|-----|
| Frontend (interfaz de presentación) | http://localhost:5173 |
| Backend (FastAPI) | http://localhost:8000 |
| MLflow Tracking UI | http://localhost:5000 |
| Consola de MinIO | http://localhost:9001 |

La interfaz abre en **Arquitectura**. El menú principal sigue el orden de la defensa: **Arquitectura** (cómo está construido), **Caso de demostración** (Pergamino, Melchor Romero y Laboratorio de sensores) y **Resultados** (qué se obtuvo). **Mi cultivo** y **Herramientas técnicas** están bajo «Más».

**2. Solo la interfaz de Mi cultivo, con datos y modelos sintéticos:** `docker compose -f compose.producer-preview.yml up -d --build` y abrir http://localhost:5180 (ver [`docker/producer-preview/README.md`](docker/producer-preview/README.md)). No requiere instalar Python/Node, no modifica los servicios del stack habitual y no representa validación predictiva real ni cierre científico.

**3. Demo de defensa (Pergamino, Melchor Romero y Laboratorio):** requiere artefactos preparados fuera de `data/`. Melchor Romero es reproducible desde este repositorio; los artefactos de Pergamino no se distribuyen en un clon limpio. El paquete externo (parcial) y su restauración se describen en [`docs/delivery/RESTORE.md`](docs/delivery/RESTORE.md). Pasos y alcance de cada modo en [`docs/design/defense-demo-startup-guide.md`](docs/design/defense-demo-startup-guide.md); arranque con `scripts/start_defense_demo.ps1`.

**4. Controlador de la demo acelerada (opcional):** `docker compose --profile demo up -d` habilita `demo-control` en `127.0.0.1:8010`. No forma parte del arranque normal (ADR-0012).

Para correr el frontend fuera de Docker: `cd frontend && npm ci && npm run dev`. Si el backend está en otro host o puerto, configurar `VITE_API_BASE_URL` (ver `frontend/.env.example`; por defecto `http://localhost:8000`).

## Datos y memoria técnica

- `data/`: conjuntos procesados de la memoria (NASA POWER La Plata 2024-2025 y Melchor Romero 2024, ESA CCI Soil Moisture y consolidado de Melchor Romero), cada uno con su archivo `_coverage.csv`, y `data/dictionaries/` con los diccionarios de datos.
- `data/external/raw/`: respaldo de los CSV crudos de Pergamino y Balcarce (ERA5-Land horario y NASA POWER diario, 2015-2025), con tamaños y hashes SHA-256 en su `README.md`. El protocolo `controlled_daily_v4` los referencia fuera del repositorio; esta carpeta es una copia byte a byte.
- `replay_packages/`: paquetes científicos autorizados de la reproducción histórica.
- Memoria técnica: [`docs/memoria/TI_Rivas_Gustavo_V6.pdf`](docs/memoria/TI_Rivas_Gustavo_V6.pdf), versión final entregada, pendiente de aprobación de la cátedra. Índice de respaldo de sus cifras: [`docs/memoria/trazabilidad-cifras-memoria-v6.md`](docs/memoria/trazabilidad-cifras-memoria-v6.md).

## Estado del proyecto

Ver [`docs/seguimiento-tareas.md`](docs/seguimiento-tareas.md) para la auditoría detallada, tarea por tarea, con evidencia verificable. Resumen por historia de usuario:

| HU | Capacidad | Estado |
|----|-----------|--------|
| HU1 | Estado del arte y comprensión del dominio | ✅ Cerrada (estado del arte definitivo y auditoría de cierre completos) |
| HU2 | `data-ingestion` — preparación del conjunto experimental de datos | ✅ Cerrada (conjunto experimental reproducible a partir de NASA POWER (reanálisis) y ESA CCI Soil Moisture (satelital), Melchor Romero 2024) |
| HU3 | `data-quality` — calidad, anomalías y datos sintéticos | ✅ Cerrada (revalidada sobre el pipeline causal vigente) |
| HU4 | `predictive-modeling` — modelado predictivo y alertas tempranas | ✅ Cerrada (revalidada sobre el esquema temporal y de selección vigente) |
| HU5 | `human-feedback` — retroalimentación humana y recalibración | ✅ Cerrada (revalidada con recalibración temporalmente controlada) |
| HU6 | `architecture-integration` — integración de la arquitectura | ✅ Cerrada (revalidada sobre la integración end-to-end vigente) |
| HU7 | `experiment-runner` — diseño y ejecución del plan experimental | ✅ Implementación y ejecución experimental completadas. La evidencia de `controlled_daily_v3` se preserva y la campaña externa `controlled_daily_v4_external_pergamino` ejecutó A, B, C y H. El cierre científico confirmatorio no se alcanzó: RB-05, `sc-06-scientific-synthesis`, `SC-GOV-025` y el gate `GF` permanecen en `FAIL` por una no conformidad de gobernanza documentada. |
| HU8 | Análisis de resultados y contrastación de la hipótesis | 🟡 Análisis y discusión completados con limitaciones explícitas. Los resultados de `controlled_daily_v3` se preservan; B y C de `controlled_daily_v4_external_pergamino` se interpretan como evidencia retrospectiva exploratoria. No se declara validación agronómica ni cierre científico confirmatorio. La memoria técnica está en su versión final (V6) y espera la aprobación de la cátedra. |

Además de las HU del backlog de tesis, el repo incluye una interfaz de usuario (`backend/` + `frontend/`, ver sección siguiente) que expone HU5+HU6 y cierra el loop de recalibración manual disparada desde la UI (ver `docs/adr/0006-recalibracion-disparada-desde-la-ui.md`).

## Estructura del código

- `src/data_ingestion/`: esquema del contrato de datos, conectores (NASA POWER, ESA CCI Soil Moisture) y consolidación de fuentes.
- `src/data_quality/`: limpieza, detección de anomalías (Isolation Forest), generación de datos sintéticos y pipeline integrado.
- `src/predictive_modeling/`: etiquetado, ingeniería de variables, modelos (persistencia, regresión logística, Random Forest e Hist Gradient Boosting), ensamble por promedio, calibración, evaluación, contratos de inferencia operativa y alertas.
- `src/human_feedback/`: esquema y registro de retroalimentación humana sobre alertas, e integración con predicciones para recalibración supervisada.
- `src/architecture_integration/`: orquestador de punta a punta que encadena las capacidades anteriores.
- `src/historical_replay/`: reproducción histórica causal (emisiones preparadas, observaciones futuras ocultas hasta la fecha simulada).
- `src/experiment_runner/`: ejecución del plan experimental (`controlled_daily_v3` y `controlled_daily_v4`, escenarios de escasez/ruido, aumentación sintética, evaluación retrospectiva del ensamble, registro de corridas en MLflow).
- `scripts/`: puntos de entrada de línea de comandos para correr cada pipeline sobre un conjunto de datos de reanálisis o satelital (`run_data_quality_pipeline.py`, `run_end_to_end_pipeline.py`, conectores de ingesta).
- `backend/`: API FastAPI de la interfaz de usuario (alerting-ui) — fachada delgada que orquesta el pipeline y expone `POST /sensors/{sensor_id}/readings`, `POST /forecast/{sensor_id}/run`, `GET /feedback/{sensor_id}` + confirmar/rechazar por fecha, `POST /recalibrate/{sensor_id}`, y tres endpoints de observabilidad de solo lectura para la demo académica (`GET /quality/{sensor_id}`, `GET /models/{sensor_id}/active`, `GET /lineage/{sensor_id}`).
- `frontend/`: aplicación React + TypeScript (Vite) que consume la API del productor (`/api/v2`), el pipeline plano y `/replay`. Menú de presentación de tres entradas (**Arquitectura**, **Caso de demostración** y **Resultados**); bajo «Más» quedan **Mi cultivo** (pantalla pensada para un productor, prototipo local) y **Herramientas técnicas** (recorrido datos → calidad → predicción → feedback → recalibración → linaje). El Laboratorio (datos sintéticos, sin validez de campo) se elige dentro de «Caso de demostración».
- `openspec/specs/`: especificación viva de cada capacidad (requisitos, escenarios, verificación con datos externos de reanálisis y satelitales, limitaciones conocidas). `openspec/changes/`: historial de decisiones de diseño por *change*.
- `docs/adr/`: decisiones de arquitectura (ADR-0001 a ADR-0013): stack del PoC, stack web, MLflow/MinIO, dockerización, recalibración desde la UI, ingesta de sensores, contratos temporales, selección de modelos y protocolo `controlled_daily_v4`, controlador de la demo y backend del productor.
- `docs/memoria/`: memoria técnica (V6). `docs/research/`: protocolos y resultados experimentales. `docs/design/`: guías de la interfaz y de la demo.

## Interfaz de usuario (alerting-ui)

Backend y frontend dockerizados que exponen el pipeline completo (HU6) y la retroalimentación humana (HU5), incluyendo recalibración manual del modelo desde un botón en la UI (ver `docs/seguimiento-tareas.md`, sección "Interfaz de usuario").

La interfaz es apoyo a la decisión, no automatiza el riego. «Sin alerta prevista» no equivale a ausencia de estrés hídrico, y un pronóstico con datos viejos se señala como «Este pronóstico no es actual». Mi cultivo solo lee el último pronóstico guardado; nunca emite uno por su cuenta.

- Diseño y criterios: [`docs/design/ui-professional-redesign-plan.md`](docs/design/ui-professional-redesign-plan.md) y [`docs/design/alerting-ui-visual-design.md`](docs/design/alerting-ui-visual-design.md). El prototipo de la etapa de diseño se conserva en `design/prototypes/ui-professional/`.
- Prueba con un productor: [`docs/design/prueba-con-productor.md`](docs/design/prueba-con-productor.md).
- Demo de defensa (Pergamino, Melchor Romero, Laboratorio): [`docs/design/defense-demo-startup-guide.md`](docs/design/defense-demo-startup-guide.md). Para reiniciarla de cero con la línea base verificada: `./scripts/demo_reset.ps1 -Action Reset -StartFrontend`.
- Versiones congeladas: tag `memoria-base-2026-09-29` (backend y protocolo) y `memoria-ui-2026-10-03` (interfaz profesional, PR #231).

El arranque del stack y las URLs están en «Cómo levantar el proyecto».

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
npm ci
npm run test      # vitest
npm run lint      # oxlint
npm run build     # tsc -b && vite build
```

## Evidencia y protocolos experimentales

El repositorio conserva dos líneas de evidencia complementarias. `controlled_daily_v3` establece el esquema causal diario utilizado para la evaluación sobre Melchor Romero: objetivo observado separado de entradas imputadas o ruidosas, calendario diario obligatorio, contratos completos de modelos y evaluación temporal del ciclo de recalibración. Ver [protocolo experimental v3](docs/research/protocolo-experimental-v3.md).

La campaña externa `controlled_daily_v4_external_pergamino` ejecutó las etapas A, B y C, junto con el complemento H, sobre datos de reanálisis de Pergamino. Los resultados y sus limitaciones se preservan. Sin embargo, la auditoría final RB-05 concluyó en `FAIL` por una no conformidad de gobernanza. En consecuencia, `sc-06-scientific-synthesis`, `SC-GOV-025` y el gate `GF` permanecen en `FAIL`. Las etapas B y C se interpretan como evidencia retrospectiva exploratoria y no como cierre científico confirmatorio.

Las etapas A, B y C, junto con H, no deben repetirse dentro de la campaña cerrada. Una confirmación futura requeriría una campaña nueva, independiente y basada en datos no utilizados. Ver [estado canónico del cierre científico](openspec/scientific-closure/current-execution-checkpoint.md).

La interfaz de reproducción histórica conserva la causalidad temporal: presenta la fecha de origen, mantiene ocultas las observaciones futuras hasta la fecha simulada correspondiente y solo habilita la retroalimentación cuando existe una observación efectivamente medida (no imputada) en el producto de datos. Esta interfaz permite inspección y trazabilidad. No constituye validación agronómica, eficacia de campo ni operación automática del riego.
