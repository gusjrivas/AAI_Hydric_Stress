# Tareas — add-data-ingestion

Subconjunto de las tareas técnicas de HU2 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9).

- [x] Definir el esquema tabular del contrato de acceso a datos (columnas obligatorias/opcionales, tipos, unidades) a partir de `docs/research/hu1-variables-y-antecedentes.md`. — `src/data_ingestion/schema.py`.
- [x] Identificar y documentar las fuentes de datos seleccionadas (datasets públicos, SMN, NASA POWER, Copernicus). — `docs/research/hu2-fuentes-datos-acceso.md`. NASA POWER y ESA CCI Soil Moisture con conector implementado y datos reales descargados; SMN bloqueado por acceso técnico; Copernicus bloqueado por falta de registro (ver checklist para detalle y estado de cada una).
- [x] Evaluar metadatos, licencias, procedencia y restricciones de uso de cada fuente. — Diccionarios de datos reales generados para NASA POWER y ESA CCI (`data/dictionaries/`, licencia y limitaciones reales); SMN/Copernicus documentados a nivel de checklist mientras siguen bloqueados.
- [x] Implementar `load_dataset()` / `save_dataset()` como interfaz estable sobre almacenamiento Parquet/CSV local (ADR-0002). — `src/data_ingestion/storage.py`.
- [x] Implementar el flag de procedencia (`origen: real | sintético`) en el esquema, con valor `real` para toda ingesta de esta capacidad. — `src/data_ingestion/schema.py` (`normalize_to_schema`).
- [x] Homogeneizar formatos, unidades, frecuencias y zonas horarias entre fuentes. — `src/data_ingestion/schema.py` (`normalize_to_schema`) + `src/data_ingestion/consolidate.py` (`consolidate_sources`), validado con dos fuentes reales combinadas por timestamp (`data/melchor_romero_2024_consolidado.parquet`).
- [x] Implementar la agregación a granularidad diaria preservando la serie nativa. — `src/data_ingestion/aggregation.py` (`to_daily`).
- [x] Implementar el reporte de cobertura por columna obligatoria (rango temporal, % de completitud). — `src/data_ingestion/coverage.py` (`coverage_report`), corrido sobre el dataset consolidado real.
- [x] Documentar el diccionario de datos (procedencia, licencia, limitaciones) versionado junto al dataset. — `src/data_ingestion/dictionary.py` (`write_data_dictionary`).
- [x] Verificar reproducibilidad: el procedimiento de ingesta puede re-ejecutarse a partir de la documentación generada (criterio de aceptación de HU2). — `scripts/ingest_nasa_power.py`, `scripts/ingest_esa_cci_soil_moisture.py` y `scripts/consolidate_datasets.py` son CLIs reproducibles, re-ejecutados en la práctica para dos años distintos (2024 y 2025).

**Estado del change:** implementado y verificado con datos reales para dos fuentes (NASA POWER, ESA CCI Soil Moisture) en un punto y año (Melchor Romero, 2024). Limitaciones que quedan fuera de este change: SMN y Copernicus siguen bloqueados (ver `docs/research/hu2-fuentes-datos-acceso.md`); no se validó en más de un punto geográfico ni más de un año; no hay criterios explícitos de calidad/relevancia agronómica para seleccionar fuentes candidatas (tarea de HU2 aparte, todavía 🟡 en `docs/seguimiento-tareas.md`).
