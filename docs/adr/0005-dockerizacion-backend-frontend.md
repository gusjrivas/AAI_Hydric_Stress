# ADR-0005: Dockerización de backend y frontend (alerting-ui)

## Estado

Aceptado (2026-08-18)

## Contexto

ADR-0003 scaffoldeó `backend/` (FastAPI) y `frontend/` (React) para la capa 4, implementados en la práctica como la feature `alerting-ui` (PR #149). Hasta ese punto, ambos se ejecutaban localmente contra el intérprete de Python y el Node.js instalados en la máquina de desarrollo (`pip install -e ".[backend]"`, `npm install`), sin contenedor propio — a diferencia del stack de MLflow/Postgres/MinIO de ADR-0004, que sí corre en Docker desde su creación.

Esto dejaba una inconsistencia: el prototipo tenía dos formas distintas de levantarse (Docker para MLflow/Postgres/MinIO, entorno local desnudo para backend/frontend), y no había una forma de validar el comportamiento de `alerting-ui` de punta a punta sin depender del intérprete específico de la máquina de desarrollo. Verificar el flujo completo (correr pronóstico → ver alertas → confirmar/rechazar) requiere que backend y frontend puedan levantarse de manera reproducible, no solo en la máquina donde se implementó.

## Decisión

### Servicios nuevos en `docker-compose.yml`

Se agregan dos servicios al mismo `docker-compose.yml` de ADR-0004:

1. **`backend`** — construido desde `backend/Dockerfile` (imagen `python:3.11-slim`), con contexto de build en la raíz del repo (necesita copiar `src/`, `data/` y `pyproject.toml`, no solo `backend/`). Instala el paquete editable con el extra `backend` (`pip install -e ".[backend]"`), expone el puerto `8000` y monta `./data` como volumen para persistir el registro de retroalimentación (`feedback_ui.parquet`) fuera del contenedor.
2. **`frontend`** — construido desde `frontend/Dockerfile` (imagen `node:22-slim`, misma versión fijada en CI tras el fix post-merge de PR #149), expone el puerto `5173` y corre `npm run dev -- --host 0.0.0.0` (Vite necesita `--host` explícito para aceptar conexiones fuera de `localhost` dentro del contenedor).

Ambos servicios se agregan **sin relación `depends_on` con `postgres`/`minio`/`mlflow`**: `alerting-ui` no usa MLflow (ver `openspec/changes/add-alerting-ui/proposal.md`, alternativas consideradas), por lo que no tiene sentido acoplar su arranque al stack de tracking de experimentos. `frontend` sí depende de `backend` (`depends_on: backend`), porque no tiene utilidad mostrar la UI sin la API que consume.

Se renombra el `name:` del archivo de `aai-hydric-stress-mlflow` a `aai-hydric-stress`, ya que a partir de esta decisión el compose ya no describe solo el stack de MLflow sino todo el prototipo.

### Por qué build con contexto en la raíz para `backend`

El Dockerfile de `backend/` no puede limitarse a `COPY backend/` porque el backend importa paquetes de `src/` como fachada delgada (ADR-0003) y necesita el dataset consolidado bajo `data/` para poder ejecutar `POST /forecast/run`. El contexto de build se fija en la raíz del repo (`context: .` en el compose) y el Dockerfile referencia `backend/Dockerfile` explícitamente vía `dockerfile:`.

### Verificación realizada

Se validó el flujo completo dentro de los contenedores (no solo que las imágenes construyan): `docker compose up -d backend frontend`, confirmación de `/docs` (backend) y `/` (frontend) respondiendo 200, y una prueba manual desde el navegador contra `http://localhost:5173` que ejecutó el ciclo completo (correr pronóstico → tabla poblada con veredictos reales → confirmar alertas), replicando el mismo resultado ya validado en el entorno local sin Docker durante la implementación de `alerting-ui`. El único comportamiento distinto observado fue un arranque más lento del backend dentro del contenedor (el primer chequeo a los 5 segundos todavía no mostraba filas; una segunda revisión momentos después sí las mostró) — no es un defecto, es el costo esperado de instalar el paquete editable y entrenar el modelo dentro del contenedor en frío.

## Alternativas consideradas

- **Un único Dockerfile para backend+frontend en una imagen multi-stage**: se descarta porque backend y frontend tienen ciclos de vida y runtimes completamente distintos (Python vs. Node), y ADR-0003 ya estableció backend y frontend como responsabilidades separadas dentro del monorepo; una sola imagen mezclaría esa separación sin necesidad real.
- **Acoplar `backend`/`frontend` al arranque de `mlflow`/`postgres`/`minio` vía `depends_on`**: se descarta porque `alerting-ui` no usa MLflow (decisión ya tomada en su proposal.md); forzar esa dependencia solo alargaría el arranque sin aportar nada.
- **Imagen de producción con build estático de Vite en vez de `npm run dev`**: se descarta por ahora porque el objetivo de esta dockerización es reproducibilidad del entorno de desarrollo/prueba local, no un despliegue productivo; puede reevaluarse si el proyecto necesita un despliegue real más adelante.

## Consecuencias

- Levantar el prototipo completo pasa a ser `docker compose up -d` (los 5 servicios: `postgres`, `minio`, `minio-init`, `mlflow`, `backend`, `frontend`), sin depender del intérprete de Python ni la versión de Node instalados en la máquina de desarrollo.
- El flujo de desarrollo local sin Docker (descrito en `backend/README.md`/`frontend/README.md` si existieran, o en la sesión de implementación de `alerting-ui`) sigue siendo válido para iteración rápida (hot reload sin rebuild de imagen); Docker se usa para verificación de integración, no reemplaza el ciclo de desarrollo diario.
- Cambios en `pyproject.toml` o en las dependencias de `backend/`/`frontend/` requieren reconstruir la imagen correspondiente (`docker compose build backend` / `docker compose build frontend`) para que el contenedor los refleje; a diferencia del entorno local, no se actualizan solos.
- El volumen `./data:/workspace/data` implica que el contenedor de `backend` lee y escribe sobre el mismo dataset y registro de retroalimentación que el entorno local — no hay aislamiento de datos entre ambos modos de ejecución.

## Referencias

- [ADR-0003: Stack web (backend/frontend) y ciclo de vida de desarrollo automatizado con IA](0003-stack-web-y-ciclo-de-vida-automatizado.md)
- [ADR-0004: Orquestación de experimentos con MLflow, backend Postgres y almacenamiento de artefactos MinIO](0004-orquestacion-experimentos-mlflow-minio.md)
- `openspec/changes/add-alerting-ui/proposal.md` — alternativas consideradas que excluyen MLflow de esta UI.
- `.github/workflows/ci.yml` — fija Node 22 para `frontend-quality`, misma versión usada en `frontend/Dockerfile`.
