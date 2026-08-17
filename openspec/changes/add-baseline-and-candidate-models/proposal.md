# Change: Add baseline and candidate models capability

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU4 — Componente de modelado predictivo (subconjunto: modelos de referencia y candidatos, segundo de tres sub-proyectos en que se dividió HU4).
- **Fase de CRISP-DM:** Modelado / Evaluación.
- **Configuración experimental afectada:** base (Épica 4) — este *change* entrena los modelos sobre la configuración base de `data-quality` (sin anomalías ni sintéticos todavía); las otras 3 configuraciones se ejecutan igual una vez integrado con `experiment-runner` (HU7).
- **Insumo de diseño:** [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (variable objetivo, variables predictoras), [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (`run_quality_pipeline` para train/test sin fuga).

## Why

La ingeniería de variables (`add-feature-engineering`) deja lista la matriz de variables y el objetivo, pero no hay todavía ningún modelo entrenado ni un punto de comparación (baseline) contra el cual medir si un modelo más complejo realmente aporta.

## What Changes

- **Modelo de referencia**: persistencia — predice estrés futuro si la humedad de suelo *actual* ya está por debajo del mismo umbral usado para la etiqueta. Es el baseline estándar en pronóstico de series temporales (más informativo que predecir siempre la clase mayoritaria) y no requiere entrenamiento.
- **Modelos candidatos**: regresión logística (simple, interpretable) y Random Forest (captura no linealidades), ambos de scikit-learn (ADR-0002).
- Se implementa el flujo de entrenamiento para ambos candidatos sobre el conjunto de entrenamiento.
- **Validación**: `TimeSeriesSplit` de scikit-learn para validación cruzada y para el ajuste de hiperparámetros (`GridSearchCV`), respetando el orden temporal — cada fold de validación es posterior a su fold de entrenamiento, sin fuga dentro del propio conjunto de entrenamiento.
- Se ejecuta el entrenamiento inicial y el ajuste de hiperparámetros de ambos candidatos.
- Se comparan desempeño (precisión/recall/F1/ROC-AUC de la clase de estrés, dado el desbalance ~80/20), estabilidad (desvío de la métrica entre folds de validación cruzada) y complejidad (tipo de modelo y cantidad de parámetros/estimadores) de los tres modelos (referencia + 2 candidatos).

## Impact

- **Specs afectadas:** `predictive-modeling` (extiende el spec existente).
- **Specs futuras que dependen de esta:** el *change* siguiente de HU4 (alertas tempranas) consumirá el modelo elegido tras la comparación; `experiment-runner` (HU7) ejecutará este mismo flujo sobre las 4 configuraciones de `data-quality`.
- **Código afectado:** nuevo módulo `src/predictive_modeling/models.py`, `training.py`, `evaluation.py`.
- **Fuera de alcance de este change:** lógica de generación de alertas a partir de las predicciones (tercer *change* de HU4); ejecución sistemática sobre las 4 configuraciones experimentales (HU7, no iniciada).

## Alternativas consideradas

- **Baseline de clase mayoritaria** (predecir siempre "sin estrés"): se descarta porque no aporta ninguna señal real y es un punto de comparación menos exigente que la persistencia.
- **Un único modelo candidato (solo Random Forest)**: se descarta para esta primera versión porque comparar contra un modelo lineal simple (regresión logística) ayuda a detectar si la relación es mayormente lineal antes de justificar un modelo más complejo.
- **Validación cruzada aleatoria (K-fold estándar)**: se descarta porque mezclaría fechas futuras y pasadas entre folds de entrenamiento/validación, violando el mismo principio de no-fuga temporal ya establecido en `data-quality` y `feature-engineering`.

## Estado: implementado

Ver [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) para los requisitos vigentes y la verificación con datos reales.
