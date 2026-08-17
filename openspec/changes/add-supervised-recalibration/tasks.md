# Tareas — add-supervised-recalibration

Subconjunto de las tareas técnicas de HU5 del plan de tesis relevante para esta capacidad (ver también el desglose completo en el plan de proyecto, sección 9). Tercer y último *change* en que se dividió HU5.

- [x] Definir reglas para seleccionar observaciones de recalibración. `src/human_feedback/recalibration.py::select_recalibration_observations` (solo `rechazada` con `etiqueta_corregida` no nula). Tests: `tests/test_recalibration.py`.
- [x] Implementar una prueba de recalibración supervisada. `recalibrate_model` (reemplaza etiquetas por las corregidas y reentrena). Verificado sobre el dataset real con 3 correcciones sintéticas inyectadas (retroalimentación humana real todavía insuficiente en volumen): las 3 observaciones fueron seleccionadas correctamente, las etiquetas de entrenamiento quedaron reemplazadas, y el modelo recalibrado predice distinto exactamente en esas 3 fechas respecto del modelo original (1,1,0 → 0,0,1, coincidiendo con la corrección).
