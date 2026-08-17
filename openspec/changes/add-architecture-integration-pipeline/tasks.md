# Tareas — add-architecture-integration-pipeline

Subconjunto de las tareas técnicas de HU6 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Primero de dos *changes* en que se dividió HU6.

- [x] Definir contratos, entradas y salidas entre componentes. Documentado en `openspec/specs/architecture-integration/spec.md` y en el orden de etapas de `run_end_to_end_pipeline` (docstring del módulo).
- [x] Integrar el componente de calidad con el componente predictivo. `src/architecture_integration/pipeline.py::run_end_to_end_pipeline` encadena imputación/detección de anomalías (`data-quality`) con etiquetado/variables predictoras/entrenamiento (`predictive-modeling`), en el orden que evita fuga temporal. Tests: `tests/test_architecture_integration_pipeline.py`.
- [x] Integrar las alertas con el mecanismo de retroalimentación. El orquestador genera alertas y las pasa a `human_feedback.schema.init_feedback_log`. Verificado sobre el dataset real (Melchor Romero 2024): 286 filas de entrenamiento, 71 de test, 0 NaN en variables predictoras del test, 22 alertas generadas, registro de retroalimentación inicializado con 71 filas `pendiente`.
