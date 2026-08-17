# Tareas — add-anomaly-detection

Subconjunto de las tareas técnicas de HU3 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Segundo de tres *changes* en que se dividió HU3.

- [x] Seleccionar métodos candidatos para detección de anomalías. — Isolation Forest (scikit-learn) seleccionado como método base no supervisado; justificación y alternativas descartadas (no definitivamente) en `proposal.md`.
- [x] Implementar el método base de detección de anomalías. — `src/data_quality/anomaly_detection.py` (`detect_anomalies`).
- [x] Evaluar el comportamiento del detector de anomalías. — `evaluate_with_injected_anomalias`, verificado sobre `data/melchor_romero_2024_consolidado.parquet`: 100% de detección de 10 anomalías sintéticas inyectadas; sobre los datos reales sin modificar, el detector marcó 19 de 366 filas (~5.2%, consistente con `contamination=0.05`), correspondientes a una ola de calor (fines de enero/inicio de febrero) y eventos de lluvia intensa (febrero-marzo) — ninguna violaba el rango físico de `data_quality.rules`, pero sí son estadísticamente atípicas respecto de la serie.
