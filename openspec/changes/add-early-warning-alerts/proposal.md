# Change: Add early warning alerts capability

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU4 — Componente de modelado predictivo (subconjunto: alertas tempranas, tercer y último sub-proyecto en que se dividió HU4).
- **Fase de CRISP-DM:** Evaluación / Despliegue (parcial).
- **Configuración experimental afectada:** base (Épica 4), igual que el sub-proyecto anterior.
- **Insumo de diseño:** [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (modelos entrenados, comparación de desempeño).

## Why

Los modelos ya entrenados y comparados (`add-baseline-and-candidate-models`) producen predicciones, pero todavía no hay una capa que las convierta en una alerta binaria interpretable, ni un análisis de en qué casos concretos el modelo se equivoca — insumo necesario antes de pensar en HU5 (retroalimentación humana) sobre esas alertas.

## What Changes

- **Generación de alertas**: función que, dado un modelo entrenado y un conjunto de datos, convierte la probabilidad predicha de estrés en una alerta binaria usando un umbral de decisión (0.5 por defecto — no se ajusta contra el propio conjunto de validación para evitar sobreajustar un umbral con ~285 filas de entrenamiento; queda documentado como punto a recalibrar cuando haya más datos o retroalimentación humana real, HU5).
- **Modelo usado**: Random Forest (mejor precisión y ROC-AUC de los tres modelos comparados en el *change* anterior), aunque la función de generación de alertas acepta cualquier modelo con `predict_proba`, no queda atado a esa elección.
- **Análisis de errores**: función que identifica, sobre un conjunto de evaluación, las fechas concretas de falsos positivos (alerta emitida sin estrés real) y falsos negativos (estrés real sin alerta), para inspección manual posterior — no solo conteos agregados.
- **Documentación**: se documenta en el spec la configuración final (modelo, umbral), las métricas de la capa de alertas sobre el dataset real, y las limitaciones conocidas heredadas de los sub-proyectos anteriores más las propias de esta capa (umbral no calibrado, tamaño de muestra).

## Impact

- **Specs afectadas:** `predictive-modeling` (extiende el spec existente, cierra los 3 sub-proyectos de HU4).
- **Specs futuras que dependen de esta:** HU5 (retroalimentación humana) consumirá estas alertas para permitir corrección/recalibración; `experiment-runner` (HU7) ejecutará este mismo flujo sobre las 4 configuraciones experimentales.
- **Código afectado:** nuevo módulo `src/predictive_modeling/alerts.py`.
- **Fuera de alcance de este change:** recalibración del umbral con retroalimentación humana real (HU5); ejecución sistemática sobre las 4 configuraciones experimentales (HU7, no iniciada); interfaz de usuario para mostrar alertas (HU6/frontend).

## Alternativas consideradas

- **Umbral optimizado por F1 en validación cruzada**: se descarta para esta primera versión por riesgo de sobreajuste con un conjunto de entrenamiento pequeño (~285 filas) y por mantener el umbral simple y auditable como punto de partida; queda documentado como mejora futura.
- **Solo matriz de confusión agregada para el análisis de errores**: se descarta porque no permite inspeccionar manualmente qué condiciones climáticas concretas llevaron a un error, que es el insumo más útil para depurar el modelo antes de HU5.

## Estado: implementado

Ver [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) para los requisitos vigentes y la verificación con datos reales. Con esta *change* se completan los tres sub-proyectos de HU4.
