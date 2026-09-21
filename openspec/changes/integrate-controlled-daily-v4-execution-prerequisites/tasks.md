# Tareas — integrate-controlled-daily-v4-execution-prerequisites

## 1. Protocolo y decisiones

- [x] 1.1 Corregir la sección 4 del protocolo al contrato v4 real de ocho features, diferenciado explícitamente de `controlled_daily_v3`.
- [x] 1.2 Incorporar la sección de condiciones de interpretación y soporte previas a ejecución.
- [x] 1.3 Renumerar a `## 19` la sección nueva, que en la rama de origen `feat/scientific-closure` se había numerado `## 16` y colisionaba con `## 16. Provenance`. El protocolo de `main` no tenía esa duplicación: el defecto se corrige durante el port, no se arrastra.
- [x] 1.4 Incorporar `docs/research/scientific-closure-decisions.md`.
- [x] 1.5 Incorporar `docs/research/scientific-closure-runbook.md`, sustituyendo las rutas concretas de un host por marcadores de posición y omitiendo la sección de migración a Linux de la rama de origen (evidencia de preparación, fuera del alcance de este cambio).
- [x] 1.6 Actualizar `implementation_status` y `current_interpretation` en el manifiesto de provenance.

## 2. Runner y soporte técnico

- [x] 2.1 Exponer `features.feature_contract()` y serializarlo en `resolved_config.json` de A/B/C y en el contrato congelado de A.
- [x] 2.2 Exigir ≥ 2 folds con MCC definido en `tuning.select_best_config` y en `selection.select_family`.
- [x] 2.3 Exigir ≥ 80 % de réplicas bootstrap válidas y exponer `support_sufficient`/`discarded_fraction`.
- [x] 2.4 Aplicar el mismo piso de soporte en `admissibility.check_stage_c_admissibility`.
- [x] 2.5 Declarar MCC indefinido con verdad o predicción constante y `balanced_accuracy` indefinida con verdad monoclase.
- [x] 2.6 Conservar predicciones y métricas definibles en evaluaciones monoclase de B y C.
- [x] 2.7 Implementar `metrics.onset_metrics()` con censura de fronteras y gaps.
- [x] 2.8 Implementar la custodia del primer intento científico de B y su recuperación de solo lectura.
- [x] 2.9 Implementar el preflight de metadatos, sin lectura de valores ni inicialización de ledger.
- [x] 2.10 Extender la CLI con `--image-id`, `--stage-b-registry-path`, `--recover-stage-b` y `--recovery-reason`.

## 3. ADR y gobernanza

- [x] 3.1 Registrar en ADR-0011 el contrato de features vigente y corregir la justificación que invocaba la herencia de v3.
- [x] 3.2 Registrar que la condición 4 queda satisfecha al mergear, sin que ello autorice ejecutar A, B o C.
- [x] 3.3 Registrar la ratificación expresa de los dos pushes históricos identificados por `RK-14`.

## 4. Validación

- [x] 4.1 `pytest tests/test_controlled_daily_v4_*.py` en verde.
- [x] 4.2 Suite completa `pytest` en verde.
- [x] 4.3 `ruff check src tests` y `black --check src tests` en verde.
- [x] 4.4 `git diff --check` sin hallazgos.

## 5. Fuera de alcance (no ejecutado)

- [ ] 5.1 Ejecutar la Etapa A sobre datos reales — **requiere autorización explícita**.
- [ ] 5.2 Ejecutar la Etapa B — **requiere autorización explícita y A admisible**.
- [ ] 5.3 Ejecutar la Etapa C / abrir el holdout 2024–2025 — **requiere autorización adicional y B validada**.
- [ ] 5.4 Inicializar el ledger definitivo del holdout — **no autorizado**.
- [ ] 5.5 Implementar los runners complementarios (regresión, HITL, anomalías, robustez) — diseñados, no implementados.
