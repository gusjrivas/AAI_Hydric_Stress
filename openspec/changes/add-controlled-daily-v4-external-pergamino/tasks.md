# Tareas — add-controlled-daily-v4-external-pergamino

Ninguna tarea de este listado está completada. Este *change* es exclusivamente documental
(ADR-0011 + protocolo + manifiesto + spec delta); la implementación real queda para un
*change* de código posterior, todavía no propuesto. El holdout 2024–2025 permanece cerrado
hasta que la Etapa B produzca `CANDIDATE_VALIDATED` y exista autorización explícita de
apertura (ver protocolo, secciones 10–11, y manifiesto, `stage_c_holdout`). Balcarce
permanece fuera de esta ejecución, registrado únicamente como `FUTURE_GEOGRAPHIC_VALIDATION`.

- [ ] Fijar y validar el entorno experimental reproducible (versiones exactas de Python, NumPy, pandas, SciPy, PyArrow y scikit-learn en un manifiesto o lock), `PRECONDITION_FOR_EXECUTION` según protocolo sección 15.
- [ ] Completar el manifiesto definitivo de provenance de Pergamino (confirmar licencias y fecha de adquisición hoy `PENDING_CONFIRMATION`, resolver los campos `PENDING_BEFORE_EXECUTION` de `controlled-daily-v4-external-pergamino-manifest.yaml`).
- [ ] Implementar la ingesta y alineación causal ERA5-Land/NASA POWER (agregación horaria→diaria, inner join por fecha, ambas fuentes de Pergamino).
- [ ] Implementar el target, los lags (1, 2, 3) y las medias móviles causales (3, 7 días) con protección temporal explícita (`P20_train` exclusivo del train autorizado, operador estrictamente `<`).
- [ ] Implementar Logistic Regression, Random Forest, HistGradientBoostingClassifier y Soft Voting con balanceo exclusivo vía `sample_weight` fold-local (protocolo sección 7).
- [ ] Implementar el nested temporal cross-validation de la Etapa A (`TimeSeriesSplit(n_splits=3, gap=3)` outer e inner, protocolo sección 6).
- [ ] Implementar el cálculo de MCC global sobre OOF concatenado y las métricas secundarias/operativas (protocolo secciones 8 y 12).
- [ ] Implementar el moving block bootstrap pareado y segment-aware (bloques de 30 días, 5.000 réplicas, semilla `20250109`, sin cruzar discontinuidades de outer folds).
- [ ] Implementar el congelamiento final de hiperparámetros tras seleccionar familia en la Etapa A (protocolo sección 9).
- [ ] Agregar tests unitarios, de fronteras temporales/causalidad, de integración y de provenance para el runner de `controlled_daily_v4_external_pergamino`.
- [ ] Ejecutar la Etapa A (2015–2022) y congelar el candidato seleccionado. No ejecutado todavía.
- [ ] Ejecutar la Etapa B (2023) únicamente después de cerrar y congelar la Etapa A. No ejecutado todavía.
- [ ] Abrir la Etapa C (2024–2025) únicamente si la Etapa B produce `CANDIDATE_VALIDATED` y existe registro explícito de autorización (fecha y responsable) en el manifiesto de provenance. Holdout cerrado hasta entonces.
- [ ] Persistir resultados (predicciones OOF, métricas, dataset diario derivado con su propio SHA-256) y actualizar la documentación científica correspondiente, sin modificar ni reinterpretar retrospectivamente `controlled_daily_v3` ni `scientific-baseline-v3`.
