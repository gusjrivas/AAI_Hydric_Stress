# Tareas — add-feature-engineering

Subconjunto de las tareas técnicas de HU4 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Primero de tres *changes* en que se dividió HU4.

- [x] Definir la variable objetivo y el horizonte de anticipación. — Clasificación binaria (estrés hídrico sí/no) con horizonte de 3 días, umbral relativo (percentil 20 de la distribución observada de humedad de suelo). Justificación en `proposal.md`.
- [x] Identificar variables predictoras, retardos y ventanas temporales. — Variables climáticas y humedad de suelo con retardos (1, 2, 3 días) y ventanas móviles (3, 7 días).
- [x] Implementar la ingeniería de variables temporales y agronómicas. — `src/predictive_modeling/labeling.py` (`add_stress_label`) y `src/predictive_modeling/feature_engineering.py` (`add_lag_features`, `add_rolling_features`).
- [x] Evaluar relevancia de variables y posibles fugas de información. — `src/predictive_modeling/relevance.py` (`feature_relevance`); test explícito de no-fuga (`tests/test_no_leakage.py`) que verifica que modificar un valor futuro no altera las variables de días anteriores. Verificado sobre `data/melchor_romero_2024_consolidado.parquet`: 363/366 filas etiquetadas (292 sin estrés, 71 con estrés, ~19.6%), variables más correlacionadas con el objetivo con sentido físico (radiación solar acumulada correlacionada positivamente, humedad relativa y humedad de suelo negativamente).
