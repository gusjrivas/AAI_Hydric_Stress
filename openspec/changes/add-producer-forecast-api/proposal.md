# Change: API de soporte a la experiencia del productor

Estado: aceptado por el autor el 2026-09-19; implementación parcial mediante las
porciones de catálogo/histórico, emisión desde bundles y revisión humana. Resumen,
assessments, registro/activación MLflow y recalibración v2 siguen pendientes.

## Why
La pantalla necesita un contrato coherente para sectores, historial, tres días
pronosticados y opiniones persistentes. El backend actual no ofrece esa vista
y no corresponde reconstruir significado científico dentro del frontend.

## What Changes
- API v2 aditiva con catálogo, lecturas, resumen, emisiones y revisión.
- Contrato documentado con fechas, unidades, faltantes y procedencia explícitos.
- Integración de los changes HU2, HU4 y HU5 y regresión de API/demo legacy.
- La aceptación habilita implementación incremental; frontend permanece fuera de alcance.

## Impact
HU6; architecture-integration y alerting-ui. Dependencias:
add-producer-sensor-catalog, add-daily-multihorizon-predictors,
extend-dated-alert-feedback. CRISP-DM: despliegue e integración.
Sin cambio de configuraciones experimentales, hipótesis o alcance de tesis.
Conserva FastAPI como fachada, lógica en src y almacenamiento existente.
API aditiva versionada; capítulos 2 y 3. HU7/HU8 preservados.

Épica 3: Integración y mejora. Configuraciones base / +sintéticos / +anomalías /
completa: ninguna se modifica; nueva fachada operacional.

## Entrega incremental PR #207

El autor aprobó integrar la versión funcional probada y separar el despliegue
operacional real. Alcance, evidencia y pendientes trazados en
[el informe de cierre](../../../docs/design/producer-ui-main-integration.md).
El change sigue abierto: no se eliminan requisitos ni se habilitan porcentajes.
