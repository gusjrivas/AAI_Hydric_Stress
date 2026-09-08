# Protocolo experimental: controlled_daily_v4_external_pergamino

Estado: **PROTOCOL_ONLY** — protocolo formalizado, sin implementación de código ni ejecución. Este documento es la fuente detallada y reproducible del protocolo; la decisión y su justificación quedan registradas en [ADR-0011](../adr/0011-protocolo-controlled-daily-v4-external-pergamino.md), que no debe duplicar este contenido.

Rige `ADR-0011` y `ADR-0010`. No modifica, reinterpreta ni recalcula `controlled_daily_v3` (protocolo vigente en `protocolo-experimental-v3.md`, evidencia congelada bajo `scientific-baseline-v3`).

## 1. Identificador y objetivo

- **Identificador:** `controlled_daily_v4_external_pergamino`.
- **Objetivo:** evaluar transferibilidad temporal y robustez metodológica de la arquitectura de modelado de `controlled_daily_v3` sobre una segunda fuente agroclimática externa (reanálisis de Pergamino), sin sustituir ni modificar la evidencia formal de `controlled_daily_v3`.
- Pergamino es una fuente agroclimática externa de reanálisis/modelado (ERA5-Land vía Open-Meteo, NASA POWER). **No debe describirse como evidencia de campo directa proveniente de sensores físicos propios.**

## 2. Dataset y alcance geográfico/de profundidad

- **Localización:** Pergamino.
- **Profundidad principal:** humedad de suelo 0–7 cm.
- **Sensibilidad separada:** 7–28 cm — corre en paralelo, no interviene en la selección del análisis principal, se reporta por separado.
- **Excluidas de esta iteración:** 28–100 cm y 100–255 cm (esta última mostró folds monoclase sistemáticos en la microvalidación previa, y 109 de 2.913 valores de humedad futura exactamente iguales al umbral P20 — evidencia de baja variabilidad estructural del reanálisis a esa profundidad).
- **Balcarce:** fuera de esta ejecución. Se registra como `FUTURE_GEOGRAPHIC_VALIDATION` en el manifiesto de provenance (`controlled-daily-v4-external-pergamino-manifest.yaml`).

## 3. Target

Para cada fecha de emisión `t` (`feature_timestamp`):

```
stress(t) = 1 si soil_moisture(t + 3 días) < P20_train
stress(t) = 0 en caso contrario
```

- Horizonte: **3 días** (`target_timestamp = feature_timestamp + 3 días`).
- Comparación **estrictamente `<`**, nunca `<=` (ver microvalidación previa: en 100–255 cm, `<=` incorporaba 109 filas cuyo valor futuro coincide exactamente con el percentil, distorsionando la prevalencia en casi 4 puntos porcentuales).
- `P20_train` se calcula **exclusivamente** con el `train` autorizado del fold/etapa correspondiente. Nunca con validación, test ni con datos de una etapa posterior.

Diferenciar explícitamente de este umbral de construcción del target:

```
predicted_class(t) = 1 si predict_proba(t) >= 0.5
```

El umbral probabilístico de decisión es **fijo en 0.5** para los cuatro candidatos, incluido Soft Voting. No se ajusta con A, B ni C. Explorar otros umbrales queda como trabajo futuro, fuera de este protocolo.

## 4. Features autorizadas

Contrato causal heredado de `controlled_daily_v3`, sin modificación:

- humedad de suelo 0–7 cm (autorregresiva);
- humedad relativa (RH2M, NASA POWER);
- radiación solar (ALLSKY_SFC_SW_DWN, NASA POWER);
- lags 1, 2 y 3 días de humedad de suelo;
- medias móviles causales de 3 y 7 días de humedad de suelo.

Temperatura (T2M) y precipitación (PRECTOTCORR) quedan **fuera del protocolo principal**, por criterio metodológico previo (no derivado de resultados): mantener el mismo conjunto de variables que `controlled_daily_v3` evita confundir "efecto del sitio/dominio" con "efecto de variables adicionales". Pueden incorporarse únicamente como un experimento de sensibilidad separado y predeclarado, ejecutado después de cerrar la comparación principal, sin influir en la selección de ningún candidato.

## 5. Apertura causal de las etapas — fronteras temporales exactas

El pipeline procesa, en cada etapa, **solo el período autorizado más la historia causal estrictamente necesaria** para lags(1,2,3)/rolling(3,7) — no se calculan features sobre toda la serie 2015–2025 por adelantado.

