# Spec delta: data-ingestion

## MODIFIED Requirements

### Requirement: Generación de lecturas sintéticas por random walk acotado

El sistema DEBE poder generar una lectura sintética plausible para las columnas obligatorias del esquema, a partir de la lectura anterior si existe, recortada a los rangos físicos/climáticos ya documentados (`data_quality.rules.AGRONOMIC_RANGES`), y marcada explícitamente con procedencia `sintetico`. `et0` es la excepción al random walk: se deriva del resto de la lectura generada por `data_quality.reference_et.estimate_et0` (FAO-56 Penman-Monteith con temperatura media), no por paso aleatorio propio.

#### Scenario: Generar la primera lectura sin historia previa

- **GIVEN** ninguna lectura anterior
- **WHEN** se genera una lectura sintética para una fecha dada
- **THEN** se obtiene un valor plausible (dentro del rango físico documentado) para cada columna obligatoria, incluyendo `et0`, marcado con procedencia `sintetico`

#### Scenario: Generar una lectura a partir de la anterior

- **GIVEN** una lectura anterior con valores conocidos
- **WHEN** se genera la siguiente lectura sintética
- **THEN** cada valor nuevo (excepto `et0`) está dentro de un paso acotado del valor anterior, y dentro del rango físico documentado para esa columna

#### Scenario: et0 se deriva del resto de la lectura, no por random walk

- **GIVEN** una lectura sintética ya generada para las columnas obligatorias excepto `et0`
- **WHEN** se completa esa lectura
- **THEN** `et0` es exactamente el resultado de `data_quality.reference_et.estimate_et0` aplicado a la temperatura, humedad relativa, radiación solar y velocidad de viento de esa misma lectura
