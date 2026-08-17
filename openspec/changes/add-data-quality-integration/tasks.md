# Tareas — add-data-quality-integration

Tareas de cierre de HU3 (ver también el desglose completo en el plan de proyecto, sección 9).

- [x] Integrar las transformaciones en un flujo reproducible. — `src/data_quality/pipeline.py` (`run_quality_pipeline`) + `scripts/run_data_quality_pipeline.py`. Verificado sobre `data/melchor_romero_2024_consolidado.parquet` en las 4 configuraciones de la Épica 4 (base, +sintéticos, +anomalías, completa), sin fuga de información entre entrenamiento y evaluación.
- [x] Documentar decisiones, parámetros y limitaciones del componente. — `openspec/specs/data-quality/spec.md` consolida las decisiones y limitaciones de los 4 *changes* de HU3 (calidad básica, anomalías, sintéticos, integración) en un único documento vigente.
