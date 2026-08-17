# Tareas — add-data-quality-basics

Subconjunto de las tareas técnicas de HU3 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Primero de tres *changes* en que se dividió HU3.

- [x] Analizar distribuciones, rangos y tipos de las variables. — `src/data_quality/distributions.py` (`describe_variables`), verificado sobre `data/melchor_romero_2024_consolidado.parquet`.
- [x] Definir reglas de calidad y rangos agronómicos esperados. — `src/data_quality/rules.py` (`AGRONOMIC_RANGES`), rangos físicos/climáticos genéricos con justificación documentada por variable.
- [x] Implementar el reporte de valores faltantes, duplicados y atípicos. — `src/data_quality/quality_report.py` (`quality_report`); sobre el dataset real: 24.04% de faltantes en humedad de suelo, 0 duplicados, 0 valores fuera de rango.
- [x] Implementar el tratamiento de valores faltantes. — `src/data_quality/imputation.py` (`interpolate_missing`); sobre el dataset real, imputó 88 de 366 filas de humedad de suelo, dejando 0 faltantes y preservando la marca de qué filas fueron imputadas.
- [x] Implementar normalización, codificación y alineación temporal (interpretado como estandarización numérica para modelado; la alineación de formato/zona horaria entre fuentes ya la resuelve `data-ingestion`, HU2). — `src/data_quality/scaling.py` (`standardize`/`inverse_standardize`), verificado con roundtrip exacto sobre el dataset real.
- [x] Preparar particiones sin contaminación entre entrenamiento y evaluación. — `src/data_quality/splitting.py` (`temporal_train_test_split`), verificado sobre el dataset real (corte en 2024-10-01: 274 filas de entrenamiento, 92 de evaluación, sin fechas mezcladas).
