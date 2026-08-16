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
| [ESA CCI Soil Moisture](https://climate.esa.int/en/projects/soil-moisture/) (vía [CEDA Archive](https://catalogue.ceda.ac.uk/)) | Humedad de suelo satelital global (activo/pasivo/combinado), serie larga hasta 2024 | No — descarga libre sin registro | Gratuito | Descargar directamente desde el CEDA Archive | Sin bloqueo |
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

## Próximos pasos

1. El responsable del proyecto gestiona el registro en Copernicus CDS (y, si corresponde, NASA Earthdata/ISMN) siguiendo los enlaces de la tabla.
2. Mientras tanto, la implementación de `data-ingestion` puede arrancar con las fuentes sin bloqueo de registro: NASA POWER, SMN/datos.gob.ar, INTA RIAN (prioritaria por ser específica de Argentina) y ESA CCI Soil Moisture.
3. Relevar en detalle datos.magyp.gob.ar y el grupo "agri" de datos.gob.ar para identificar datasets hortícolas específicos más allá de las fuentes agroclimáticas generales.
4. Una vez obtenidas las credenciales de Copernicus (y de NASA Earthdata/ISMN si corresponde), se actualiza el estado de este documento y se incorporan esas fuentes a la ingesta.