| Etapa | Train autorizado (`target_timestamp`) | Emisiones evaluables (`feature_timestamp`) | Targets evaluables |
|---|---|---|---|
| A | ≤ 2022-12-31 | 2015-01-07 → 2022-12-28 | 2015-01-10 → 2022-12-31 |
| B | ≤ 2022-12-31 (modelo ya congelado en A) | 2023-01-01 → 2023-12-28 | 2023-01-04 → 2023-12-31 |
| C | ≤ 2023-12-31 (reentrenamiento) | 2024-01-01 → 2025-12-28 | 2024-01-04 → 2025-12-31 |

Reglas:

- **Historia causal permitida para features:** cualquier observación cruda con fecha `≤ feature_timestamp`, sin importar a qué etapa "pertenece" esa observación cruda. Diciembre de 2022 puede usarse como historia causal para lags/rolling de las emisiones de enero de 2023 (Etapa B); diciembre de 2023, análogamente, para enero de 2024 (Etapa C). Esto es correcto porque esa historia ya existía y era observable en el momento real de emisión — no es leakage.
- **Información futura prohibida:** (a) el `target_timestamp` de una fila nunca puede caer fuera del período autorizado de la etapa que la usa; (b) ningún estadístico *aprendido* (`P20_train`, medias/desvíos de `StandardScaler`, `sample_weight`) puede calcularse usando filas cuyo `target_timestamp` exceda el corte de entrenamiento autorizado de esa etapa, aunque esas filas usen solo historia pasada en sus *features*.
- No se incluyen emisiones de diciembre de 2022 como filas de la Etapa B, ni de diciembre de 2023 como filas de la Etapa C — diciembre solo aporta historia cruda para lags/rolling, nunca filas evaluables propias.
- **Consecuencia verificable:** en A ninguna etiqueta usa datos de 2023; en B ninguna etiqueta usa datos de 2024; en C ninguna etiqueta excede el 2025-12-31. Esto evita entrenar un modelo con etiquetas que todavía no estaban disponibles en el momento en que se habría emitido la predicción correspondiente.

## 6. Nested temporal cross-validation (Etapa A)

- Outer: `TimeSeriesSplit(n_splits=3, gap=3)` sobre las filas elegibles de la Etapa A.
- Inner: `TimeSeriesSplit(n_splits=3, gap=3)`, aplicado exclusivamente dentro de cada `outer_train`.
- Invariante verificable, exigido en cada partición (outer e inner): `max(target_timestamp_train) < min(feature_timestamp_validation)`. Ya verificado explícitamente para 0–7 cm/Pergamino en la microvalidación previa (margen de 1 día en los tres outer folds).
- `P20_train`, `sample_weight` y `StandardScaler` se ajustan exclusivamente con el `train` de cada fold — nunca con la validación correspondiente.
- Ya verificado: 0 folds monoclase para Pergamino 0–7 cm en esta configuración (outer y también a nivel inner, salvo casos aislados documentados en la microvalidación).

## 7. Modelos y grillas de hiperparámetros

Deterministas y acotadas. Todos usan las mismas fechas, features, target, folds, horizonte, reglas de imputación y semillas comparables.

### 7.1 Balanceo de clases (todos los modelos)

Exclusivamente vía `sample_weight`, calculado con el `train` de cada fold:

```
w_c = n_train / (n_classes × n_train_c)     # por clase c, n_classes = 2
sample_weight[i] = w_{y_i}                   # por fila i del train
```

No se usa `class_weight` en ningún modelo — elimina la dependencia de si `class_weight` está soportado en la versión exacta de scikit-learn instalada (ver sección 11). Se comparan dos modos: `{sin ponderar, sample_weight balanceado}`.

### 7.2 Logistic Regression — 8 configuraciones

- Preprocesamiento: `StandardScaler` fold-local.
- `solver='lbfgs'`, `penalty='l2'`, `max_iter=2000`.
- Sin `random_state`: `lbfgs` es determinista para clasificación binaria en este problema (sin submuestreo ni shuffling internos); fijar una semilla no tiene efecto. Si en el futuro se cambiara a `solver='saga'` o `'liblinear'`, `random_state=42` debería reincorporarse.
- `C ∈ {0.01, 0.1, 1.0, 10.0}`
- Ponderación: `{sin ponderar, sample_weight balanceado}`
- Total: 4 × 2 = **8**.

### 7.3 Random Forest — 24 configuraciones

