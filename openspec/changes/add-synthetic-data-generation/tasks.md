# Tareas — add-synthetic-data-generation

Subconjunto de las tareas técnicas de HU3 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Tercero de tres *changes* en que se dividió HU3.

- [x] Seleccionar técnicas candidatas para generación de datos sintéticos. — Muestreo de distribución normal multivariada seleccionado como técnica base; GAN/VAE descartado para este prototipo (no definitivamente) por el tamaño del dataset disponible. Justificación en `proposal.md`.
- [x] Implementar un prototipo de generación de datos sintéticos. — `src/data_quality/synthetic_data.py` (`generate_synthetic`).
- [x] Evaluar similitud estadística y utilidad predictiva de los datos sintéticos. — `statistical_similarity` y `evaluate_predictive_utility`, verificados sobre `data/melchor_romero_2024_consolidado.parquet`: diferencia de correlación promedio 0.023 entre real y sintético; utilidad predictiva casi idéntica (MAE real 0.02312 vs. MAE sintético 0.02323 al predecir humedad de suelo a partir de variables climáticas, evaluado sobre el mismo conjunto de test real).
