# Change: Add architecture integration pipeline capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historia de usuario:** HU6 — Integración de la arquitectura experimental (primer de dos sub-proyectos: contratos entre componentes y orquestador de punta a punta).
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md), [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md), [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md).

## Why

HU2-HU5 dejaron cuatro capacidades completas (`data-ingestion`, `data-quality`, `predictive-modeling`, `human-feedback`), cada una probada y verificada por separado, pero conectadas manualmente cada vez (como en los scripts de verificación de cada *change* anterior). No existe todavía una única función que las encadene de punta a punta, ni un documento que fije el contrato (entradas/salidas) entre cada componente — el objetivo central de HU6 y de la capa de integración de la arquitectura (ADR-0001).

## What Changes

- **Contratos entre componentes**: se documenta en el spec, para cada frontera entre capacidades, qué entra y qué sale (ej. `data-quality` recibe el dataset crudo imputable y devuelve el dataset imputado + reporte de calidad; `predictive-modeling` recibe ese dataset imputado y devuelve el modelo entrenado + alertas; `human-feedback` recibe las alertas y devuelve el registro inicializado).
- **Orquestador de punta a punta**: una función (`run_end_to_end_pipeline`) que encadena, sobre un dataset ya consolidado: imputación y detección de anomalías opcional (`data-quality`), etiquetado y variables predictoras, partición temporal, entrenamiento de un modelo (`predictive-modeling`), generación de alertas y, por último, inicialización del registro de retroalimentación (`human-feedback`).
- **Orden de las etapas**: el etiquetado y la ingeniería de variables ocurren sobre la serie completa ya imputada, *antes* de partir en train/test (necesario para que las variables de retardo/ventana móvil de los primeros días del conjunto de test tengan historia disponible, sin fuga temporal — ya verificado por `tests/test_no_leakage.py` en HU4), y la detección de anomalías se aplica después de la partición, igual que en `data_quality.pipeline.run_quality_pipeline`.

## Impact

- **Specs afectadas:** nueva capacidad `architecture-integration`.
- **Specs futuras que dependen de esta:** el segundo *change* de HU6 (configuración de ejecución completa, pruebas funcionales y ajustes) se apoya en este orquestador; `experiment-runner` (HU7) lo reutilizará para correr las 4 configuraciones experimentales de la Épica 4.
- **Código afectado:** nuevo paquete `src/architecture_integration/` con `pipeline.py`.
- **Fuera de alcance de este change:** generación de datos sintéticos dentro del orquestador (no compone limpiamente con variables de retardo/ventana móvil, que requieren continuidad temporal real — ver "Limitaciones conocidas"); estandarización/escalado de las variables (los modelos candidatos de HU4 ya se entrenaron y verificaron sin escalar, y escalar rompería la interpretación física del umbral de estrés); recalibración automática con retroalimentación (HU5 ya implementa el mecanismo, pero dispararlo desde este orquestador es una decisión de ejecución, no de contrato entre componentes).

## Alternativas consideradas

- **Reutilizar `data_quality.pipeline.run_quality_pipeline` tal cual, sin modificar el orden de etapas**: se descarta porque esa función parte y estandariza el dataset *antes* de que exista la etiqueta/variables de HU4, lo que dejaría los primeros días de cada partición sin historia suficiente para las variables de retardo — se prefiere reordenar explícitamente las etapas en el orquestador, reutilizando las funciones individuales de `data_quality` en el orden correcto.
- **Incluir generación de datos sintéticos en este primer orquestador**: se descarta porque las filas sintéticas de HU3 no tienen continuidad temporal real, y no está definido cómo calcular variables de retardo/ventana móvil para ellas sin inventar una fecha ficticia — se documenta como límite conocido a resolver en `experiment-runner` (HU7) si la configuración experimental lo requiere.

## Estado: implementado

Ver [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) para los requisitos vigentes y la verificación con datos reales.
