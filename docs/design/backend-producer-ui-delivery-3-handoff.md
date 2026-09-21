# Handoff — entrega 3 backend productor

Fecha: 2026-09-19. Rama: `feat/hu6-backend-soporte-ui`.

## Alcance completado

Se conciliaron las tareas OpenSpec con la evidencia ya documentada de las
entregas 1 y 2. Las tareas que mezclaban preparación ya verificada con
entrenamiento, calibración, inferencia o assessments todavía inexistentes se
desglosaron para no declarar completa una capacidad mayor que la implementada.
No se repitieron las regresiones registradas por esas entregas.

Se materializó
`config/producer-calibration-plan.draft.json` como borrador compatible con
`predictive_modeling.calibration_manifest`. Contiene únicamente decisiones
determinadas por los contratos y documentos aprobados. Continúan ausentes los
valores candidatos que requieren decisión; el estado es `draft` y
`require_ready_for_fit` lo rechaza.

La prueba agregada carga el artefacto real y comprueba simultáneamente que:

- no habilita ajuste;
- las decisiones no aprobadas no están materializadas;
- el inspector identifica los campos obligatorios pendientes.

## Validación ejecutada

- `tests/test_calibration_manifest.py`: **19 passed**.
- Black sobre el archivo de prueba afectado: sin cambios pendientes.
- Ruff `--no-cache` sobre el archivo de prueba afectado: sin hallazgos.
- `openspec validate add-daily-multihorizon-predictors --strict`: válido.
- `openspec validate add-producer-forecast-api --strict`: válido.
- `git diff --check`: sin errores.

El segundo validador conserva el aviso informativo preexistente: la spec
canónica `architecture-integration` tiene dos requirements fuera de su sección
principal. No se corrigió porque esta entrega no actualiza specs canónicas ni
archiva changes; el pendiente continúa explícito en la tarea 1.12.

## Decisiones que siguen pendientes

1. Ratificar o reemplazar los pisos de soporte por bin, clase y bloques.
2. Definir tolerancias de producto para ECE y error por bin.
3. Ratificar cobertura mínima y comportamiento de UI fuera del rango respaldado.
4. Ratificar método, longitud de bloques y tratamiento de huecos.
5. Ratificar ventanas de estabilidad.
6. Ratificar réplicas, semilla de remuestreo y control conjunto de multiplicidad.
7. Ratificar semilla de despliegue u otro procedimiento determinista.
8. Identificar sensor, variables/unidades, versiones e hiperparámetros efectivos.

Hasta resolverlas y congelar una nueva identidad, el estado operativo correcto
es `incomplete_assessment_plan`: no hay ajuste habilitado ni porcentaje
publicable.

## Trazabilidad e impacto

- HU4/HU6; capacidades `predictive-modeling` y
  `architecture-integration`.
- CRISP-DM: modelado, evaluación de desarrollo e integración.
- Configuración experimental: se versiona solo un borrador; no se ejecuta ni
  modifica `controlled_daily_v3`, HU7 o HU8.
- Hipótesis, alcance y arquitectura: sin cambios.
- Memoria técnica: aporta trazabilidad para los capítulos 2 y 3 sobre límites
  metodológicos y contrato operacional.

No se entrenaron ni calibraron modelos, no se abrieron holdouts, no se
modificaron datasets, protocolos, resultados históricos o specs canónicas, y no
se archivaron changes.
