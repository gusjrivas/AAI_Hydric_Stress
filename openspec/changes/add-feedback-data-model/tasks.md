# Tareas — add-feedback-data-model

Subconjunto de las tareas técnicas de HU5 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Primero de tres *changes* en que se dividió HU5.

- [x] Definir casos de uso y estados de validación de las alertas. Estados `pendiente`/`confirmada`/`rechazada` (`src/human_feedback/schema.py::VALIDATION_STATES`); justificación en `proposal.md`.
- [x] Diseñar el modelo de datos para registrar retroalimentación. `src/human_feedback/schema.py::FEEDBACK_COLUMNS`, `init_feedback_log`; `tests/test_feedback_schema.py`.
- [x] Diseñar el flujo de interacción entre alerta, usuario y modelo. `update_feedback` (confirmar/rechazar con corrección y observación opcionales); verificado sobre datos reales: registro inicializado con 72 alertas `pendiente`, una confirmada y una rechazada con corrección y observación.