- `n_estimators ∈ {100, 300}`
- `max_depth ∈ {4, 8, None}`
- `min_samples_leaf ∈ {5, 20}`
- Ponderación: `{sin ponderar, sample_weight balanceado}`
- `random_state=42` (con efecto real: bootstrap de bagging y selección aleatoria de features en cada split).
- `n_jobs=1` (reproducibilidad).
- Total: 2 × 3 × 2 × 2 = **24**.

### 7.4 HistGradientBoostingClassifier — 32 configuraciones

- `learning_rate ∈ {0.03, 0.1}`
- `max_iter ∈ {100, 300}`
- `max_leaf_nodes ∈ {15, 31}`
- `l2_regularization ∈ {0.0, 1.0}`
- `max_depth=None` (fijo — no se cruza como dimensión adicional junto con `max_leaf_nodes`, redundante para el volumen de datos disponible).
- Ponderación: `{sin ponderar, sample_weight balanceado}`
- `early_stopping=False` (evita una fuente de validación interna no controlada por el protocolo).
- `random_state=42` (con efecto real: binning/histogramas y muestreo interno de features).
- Total: 2 × 2 × 2 × 2 × 2 = **32**.
- **Uso exclusivo de parámetros soportados por la versión de scikit-learn efectivamente fijada en el manifiesto de provenance** (sección 11) — sin condicionales de versión en el código.

### 7.5 Soft Voting — cuarto candidato real

- `VotingClassifier(voting='soft')`, construido únicamente con las tres familias anteriores.
- Pesos fijos `(1/3, 1/3, 1/3)`, nunca ajustados con validación ni holdout.
- Es un candidato más: puede ganar, pero no está garantizado ni es obligatorio que lo haga.
- Sin grilla propia — se compone con las configuraciones ya seleccionadas de LR/RF/HGB (ver sección 9).

## 8. Selección estadística en la Etapa A

1. Generar predicciones OOF de cada candidato mediante el nested CV de la sección 6.
2. Concatenar las predicciones OOF en orden temporal (los tres `outer_val` son disjuntos y cronológicamente ordenados — **no** estrictamente contiguos, porque `gap=3` deja una discontinuidad de 4 días entre el fin de cada `outer_train` y el comienzo de su `outer_val`).
3. **Criterio principal:** MCC calculado una sola vez sobre esa concatenación completa.
4. **Diagnóstico (no decide):** MCC por outer fold individual, reportado como mediana e IQR de los 3 valores.
5. **Comparación pareada entre candidatos:** moving block bootstrap temporal sobre la serie OOF concatenada — bloques de **30 días**, **5.000 réplicas**, semilla **`20250109`**. Los bloques respetan las discontinuidades de los outer folds: no se construye ningún bloque que cruce el final de un segmento outer y el comienzo del siguiente; el muestreo con reemplazo ocurre dentro de cada segmento temporal válido, preservando la comparación pareada por `timestamp` compartido entre candidatos.
6. No se afirma significancia simultánea ni control familiar del error a partir de varios intervalos del 95% individuales sin corrección — cada comparación pareada se interpreta por separado.

### Margen práctico

`δ = 0.05` (en escala MCC, rango `[-1, 1]`). Fijado **antes de observar resultados** de A, B o C — no derivado del desvío estándar bootstrap ni de ninguna otra cantidad calculada durante la ejecución. Representa cinco centésimas de capacidad discriminativa, adoptado como umbral conservador de diferencia práctica apropiado para un conjunto temporal de tamaño modesto (~2.900 filas elegibles en desarrollo).

### Definiciones

- **Candidato superior estable:** mayor MCC global, con diferencia observada `≥ δ=0.05` frente a **cada** rival, y límite inferior del intervalo pareado bootstrap `> 0` frente a cada rival.
- **Conjunto de equivalencia práctica:** todo candidato cuya diferencia de MCC global respecto del mejor es `< δ`, o cuyo intervalo pareado frente al mejor incluye el cero.
- **`SIN_GANADOR_ESTABLE`:** el mejor candidato tiene al menos otro miembro en su conjunto de equivalencia práctica.
- **Desempate predeclarado** (solo ante `SIN_GANADOR_ESTABLE`): se selecciona el más simple dentro del conjunto equivalente, orden fijo `LR < RF < HGB < Soft Voting`. Se documenta explícitamente como "elegido por simplicidad predeclarada ante empate práctico" — **nunca** como superioridad predictiva.
- AP, Brier Score, log loss, calibración, F1, precisión, recall y balanced accuracy son **secundarias**: se reportan siempre, pero no pueden reemplazar post hoc los pasos 3–6 ni alterar un resultado de `SIN_GANADOR_ESTABLE`/desempate ya determinado.

