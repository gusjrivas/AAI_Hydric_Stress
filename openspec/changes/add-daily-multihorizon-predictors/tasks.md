# Tasks
- [x] 1.1 Implementar el contrato de manifiesto fail-closed, su inspección y el
      congelamiento con identidad SHA-256, sin ajustar modelos.
- [x] 1.2 Versionar un manifiesto `draft` con los campos ya determinados y las
      decisiones no aprobadas ausentes; comprobar que no habilita ajuste.
- [x] 1.3 Resolver y justificar las decisiones pendientes, completar el manifiesto
      `ready_for_fit` y congelarlo ANTES de cualquier ajuste: tolerancias, soporte,
      cobertura, bloques, ventanas, multiplicidad, semilla de despliegue e identidad
      efectiva de sensor/modelo.
- [x] 2.1 Implementar etiquetas y calendario exacto h=1,2,3, con purga por
      `target_date`, aislados de legacy.
- [x] 2.2 Implementar contratos por horizonte, identidades de artefacto y validación
      de compatibilidad de la familia h=1,2,3, sin entrenar ni cargar bundles.
- [x] 3. Entrenar bundles independientes por horizonte/semilla y congelar su
      estado efectivo (`predictive_modeling.operational_run.fit_seed` +
      `HorizonContract(artifact_state="trained_bundle")`). Cargar un bundle
      ya persistido para reusarlo sin reentrenar queda fuera de esta
      entrega (no pedido por el alcance acordado).
- [x] 4.1 Probar que modificar un valor futuro no altera entradas de inferencia
      anteriores y solo cambia el target que corresponde.
- [x] 4.2 Probar que modificar valores futuros no altera la inferencia previa de los
      bundles entrenados.
- [x] 5.1 Probar gaps, targets faltantes, unidades e incompatibilidades entre
      contratos por horizonte.
- [x] 5.2 Probar clases insuficientes y fallo parcial de ejecución por horizonte
      (`tests/test_operational_run.py::test_operational_run_isolates_a_single_horizon_training_failure`).
- [ ] 6. Ejecutar evaluación de desarrollo permitida y gate predeclarado de porcentajes.
- [ ] 7. Publicar métricas completas y limitaciones, aun si no se aprueba calibración.
- [x] 8.1 Verificar la regresión legacy directamente afectada por la preparación y
      que la entrega no modifica configuraciones, protocolos ni resultados v3/v4.
- [ ] 8.2 Repetir la regresión t+3 y la verificación v3/v4 al integrar entrenamiento,
      calibración y gate de porcentajes.
- [ ] 9. Registrar evidencia y actualizar canon solo al completar implementación.
- [x] 10. Implementar diagnósticos directos por intervalo e incertidumbre temporal con límites simultáneos; comprobarlos con fixtures de calibración conocida y mala calibración.
- [x] 11. Probar mejora de Brier sin aprobación directa, banda amplia, plan incompleto,
      soporte insuficiente, ventanas inestables y rango sin respaldo (banda amplia,
      rango sin respaldo y ventanas inestables agregados en
      `tests/test_calibration_assessment.py`; los demás ya estaban cubiertos por
      `test_final_decision_*` y por `tests/test_calibration_manifest.py`).
- [ ] 12. Publicar informe reproducible por horizonte con fechas, predicciones, conteos, intervalos, comparación de referencias y límites de generalización.

- [x] 3.1 Cargar bundles persistidos sin reajuste, verificando archivos, entorno, sensor, horizonte, unidades y features; probar corrupción, fechas y faltantes con modelos sintéticos ajustados.
