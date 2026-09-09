# Tareas — implement-controlled-daily-v4-stage-a

- [x] Fijar y validar el entorno experimental reproducible (versiones exactas de Python, NumPy, pandas, SciPy, PyArrow, scikit-learn, joblib, threadpoolctl, resueltas en un contenedor limpio y validadas ejecutando allí la suite de tests con datos sintéticos).
- [x] Implementar la validación de provenance de los dos CSV de Pergamino (existencia, nombre, SHA-256, tamaño, encabezados, columnas, timezone, coordenadas devueltas, duplicados, alineación por fecha), sin modificarlos.
- [x] Implementar la ingesta y alineación causal ERA5-Land/NASA POWER (agregación horaria→diaria, inner join por fecha) sobre la serie diaria continua completa, sin filtrar por etapa.
- [x] Implementar el target (`stress(t)=1` si `soil_moisture(t+3) < P20_train`, operador estrictamente `<`), lags (1,2,3) y medias móviles causales (3,7 días), con filtro de elegibilidad por `target_timestamp` y protección temporal explícita de la Etapa A.
- [x] Implementar Logistic Regression, Random Forest, HistGradientBoostingClassifier y Soft Voting, balanceo exclusivo vía `sample_weight` fold-local, sin `class_weight`.
- [x] Implementar el nested temporal cross-validation de la Etapa A (`TimeSeriesSplit(n_splits=3, gap=3)` outer e inner), con verificación explícita del invariante `max(target_timestamp_train) < min(feature_timestamp_validation)`.
- [x] Implementar el cálculo de MCC global sobre OOF concatenado y las métricas secundarias/operativas, con convención explícita de `NaN` en casos degenerados (nunca reemplazado por 0).
- [x] Implementar el moving block bootstrap pareado y segment-aware (bloques de 30 días, semilla `20250109`, réplicas configurables para tests — 5000 como valor normativo del runner real).
- [x] Implementar la selección de familia (ganador estable / `SIN_GANADOR_ESTABLE` con desempate por simplicidad predeclarada / ausencia de selección válida ante OOF monoclase).
- [x] Implementar el congelamiento final de hiperparámetros (segunda pasada de `TimeSeriesSplit(3, gap=3)` sobre toda la Etapa A, independiente de la comparación de familias).
- [x] Implementar los esquemas de artefactos y su serialización atómica, con rechazo explícito de sobreescritura accidental, sin escribir en `docs/research/` ni en MLflow.
- [x] Implementar la CLI de la Etapa A (`--stage A` únicamente, `--validate-inputs-only`, sin rutas ocultas a datos formales ni a MLflow).
- [x] Agregar tests unitarios y de integración con fixtures sintéticas cubriendo causalidad, invariante temporal, grillas, selección, congelamiento, serialización, CLI y ausencia de MLflow — **67 tests, exclusivamente con datos sintéticos**.
- [ ] Ejecutar la Etapa A real sobre los CSV de Pergamino (`AAI_Hydric_Stress_external_data/raw/`) y congelar el candidato seleccionado. **No ejecutado en este *change*.**
- [ ] Ejecutar la Etapa B (2023). **No implementada. No ejecutada.**
- [ ] Abrir la Etapa C (2024–2025). **No implementada. Holdout permanece cerrado.**
- [ ] Persistir resultados reales (predicciones OOF, métricas, dataset diario derivado con su propio SHA-256) y actualizar `openspec/specs/experiment-runner/spec.md` (canónico) reflejando la capacidad implementada. **Pendiente de una corrida real y de una decisión explícita de cuándo el spec canónico debe actualizarse.**
