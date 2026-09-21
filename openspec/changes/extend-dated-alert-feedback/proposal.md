# Change: Revisión humana por pronóstico y fecha objetivo

Estado: aceptado por el autor el 2026-09-19; pendiente de implementación.

## Why
La revisión debe habilitarse el día anunciado y seguir disponible después.
La clave legacy por fecha de entrada no distingue tres horizontes y su regla
de madurez impide registrar una observación el mismo día.

## What Changes
- Registro v2 por forecast_id, revisión versionada y sin vencimiento.
- Separar captura de opinión, madurez temporal y elegibilidad para entrenamiento.
- Mantener intactos API legacy, registros anteriores y protocolos formales.
- Implementar incrementalmente tras validar las dependencias e invariantes del contrato.

## Impact
HU5; capacidad human-feedback; CRISP-DM: evaluación e integración.
Depende de la identidad emitida por HU4 y se expone por HU6.
Configuración experimental: ninguna modificación; no alterar controlled_daily_v3
ni v4 ni sus resultados. No cambia hipótesis ni alcance. Extiende persistencia
operativa dentro de la arquitectura existente. Capítulos 2 y 3.
Ver design.md, tasks.md y ../add-producer-forecast-api/api-contract.md.

Épica 3: Integración y mejora. Configuraciones base / +sintéticos / +anomalías /
completa: sin modificación; funcionalidad operacional separada.
