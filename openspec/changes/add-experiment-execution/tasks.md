# Tareas — add-experiment-execution

Subconjunto de las tareas técnicas de HU7 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Tercer y último *change* en que se dividió HU7.

- [x] Ejecutar una prueba piloto del protocolo experimental. Configuración base, 2 semillas, contra el servidor MLflow real (`http://localhost:5000`, docker-compose levantado). Run padre `piloto-base` con 2 runs hijos anidados, registrado sin errores.
- [x] Ejecutar experimentos con modelos de referencia. Configuraciones `base` y `+sintéticos`, 5 semillas cada una, registradas en MLflow. Resultado real: `base` F1=0.4585±0.0423, ROC-AUC=0.5551±0.0191; `+sintéticos` F1=0.3123±0.0862, ROC-AUC=0.5083±0.0439 (peor que base).
- [x] Ejecutar experimentos con mecanismos de robustez integrados. Configuraciones `+anomalías` y `completa`, 5 semillas cada una, registradas en MLflow. **Hallazgo real**: `+anomalías` produjo métricas *idénticas* a `base`, y `completa` idénticas a `+sintéticos` — la detección de anomalías no tiene ningún efecto medible porque `is_anomaly` no se incluye entre las variables predictoras del modelo (ver "Limitaciones conocidas" del spec).
- [x] Verificar integridad y reproducibilidad de los experimentos. Se re-ejecutó `base` con las mismas 5 semillas; `pd.testing.assert_frame_equal` confirmó que las métricas son idénticas bit a bit entre ambas corridas.
