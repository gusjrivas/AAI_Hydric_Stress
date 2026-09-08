# Spec delta: experiment-runner

> Estado de este delta: **propuesta, sin implementación de código todavía** (`PROTOCOL_ONLY`, ver `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`). Ninguno de los escenarios siguientes está implementado ni ejecutado; se documentan como el contrato verificable que una futura implementación deberá cumplir. No reemplaza ni modifica el requirement vigente de `controlled_daily_v3` en `openspec/specs/experiment-runner/spec.md`.

## ADDED Requirements

### Requirement: Protocolo formal controlled_daily_v4_external_pergamino sobre dataset externo de reanálisis

El sistema DEBE poder ejecutar el protocolo `controlled_daily_v4_external_pergamino` (definido en `docs/research/controlled-daily-v4-external-pergamino-protocol.md`) sobre el dataset diario derivado del cruce ERA5-Land/NASA POWER de Pergamino, produciendo predicciones OOF y métricas para los cuatro candidatos de ADR-0010 (Logistic Regression, Random Forest, HistGradientBoostingClassifier, Soft Voting), sin utilizar en ningún paso el conjunto de test de `controlled_daily_v3`.

#### Scenario: Etiquetado con target estrictamente menor al percentil de entrenamiento

- **GIVEN** una serie diaria de humedad de suelo de Pergamino y un umbral `P20_train` calculado exclusivamente sobre el segmento de entrenamiento autorizado
- **WHEN** se etiqueta una fila cuya humedad a `t+3` días es exactamente igual a `P20_train`
- **THEN** esa fila queda etiquetada como `stress=0` (el operador es estrictamente `<`, nunca `<=`)

#### Scenario: Ningún target usa observaciones fuera del período autorizado de la etapa

- **GIVEN** las tres etapas del protocolo (A: 2015–2022, B: 2023, C: 2024–2025) y sus `target_timestamp` autorizados
- **WHEN** se construyen los targets de cada etapa
- **THEN** ningún target de la Etapa A tiene `target_timestamp` posterior a 2022-12-31, ningún target de la Etapa B tiene `target_timestamp` posterior a 2023-12-31, y ningún target de la Etapa C tiene `target_timestamp` posterior a 2025-12-31

#### Scenario: Las features de una emisión pueden usar historia causal de la etapa anterior

- **GIVEN** una emisión del 2023-01-01 (Etapa B), cuyos lags/ventanas móviles requieren observaciones de diciembre de 2022
- **WHEN** se construyen sus variables predictoras
- **THEN** esas observaciones de diciembre de 2022 se usan como historia causal válida, sin que diciembre de 2022 se agregue como fila evaluable propia de la Etapa B

#### Scenario: Ningún estadístico aprendido usa datos posteriores al corte de su etapa

- **GIVEN** un `P20_train`, un `StandardScaler` o un `sample_weight` calculados para la Etapa A, B o C
- **WHEN** se inspecciona qué filas participaron en ese cálculo
- **THEN** ninguna de esas filas tiene `target_timestamp` posterior al corte de entrenamiento autorizado de esa etapa

#### Scenario: Nested cross-validation temporal con gap suficiente para el horizonte

- **GIVEN** las filas elegibles de la Etapa A y `TimeSeriesSplit(n_splits=3, gap=3)` aplicado a nivel outer e inner
- **WHEN** se generan las particiones
- **THEN** en cada partición (outer e inner), el último `target_timestamp` del segmento de entrenamiento es estrictamente anterior al primer `feature_timestamp` del segmento de validación correspondiente

#### Scenario: Selección de candidato por MCC global sobre OOF concatenado, con margen práctico predeclarado

- **GIVEN** las predicciones OOF de los cuatro candidatos, concatenadas en orden temporal
- **WHEN** se calcula el MCC global de cada candidato y se comparan por moving block bootstrap (bloques de 30 días, 5.000 réplicas, semilla 20250109)
- **THEN** se declara candidato superior estable solo si su MCC global supera a cada rival por al menos `δ=0.05` y el límite inferior del intervalo pareado correspondiente es mayor que cero frente a cada rival; en caso contrario, se declara `SIN_GANADOR_ESTABLE` y se aplica el desempate predeclarado por simplicidad (`LR < RF < HGB < Soft Voting`), documentado explícitamente como tal y no como superioridad predictiva

#### Scenario: Compuerta real de validación temporal antes de abrir el holdout

- **GIVEN** el candidato congelado en la Etapa A, evaluado una única vez sobre 2023
- **WHEN** se calcula `ΔMCC_B = MCC_candidato_2023 − MCC_persistencia_2023` y su intervalo pareado de bootstrap
- **THEN** el resultado es `CANDIDATE_VALIDATED` únicamente si `MCC_candidato_2023 > 0` y el límite inferior del intervalo es `≥ −0.05`; en caso contrario es `CANDIDATE_NOT_VALIDATED`, el protocolo se detiene, y el holdout de 2024–2025 permanece cerrado sin excepción

#### Scenario: El holdout no admite ajustes posteriores a su apertura

- **GIVEN** un candidato congelado que obtuvo `CANDIDATE_VALIDATED` en la Etapa B y fue reentrenado con `target_timestamp ≤ 2023-12-31`
- **WHEN** se evalúa una única vez sobre 2024–2025
- **THEN** el resultado se reporta tal cual, incluso si es negativo, sin permitir reentrenamientos alternativos, recalibración ni repetición de la evaluación

#### Scenario: Métrica indefinida en un conjunto monoclase nunca se convierte en resultado favorable

- **GIVEN** un fold o un período de evaluación cuyo `y_true` resulta monoclase
- **WHEN** se calculan MCC, average precision o ROC-AUC sobre ese conjunto
- **THEN** cada una de esas métricas se registra como `NaN` explícito, nunca como 0, y ese conjunto no puede producir `CANDIDATE_VALIDATED` en la Etapa B

Sin implementación asociada todavía — este delta describe el contrato que deberá satisfacer un *change* de implementación futuro, no propuesto en esta iteración.
