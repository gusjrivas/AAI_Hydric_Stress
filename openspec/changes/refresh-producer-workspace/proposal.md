# Change: Espacio del productor más claro y consistente

## Why
El usuario necesita una UI comprensible sin conocimientos de IA y solicitó
integrar las correcciones backend antes de aprobar cualquier merge a main.

## What Changes
- Jerarquía visual, tarjetas por fecha, paleta verde/lima/ámbar y diseño responsive.
- Opiniones compartidas por forecast_id; historial y fechas futuras plegables.
- Recuperación explícita de invalid_cursor y errores de paginación.
- Navegación legacy conservada en un desplegable en Mi cultivo.
- Demo independiente en puertos 5182/8182 y proyecto Compose propio.

## Impact
HU5/HU6/UI; alerting-ui; CRISP-DM integración/despliegue; memoria capítulo 3.
Depende de fix/hu6-backend-paginacion-robusta (PR #209). Rama separada, sin merge.
Sin cambios a configuración experimental base/+sintéticos/+anomalías/completa,
hipótesis, arquitectura, manifiestos, modelos ni resultados HU7/HU8.
No habilita porcentajes, ajuste de modelos ni automatización de riego.