# Tareas — add-early-warning-alerts

Subconjunto de las tareas técnicas de HU4 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Tercer y último *change* en que se dividió HU4.

- [x] Definir e implementar la lógica de generación de alertas tempranas. `src/predictive_modeling/alerts.py::generate_alerts` (umbral 0.5 sobre `predict_proba` del modelo Random Forest ya entrenado/ajustado); `tests/test_alerts.py`. Verificado sobre datos reales: 21 alertas de 72 filas de test.
- [x] Analizar errores de predicción y alertas incorrectas. `src/predictive_modeling/alerts.py::analyze_prediction_errors`; `tests/test_alerts.py`. Verificado sobre datos reales: 7 falsos positivos (ej. 2024-11-15, 2024-12-10 a 2024-12-13) y 24 falsos negativos (ej. 2024-10-18 a 2024-10-20, 2024-11-17 a 2024-11-22).
- [x] Documentar configuración, métricas y limitaciones del modelo. `openspec/specs/predictive-modeling/spec.md` (requirements agregados + tabla de configuración final + "Limitaciones conocidas" actualizada).
