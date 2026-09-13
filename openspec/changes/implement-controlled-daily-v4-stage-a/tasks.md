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

## Correcciones de la revisión técnica dirigida

- [x] Reemplazar `VotingClassifier` por un Soft Voting propio con balanceo independiente por base (`SelfWeightingClassifier` + `SoftVotingClassifier`), alineación explícita de clases y cloning compatible con scikit-learn; probar las 8 combinaciones de modos (P1-1).
- [x] Implementar el moving block bootstrap real: bloques solapados de largo exacto dentro de cada segmento, remuestreo independiente por segmento que preserva `n_s`, fallo explícito si un segmento es más corto que el bloque, largo no normativo solo en modo de test, y contabilidad de réplicas válidas/descartadas con su motivo (P1-2).
- [x] Recortar la serie a la ventana autorizada más la historia causal mínima antes de construir features y target, con instrumentación del constructor y comprobación por centinelas en 2023–2025 (P2-4).
- [x] Integrar `compute_metrics` y `compute_operational_metrics` en el runner y persistir `metrics.json` con métricas globales recalculadas desde el OOF concatenado, métricas por outer fold, calibración de 10 bins y motivos de indefinición (P2-2).
- [x] Poblar `per_fold_mcc` y reportar mediana, Q1, Q3, IQR y recuento de folds definidos/indefinidos con método de percentil declarado (P2-3).
- [x] Serializar con `allow_nan=False` y normalización recursiva, representando toda métrica indefinida como `{"value": null, "status": "undefined", "undefined_reason": ...}` (P2-1).
- [x] Capturar el entorno real de la corrida en `environment.json` en lugar de un placeholder (P2-5).
- [x] Resolver los P3: `.dockerignore` hermético y `pip check` como compuerta del build; transitivas fijadas; parámetros de grilla efectivamente conectados al estimador; regularización efectiva L2 verificada por API y registrada; equivalencia práctica que exige que el intervalo incluya el cero; marcado de corridas no normativas; barrido AST de MLflow ampliado; y aserciones tautológicas o casi vacuas reemplazadas.
- [ ] Última revisión técnica dirigida sobre el delta corregido, previa a la PR.

## Correcciones de la auditoría externa post-merge (H-01 a H-04)

Auditoría realizada sobre `b8575f3` (merge de este *change*). Corrige exclusivamente
los cuatro hallazgos adversariales siguientes, con fixtures sintéticas y sin
ejecutar la Etapa A real:

- [x] H-01 (identidad de las entradas): la ruta científica ahora valida hash y
  coordenadas por proveedor contra una referencia leída del manifiesto
  versionado (`manifest_reference.py`), nunca calculada de los archivos
  recibidos; se agrega el modo explícito `--input-mode {scientific,synthetic}`
  (por defecto `scientific`, nunca degrada automáticamente ante un fallo de
  validación) y metadatos de encabezado inválidos generan errores controlados
  en lugar de excepciones sin manejar.
- [x] H-02 (calendario y horizonte): `validate_continuous_daily_calendar`
  exige, sobre el propio rango recibido, continuidad/unicidad/orden del
  calendario diario, cobertura horaria completa (24 horas distintas, sin
  duplicados que oculten una hora ausente) y valores finitos en las columnas
  requeridas antes de que `build_feature_frame` calcule `shift`/lags/rolling;
  nunca se degrada ni imputa, se rechaza con diagnóstico preciso.
- [x] H-03 (aislamiento de A desde la ingesta): `provenance.py` deja de
  agregar humedad de suelo y de contar centinelas `-999` sobre el archivo
  completo -- la identidad/provenance queda exclusivamente estructural (hash,
  encabezados, columnas, cobertura de fechas); el análisis de valores
  permanece confinado a la ventana autorizada de cada etapa, ya recortada.
- [x] H-04 (validación previa del entorno): `validate_environment` contrasta
  Python y las dependencias exactas contra `docker/experiment-v4/constraints.txt`
  (vía `manifest_reference.py`) ANTES del primer ajuste; en modo científico
  aborta con código de salida dedicado ante incompatibilidad o dependencia
  ausente; la CI agrega un job dedicado que construye la imagen del entorno
  experimental fijado y ejecuta allí la suite sintética de la Etapa A.

### Correcciones detectadas por la revisión externa del paquete de la corrección

La entrada anterior declaró H-02 y H-03 corregidos de forma prematura. Una revisión
externa sobre `controlled-daily-v4-stage-a-fix-review_20260912_222919.zip` reprodujo,
con datos sintéticos, tres defectos adicionales -- corregidos a continuación:

- [x] H-03 (completado): `cli.py` todavía agregaba/procesaba el CSV completo
  (2015-2025) antes del recorte del runner. Se agrega
  `features.compute_stage_window_bounds` (única fuente de verdad de la ventana,
  reutilizada por `restrict_to_stage_window`) e
  `ingestion.restrict_era5_hourly_to_window`/`restrict_nasa_power_daily_to_window`,
  invocadas en la CLI antes de `aggregate_era5_daily`/`replace_missing_sentinel`.
- [x] H-02 (completado): `n_obs`/`n_unique_hours` no detectaban una lectura
  horaria ausente/no finita oculta por `mean(skipna=True)`. Se agrega
  `n_finite_<columna>` por columna de humedad en `aggregate_era5_daily` y su
  verificación en `validate_continuous_daily_calendar`, acotada a la
  profundidad efectivamente evaluada.
- [x] Columnas NASA ausentes: `load_nasa_power_daily_raw` ahora valida las
  columnas requeridas y levanta `ValueError` con diagnóstico explícito, en vez
  de dejar propagar un `KeyError` sin controlar.
- [x] Corrección documental: comentario de tolerancia de coordenadas (1e-4° ≈
  11 m en el ecuador, no ~1 cm) y actualización de la documentación de
  `ingestion.py`/seguimiento para no declarar cerrados H-02/H-03 antes de
  verificar sus regresiones.
