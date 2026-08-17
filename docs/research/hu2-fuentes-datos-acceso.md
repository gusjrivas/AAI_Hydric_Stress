# HU2 — Checklist de acceso a fuentes de datos

Tarea de origen: "Relevar datos disponibles en SMN, NASA POWER y Copernicus" y "Evaluar metadatos, licencias, procedencia y restricciones de uso" (HU2, Épica 1).

Objetivo: dejar registrado qué gestión de acceso (registro, cuenta, licencia, API key) requiere cada fuente candidata, para poder ejecutar la ingesta (`data-ingestion`, ver `openspec/changes/add-data-ingestion/`) sin bloqueos. **Ninguna credencial se guarda en este repositorio** — este documento solo registra el estado de gestión.

Estado general: **pendiente de gestión por el responsable del proyecto**.

## Fuentes climáticas / meteorológicas

| Fuente | Qué provee | ¿Requiere registro? | Costo | Cómo gestionarlo | Estado |
|--------|------------|----------------------|-------|-------------------|--------|
| [NASA POWER](https://power.larc.nasa.gov/) | Radiación solar, temperatura, humedad, viento, precipitación (comunidad Agroclimatology), vía API REST | No — datos abiertos, sin cuenta ni API key | Gratuito | Consultar directamente el [API Overview](https://power.larc.nasa.gov/docs/services/api/) y el [tutorial de la API](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/) | Sin bloqueo — se puede empezar a usar de inmediato |
| [Copernicus Climate Data Store (CDS)](https://cds.climate.copernicus.eu/) | ERA5 y otros reanálisis climáticos (temperatura, precipitación, radiación, viento) | Sí — cuenta gratuita + token personal | Gratuito | 1) Registrarse en [cds.climate.copernicus.eu/user/register](https://cds.climate.copernicus.eu/user/register). 2) Seguir [CDSAPI setup](https://cds.climate.copernicus.eu/how-to-api) para obtener el token y guardarlo en `$HOME/.cdsapirc` (**fuera del repositorio**). 3) Aceptar la licencia de cada dataset específico en la web antes de la primera descarga | Pendiente — requiere que el responsable del proyecto se registre |
| [SMN Argentina — datos.gob.ar](https://datos.gob.ar/dataset?organization=smn) | Estaciones meteorológicas argentinas (temperatura, precipitación, humedad, viento) | No requiere registro, pero **bloqueado por acceso técnico** (ver nota) | Gratuito | Descargar directamente desde datos.gob.ar o [smn.gob.ar/descarga-de-datos](https://www.smn.gob.ar/descarga-de-datos) | **Bloqueado (2026-08-16):** el dataset `smn-listado-estaciones-meteorologicas-smn` de datos.gob.ar ya no existe (404); la API CKAN de datos.gob.ar (`/api/3/action/package_search`) no devuelve ningún dataset vigente del organismo SMN con series diarias por estación; `smn.gob.ar/descarga-de-datos` devuelve 403 tanto a `curl` como a un fetch automatizado (protección anti-bot), y no se pudo verificar con navegador real (extensión Claude in Chrome no disponible en el intento). Antes de reintentar, verificar manualmente en un navegador si la página ofrece una descarga real, o evaluar INTA RIAN (fila siguiente, ya priorizado por ser específico de Argentina) como segunda fuente real más accesible. |
| SMN — API no oficial (`ws.smn.gob.ar`) | Condiciones actuales y pronóstico a 1-3 días | No | Gratuito | **No usar como fuente principal**: no está documentada oficialmente ni garantiza estabilidad, y no provee series históricas (solo pronóstico/actual) | Descartado para el conjunto experimental — solo datos abiertos históricos vía datos.gob.ar |

## Fuentes de humedad de suelo

| Fuente | Qué provee | ¿Requiere registro? | Costo | Cómo gestionarlo | Estado |
|--------|------------|----------------------|-------|-------------------|--------|
| [ESA CCI Soil Moisture](https://climate.esa.int/en/projects/soil-moisture/) (vía [CEDA Archive](https://catalogue.ceda.ac.uk/)) | Humedad de suelo satelital global (activo/pasivo/combinado), serie larga hasta 2024 | No — descarga libre sin registro | Gratuito | Descargar directamente desde el CEDA Archive (`https://dap.ceda.ac.uk/neodc/esacci/soil_moisture/data/daily_files/COMBINED/v09.2/{año}/`, un NetCDF por día, sin login) | **Confirmado y con conector implementado** (`src/data_ingestion/sources/esa_cci_soil_moisture.py`); producto COMBINED v09.2 llega hasta 2024, no hay 2025 todavía por rezago de reprocesamiento. **Hallazgo de ubicación:** el punto original evaluado (centro de la ciudad de La Plata, -34.92/-57.95) cae sobre el estuario del Río de la Plata en la grilla de 0.25° del producto, que enmascara esa celda por completo (`sm` y `flag` NaN los 365 días del año, confirmado empíricamente). Se usa en su lugar Melchor Romero (-34.95/-58.05), localidad real dentro del mismo Cinturón Hortícola Platense, tierra adentro. |
| NASA SMAP (vía [Earthdata](https://www.earthdata.nasa.gov/topics/land-surface/soil-moisture-water-content/data-access-tools)) | Humedad de suelo satelital, revisita ~3 días | Sí — cuenta gratuita NASA Earthdata Login | Gratuito | Registrarse en [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/) | Pendiente — evaluar si aporta valor adicional sobre ESA CCI antes de gestionar el registro |
| [International Soil Moisture Network (ISMN)](https://ismn.earth/) | Humedad de suelo in situ de redes de estaciones globales | Sí — registro para descarga de datos | Gratuito | Registrarse en el portal ISMN | Pendiente — evaluar si hay estaciones relevantes para Argentina/hortícolas antes de gestionar el registro |
| [Dataset de riego en tomate (Mendeley Data)](https://data.mendeley.com/datasets/33cngpcrmx/2) | Serie de sensores en tiempo real para riego automatizado de tomate | No — descarga directa | Gratuito | Descargar directamente; citar el trabajo asociado si se usa | Sin bloqueo — evaluar relevancia y calidad antes de incorporar |

## Fuentes específicas de Argentina

Complementan a NASA POWER/Copernicus/ESA CCI con datos locales, relevantes para que el conjunto experimental represente condiciones agroclimáticas argentinas (no solo fuentes globales).

| Fuente | Qué provee | ¿Requiere registro? | Costo | Cómo gestionarlo | Estado |
|--------|------------|----------------------|-------|-------------------|--------|
| [INTA RIAN](http://rian.inta.gov.ar/sistemas/) | Red agrometeorológica nacional: datos de estaciones experimentales del INTA, antena satelital INTA Castelar, y SMN consolidados. Incluye SIGA (información climática), SEPA (seguimiento de cultivos) y estado hídrico | No — datos de libre descarga y consulta permanente | Gratuito | Consultar directamente [rian.inta.gov.ar/sistemas](http://rian.inta.gov.ar/sistemas/) y [SIGA](https://intainforma.inta.gob.ar/nuevo-siga-acceder-a-la-informacion-climatica-mas-rapido-y-seguro/) | Sin bloqueo — candidato prioritario por ser específico de Argentina y ya integrar SMN |
| [SMN — Monitoreo de estados](https://www.smn.gob.ar/monitoreo_estados) | Monitoreo de cobertura vegetal (periódico), balance hídrico de suelo (diario) y humedad de suelo (mensual) a nivel nacional | No | Gratuito | Consultar directamente el portal | Sin bloqueo — buena fuente complementaria de balance hídrico, aunque con menor frecuencia (mensual) que los sensores de campo |
| [Datos Agroindustriales — MAGyP](https://www.magyp.gob.ar/datosagroindustriales/) / [datos.magyp.gob.ar](https://datos.magyp.gob.ar/dataset) | Datos numéricos, estadísticos y georreferenciados del sector agropecuario (Ministerio de Agricultura, Ganadería y Pesca) | No | Gratuito | Buscar datasets hortícolas específicos en el portal | Pendiente — evaluar si hay series relevantes a estrés hídrico/riego hortícola más allá de datos de mercado |
| [datos.gob.ar — grupo "agri"](https://datos.gob.ar/dataset?groups=agri) | Catálogo agregado de datasets agropecuarios de organismos argentinos | No | Gratuito | Filtrar por relevancia a cultivos hortícolas y variables hídricas | Pendiente — relevamiento inicial de qué datasets del grupo aplican |

## Notas de seguridad

- Ninguna API key, token o archivo de credenciales (`.cdsapirc`, `.env`, etc.) debe commitearse a este repositorio. Ver `.gitignore` agregado en este mismo change.
- El token de Copernicus CDS y las credenciales de NASA Earthdata son personales — no deben compartirse en código ni en documentación versionada.

## Criterios de selección y descarte de fuentes de datos

Tarea de origen: "Definir criterios de selección y descarte de fuentes de datos" (HU2, Épica 1). El checklist de arriba usaba únicamente "¿requiere registro?" como criterio; esta sección lo reemplaza por criterios explícitos de calidad y relevancia agronómica, informados por los intentos reales de incorporación de fuentes documentados en este mismo archivo (NASA POWER, ESA CCI, SMN, INTA RIAN/SIGA).

### Criterios de inclusión (una fuente se adopta si cumple todos)

1. **Aporte de variable obligatoria.** La fuente debe proveer al menos una columna obligatoria del esquema (`src/data_ingestion/schema.py`: humedad de suelo, temperatura, humedad relativa, precipitación, radiación solar, viento). Una fuente que solo aporta variables opcionales no justifica el esfuerzo de incorporación por sí sola.
2. **Cobertura geográfica verificada en el punto de interés, no solo en general.** No alcanza con que la fuente cubra "Argentina" o "global": hay que verificar el punto/región específica antes de adoptarla. Hallazgo real que motiva este criterio: el punto original de La Plata (-34.92, -57.95) cae sobre el estuario del Río de la Plata en la grilla de ESA CCI Soil Moisture, enmascarado por completo — una fuente con cobertura "global" fallaba igual en el punto elegido.
3. **Accesibilidad técnica real por script, no solo ausencia de registro.** Una fuente "sin bloqueo de registro" puede seguir bloqueada por protección anti-bot, endpoints removidos, o requerir necesariamente un navegador interactivo. Hallazgos reales que motivan este criterio: SMN (`datos.gob.ar` con dataset removido, `smn.gob.ar` con protección anti-bot) y AGRIS (SPA que renderiza por JavaScript, 403 en fetch automatizado) — ambas "sin registro" según el criterio anterior, ambas bloqueadas en la práctica.
4. **Licencia compatible con uso académico.** Datos abiertos, dominio público, o licencia que permita uso en un trabajo de tesis con atribución (todas las fuentes ya incorporadas — NASA POWER, ESA CCI — cumplen esto explícitamente en su documentación).
5. **Completitud suficiente para ser útil, no necesariamente perfecta.** Un producto satelital con gaps reales (ej. ESA CCI Soil Moisture, 75.96% de completitud en el punto y año evaluados) se considera aceptable porque el hueco es cuantificable y documentado (`coverage_report`, `data_ingestion.coverage`), no oculto. Se descartaría una fuente con completitud tan baja que no permita ningún análisis (por debajo de, orientativamente, 50% en una variable obligatoria), salvo que sea la única fuente disponible para esa variable.

### Criterios de descarte (o de "pendiente", según el caso)

- **Bloqueo técnico persistente sin alternativa de acceso en un plazo razonable** → descarte temporal, documentado con fecha y motivo (ver filas de SMN y AGRIS en este documento y en `docs/research/hu1-protocolo-revision-bibliografica.md`), reevaluable si cambia el acceso (ej. si se prueba con navegador real más adelante).
- **Registro que depende de un tercero fuera del control del proyecto** (ej. acceso institucional a Scopus/Web of Science, o registro pendiente de Copernicus CDS) → estado "pendiente", no descarte definitivo; no bloquea el avance de otras fuentes.
- **Fuente que solo aporta pronóstico a corto plazo o datos no históricos** → descarte definitivo si el objetivo es series históricas para el conjunto experimental (ya aplicado explícitamente a la API no oficial de SMN, fila de "Fuentes climáticas / meteorológicas").
- **Fuente redundante sin aporte diferencial** → si dos fuentes cubren exactamente las mismas variables con la misma calidad para el mismo punto/período, se prioriza la de menor fricción de acceso; no se incorporan ambas solo por completitud del checklist.

## Próximos pasos

1. El responsable del proyecto gestiona el registro en Copernicus CDS (y, si corresponde, NASA Earthdata/ISMN) siguiendo los enlaces de la tabla.
2. Mientras tanto, la implementación de `data-ingestion` puede arrancar con las fuentes sin bloqueo de registro: NASA POWER, SMN/datos.gob.ar, INTA RIAN (prioritaria por ser específica de Argentina) y ESA CCI Soil Moisture.
3. Relevar en detalle datos.magyp.gob.ar y el grupo "agri" de datos.gob.ar para identificar datasets hortícolas específicos más allá de las fuentes agroclimáticas generales.
4. Una vez obtenidas las credenciales de Copernicus (y de NASA Earthdata/ISMN si corresponde), se actualiza el estado de este documento y se incorporan esas fuentes a la ingesta.
