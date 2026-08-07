# Tareas — add-data-ingestion

Subconjunto de las tareas técnicas de HU2 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9).

- [ ] Definir el esquema tabular del contrato de acceso a datos (columnas obligatorias/opcionales, tipos, unidades) a partir de `docs/research/hu1-variables-y-antecedentes.md`.
- [ ] Identificar y documentar las fuentes de datos seleccionadas (datasets públicos, SMN, NASA POWER, Copernicus).
- [ ] Evaluar metadatos, licencias, procedencia y restricciones de uso de cada fuente.
- [ ] Implementar `load_dataset()` / `save_dataset()` como interfaz estable sobre almacenamiento Parquet/CSV local (ADR-0002).
- [ ] Implementar el flag de procedencia (`origen: real | sintético`) en el esquema, con valor `real` para toda ingesta de esta capacidad.
- [ ] Homogeneizar formatos, unidades, frecuencias y zonas horarias entre fuentes.
- [ ] Implementar la agregación a granularidad diaria preservando la serie nativa.
- [ ] Implementar el reporte de cobertura por columna obligatoria (rango temporal, % de completitud).
- [ ] Documentar el diccionario de datos (procedencia, licencia, limitaciones) versionado junto al dataset.
- [ ] Verificar reproducibilidad: el procedimiento de ingesta puede re-ejecutarse a partir de la documentación generada (criterio de aceptación de HU2).
