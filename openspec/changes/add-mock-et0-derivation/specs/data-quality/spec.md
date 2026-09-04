# Spec delta: data-quality

## ADDED Requirements

### Requirement: Derivación de et0 con temperatura media

El sistema DEBE poder estimar la evapotranspiración de referencia diaria (`et0`, mm/día) por FAO-56 Penman-Monteith a partir de temperatura media, humedad relativa, radiación solar entrante y velocidad de viento, sustituyendo Tmax/Tmin (no disponibles en el esquema del proyecto) por la temperatura media, con latitud y elevación configurables (por defecto, el sitio de referencia del proyecto: Melchor Romero, Partido de La Plata).

#### Scenario: et0 aumenta con mayor radiación solar entrante

- **GIVEN** dos lecturas idénticas salvo por la radiación solar
- **WHEN** se estima `et0` para ambas
- **THEN** la lectura con mayor radiación solar tiene un `et0` mayor

#### Scenario: et0 disminuye con mayor humedad relativa

- **GIVEN** dos lecturas idénticas salvo por la humedad relativa
- **WHEN** se estima `et0` para ambas
- **THEN** la lectura con mayor humedad relativa tiene un `et0` menor

#### Scenario: et0 respeta el rango físico documentado

- **GIVEN** una lectura con valores plausibles de temperatura, humedad relativa, radiación solar y viento
- **WHEN** se estima `et0`
- **THEN** el resultado está dentro del rango físico ya documentado en `data_quality.rules.AGRONOMIC_RANGES` para `et0`

#### Scenario: et0 varía estacionalmente por la latitud del sitio

- **GIVEN** las mismas variables meteorológicas para dos fechas del año, una de verano y otra de invierno en el hemisferio sur
- **WHEN** se estima `et0` para ambas fechas con la latitud por defecto
- **THEN** el `et0` de la fecha de verano es mayor que el de invierno
