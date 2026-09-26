# Hito 2 — Estado real de la habilitación del ensamble v4 (documento de estado; nada ejecutado en esta intervención)

**Estado:** documento de estado y planificación. Ningún paso de entrenamiento, calibración, refit o empaquetado real se ejecutó en esta intervención. No autoriza, por sí mismo, ninguna acción nueva sobre datos reales, ni la apertura o reutilización del holdout, ni ningún experimento A/B/C.

**Origen:** sección 7 de `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (Hito 1, contrato técnico del ensamble operativo, mergeado en PR #217, verificado exclusivamente con fixtures sintéticas).

**HU/capacidad:** `experiment-runner` (HU7, `controlled_daily_v4_external_pergamino`) + `predictive-modeling` (contrato operativo del ensamble, Hito 1). **Fase CRISP-DM:** evaluación de admisibilidad — no despliegue, no modelado nuevo.

## 0. Corrección respecto de la versión anterior de este documento

La versión anterior afirmaba: *"No se encontró en lo inspeccionado ninguna ejecución real de Stage A sobre Pergamino."* Esa afirmación es **incorrecta** a la luz de evidencia que esta intervención sí revisó: la campaña `controlled_daily_v4_external_pergamino` (Etapas A→B→C) **se ejecutó realmente el 2026-09-21**, una sola vez, con identidad ejecutable verificada (commit `214735e42ee04f018156cd630591e798aadd8bf3`, imagen `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`), exit 0 y custodia verificada en las tres etapas. Fuentes: `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` (`status: EXECUTED_2026_09_21`), `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/changes.json` (`sc-03-stage-a`/`sc-04-stage-b`/`sc-05-stage-c`, los tres `"status": "PASS"`), y `docs/research/scientific-closure-synthesis-2026-09-22.md`.

**No confundir "no encontrado" con "nunca ejecutado":** esta corrección es precisamente el caso que esa distinción advertía. Lo que sigue siendo válido de la sección 0 original —consultar antes de proponer repetir cualquier experimento— ya no aplica a la pregunta "¿existe una ejecución real de A?" (respuesta: sí, verificada), pero sigue aplicando a cualquier pregunta sobre datos que la campaña *no* usó.

## 1. Qué se acreditó realmente (release de la campaña 2026-09-21)

- **Cierre científico:** `SC-GOV-025`/`GF` cierran en **`FAIL`**, no en `PASS` ni `PASS_WITH_LIMITATIONS` (`openspec/scientific-closure/README.md`, `decisions.md` GD-40). Causa: defecto de **gobernanza de secuencia de gates** — las auditorías independientes de A y B se escribieron a disco *después* de que B y C, respectivamente, ya habían corrido (`changes.json`: la aprobación de `sc-04-stage-b` cita "sc-03 PASS" a las `03:20:00Z`, pero la transición `REVIEW→PASS` de `sc-03-stage-a` no ocurre hasta las `04:30:00Z` — 70 minutos después; mismo patrón entre B y C). **No** es una falla de los resultados numéricos de A/B/C en sí (`decisions.md` GD-40: "no invalida las métricas recomputadas... que permanecen como resultados numéricos verificados").
- **Aceptación administrativa (GD-40):** desviación histórica permanente e irreparable. B y C deben presentarse solo como **evidencia retrospectiva exploratoria**, nunca como validación confirmatoria gobernada. **No se autoriza reejecutar B, C ni reabrir el holdout 2024-2025 bajo ningún supuesto derivado de esta decisión.**
- **Holdout 2024-2025:** abierto una única vez, de forma irreversible, `2026-09-21T04:06:11Z`, autorización explícita del responsable, ledger `holdout.sqlite` estado `CONFIRMADA`. Cerrado; no se reabre.

## 2. Qué familias y horizontes tienen soporte real — y por qué el ensamble de 3 votos no puede armarse con lo ejecutado

- **Horizonte:** la campaña real cubrió **exclusivamente t+3** (`experimental_design.target.horizon_days: 3` en el manifiesto; corroborado por `scientific-closure-synthesis-2026-09-22.md`). **No existe ninguna ejecución real, ni siquiera parcial, para horizonte +1 o +2.** Extender el protocolo a esos horizontes sería una decisión metodológica nueva, fuera del alcance de este documento y de esta intervención — no se propone aquí.
- **Selección de familia (Etapa A, 2015–2022, OOF anidado):** se evaluaron las 4 candidatas del diseño (`logistic_regression`, `random_forest`, `hist_gradient_boosting_classifier`, `soft_voting` con pesos fijos 1/3) — el mismo universo de familias que la política `ensemble_agreement_v1` de Hito 1 usa para las tres primeras. Resultado: **`SIN_GANADOR_ESTABLE`** (ninguna superó a las demás por el margen predeclarado Δ=0.05 MCC; MCC OOF: soft_voting 0.7080, logistic_regression 0.6980, random_forest 0.6954, hist_gradient_boosting_classifier 0.6858). El desempate predeclarado por simplicidad eligió **`logistic_regression`** como única candidata llevada a B y C.
- **Consecuencia directa, verificada en código (`src/experiment_runner/controlled_daily_v4/stage_a_runner.py`, `freezing.py`):** el protocolo v4 congela (`freeze_family` + `fit_final_estimator`) **únicamente a la familia ganadora**. `random_forest` y `hist_gradient_boosting_classifier` **nunca fueron congeladas ni reajustadas sobre el `eligible_frame` completo** — solo existen sus métricas de comparación de la Etapa A. La rama de código que sí congelaría las tres bases (`stage_a_runner.py`, cuando `selection.selected_family == FAMILY_SOFT_VOTING`) **no se ejecutó** en la corrida real, porque la ganadora fue `logistic_regression`, no `soft_voting`.
- **Calibración:** el protocolo real **no aplicó ningún paso de calibración** a la familia ganadora ni a ninguna otra (`scientific-closure-synthesis-2026-09-22.md`, §7: "Calibración no corregida... el protocolo congelado no lo predeclaraba"). Es una limitación documentada y verificada: las probabilidades sobre el holdout 2024–2025 son sistemáticamente sobreconfiadas (ej. 96% predicho vs. 66% observado en el bin superior).
- **Persistencia de estimadores:** confirmado directamente en código (`freezing.py`, sin llamadas a `joblib.dump`/`pickle.dump` en todo el paquete `controlled_daily_v4/`) — `fit_final_estimator` devuelve el estimador ajustado **solo en memoria**, nunca lo serializa. No existe ningún `model.joblib`/`calibrator.joblib` de la campaña real, ni de `logistic_regression` ni de ninguna otra familia.

## 3. Dónde viven los artefactos reales — y por qué esta sesión no puede acceder a ellos

- `evidence_root: /home/gus/scientific-closure-runtime/evidence` + respaldo externo en un disco USB físicamente separado (`docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`, sección `execution_artifacts`). Ninguno de los dos está versionado en git.
- En esta máquina Windows, `C:\Repo\AAI_Hydric_Stress_scientific_runtime\evidence`, `\ledger` y `\backups` están **vacíos**. Lo único presente es `validation\preexecution-environment.json`, fechado 2026-09-18, `"status": "TECHNICAL_PREEXECUTION_ONLY"`, `"scientific_experiments_executed": false` — una verificación *previa* a la ejecución real, no la evidencia de la campaña.
- **Entorno de ejecución real:** Linux/WSL2, Python 3.11.16, scikit-learn 1.9.0, imagen Docker `sha256:55bc923e...` (`docker/experiment-v4/Dockerfile`). Distinto del entorno de esta sesión (Windows, `tcnenv`). `load_operational_bundle` (`src/predictive_modeling/operational_inference.py`) exige igualdad exacta de `capture_environment()` entre el bundle y el entorno que lo carga — un artefacto empaquetado en esa imagen Linux no cargaría aquí sin reproducir esa misma imagen, y viceversa.
- **Conclusión de esta sección:** aunque existiera autorización, esta sesión no tiene acceso físico ni de entorno a los datos (`eligible_frame`, `dataset_fingerprint_sha256: 8062605b...38931`) ni a ningún artefacto real de la campaña.

## 4. Búsqueda de autorización operativa — resultado: no encontrada, y un hallazgo explícitamente negativo

Se revisaron `openspec/scientific-closure/decisions.md` (GD-1 a GD-40), `README.md`, `risks.md`, `changes.json`, ADR-0009/0010/0011 y el protocolo de Pergamino, buscando cualquier autorización, ADR o decisión que habilite reutilizar los artefactos/código/configuración de A/B/C con un fin **operativo** (alimentar un ensamble de apoyo a la decisión en vivo), distinto del fin **científico** (confirmación HU7/HU8, ya cerrada en `FAIL` de gobernanza). **No se encontró ninguna.** Ningún documento afirma que el protocolo se haya "ampliado" para uso operativo.

El hallazgo más directamente relevante es explícitamente **negativo**: `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json` registra la pregunta "Is operational anticipation asserted?" con respuesta **"NO"**, y cita la limitación de que la anticipación operativa prospectiva "cannot be asserted without further own evidence". `scientific-closure-synthesis-2026-09-22.md` (§8/§11) refuerza lo mismo: la campaña es "retrospectivo, no operativo", sin medición de latencia, disponibilidad de dato en tiempo real, ni utilidad de riego.

**No se infiere ni se da por aprobada ninguna autorización a partir de este silencio.** La ausencia de una prohibición explícita no equivale a una habilitación.

## 5. Matriz por horizonte

| Horizonte | Estado | Causa |
| --- | --- | --- |
| +1 | **BLOQUEADO** | Sin cobertura real de protocolo. Ninguna ejecución, ni parcial, existe para este horizonte. Extenderlo es un cambio metodológico fuera de este alcance. |
| +2 | **BLOQUEADO** | Idéntica causa que +1. |
| +3 | **BLOQUEADO** | Múltiples causas independientes, ninguna resoluble por esta sesión por sí sola (detalle en sección 6). |

Ningún horizonte alcanza el cuarto estado ("ensemble habilitado con artefactos reales admisibles", sección 7). Hito 2 permanece sin ejecutar.

## 6. Por qué +3 está bloqueado incluso siendo el único horizonte con ejecución real — y qué operación concreta requeriría aprobación

Aun con la corrección de la sección 0 (sí hubo ejecución real), **nada es empaquetable hoy** para +3, por razones independientes y acumulativas:

1. **Solo 1 de las 3 familias requeridas por `ensemble_agreement_v1` fue congelada.** `random_forest` e `hist_gradient_boosting_classifier` no tienen un modelo final ajustado — solo métricas de comparación de la Etapa A. Completar el ensamble exigiría congelarlas ahora, reutilizando su mejor configuración ya evaluada en la grilla de A, sobre el mismo `eligible_frame` ya usado (sin tocar B, C ni el holdout). **Esto no está claramente comprendido en ninguna autorización existente** — es la reutilización de una evaluación ya hecha para producir un artefacto que el protocolo real nunca produjo. No lo decido por mi cuenta: `decisions.md` (GD-38) reserva expresamente ese tipo de decisión al responsable ("el orquestador no tiene autoridad para decidir eso por su cuenta").
2. **Ninguna de las 3 familias tiene calibrador real.** El contrato de Hito 1 (`load_operational_bundle`) exige un `calibrator.joblib` por componente; la campaña real nunca calibró nada. Introducir calibración donde el protocolo nunca la tuvo **es un cambio metodológico** — explícitamente fuera del alcance que este mismo encargo delimita ("no autoriza... cambios metodológicos"). Sin este paso, **ninguna familia real, ni siquiera la ganadora `logistic_regression`, puede empaquetarse en el formato v2** independientemente de las otras dos causas.
3. **Los datos y el entorno reales no están accesibles desde esta sesión** (sección 3) — bloqueo práctico, independiente de cualquier autorización.

**Operación concreta que requeriría aprobación explícita, si en algún momento se autoriza:** (a) confirmar con el responsable si completar los dos componentes faltantes de +3 (paso 1) y agregar calibración (paso 2) se consideran reutilización admisible o cambio metodológico nuevo; (b) de ser admisible, ejecutar el refit/calibración *dentro de la imagen Docker original* (`sha256:55bc923e...`) sobre el `eligible_frame` real (`dataset_fingerprint_sha256: 8062605b...38931`), nunca en este entorno Windows; (c) empaquetar con `attach_feature_names` + el patrón de `write_single_bundle` de Hito 1, destino `bundle_root/<sitio>/horizon_3/ensemble/<familia>/`; (d) verificar carga/inferencia vía la API v2 real, exactamente como en `tests/test_ensemble_bundle_real_families.py` pero sin ningún dato sintético. Nada de esto se ejecutó en esta intervención.

## 7. Umbrales, particiones y demostración histórica (sin cambios respecto de la versión anterior)

- `decision_threshold = 0.5`, comparador `>=`, sin optimizar — confirmado también como el umbral fijo de la campaña real (nunca ajustado contra evaluación/holdout).
- Particiones ya definidas por el protocolo real: A = 2015–2022, B = 2023, C = 2024–2025 (holdout, cerrado). No se alteran.
- Cualquier demostración histórica futura debe ser causalmente válida y no debe tocar `replay_packages/` ni el paquete `base-seed4` custodiado.

## 8. Los cuatro estados (referencia)

Definidos en `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`, sección 1:

1. Single-model disponible (sin cambios).
2. Ensemble configurado pero `unavailable` (artefactos incompletos/inválidos/ausentes).
3. Integración probada con datos sintéticos (Hito 1 — alcanzado, PR #217 mergeado).
4. Ensemble habilitado con artefactos reales admisibles — **no alcanzado**. Bloqueado en los tres horizontes (sección 5); para +3, condicionado a una decisión explícita del responsable sobre las dos cuestiones de la sección 6, no solo a disponibilidad de datos/entorno.

## 9. Trazabilidad

- **HU:** HU7 (`experiment-runner`, `controlled_daily_v4_external_pergamino`, campaña real 2026-09-21, cierre `FAIL` de gobernanza) + `predictive-modeling` (contrato operativo del ensamble, Hito 1, PR #217).
- **Impacto en configuración experimental:** ninguno — este documento no ejecuta ningún experimento ni reabre el holdout.
- **Impacto en hipótesis/alcance/arquitectura:** ninguno. No se propone reejecutar B/C, no se propone ampliar el protocolo a nuevos horizontes, no se decide por cuenta propia si completar las familias faltantes o agregar calibración es admisible.
- **Fuentes citadas:** `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`, `docs/research/scientific-closure-synthesis-2026-09-22.md`, `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md`, `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/README.md`, `openspec/scientific-closure/changes.json`, `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json`, `src/experiment_runner/controlled_daily_v4/{stage_a_runner.py,freezing.py}`.
