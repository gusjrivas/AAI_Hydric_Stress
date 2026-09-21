# Integración de Mi cultivo — alcance de cierre del PR #207

Fecha: 2026-09-21. Entrega funcional incremental aprobada por el autor.
El merge requiere los cuatro checks de CI aprobados sobre el HEAD publicado y
ausencia de conflictos con main. No cierra los cuatro changes completos ni HU7/HU8.

## Decisión de alcance

El autor probó el entorno Docker y aprobó continuar. Luego aceptó incorporar una
primera versión funcional a main y separar el despliegue operacional real.
Esta decisión sustituye la lista anterior que condicionaba este PR al desarrollo
completo de todas las capacidades v2. No elimina ni marca cumplidos sus requisitos.

## Entregado y verificable

| Capacidad | Alcance que se integra |
|---|---|
| Catálogo | GET/POST/PATCH de sectores y sensores; selección de primario, adopción legacy, revisiones optimistas. La UI selecciona; el alta/edición se hace por API. |
| Históricos | Gráfico/tabla de 7/30 días, snapshots, fechas UTC, unidades, procedencia, faltantes y antigüedad. |
| Modelos persistidos | Exportación y carga local por sensor/horizonte, verificación de identidad y compatibilidad; inferencia sin ajuste por HTTP. |
| Tres días | POST explícito con snapshot común, fechas +1/+2/+3 y disponibilidad individual. Falta de estimación nunca significa sin alerta. |
| Opiniones | Confirmación/rechazo desde el día objetivo UTC, sin vencimiento; correcciones, control de revisión, replay y pendientes duraderos. |
| Compatibilidad | Rutas v2 aditivas, feature flag desactivado por defecto y reserva demo-; legacy permanece disponible. |
| Prueba local | Compose independiente, fixtures/modelos sintéticos, volumen persistente y proxy UI/API. |

`display_probability` permanece null en la emisión integrada. El frontend no
convierte score en porcentaje. La disponibilidad de un calibrador no certifica
calibración ni validez agronómica. Sin bundles compatibles se informa ausencia;
ningún GET entrena ni inventa un pronóstico.

## Continuación trazada, fuera de este merge

| Pendiente | Fuente y condición para completarlo |
|---|---|
| Evaluación operacional real e informe reproducible | add-daily-multihorizon-predictors: 6, 7, 8.2, 9 y 12. Respetar manifiesto congelado y preservar resultados incluso si son insufficient_evidence. |
| Registro/activación MLflow y gate de porcentajes | add-producer-forecast-api: 1.3b-ii y 1.13b. Requiere assessment compatible por dominio/rango; el directorio local no sustituye ADR-0013. |
| Resumen/linaje y recalibración v2 | add-producer-forecast-api: 1.5, 1.6, 1.7b-ii; extend-dated-alert-feedback: 1.5. Registrar opiniones no implica aplicarlas a un modelo. |
| UI completa, incluida gestión de catálogo | No se entrega el mock completo. Alta/edición visual y consumidores de capacidades restantes quedan ligados a 1.9b y 1.11b. |
| QA visual específica | Móvil real, teclado y recorrido visual exhaustivo de conflictos siguen pendientes en 1.11b. La aceptación general no demuestra cada escenario. |
| Consolidación final | Mantener changes abiertos y tareas sin completar. Consolidar canónicas/archivar al completar cada capacidad, sin promover contratos futuros a implementados. |

Estos pendientes pueden separarse porque sus rutas/consumidores no se presentan
como disponibles, los porcentajes se bloquean y el backend v2 requiere opt-in.
Las specs completas siguen vigentes como objetivo de implementación incremental.

## Evidencia

- Backend en bdb6a50: 101 tests aprobados desde backend/ en contenedor temporal.
  Se corrigió pythonpath de pytest para encontrar fixtures compartidas desde ese
  directorio, que era la causa del fallo remoto de colección. No se excluyeron tests.
- Frontend: 136 tests, lint y build; datos/modelado afectados: 97 tests.
  Detalle en [emisión integrada](producer-ui-emission-integration.md).
- Docker: UI/API saludables, catálogo/históricos/emisión probados por HTTP real
  con fixtures sintéticos, persistencia comprobada tras reiniciar.
- El autor confirmó «lo probé estamos ok para seguir». Aceptación funcional general,
  sin inferir dispositivos o escenarios específicos que no declaró.
- Los checks remotos del HEAD son la autoridad para el estado de CI; no extrapolar
  el resultado de un commit anterior. El PR registra los enlaces de la ejecución.

## Activación y rollback

Ver [guía Docker](../../docker/producer-preview/README.md). Desde la raíz del
checkout: `docker compose -f compose.producer-preview.yml up -d --build`.
UI: http://localhost:5180; API: http://localhost:8180/docs.
No se requieren los otros servicios del usuario y no se montan sus datasets.
`docker compose -f compose.producer-preview.yml down` conserva el volumen.

En el stack habitual, PRODUCER_V2_ENABLED=false es el valor por defecto.
Activarlo explícitamente requiere catálogo, lecturas y bundles propios compatibles.
Desactivarlo y recrear backend revierte la exposición v2 sin borrar archivos.
La vista legacy sigue disponible. No migrar ni renombrar bundles para omitir controles.

## Base, preservación y trazabilidad

Rama feat/hu6-productor-integracion-final; base a657014 (PR #206), backend b573088,
UI a250a9e. Se preservaron los cambios ajenos de los worktrees originales.
Los manifiestos congelados v1/v2/v3 conservan sus hashes; .gitattributes evita
conversiones de finales de línea. No se ejecutó evaluación operacional real.

HU2/HU4/HU5/HU6 y UI; data-ingestion, predictive-modeling, human-feedback,
architecture-integration y alerting-ui. CRISP-DM integración/despliegue.
Sin cambios a hipótesis, capas de arquitectura o configuración experimental.
La prueba ajusta modelos sintéticos aislados; los datos/resultados históricos y
controlled_daily_v3/v4 no se modifican. Aporte a capítulo 3, sin nueva evidencia
científica para capítulo 2 ni declaración de cierre HU7/HU8.
