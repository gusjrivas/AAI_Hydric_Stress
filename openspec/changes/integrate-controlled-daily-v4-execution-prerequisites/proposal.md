# Change: Integrar en `main` los prerrequisitos de ejecución de controlled_daily_v4

## Trazabilidad

- **HU afectada:** HU7 (ejecución experimental) y, por dependencia documental, HU8 (análisis de resultados). No se ejecuta ningún experimento en este *change*.
- **Capacidad OpenSpec:** `experiment-runner`.
- **Fase de CRISP-DM:** Preparación (integración del protocolo y del entorno de ejecución). No alcanza Modelado ni Evaluación: no se entrena ni se evalúa nada.
- **Impacto sobre configuración experimental:** ninguno sobre `controlled_daily_v3`. Sobre `controlled_daily_v4_external_pergamino` fija pisos de soporte predeclarados (≥ 2 folds con MCC definido de 3; ≥ 80 % de réplicas bootstrap válidas) y el contrato de features ejecutable `pergamino_features.v1`.
- **Impacto sobre hipótesis, alcance o arquitectura:** ninguno. No se modifican hipótesis, propósito, alcance, arquitectura, UI ni contratos públicos.
- **Insumo de diseño:** `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `docs/research/controlled-daily-v4-external-pergamino-protocol.md`, `docs/research/scientific-closure-decisions.md`, `docs/research/scientific-closure-runbook.md`.

## Why

La condición 4 de ADR-0011 exige que el ADR **y el protocolo detallado** estén mergeados en `main` antes de que pueda comenzar cualquier ejecución. El ADR ya estaba en `main`; el protocolo presente en `main` era una versión anterior cuya sección 4 afirmaba que el contrato de features era el de `controlled_daily_v3` «sin modificación».

Esa afirmación es falsa contra la implementación: `features.FEATURE_COLUMNS` define **ocho** features con `include_current` efectivo y derivaciones temporales exclusivamente sobre humedad de suelo, mientras que `controlled_daily_v3` usa **quince** variables temporales sobre tres magnitudes con `include_current=false`. Ejecutar bajo el texto de `main` habría preregistrado un contrato de features falso, y habría permitido leer una diferencia v3→v4 como efecto de sitio, período o modelo cuando también cambió el contrato.

Además, el runner en `main` no implementaba los pisos de soporte predeclarados, el tratamiento de casos monoclase, las métricas de inicio de episodio, ni la custodia del primer intento científico de la Etapa B.

## What Changes

- **Protocolo vigente**: sección 4 corregida al contrato v4 real y explícitamente diferenciado de v3; nueva sección de condiciones de interpretación y soporte previas a ejecución. La sección nueva se numera `## 19`: en la rama de origen `feat/scientific-closure` se había numerado `## 16`, colisionando con `## 16. Provenance`. El protocolo de `main` no tenía esa duplicación, de modo que el defecto se corrige durante el port y no llega a `main`.
- **Decisiones preejecución y guía de ejecución**: se incorporan `scientific-closure-decisions.md` (diseños congelados) y `scientific-closure-runbook.md` (procedimiento operativo de preflight → A → B → C, backup y recuperación).
- **Contrato de features ejecutable**: `features.feature_contract()` (`pergamino_features.v1`), serializado en `resolved_config.json` de A/B/C y en el contrato congelado de transferencia de A.
- **Pisos de soporte**: `tuning`/`selection` exigen ≥ 2 folds con MCC definido; `bootstrap` exige ≥ 80 % de réplicas válidas; `admissibility` aplica el mismo piso en la compuerta B→C. Sin soporte, la Etapa A termina `NO_VALID_SELECTION` con diagnósticos y sin candidato transferible.
- **Métricas indefinidas y monoclase**: MCC indefinido con verdad *o* predicción constante; `balanced_accuracy` indefinida con verdad monoclase; representación JSON `null` con estado, razón y soporte, nunca `NaN` ni cero sustituto. B y C monoclase conservan predicciones y métricas definibles; B monoclase no abre C.
- **Métricas de inicio de episodio**: `onset_metrics()` distingue anticipación, detección en el día de inicio, detección tardía y omisión, con censura por izquierda en fronteras de segmento y huecos de calendario, días de anticipación, falsos avisos y soporte.
- **Custodia del primer intento B**: registro SQLite persistente (`stage_b_custody.py`) que reserva el intento antes de parsear o analizar valores y lo finaliza autenticando artefactos por hash; la recuperación es de solo lectura y verifica hashes, sin reentrenar ni cambiar candidato.
- **Preflight**: `preflight.py`, entrada `python -m`, valida disposición de rutas, identidad de código e imagen inmutable sin leer valores de entrada ni inicializar ningún ledger.
- **Manifiesto de provenance**: `implementation_status` actualizado (B y C implementadas, sin ejecución científica) y bloque `current_interpretation` con el contrato vigente.
- **ADR-0011**: se registra el contrato de features verdadero, se corrige la justificación de la alternativa descartada que aún invocaba la herencia de v3, se deja constancia de que la condición 4 queda satisfecha al mergear, y se ratifica la desviación de gobernanza `RK-14`.

## Impact

- **No ejecuta ciencia.** A, B y C **no** se ejecutan; el holdout 2024–2025 permanece cerrado; el ledger definitivo **no** se inicializa. La condición 4 es un prerrequisito de integración, no una autorización de ejecución.
- **No se modifica `controlled_daily_v3`** ni su evidencia congelada bajo `scientific-baseline-v3`.
- Verificación existente: exclusivamente pruebas sintéticas. La existencia de estos mecanismos y de sus fixtures **no** demuestra eficacia real.
