# Change: Add controlled_daily_v4_external_pergamino protocol

## Trazabilidad

- **Épica:** 4. Evaluación experimental — extensión posterior al cierre de HU7/HU8, derivada de ADR-0010. No corresponde a ninguna HU1–HU8 del backlog original; es trabajo adicional explícitamente anticipado en ADR-0010 (capítulo 5 de la memoria técnica: "XGBoost, Deep Learning y las evaluaciones multianuales como trabajo futuro").
- **Capacidad OpenSpec:** `experiment-runner` (protocolo formal de ejecución de experimentos comparativos, mismo rol que cumple `controlled_daily_v3`/ADR-0009 en la spec vigente).
- **Fase de CRISP-DM:** Preparación de datos (fuente externa Pergamino) + Evaluación (nested CV, validación temporal, holdout).
- **Insumo de diseño:** `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md`, `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `docs/research/controlled-daily-v4-external-pergamino-protocol.md`, `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`.

## Why

ADR-0010 registró la estrategia multimodelo (Logistic Regression, Random Forest, HistGradientBoostingClassifier, Soft Voting) para una futura iteración `controlled_daily_v4`, condicionada a definir el protocolo completo antes de observar nuevos resultados y a no reutilizar el conjunto de test de `controlled_daily_v3`. Un relevamiento y una microvalidación read-only sobre datasets externos de reanálisis (Pergamino, Balcarce) identificaron que Pergamino ofrece una secuencia diaria continua 2015–2025 sin faltantes estructurales, con un período 2024–2025 todavía no observado reservable como holdout independiente del de `controlled_daily_v3`. ADR-0011 formalizó el protocolo resultante. Este *change* propone la especificación verificable de ese protocolo como capacidad futura de `experiment-runner`, **sin implementar código ni ejecutar nada todavía** — es la condición previa documental exigida por ADR-0010 antes de que exista un *change* de implementación real.

## What Changes (propuesto, sin implementación de código todavía)

- Nueva capacidad futura de `experiment-runner`: ejecución del protocolo `controlled_daily_v4_external_pergamino` sobre el dataset externo de Pergamino (ERA5-Land + NASA POWER), con nested `TimeSeriesSplit(n_splits=3, gap=3)` (outer e inner), target `stress(t) = 1 si soil_moisture(t+3) < P20_train` (operador estrictamente `<`), cuatro candidatos (LR, RF, HGB, Soft Voting) balanceados vía `sample_weight` fold-local, selección por MCC global sobre OOF concatenado con margen práctico `δ=0.05`, y una compuerta real de validación temporal (Etapa B, 2023) que condiciona la apertura de un holdout final protegido (Etapa C, 2024–2025).
- Ver el detalle completo, reproducible y verificable en `docs/research/controlled-daily-v4-external-pergamino-protocol.md` (fuente de verdad del protocolo) y el delta de especificación de este *change* (`specs/experiment-runner/spec.md`), que expresa los requisitos en formato Given/When/Then.
- **Ningún archivo de código (`src/`, `scripts/`, `backend/`) se crea ni modifica en este *change*.** La implementación real (módulo de ejecución, tests, integración con MLflow) queda para un *change* posterior, todavía no propuesto.

## Impact

- **Specs afectadas:** `experiment-runner` (nuevo requirement propuesto, ver `specs/experiment-runner/spec.md` de este *change* — no se modifica el spec canónico `openspec/specs/experiment-runner/spec.md`, que sigue documentando exclusivamente la capacidad ya implementada de `controlled_daily_v3`).
- **Código afectado:** ninguno en este *change*.
- **Datasets afectados:** ninguno — los CSV crudos de Pergamino permanecen fuera de Git, sin modificar.
- **`controlled_daily_v3` / `scientific-baseline-v3` / `technical-baseline-v1` / `technical-baseline-v2`:** sin alteración, sin movimiento.
- **Fuera de alcance de este *change*:** implementación del runner, ejecución de cualquier experimento, apertura de 2023 o 2024–2025, incorporación de Balcarce (registrada como `FUTURE_GEOGRAPHIC_VALIDATION`), incorporación de temperatura/precipitación al conjunto principal de features (sensibilidad separada, no incluida aquí).

## Alternativas consideradas

- **Actualizar directamente `openspec/specs/experiment-runner/spec.md`** con una sección para `controlled_daily_v4_external_pergamino`. Descartada: ese archivo es la fuente de verdad de una capacidad ya **implementada** (cada requirement cita módulos y tests reales de `src/experiment_runner/`); agregar requisitos de un protocolo sin código propio mezclaría capacidad vigente con protocolo pendiente, contra la convención del repositorio de que los *changes* proponen antes de que el spec canónico se actualice tras la implementación.
- **No crear ningún artefacto OpenSpec, solo ADR + protocolo en `docs/`.** Descartada: la tarea que originó este documento pidió explícitamente una especificación con requisitos verificables en formato Given/When/Then, y el repositorio ya tiene una convención establecida (*changes* con delta de spec) para expresar exactamente ese tipo de contrato antes de implementar.
