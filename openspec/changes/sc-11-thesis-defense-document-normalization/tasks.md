# Tareas de sc-11-thesis-defense-document-normalization

- [x] T01 Registrar alcance, autoridad, trazabilidad y exclusiones del cambio.
- [x] T02 Normalizar README, checkpoint, prompt siguiente, matriz y claims con
  una cabecera vigente que preserve la historia.
- [x] T03 Corregir la lectura confirmatoria residual de la síntesis científica.
- [x] T04 Registrar en `sc-06/tasks.md` que T08 permanece incumplida, REVIEW-3
  no fue ejecutada y está documentada por OBS-03 —sin atribuir esa ausencia a
  una aceptación de GD-40— y T25 ya se ejecutó con veredicto `FAIL`.
- [x] T05 Crear la posición breve para tesis y defensa.
- [x] T06 Corregir `CRIT-SC11-01`: separar en una tabla autocontenida la
  evidencia formal v3, la campaña v4 A/B/C/H y el ensamble demostrativo.
- [x] T07 Corregir `CRIT-SC11-02`: documentar desde fuentes primarias que la
  alerta del ensamble usa promedio y umbral 0,5; votos/categoría son metadata,
  mayoría no está implementada y `display_probability` no está calificada.
- [x] T08 Corregir `CRIT-SC11-03`: separar review v2/histórico, recalibración
  legacy/HU5 de un solo modelo y las pistas simulada y humana controlada de H.
- [x] T09 Ejecutar `git diff --check`, búsquedas dirigidas y validación OpenSpec
  estricta tras la corrección.
- [x] T10 Corregir `CRIT-SC11-04`: declarar que cada carril/evaluación es de un
  solo sitio —v3 Melchor Romero; v4 y demostración Pergamino— y que el conjunto
  no constituye validación multisitio ni agronómica longitudinal.
- [x] T11 Precisar la carga transitoria y exclusión temprana de 2024–2025 en el
  runner demostrativo, separada de la custodia del holdout ya evaluado.
- [x] T12 Precisar los estados de `training_eligibility`: madurez/revisión,
  `confirmation_only` e `incompatible_source_model` para `reject` maduro.
- [ ] REVIEW-1 Evidence checker: verificar mecánicamente rutas, formato y
  ausencia de contradicciones en el snapshot congelado.
- [ ] REVIEW-2 Scientific critic: intentar refutar la coherencia metodológica y
  la separación entre resultados exploratorios y confirmación.
- [ ] REVIEW-3 Scientific auditor: emitir veredicto independiente sobre el
  snapshot revisado.
- [ ] CLOSE Registrar snapshot y veredicto. El implementador no cierra ni
  aprueba este change.

La corrección de `CRIT-SC11-01..03` completa tareas de implementación, pero no
constituye `PASS`: REVIEW-1/2/3 y CLOSE siguen reservadas a revisores
independientes sobre el snapshot corregido.
