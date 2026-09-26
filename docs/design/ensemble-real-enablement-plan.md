# Hito 2 — Plan de habilitación real del ensamble v4 (documento de planificación; nada ejecutado)

**Estado:** documento de planificación exclusivamente. Ningún paso de este documento se ejecutó. No autoriza, por sí mismo, entrenamiento sobre datos reales, apertura de holdout, ni ningún experimento A/B/C.

**Origen:** sección 7 de `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (Hito 1, contrato técnico del ensamble operativo, implementado y verificado exclusivamente con fixtures sintéticas — ver ese documento y `docs/superpowers/plans/2026-09-25-ensemble-operational-integration-plan.md`).

**HU/capacidad:** `experiment-runner` (HU7, `controlled_daily_v4_external_pergamino`) + `predictive-modeling` (contrato operativo del ensamble). **Fase CRISP-DM:** planificación de modelado — no despliegue.

## 0. Paso previo obligatorio: verificar antecedentes antes de proponer repetir cualquier experimento

`docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (sección 2) certifica únicamente **"no encontrado en lo inspeccionado en esta máquina"** (git, 2 servidores MLflow, 2 buckets MinIO, 3 contenedores Docker en ejecución, CI efímero) — nunca "no existe" ni "nunca se ejecutó". Antes de plantear ejecutar Stage A real sobre Pergamino por primera vez, este plan exige como primer paso:

1. Consultar con quien tenga autoridad normativa sobre el Trabajo Final (director/a de tesis; protocolo de cierre científico, `openspec/scientific-closure/`) si existe una corrida real de Stage A/B/C sobre Pergamino en algún lugar no inspeccionado desde esta máquina (otro entorno, almacenamiento externo, corrida de otro colaborador).
2. Si la respuesta es afirmativa: usar esos artefactos/resultados reales en lugar de proponer una nueva ejecución, y documentar su procedencia (commit, imagen, configuración, semillas, datos, hashes) antes de reutilizarlos.
3. Solo si la respuesta es negativa (o no verificable), continuar con los pasos siguientes de este plan.

## 1. Dataset

- **Dataset objetivo:** Pergamino (`controlled_daily_v4_external_pergamino`, protocolo `docs/research/controlled-daily-v4-external-pergamino-protocol.md`) — no el dataset formal `melchor_romero_2024_consolidado` de `controlled_daily_v3`.
- Verificar fingerprint/hash del CSV/fuente real antes de cualquier ajuste; registrar el hash exacto usado.
- No introducir ningún dato sintético en esta etapa: el objetivo de Hito 2 es exclusivamente el dataset real de Pergamino.

## 2. Particiones temporales

- Respetar los cortes ya definidos por el protocolo v4 existente: Stage A → Stage B (validación temporal sobre 2023) → Stage C (evaluación única sobre 2024–2025, con `holdout_ledger.py`).
- No alterar esos cortes para este plan; cualquier cambio de partición es una decisión metodológica fuera de este alcance y requiere advertencia explícita.

## 3. Entrenamiento

- No se encontró en lo inspeccionado ninguna ejecución real de Stage A sobre Pergamino (solo verificado sintéticamente hasta la fecha de este documento; ver sección 0 sobre las limitaciones de ese inventario) — ejecutarlo por primera vez, o reutilizar una ejecución real ya existente en algún lugar no inspeccionado, requiere la autorización de la sección 0.
- Refit vía `freezing.fit_final_estimator`, por familia, sobre el `eligible_frame` real resultante de Stage A — sin modificar esa función ni el resto de `controlled_daily_v4/` (frozen).
- Empaquetado real usando `attach_feature_names` (`src/predictive_modeling/bundle_packaging.py`, sin cambios respecto de Hito 1) para restituir `feature_names_in_` sobre los estimadores reales ajustados por array.

## 4. Calibración

- Un calibrador por familia, cada uno ajustado con `CalibratedClassifierCV(FrozenEstimator(modelo), method="sigmoid")` sobre una partición de calibración real disjunta de entrenamiento — mismo patrón que `operational_run.fit_seed` y que la prueba de Nivel 2 de Hito 1 (`tests/test_ensemble_bundle_real_families.py`), pero sobre datos reales de Pergamino en lugar de sintéticos.
- No introducir ningún mecanismo de recalibración automática a partir de feedback (HU5): la calibración de Hito 2 es un ajuste inicial sobre datos históricos, no un lazo de reentrenamiento continuo.

## 5. Umbrales

- `decision_threshold = 0.5`, comparador `>=`, sin optimizar — mismo valor no-tuneado que Hito 1 y que el resto del sistema. No mirar el conjunto de evaluación/holdout para elegir este umbral.

## 6. Horizontes compatibles

- Verificar explícitamente cuáles horizontes (1, 2 y/o 3 días) tienen soporte real y probado en `controlled_daily_v4` antes de asumir que los tres existen igual que en el pipeline v2 de un solo modelo. No completar por inferencia un horizonte sin evidencia.

## 7. Período admisible para una demostración histórica

- Cualquier ventana de demostración tipo `historical_replay` debe ser causalmente válida (nunca usar información posterior al `as_of_date` simulado).
- No tocar `replay_packages/` ni mezclar este ensamble con el paquete `base-seed4` custodiado — son corridas históricas preservadas, ajenas a este plan.

## 8. Autorizaciones científicas requeridas

- Rol/autoridad que debe aprobar la primera ejecución real de Stage A sobre Pergamino con fines operativos (protocolo de cierre científico, `openspec/scientific-closure/`).
- Documentar explícitamente que esto excede el protocolo v3/v4 vigente: no se encontró en lo inspeccionado ninguna ejecución de v4 sobre datos reales con fines operativos (distinto de fines científicos) — esa distinción y su aprobación exceden este documento y requieren la autorización correspondiente antes de ejecutar cualquier paso de las secciones 1–7.

## 9. Los cuatro estados (referencia)

Definidos en `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`, sección 1:

1. Single-model disponible (sin cambios).
2. Ensemble configurado pero `unavailable` (artefactos incompletos/inválidos/ausentes).
3. Integración probada con datos sintéticos (Hito 1 — alcanzado).
4. Ensemble habilitado con artefactos reales admisibles — **no alcanzado por este documento**; su ejecución (con las autorizaciones de la sección 8) es la única vía hacia este cuarto estado.

## 10. Trazabilidad

- **HU:** HU7 (`experiment-runner`, `controlled_daily_v4_external_pergamino`) + `predictive-modeling` (contrato operativo del ensamble, Hito 1).
- **Impacto en configuración experimental:** ninguno — este documento no ejecuta ningún experimento.
- **Impacto en hipótesis/alcance/arquitectura:** ninguno adicional al ya declarado en Hito 1; este documento no amplía el alcance, solo planifica su posible ejecución futura bajo autorización explícita.
