# Change: Add caching for the auto-selected model

## Trazabilidad

- **Épica:** 3. Integración y mejora (`alerting-ui`, backend) + 1. Fundamentación científica (`data-ingestion`, agrega una función chica de utilidad).
- **Historia de usuario:** HU5+HU6 (`alerting-ui`) — resuelve la limitación conocida "El backend entrena el modelo en cada corrida (sin cachear)... esa corrida por request es una búsqueda de hiperparámetros con validación cruzada sobre ambos candidatos... aceptada como tradeoff deliberado" (`openspec/specs/alerting-ui/spec.md`, "Limitaciones conocidas", agregada por `openspec/changes/add-model-selection-engine/`). También toca HU2 (`data-ingestion`, nueva función `get_dataset_fingerprint`).
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** `openspec/changes/add-model-selection-engine/` (introduce el costo que este *change* mitiga), `docs/adr/0006-recalibracion-disparada-desde-la-ui.md` (la recalibración debe seguir siendo manual — esta restricción acota el diseño).

## Why

Desde `add-model-selection-engine`, cada `POST /forecast/run` (y `POST /recalibrate`) sin modelo recalibrado registrado corre una búsqueda de hiperparámetros completa (`GridSearchCV` + `TimeSeriesSplit`) sobre los dos candidatos, en vez de un único `.fit()`. Eso se aceptó como tradeoff deliberado con el tamaño de dataset actual, pero es un prerequisito real antes de conectar una fuente de datos en vivo (sensores): pronósticos más frecuentes multiplicarían ese costo en cada corrida, sin ningún beneficio adicional si el dataset no cambió entre una corrida y la siguiente.

## What Changes

- **`src/data_ingestion/storage.py`**: agrega `get_dataset_fingerprint(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[float, int]`, que devuelve `(mtime, tamaño en bytes)` del archivo `.parquet` correspondiente, sin leer su contenido — mantiene el contrato de que ningún otro módulo accede a archivos directamente.
- **`backend/app/pipeline.py`**: `execute_configured_pipeline` cachea en memoria (variable a nivel de módulo, protegida por un `threading.Lock`) el último modelo auto-seleccionado junto con el `model_name` y el fingerprint del dataset con el que se seleccionó. En cada corrida sin modelo recalibrado: si el fingerprint actual coincide con el cacheado, reusa ese modelo (`skip_fit=True`, sin selección); si no coincide (o no hay caché todavía), corre la selección (`model=None`) y actualiza el caché con el resultado. La prioridad de un modelo recalibrado registrado en MLflow no cambia — sigue siendo la más alta, y ese camino ignora el caché por completo.
- **`src/architecture_integration/pipeline.py`**: sin cambios — el caché vive enteramente en la capa de orquestación del backend, no en el orquestador de HU6.

## Impact

- **Specs afectadas:** `data-ingestion` (nuevo requirement chico), `alerting-ui` (agrega un nuevo requirement — "Reutilización del modelo auto-seleccionado mientras el dataset no cambie" — y actualiza la nota de "Limitaciones conocidas" ya existente que citaba la falta de caché).
- **Código afectado:** `src/data_ingestion/storage.py`, `backend/app/pipeline.py`, y sus tests.
- **Fuera de alcance de este change:** el caché es en memoria del proceso backend — se pierde en cada reinicio/redeploy (aceptado: la próxima corrida paga el costo una vez y vuelve a poblarlo, igual que hoy). No se persiste a disco ni a MLflow. No cambia nada del mecanismo de recalibración manual (ADR-0006) ni de `experiment_runner.runner.run_configuration`.

## Alternativas consideradas

- **Registrar el modelo auto-seleccionado en MLflow bajo un nombre separado del de recalibración**: se descarta — agregaría una segunda noción de "modelo registrado" en MLflow, con una jerarquía de prioridad entre las dos que habría que documentar con cuidado para no confundir auditoría futura, a cambio de sobrevivir un reinicio del backend que hoy no es un caso frecuente ni costoso de recuperar (un solo request paga el costo).
- **Invalidar el caché con un TTL en vez de por fingerprint del dataset**: se descarta porque un TTL fijo no tiene relación real con "¿cambió el dataset?" — podría re-seleccionar innecesariamente con el dataset igual, o servir un modelo desactualizado si el TTL es más largo que la frecuencia real de nuevos datos (relevante justamente para el caso de sensores en vivo que motiva este *change*).
- **Cachear leyendo y hasheando el contenido completo del dataset**: se descarta por costo — leer el parquet completo en cada request para calcular un hash anularía buena parte del ahorro que el caché busca. `mtime` + tamaño del archivo es suficiente para detectar cambios en este contrato (el dataset se reescribe completo vía `save_dataset`, nunca se edita en el lugar).
