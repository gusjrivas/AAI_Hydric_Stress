# Spec delta: data-ingestion

## ADDED Requirements

### Requirement: Generación de lecturas sintéticas por random walk acotado

El sistema DEBE poder generar una lectura sintética plausible para las columnas obligatorias del esquema (excepto `et0`, que se deriva en preprocesamiento), a partir de la lectura anterior si existe, recortada a los rangos físicos/climáticos ya documentados (`data_quality.rules.AGRONOMIC_RANGES`), y marcada explícitamente con procedencia `sintetico`.

#### Scenario: Generar la primera lectura sin historia previa

- **GIVEN** ninguna lectura anterior
- **WHEN** se genera una lectura sintética para una fecha dada
- **THEN** se obtiene un valor plausible (dentro del rango físico documentado) para cada columna obligatoria excepto `et0`, marcado con procedencia `sintetico`

#### Scenario: Generar una lectura a partir de la anterior

- **GIVEN** una lectura anterior con valores conocidos
- **WHEN** se genera la siguiente lectura sintética
- **THEN** cada valor nuevo está dentro de un paso acotado del valor anterior, y dentro del rango físico documentado para esa columna

### Requirement: Backfill inicial de un dataset en vivo

El sistema DEBE poder generar de una sola vez un dataset con varios días de historia sintética consecutiva, encadenando lecturas generadas una a partir de la anterior, y guardarlo bajo el contrato de acceso a datos existente.

#### Scenario: Backfill produce una fila por día en el rango pedido

- **GIVEN** una fecha de inicio y una fecha de fin
- **WHEN** se genera el backfill inicial para ese rango
- **THEN** el dataset resultante tiene exactamente una fila por día del rango, en orden cronológico, cada una encadenada a partir de la anterior
