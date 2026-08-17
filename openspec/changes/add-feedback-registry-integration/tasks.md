# Tareas — add-feedback-registry-integration

Subconjunto de las tareas técnicas de HU5 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Segundo de tres *changes* en que se dividió HU5.

- [x] Implementar el registro de validaciones de alertas. `src/human_feedback/registry.py::save_feedback_log`/`load_feedback_log` (reutiliza `data_ingestion.storage`); `tests/test_feedback_registry.py`. Verificado sobre datos reales: guardado y recuperado sin pérdida de información.
- [x] Implementar el registro de correcciones y observaciones. `upsert_feedback_log` (agrega fechas nuevas en `pendiente`, preserva estado/corrección/observación de fechas existentes). Verificado sobre datos reales: tras simular una nueva corrida de alertas (73 filas vs. 72), la fecha ya confirmada conservó su estado.
- [x] Integrar la retroalimentación con los registros de predicción. `integrate_feedback_with_predictions` (join por fecha con probabilidad predicha y etiqueta real). Verificado sobre datos reales: 72 filas integradas con `y_proba` y `stress_label` reales.