## 9. Congelamiento de hiperparámetros (tras seleccionar familia en A)

- Se ejecuta una **segunda pasada**, independiente de los 9 pares outer×inner de la sección 8: un nuevo `TimeSeriesSplit(n_splits=3, gap=3)` sobre **todo** 2015–2022, exclusivamente para fijar hiperparámetros finales, usando solo información de A.
- **Si gana un modelo individual (LR, RF o HGB):** se ajusta su grilla sobre esos 3 folds, se elige la configuración de mayor mediana de MCC, y se reentrena una vez sobre todo 2015–2022 para congelarla.
- **Si gana Soft Voting:** se ajustan por separado las tres grillas (LR, RF, HGB) sobre esos mismos 3 folds, se congela la mejor configuración de cada una, y el Soft Voting final se compone con esas tres configuraciones fijas y pesos `(1/3, 1/3, 1/3)`.
- Prohibido construir la configuración final agregando informalmente resultados de los 9 inner folds de la sección 8 — el congelamiento usa exclusivamente esta segunda pasada, dedicada y separada.

## 10. Compuerta de la Etapa B (2023)

```
ΔMCC_B = MCC_candidato_2023 − MCC_persistencia_2023
```

`CANDIDATE_VALIDATED` si y solo si, evaluado una única vez sobre 2023:

1. `MCC_candidato_2023 > 0`.
2. Límite inferior del intervalo pareado bootstrap de `ΔMCC_B ≥ −0.05` (moving block bootstrap: bloques de 30 días, 5.000 réplicas, semilla `20250109`, calculado exclusivamente sobre las predicciones de 2023).

Si falla cualquiera de las dos condiciones:

- se produce `CANDIDATE_NOT_VALIDATED`;
- se detiene el protocolo;
- **no se abre 2024–2025**;
- **no se prueba otro modelo usando 2023**.

Si el conjunto OOF concatenado de A o el conjunto de 2023 en B resulta monoclase, el candidato **no puede ser validado** (la condición 1 queda indeterminada/incumplida por definición, sin forzar un resultado).

## 11. Etapa C — holdout final (2024–2025)

Solo si B produce `CANDIDATE_VALIDATED`:

- Reentrenamiento del candidato ya congelado (misma familia, mismos hiperparámetros) con `target_timestamp ≤ 2023-12-31`.
- `P20_train` recalculado exclusivamente con ese rango.
- Evaluación **única** sobre `target_timestamp ∈ [2024-01-04, 2025-12-31]`.
- Prohibido cualquier ajuste, recalibración o repetición motivada por el resultado, incluso si es negativo. Se reporta tal cual.
- Apertura del holdout: evento único e irreversible, que requiere registro explícito de fecha y autorización (nombre/rol de quien autoriza) en el manifiesto de provenance.

## 12. Métricas y convenciones ante casos degenerados

**Primaria:** Matthews Correlation Coefficient (MCC).

**Secundarias:** average precision, balanced accuracy, F1, precisión, recall, ROC-AUC, matriz de confusión, Brier score, log loss, calibración probabilística (reliability diagram, 10 bins).

**Operativas:** tasa de alertas, falsos positivos por 30 días, falsos negativos por 30 días, recall de episodios de estrés (por racha contigua de `target=1`, no por día suelto), precisión de alertas.

| Métrica | Convención |
|---|---|
| MCC global | Calculado directamente sobre toda la concatenación OOF, siempre que tenga ambas clases |
| MCC por fold (diagnóstico) | Un fold monoclase se registra como `NaN` solo en el reporte por fold — nunca se "excluye" del MCC global, porque el MCC global se recalcula desde cero sobre las observaciones concatenadas |
| Average Precision | `NaN` explícito por convención si no hay positivos reales en el conjunto evaluado |
| ROC-AUC | `NaN` explícito por convención si `y_true` es monoclase |
| Brier Score | Se calcula siempre, normalmente, con targets binarios 0/1 |
| Log loss | Se calcula siempre pasando explícitamente `labels=[0,1]`, para forma de salida consistente aunque `y_true` sea monoclase en ese conjunto |
| Matriz de confusión | Se calcula siempre con `labels=[0,1]`, garantizando una matriz 2×2 aunque una fila/columna quede en cero |

