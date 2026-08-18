# ADR-0004: Orquestación de experimentos con MLflow, backend Postgres y almacenamiento de artefactos MinIO (S3-compatible)

## Estado

Aceptado (2026-08-16). Reemplaza la sección "Registro y versionado de experimentos" de [ADR-0002](0002-stack-tecnico-poc.md).

## Contexto

ADR-0002 fijó MLflow ejecutado localmente (sin servidor remoto, backend de archivos en `mlruns/`) para el registro de experimentos, priorizando la simplicidad operativa del prototipo de tesis por sobre un patrón de despliegue de mayor escala.

El plan de tesis incluye explícitamente, dentro de su alcance, "recomendaciones para futuras implementaciones de mayor escala" (ver contexto de ADR-0002). Se decide adelantar esa recomendación al presente: en lugar de documentarla solo como sugerencia para el futuro, se adopta ahora un patrón de orquestación de experimentos equivalente al de un entorno colaborativo/productivo — un servidor de tracking de MLflow con backend de metadatos en Postgres y almacenamiento de artefactos en un bucket S3-compatible (MinIO, autoalojado) — como parte del propio prototipo, aunque HU3/HU4 (los componentes que efectivamente entrenarán modelos y generarán artefactos) todavía no tienen código implementado.

Esta decisión antepone la demostración del patrón de escalado a la simplicidad operativa que ADR-0002 había priorizado: a partir de ahora, registrar cualquier experimento requiere tener este stack corriendo (vía `docker compose up`), no solo importar MLflow en un script.

## Decisión

### Servicios

Un `docker-compose.yml` en la raíz del repositorio define tres servicios:

1. **`postgres`** — backend store de MLflow (parámetros, métricas, metadatos de cada *run*). Reemplaza el backend de archivos local de ADR-0002.
2. **`minio`** — almacenamiento de artefactos (modelos serializados, checkpoints, datos sintéticos generados por HU3) vía API S3-compatible. Expone también la consola web de administración.
3. **`mlflow`** — servidor de tracking (`mlflow server`), construido con una imagen propia (`docker/mlflow/Dockerfile`) que instala `mlflow`, `psycopg2-binary` (driver de Postgres) y `boto3` (cliente S3 para hablar con MinIO). Se conecta a `postgres` como backend store y a `minio` como destino de artefactos (`s3://mlflow/`), vía las variables `MLFLOW_S3_ENDPOINT_URL` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

Todo código de HU3/HU4 que registre experimentos debe apuntar `MLFLOW_TRACKING_URI` al servidor (`http://localhost:5000` por defecto), no al backend de archivos local.

### Por qué MinIO y no AWS S3 real

MinIO implementa la misma API S3 que usarían un despliegue productivo o una cuenta de AWS real, pero se autoaloja sin costo ni cuenta en la nube — apto para demostrar el patrón de artefactos tipo objeto en un prototipo de tesis local, sin las implicancias de gestionar credenciales de un proveedor cloud real ni incurrir en costos por un volumen de datos que, en este prototipo, es acotado.

### Credenciales

Las credenciales de MinIO (usuario/contraseña root) y las variables de conexión de MLflow se definen en un archivo `.env` local (no versionado, ver `.gitignore`), con `.env.example` versionado como plantilla de referencia. Ninguna credencial real se commitea a este repositorio, siguiendo el mismo criterio ya aplicado a Copernicus/NASA Earthdata en `docs/research/hu2-fuentes-datos-acceso.md`.

## Alternativas consideradas

- **Mantener MLflow local sin servidor (decisión original de ADR-0002)**: se descarta por decisión explícita de adelantar el patrón de escalado futuro al prototipo actual, en lugar de dejarlo solo como recomendación documentada para más adelante.
- **AWS S3 real en vez de MinIO**: se descarta porque exigiría una cuenta de AWS y credenciales de un proveedor cloud real para un prototipo de tesis local, sin aportar nada que MinIO no ofrezca ya a través de la misma API S3, de forma autoalojada y sin costo.
- **SQLite como backend store de MLflow (en vez de Postgres)**: se descarta porque el objetivo de este ADR es simular el patrón de un entorno colaborativo/productivo, y Postgres es el backend estándar de ese escenario; SQLite no sostiene bien el acceso concurrente de un servidor de tracking compartido.
- **Opt-in (docker-compose disponible pero no obligatorio para el desarrollo diario)**: se descarta por decisión explícita del autor de adoptar el patrón como default desde ahora, no como una opción que se activa recién cuando haga falta.

## Consecuencias

- **Docker Desktop (o un daemon Docker equivalente) pasa a ser un prerequisito de desarrollo** para cualquier tarea que registre experimentos con MLflow, incluso durante el desarrollo local de HU3/HU4 en la tesis. Esto es más carga operativa que la decisión original de ADR-0002, asumida deliberadamente para demostrar el patrón de escalado.
- ~~Ningún código de modelado existe todavía en este repositorio (HU3/HU4 no iniciadas), por lo que esta decisión no requiere migrar corridas ya registradas: se adopta el patrón antes de que exista el primer experimento.~~ **Actualización (2026-08-18):** HU7 (`experiment-runner`) ya ejecuta y registra experimentos reales contra este servidor — las 4 configuraciones de la Épica 4, 5 semillas cada una, con `mlflow>=2.14,<3` como dependencia del proyecto. El patrón demostrado con el experimento de humo (ADR-0004 original) ya tiene uso real.
- El CI (`.github/workflows/ci.yml`) sigue sin necesitar cambios: los tests de `experiment_runner` (HU7) usan un tracking store de archivo local (`file://`) para las pruebas automatizadas, no el servidor Docker real — evita que CI dependa de Docker Compose levantado. La ejecución contra el servidor real es manual/documentada, no parte del pipeline de CI.
- El contrato de acceso a datos de ADR-0002 (`load_dataset`/`save_dataset`) no cambia: este ADR solo reemplaza el mecanismo de *tracking* de experimentos, no la persistencia de los datasets de ingesta.

## Referencias

- [ADR-0001: Arquitectura modular para la detección temprana de estrés hídrico](0001-arquitectura-modular-deteccion-estres-hidrico.md)
- [ADR-0002: Stack técnico del prototipo experimental](0002-stack-tecnico-poc.md) — sección "Registro y versionado de experimentos", reemplazada por este ADR.
- [MLflow Tracking Server documentation](https://mlflow.org/docs/latest/tracking.html#tracking-server)
- [MinIO — S3 API compatibility](https://min.io/docs/minio/linux/developers/minio-drivers.html)
