# Change: Add mock live sensor ingestion

## Trazabilidad

- **Épica:** 1. Fundamentación científica (`data-ingestion`, generador de lecturas + dataset en vivo) + 3. Integración y mejora (`alerting-ui`, endpoint de ingesta).
- **Historia de usuario:** HU2 (`data-ingestion`) + HU5+HU6 (`alerting-ui`) — cierra la limitación conocida "No hay ingesta de datos de sensores en vivo; el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real" (`openspec/specs/alerting-ui/spec.md`, "Limitaciones conocidas"; también listada en `docs/seguimiento-tareas.md`, "Fuera de alcance, documentado para la próxima iteración").
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [ADR-0007](../../../docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md), `openspec/changes/add-selection-caching/` (prerequisito de performance), `src/data_quality/rules.py` (rangos físicos reutilizados por el generador).

## Why

El proyecto nunca conectó una fuente de datos en tiempo real — todo el pipeline opera sobre un dataset histórico estático consolidado una sola vez (HU2). Con el motor de selección automática ya cacheado (`add-selection-caching`), el backend puede sostener pronósticos frecuentes sin pagar el costo de reentrenar/re-seleccionar en cada corrida, lo que hace viable por primera vez conectar una fuente que actualice el dataset seguido. No hay ningún sensor real disponible todavía, así que se necesita un generador mock que produzca lecturas plausibles y una interfaz real de ingesta — construida de forma que un sensor real, el día que exista, la use sin cambios.

## What Changes

- **`src/data_ingestion/mock_sensor.py`** (nuevo): `generate_next_reading(previous: pd.Series | None, timestamp: pd.Timestamp, random_state: int) -> dict` — genera una lectura por random walk acotado a `data_quality.rules.AGRONOMIC_RANGES`, a partir de la lectura anterior (o un valor base si no hay ninguna); marca `procedencia="sintetico"`. `seed_mock_dataset(name: str, start_date: date, end_date: date, random_state: int = 42) -> pd.DataFrame` — genera y guarda un backfill de varios días encadenando `generate_next_reading`.
- **`backend/app/routers/sensors.py`** (nuevo): `POST /sensors/readings` — recibe una lectura (timestamp + valores, parcial permitido) y la agrega al dataset configurado (`DATASET_NAME`), agnóstico de si el llamador es un sensor real o un mock.
- **`scripts/seed_mock_sensor_dataset.py`** (nuevo): CLI de backfill inicial, uso único, fuera de la API HTTP.
- **`scripts/simulate_sensor_readings.py`** (nuevo): cliente HTTP standalone que genera una lectura y la postea a `/sensors/readings`, simulando tráfico de sensor.
- **`src/architecture_integration/pipeline.py`**: sin cambios.

## Impact

- **Specs afectadas:** `data-ingestion` (nuevo requirement: generación de lecturas mock y dataset en vivo con backfill), `alerting-ui` (nuevo requirement: endpoint de ingesta de sensores).
- **Código afectado:** `src/data_ingestion/mock_sensor.py` (nuevo), `backend/app/routers/sensors.py` (nuevo), `backend/app/main.py` (registra el router), `scripts/seed_mock_sensor_dataset.py` (nuevo), `scripts/simulate_sensor_readings.py` (nuevo), y sus tests.
- **Fuera de alcance de este change:** consolidar el dataset en vivo con el histórico `melchor_romero_2024_consolidado` (quedan separados, ver ADR-0007); derivar `et0` para lecturas mock (igual que las fuentes reales, se deja como limitación ya existente); autenticación del endpoint de ingesta; cualquier mecanismo de scheduler/cron real para correr `simulate_sensor_readings.py` automáticamente (se ejecuta manualmente en esta iteración).

## Alternativas consideradas

Ver [ADR-0007](../../../docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md) — las alternativas de arquitectura (push vs. pull, dataset separado vs. append al histórico, random walk vs. ruido independiente, backfill vía script vs. vía API) ya se documentaron ahí para no duplicar la discusión.
