# Prueba local de Mi cultivo con Docker

Entorno independiente para probar la UI y el backend del PR #207. Requiere
Docker Desktop con contenedores Linux. No requiere Python ni Node en Windows.

Desde PowerShell:

```powershell
cd C:\Repo\AAI_Hydric_Stress_integration
docker compose -f compose.producer-preview.yml up -d --build
```

Primera ejecución: descarga/construye imágenes y prepara datos/modelos sintéticos.
Cuando termine la preparación y los servicios estén saludables, abrir:

- UI: http://localhost:5180 (entra directamente a Mi cultivo).
- API directa / documentación: http://localhost:8180/docs.
- Documentación por el proxy de la UI: http://localhost:5180/docs.

## Qué probar

1. Elegir Huerta norte o Huerta sur. Ambos tienen mediciones simuladas.
2. Comparar históricos de 7/30 días; hay un faltante explícito de temperatura.
3. Pulsar «Consultar próximos tres días»: aparecen tres fechas posteriores a
   la última medición, con alerta o sin alerta según los modelos sintéticos.
4. En pendientes, confirmar/rechazar los resultados de fechas ya alcanzadas.
   Hay una tanda anterior con tres fechas revisables, incluida la fecha de hoy.
   Los resultados futuros se habilitan recién en su día objetivo UTC.
5. Recargar la página: las opiniones persisten. Una opinión puede corregirse.
6. En Huerta sur elegir «Punto todavía sin mediciones» para probar el estado vacío.

Los modelos se ajustan realmente a fixtures sintéticos, con parámetros de prueba
reducidos y declarados; no son modelos validados para un cultivo real. Los
porcentajes permanecen ocultos porque el gate de publicación sigue pendiente.
Las fechas se anclan al día UTC de la primera preparación. Al pasar los días la
UI muestra su antigüedad; no se simula una actualización que no ocurrió.

## Operación

```powershell
# Estado y preparación
docker compose -f compose.producer-preview.yml ps -a
docker compose -f compose.producer-preview.yml logs prepare

# Reiniciar sin perder datos ni opiniones
docker compose -f compose.producer-preview.yml restart backend frontend

# Detener/eliminar los contenedores, conservando el volumen
docker compose -f compose.producer-preview.yml down

# Volver a levantar
docker compose -f compose.producer-preview.yml up -d
```

El servicio prepare no vuelve a entrenar si encuentra su marcador de preparación.
Si detecta un volumen parcialmente preparado, se detiene sin sobreescribirlo.

**Para empezar una prueba nueva borrando solo los datos/opiniones de este entorno**:

```powershell
docker compose -f compose.producer-preview.yml down -v
docker compose -f compose.producer-preview.yml up -d --build
```

Esta acción elimina el volumen `aai-producer-preview_preview_data`; no ejecutarla
si se quieren conservar las observaciones registradas en la prueba. También sirve
para regenerar modelos si una reconstrucción actualiza sus dependencias: el loader
rechaza explícitamente un entorno distinto, en vez de cargar modelos incompatibles.

Puertos alternativos, si 5180/8180 están ocupados:

```powershell
$env:PRODUCER_PREVIEW_UI_PORT="5181"
$env:PRODUCER_PREVIEW_API_PORT="8181"
docker compose -f compose.producer-preview.yml up -d
```

## Aislamiento y alcance

Proyecto Compose `aai-producer-preview`, volumen propio, puertos en loopback,
sin mounts de `./data` ni conexiones a MLflow/Postgres/MinIO del usuario. Las
imágenes no copian datasets reales ni manifiestos científicos. Preparación y API
usan la misma imagen; el backend no entrena desde GET o desde el botón de emisión.
La UI usa un proxy del mismo origen, sin configurar CORS o URLs a mano.

HU2/HU4/HU5/HU6, capacidades data-ingestion/predictive-modeling/human-feedback/
architecture-integration/alerting-ui, CRISP-DM integración. No modifica hipótesis,
arquitectura o configuración experimental. Sin resultados científicos HU7/HU8 ni
cambios a controlled_daily_v3/v4. Aporta una prueba funcional para el capítulo 3,
no evidencia de calibración o validez agronómica. La reserva demo- legacy no se
modifica: este entorno nuevo usa IDs prueba-* y no migra datos de esa demo.