Ningún `NaN` se convierte silenciosamente en cero ni en un resultado favorable. Si el OOF concatenado de A, o el conjunto de 2023 en B, resulta monoclase, el candidato correspondiente no puede ser validado en esa etapa.

## 13. Baselines

- **Clase mayoritaria aprendida en train:** `argmax` del conteo de clases exclusivamente sobre el `train` autorizado de cada fold/etapa.
- **Persistencia causal de humedad:** predice `1` si `soil_moisture(feature_timestamp) < P20_train` (mismo umbral que el candidato en esa etapa, aplicado al valor *actual*, no al futuro).
- **Predictor constante de estrés:** predice `1` siempre.

Ninguno usa el target futuro ni un umbral calculado fuera del `train` autorizado. La persistencia causal es además el baseline formal de comparación de la compuerta de la Etapa B (sección 10).

## 14. Costo computacional aproximado

- Por outer fold: `(8 LR + 24 RF + 32 HGB) × 3 inner folds = 192` ajustes de tuning.
- Tres outer folds: `192 × 3 = 576` ajustes de tuning en la comparación OOF de A.
- Reentrenamiento para producir OOF por outer: 3 modelos individuales × 3 outer = 9; Soft Voting reentrena sus 3 modelos base por outer = 9 adicionales.
- Total comparación OOF de A: `576 + 9 + 9 = 594` ajustes base.
- Congelamiento final (sección 9), según el candidato ganador: LR `8×3+1=25`; RF `24×3+1=73`; HGB `32×3+1=97`; Soft Voting `(8+24+32)×3+3=195` (tres grillas completas más tres reentrenamientos finales — no se cuenta como un único ajuste).
- **Máximo total aproximado de la Etapa A: `594 + 195 = 789` ajustes base** (peor caso: gana Soft Voting).
- Etapa B: 1 reentrenamiento del candidato congelado + 3 baselines = 4 ajustes.
- Etapa C (condicional a `CANDIDATE_VALIDATED`): 1 reentrenamiento + 3 baselines = 4 ajustes.

Carga computacional modesta (datasets de a lo sumo ~2.400 filas, ≤10 features), apropiada para el alcance de una tesis de maestría.

## 15. Entorno reproducible

`PRECONDITION_FOR_EXECUTION` — no bloquea la documentación del protocolo, sí su ejecución:

- Debe existir un manifiesto o lock experimental con versiones exactas y validadas de Python, NumPy, pandas, SciPy, PyArrow y scikit-learn antes del primer experimento.
- El runner correspondiente (a implementar en un *change* de OpenSpec futuro) no podrá ejecutarse mientras ese manifiesto/lock no exista.
- Hoy, `pyproject.toml` solo fija pisos mínimos (`scikit-learn>=1.4`, `pandas>=2.0`, sin NumPy/SciPy/PyArrow como dependencias directas con versión fijada), sin lockfile — el entorno no es reproducible tal como está configurado.

## 16. Provenance

Manifiesto detallado en `controlled-daily-v4-external-pergamino-manifest.yaml` (plantilla versionada, sin resultados experimentales, estado `PROTOCOL_ONLY`). Los CSV crudos permanecen fuera de Git. Solo se permite, sobre los CSV crudos: leer metadatos necesarios, calcular SHA-256, verificar encabezados, verificar consistencia de URLs con las fuentes descargadas. No se permite analizar valores, clases ni métricas de 2024–2025.

## 17. Clasificación científica

| Etapa | Permite afirmar | No permite afirmar |
|---|---|---|
| A (2015–2022) | Comparación exploratoria interna de familias de modelo sobre reanálisis de Pergamino | Superioridad confirmada, generalización, portabilidad |
| B (2023) | Validación temporal candidata de un único modelo ya seleccionado | Selección de modelo, ajuste de hiperparámetros |
| C (2024–2025) | Validación temporal final de un único modelo ya congelado | Selección, recalibración, nueva comparación de familias |

En ningún punto se alcanza portabilidad geográfica (un único sitio externo) ni validación agronómica in situ (ERA5-Land/NASA POWER son reanálisis, no mediciones de campo). `controlled_daily_v3` no se modifica ni se reinterpreta en ningún paso.

## 18. Seguimiento

Ver `docs/seguimiento-tareas.md`, sección "Protocolo controlled_daily_v4_external_pergamino documentado", para el estado de esta iteración frente al plan de tesis.
