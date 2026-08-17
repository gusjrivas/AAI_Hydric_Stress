---
name: backend-python-fastapi-mlflow
description: Use when implementing or reviewing code in backend/ (FastAPI), or any code that registers experiments with MLflow in this repo — covers the thin-facade architecture constraint from ADR-0003 and the MLflow/MinIO connection conventions from ADR-0004.
---

# Backend Python: FastAPI + MLflow en este repo

## Restricción arquitectónica (ADR-0003)

El backend es la **capa 4** (salidas) de ADR-0001: una **fachada delgada** sobre `src/`, en el mismo proceso.

- Importa y llama directamente a las librerías de `src/data_ingestion`, `src/data_quality`, etc. Nunca las reimplementa.
- **No decide** cuándo correr ingesta, entrenamiento o generación de alertas — esa lógica vive en `src/`, el backend solo la invoca y expone por HTTP.
- Ningún endpoint debe leer archivos de `data/` directamente ni hablar con Postgres/MinIO por su cuenta más allá de lo que ya resuelven `data_ingestion.storage` (contrato de datos) y MLflow (experimentos).

Si una PR agrega lógica de negocio al backend (una regla de cuándo reentrenar, un cálculo que no está en `src/`), es una señal de que esa lógica pertenece a `src/`, no al backend — moverla ahí antes de mergear.

## Conexión a MLflow/MinIO (ADR-0004)

- El stack (`docker-compose.yml`) debe estar corriendo (`docker compose up -d`) antes de registrar cualquier experimento — no hay fallback local silencioso.
- Variables de entorno esperadas (ver `.env.example`): `MLFLOW_TRACKING_URI`, `MLFLOW_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. Nunca hardcodear estos valores en código ni commitear un `.env` real.
- Cada configuración experimental de la Épica 4 (base/+sintéticos/+anomalías/completa) se registra como un *run* independiente de MLflow, no como variantes de código.

## Convenciones FastAPI

- Un router por capacidad expuesta (ej. un router para alertas, otro para retroalimentación), no un único archivo con todos los endpoints.
- Los modelos Pydantic de request/response reflejan las columnas de `data_ingestion.schema` (mismos nombres), para no introducir un segundo vocabulario de variables.
- Tests con `pytest` + `httpx.AsyncClient` (o `TestClient` de FastAPI) contra la app real, no contra mocks del framework — la skill `tdd-project-conventions` de este repo aplica igual acá.

## Cuándo aplica esto

Todavía no existe `backend/` en el repo (se crea recién con HU5, ver ADR-0003 "Consecuencias"). Esta skill guía esa primera implementación cuando llegue el momento — no anticipes el scaffolding antes de que una HU lo pida.
