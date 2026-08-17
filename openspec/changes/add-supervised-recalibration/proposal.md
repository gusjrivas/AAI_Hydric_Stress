# Change: Add supervised recalibration capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historia de usuario:** HU5 — Mecanismo de retroalimentación humana (tercer y último sub-proyecto: reglas de selección de observaciones y prueba de recalibración supervisada). Cierra HU5.
- **Fase de CRISP-DM:** Evaluación / Recalibración del modelo.
- **Insumo de diseño:** [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) (registro de retroalimentación integrado con predicciones), [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (modelos candidatos y su entrenamiento).

## Why

Los dos sub-proyectos anteriores de HU5 dejan la retroalimentación humana registrada e integrada con las predicciones del modelo, pero todavía no se usa para nada: el modelo no cambia ni aprende de las correcciones que un humano hizo. Esta es la pieza que cierra el ciclo de retroalimentación de la arquitectura (capa 5, ADR-0001).

## What Changes

- **Regla de selección**: solo las observaciones con `estado_validacion = "rechazada"` y `etiqueta_corregida` no nula califican para recalibración — una alerta `confirmada` no aporta ninguna corrección (el modelo ya acertó), y una `rechazada` sin corrección no tiene con qué reemplazar la etiqueta original.
- **Recalibración supervisada**: las fechas seleccionadas reemplazan su `stress_label` original por la `etiqueta_corregida` en el conjunto de entrenamiento, y el modelo candidato se reentrena sobre ese conjunto corregido.
- **Prueba de recalibración**: dado que la retroalimentación humana real acumulada todavía es mínima (1-2 casos, generados en el *change* anterior sobre datos reales), se inyectan correcciones sintéticas controladas sobre el dataset real (mismo criterio que la inyección de anomalías sintéticas en HU3) para verificar de punta a punta que: (a) la selección de observaciones identifica exactamente las fechas corregidas y (b) el modelo reentrenado con las etiquetas corregidas efectivamente predice distinto en esas fechas respecto del modelo original.

## Impact

- **Specs afectadas:** `human-feedback` (extiende el spec existente, cierra los 3 sub-proyectos de HU5).
- **Specs futuras que dependen de esta:** HU6 (integración de arquitectura) podría disparar este flujo de recalibración desde la interfaz de usuario; `experiment-runner` (HU7) podría incluir la recalibración como una configuración experimental adicional.
- **Código afectado:** `src/human_feedback/recalibration.py` (nuevo módulo).
- **Fuera de alcance de este change:** disparo automático/programado de la recalibración (requeriría una interfaz o un scheduler, HU6); persistencia del modelo recalibrado (no hay todavía un registro de modelos entrenados más allá de MLflow, que es infraestructura de tracking, no de despliegue).

## Alternativas consideradas

- **Usar confirmaciones y rechazos por igual**: se descarta porque una confirmación no corrige ningún error — incluirla no cambiaría el conjunto de entrenamiento (la etiqueta ya era correcta), y solo agregaría ruido a la regla de selección sin ningún beneficio.
- **Solo reportar el impacto sin reentrenar**: se descarta porque no cierra el ciclo de retroalimentación que es el objetivo explícito de HU5 — un reporte sin reentrenamiento no permite verificar si la corrección efectivamente cambia el comportamiento del modelo.
- **Probar solo con los 1-2 casos reales disponibles**: se descarta porque no alcanza para observar un cambio significativo o verificar la lógica de selección con múltiples casos (ej. varias fechas corregidas a la vez); se complementa con retroalimentación sintética inyectada, documentando explícitamente que es una prueba de mecanismo, no una validación con volumen real de retroalimentación.

## Estado: implementado

Ver [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) para los requisitos vigentes y la verificación con datos reales. Con esta *change* se completan los tres sub-proyectos de HU5.
