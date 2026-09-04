# Change: Add et0 derivation for mock sensor readings

## Trazabilidad

- **Épica:** 3. Integración y mejora (`alerting-ui`/`data-ingestion`, generador de sensores mock).
- **Historia de usuario:** HU2 (`data-ingestion`) — cierra parcialmente la limitación conocida "`et0` sigue sin generarse por el mock; su derivación queda pendiente para una iteración futura, igual que para las fuentes reales" (`docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md`, "Consecuencias"; también listada en `docs/seguimiento-tareas.md`, "Fuera de alcance, documentado para la próxima iteración").
- **Fase de CRISP-DM:** Preparación de datos.
- **Insumo de diseño:** [ADR-0007](../../../docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md), `src/data_quality/rules.py` (rango físico de `et0` ya documentado), `openspec/changes/add-mock-sensor-ingestion/`.

## Why

`et0` es una columna obligatoria del esquema (`data_ingestion.schema.REQUIRED_COLUMNS`) que hoy nunca se calcula — ni para las fuentes reales (NASA POWER queda con 0% de cobertura en `et0`, ver HU2 en `docs/seguimiento-tareas.md`) ni para el generador mock, que la excluye explícitamente. Esto deja una columna obligatoria del esquema permanentemente vacía en el dataset en vivo, aunque las demás variables necesarias para derivarla (temperatura, humedad relativa, radiación solar, viento) ya están disponibles en cada lectura generada.

## What Changes

- **`src/data_quality/reference_et.py`** (nuevo): `estimate_et0(temperature, relative_humidity, solar_radiation, wind_speed, timestamp, latitude=-34.95, elevation=15.0) -> float` — evapotranspiración de referencia diaria (mm/día) por FAO-56 Penman-Monteith, con la variante que sustituye Tmax/Tmin por temperatura media (el esquema del proyecto no registra extremos diarios). `latitude`/`elevation` toman por defecto el sitio de referencia del proyecto (Melchor Romero, Partido de La Plata, HU2).
- **`src/data_ingestion/mock_sensor.py`**: `generate_next_reading` ya no excluye `et0` — la deriva del resto de la lectura generada (`temperature`, `relative_humidity`, `solar_radiation`, `wind_speed`, `timestamp`) llamando a `estimate_et0`, en vez de dejarla ausente.

## Impact

- **Specs afectadas:** `data-ingestion` (MODIFIED: el requirement "Generación de lecturas sintéticas por random walk acotado" ya no excluye `et0`), `data-quality` (ADDED: nuevo requirement "Derivación de et0 con temperatura media").
- **Código afectado:** `src/data_quality/reference_et.py` (nuevo), `src/data_ingestion/mock_sensor.py`, y sus tests (`tests/test_reference_et.py` nuevo, `tests/test_mock_sensor.py` actualizado).
- **Fuera de alcance de este change:** derivar `et0` para las fuentes reales (NASA POWER/ESA CCI) — esas sí tienen Tmax/Tmin reales y merecerían la fórmula completa de FAO-56, no la variante simplificada de este change; queda como limitación explícita, igual que antes de este cambio.

## Alternativas consideradas

- **Fórmula completa de FAO-56 Penman-Monteith (con Tmax/Tmin)**: se descarta para el mock — el esquema del proyecto no registra temperaturas extremas diarias, solo una temperatura media por lectura; adoptar la fórmula completa exigiría rediseñar el esquema o inventar un rango diurno sintético, sin beneficio real para un generador mock.
- **Hargreaves-Samani (requiere igual Tmax/Tmin para el rango térmico diario)**: se descarta por la misma razón — necesita el mismo dato que no está disponible.
- **Valor constante o por random walk acotado, igual que el resto de las columnas**: se descarta — `et0` es una cantidad derivada físicamente de las demás variables meteorológicas, no una medición independiente; generarla por random walk propio rompería la coherencia física entre columnas de la misma lectura (ej. alta radiación solar con `et0` bajo por azar).
