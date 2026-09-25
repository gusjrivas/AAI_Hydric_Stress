# Integración operativa del ensamble v4 — diseño (Hito 1: contrato técnico; Hito 2: plan de habilitación real)

**HU/capacidad:** integra `predictive-modeling` (bundles operativos v2) con `experiment-runner` (familias de `controlled_daily_v4`), expuesto vía `alerting-ui`. Trazabilidad detallada en la sección 9.

**Fase CRISP-DM:** despliegue (Hito 1: contrato técnico verificable); planificación de modelado (Hito 2: plan, sin ejecución).

**Autorización:** este documento amplía explícitamente el objetivo original del Trabajo Final (integrar el ensamble con el backend/UI), instrucción directa del usuario en esta sesión (2026-09-25), posterior al cierre técnico preparatorio de PR #216 (ya mergeado a `main`, SHA `0b9d25a3bc6a3cf00c9964f7afcb50202181b40f`, CI verde).

## 1. Objetivo y alcance

**Objetivo de este cambio:** dejar un contrato técnico operativo, probado, que permita evaluar el ensamble de tres familias (regresión logística, Random Forest, HistGradientBoosting) con una política de acuerdo explícita, **sin** reingeniería del backend existente y **sin** ejecutar ningún entrenamiento real.

**Este documento cubre dos hitos de naturaleza distinta, y el primero NO cierra el objetivo del ensamble operativo real:**
- **Hito 1** (sección 3): código + pruebas, verificado exclusivamente con fixtures sintéticas — entregable de esta etapa.
- **Hito 2** (sección 5): **documento de planificación únicamente, sin ejecutar nada en esta etapa**. Su ejecución posterior (fuera de este cambio, con las autorizaciones científicas que correspondan) es una condición **necesaria** para que el ensamble real llegue a operar en la aplicación — sin Hito 2 ejecutado, el modo ensamble seguirá siempre en `unavailable` para cualquier sensor real, por diseño (sección 3.1bis: sin artefactos, no hay directorio `ensemble/`, se mantiene single-model).

**Fuera de alcance de este cambio (explícito):**
- La UI (se implementará después, sobre este contrato).
- `historical_replay` / `replay_packages/` — confirmado estructuralmente inalcanzable desde este cambio (sin import, sin ruta de código compartida).
- Optimización de umbrales — se reutiliza `decision_threshold=0.5`, la misma constante ya usada en v2 y v4, documentada explícitamente como "nunca seleccionada sobre test".
- Cualquier entrenamiento, experimento A/B/C, apertura de holdout.
- `controlled_daily_v3`, memoria técnica existente (más allá de actualizar trazabilidad de lo efectivamente implementado).

## 2. Hallazgo de inventario (resumen — investigación completa ya realizada esta sesión)

**No se encontraron artefactos v4 utilizables en las ubicaciones inspeccionadas** (repositorio git; 2 servidores MLflow corriendo — `localhost:5000` y `:5001`, listados vía API REST, sin experimentos ni modelos registrados de v4; 2 buckets MinIO — listado recursivo completo, sin objetos `v4`/`joblib` relacionados; 3 contenedores Docker con bundles operativos reales en `/workspace/data/operational_bundles/` — son del pipeline legacy v3/productor de un solo modelo, `model_identity.version="operational_v3_h1_seed0_model"`, no de las tres familias de v4; job de CI `experiment-v4-container` — efímero, `docker run --rm`, sin persistencia). **Esto no es una afirmación de inexistencia absoluta** — no se pudo inspeccionar almacenamiento externo fuera de esta máquina. La conclusión operativa: no hay artefactos v4 admisibles para integrar hoy; Hito 1 se verifica con fixtures sintéticas; Hito 2 (abajo) es el plan para producirlos.

`controlled_daily_v4` nunca serializa un estimador ajustado (decisión de diseño explícita, hallazgo H-05 de una auditoría previa): solo persiste `frozen_config.json` (contrato de hiperparámetros) y evidencia JSON/CSV. Reconstruir un modelo real exige refit vía `freezing.fit_final_estimator` sobre el mismo `eligible_frame` — no existe ningún camino de código hoy que produzca un `model.joblib`/`calibrator.joblib` de v4.

## 3. Hito 1 — Integración técnica (implementar y probar ahora)

### 3.1 Formato de bundle de ensamble (nuevo, aditivo)

```
bundle_root/<sensor_id>/horizon_<h>/ensemble_manifest.json
bundle_root/<sensor_id>/horizon_<h>/ensemble/<family>/model.joblib
bundle_root/<sensor_id>/horizon_<h>/ensemble/<family>/calibrator.joblib
bundle_root/<sensor_id>/horizon_<h>/ensemble/<family>/contract.json
bundle_root/<sensor_id>/horizon_<h>/ensemble/<family>/bundle.json
```

`<family>` ∈ `{logistic_regression, random_forest, hist_gradient_boosting_classifier}` — mismos nombres que `controlled_daily_v4.config.FAMILY_SIMPLICITY_ORDER[:-1]`, para identidad trazable entre el mundo experimental y el operativo.

Cada `ensemble/<family>/` es **estructuralmente idéntico** al bundle v2 de un solo modelo que ya existe (`model.joblib`+`calibrator.joblib`+`contract.json`+`bundle.json`, `format_version=1`) — se reutiliza `load_operational_bundle`/`predict_operational_bundle` sin modificarlas, una vez por familia.

`ensemble_manifest.json` (nuevo, `format_version=1`):
```json
{
  "format_version": 1,
  "mode": "ensemble",
  "policy_version": "ensemble_agreement_v1",
  "sensor_id": "<sensor_id>",
  "horizon_days": 1,
  "contract_version": "<compartido por las 3 familias>",
  "families": ["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"],
  "weights": {"logistic_regression": 0.3333333333333333, "random_forest": 0.3333333333333333, "hist_gradient_boosting_classifier": 0.3333333333333333}
}
```
Los pesos son fijos (1/3 cada uno) y **nunca se renormalizan** — si falta una familia, no se recalculan pesos sobre las restantes; el resultado es evaluación incompleta (ver 3.3).

### 3.1bis Distinción single-model intencional vs. ensamble configurado incompleto/inválido (sin fallback silencioso)

**No existe hoy ningún mecanismo de configuración por sensor que declare "este sensor usa ensamble"** — verificado: `src/data_ingestion/catalog.py::CatalogRepository` (registro de sensores/sectores) solo guarda metadatos de sector/cultivo, sin ningún campo de modo de modelo; no hay variable de entorno ni archivo de configuración por sensor para esto. La única configuración existente y reutilizable es la convención de rutas ya usada por `load_operational_bundle` (`PRODUCER_BUNDLE_ROOT/<sensor_id>/horizon_<h>/`) — este diseño la extiende con un nivel más, sin inventar un eje de configuración nuevo:

- **Señal de intención = existencia del directorio `.../horizon_<h>/ensemble/`** (no la validez de su contenido). Si ese directorio no existe en absoluto → **single-model intencional**: el sensor/horizonte nunca fue configurado para ensamble, se sigue el camino actual sin cambios, sin ninguna verificación adicional.
- Si el directorio `ensemble/` **existe** (aunque `ensemble_manifest.json` falte, esté malformado, o alguna familia esté incompleta/incompatible) → **ensamble configurado, evaluación incompleta**: `status="unavailable"` con `reason_code` específico (`"ensemble_manifest_missing"`, `"ensemble_manifest_invalid:<campo>"`, `"ensemble_component_missing:<family>"`, `"ensemble_contract_mismatch:<campo>"`). **Nunca**, en este segundo caso, se cae al bundle single-model que pudiera existir en `.../horizon_<h>/model.joblib` (aunque esté presente) — la sola existencia de `ensemble/` es una declaración de intención que excluye ese fallback. Esta es la regla explícita que evita la activación silenciosa de single-model.
- Orden de verificación en `load_ensemble_bundle`/el punto de integración (3.4): (1) ¿existe `.../ensemble/`? No → camino single-model actual, fin. Sí → (2) todo lo demás (manifiesto, familias, cross-checks) debe validar correctamente o el resultado es `unavailable`, nunca una degradación a otro camino.

### 3.2 Carga: `load_ensemble_bundle`

Nuevo módulo `src/predictive_modeling/ensemble_bundle.py`. `is_ensemble_configured(bundle_root, *, sensor_id, horizon) -> bool` implementa exactamente la señal de intención de 3.1bis (existencia del directorio `ensemble/`, nada más) — es la única función que el llamador (3.4) usa para decidir entre los dos caminos. `load_ensemble_bundle(bundle_root: Path, *, sensor_id: str, horizon: int) -> EnsembleBundle` se llama **solo** cuando `is_ensemble_configured` ya dio `True`; nunca devuelve `None` — o devuelve un `EnsembleBundle` válido o lanza una excepción tipada (nunca ambigüedad "vacío = single-model", ese caso ya se descartó antes de llamarla). Pasos:

1. Leer y validar `ensemble_manifest.json` (`format_version`, `mode=="ensemble"`, `policy_version` en un conjunto soportado, `sensor_id`/`horizon_days` coinciden con los parámetros). Archivo ausente o JSON inválido → `EnsembleManifestMissingError`/`EnsembleManifestInvalidError`, nunca se continúa a los pasos siguientes.
2. Para cada familia declarada, llamar a `load_operational_bundle(bundle_root/sensor_id/f"horizon_{horizon}/ensemble/{family}", sensor_id=sensor_id, horizon=horizon)` — **sin modificar esa función**. Cualquier `BundleUnavailable` de una familia se recolecta (no se descarta el intento completo prematuramente, para reportar todas las causas).
3. **Verificación cruzada nueva** (lo que `load_operational_bundle` no puede ver, porque valida un solo bundle a la vez): las 3 familias cargadas deben coincidir en `contract_version`, `horizon_days`, `decision_threshold`, y en la preparación de entradas (`feature_columns`, `lags`, `rolling_windows` idénticos) — de lo contrario, `EnsembleBundleIncompatible` con el campo exacto en conflicto.
4. Si falta cualquier familia o hay cualquier incompatibilidad → no se devuelve un `EnsembleBundle` parcial; se propaga una excepción tipada con la causa exacta (`EnsembleComponentMissingError`/`EnsembleBundleIncompatible`), que el llamador traduce a `status="unavailable"` (ver 3.4) — **nunca** fallback silencioso a single-model, **nunca** recálculo de pesos.

`EnsembleBundle` (`@dataclass(frozen=True)`): `manifest: dict`, `components: dict[str, OperationalBundle]` (uno por familia, reutilizando el tipo ya existente).

### 3.3 Predicción: `predict_ensemble_bundle`

`predict_ensemble_bundle(ensemble: EnsembleBundle, dataframe, *, sensor_id, units, as_of_date) -> dict`. Llama a `predict_operational_bundle` (sin modificar) una vez por familia, sobre el mismo `dataframe`/`as_of_date` — el corte causal ya existente en esa función se reutiliza sin cambios para cada componente.

**Precisión exacta de umbrales, comparador y calibración (verificado en el código actual, `operational_inference.py:171,181,183`):**
- Cada componente produce su `score` llamando a `positive_probability(bundle.calibrator, row)` — **siempre** una probabilidad calibrada (`score_kind="calibrated_probability"`, literal fijo en esa función; no existe hoy ningún camino en `predict_operational_bundle` que devuelva `"raw_model_score"`). Nunca se promedian puntajes crudos de modelo sin calibrar.
- El voto individual de cada componente ya existe, sin cambios: `alert = score >= decision_threshold` (comparador **`>=`**, no `>`; línea 181 de `operational_inference.py`), usando el `decision_threshold` propio de **ese** bundle (campo `bundle.json["decision_threshold"]`, validado finito en `[0,1]` al cargar).
- **`decision_threshold` individual vs. combinado — mismo valor, nunca dos criterios distintos:** el diseño exige (paso 3.2.3) que los 3 componentes declaren el **mismo** `decision_threshold`; si no coincide, es una incompatibilidad de contrato (`unavailable`, no un promedio de umbrales distintos). Hoy, en todo bundle real o sintético existente, ese valor es `0.5` — la misma constante ya usada en `operational_run_artifacts.py` (v2) y en `controlled_daily_v4.config.DECISION_THRESHOLD` (v4). **Se documenta explícitamente como política operativa heredada, no como umbral validado científicamente para ninguna de las 3 familias ni para el ensamble** — cita textual ya presente en el código: "0.5 is the existing operational alert threshold; never selected on test". Este diseño no le atribuye ninguna validación que no existe; solo lo reutiliza con el mismo comparador `>=` para la combinada, por consistencia.
- Deriva **cuatro campos separados, nunca combinados entre sí**:
  - `probabilidad_combinada`: promedio de las 3 probabilidades **ya calibradas** (nunca crudas), pesos fijos 1/3 (`manifest["weights"]`).
  - `decision_binaria_combinada`: `probabilidad_combinada >= decision_threshold` — mismo comparador `>=`, mismo valor de umbral ya validado idéntico entre las 3 (paso 3.2.3), nunca un umbral nuevo o distinto del individual.
  - `votos_positivos`: cuenta de componentes cuyo **propio** `alert` (de su propio `decision_threshold`, ya calculado por `predict_operational_bundle` sin cambios) es verdadero.
  - `categoria_acuerdo`: `3→"alerta_por_unanimidad"`, `2→"posible_alerta_acuerdo_parcial"`, `1→"sin_alerta_por_mayoria_con_discrepancia"`, `0→"sin_alerta_por_unanimidad"`.

Chequeo de admisibilidad temporal (nuevo, mínimo): ningún componente puede tener `trained_through` posterior a `as_of_date` — si ocurre, `EnsembleTemporalInadmissibleError` (reutiliza el patrón de validación ya existente en `operational_run.py`, no una lógica nueva).

### 3.4 Integración en el punto único existente

`producer_emission.py::emit_forecasts` — antes de llamar a `load_operational_bundle` para un horizonte dado, llamar a `is_ensemble_configured(bundle_root, sensor_id=sensor_id, horizon=horizon)` (3.2):
- `False` → camino actual exacto, sin cambios (single-model intencional, sección 3.1bis).
- `True` → **exclusivamente** `load_ensemble_bundle`/`predict_ensemble_bundle`; cualquier excepción de esas funciones (`EnsembleManifestMissingError`, `EnsembleManifestInvalidError`, `EnsembleComponentMissingError`, `EnsembleBundleIncompatible`, `EnsembleTemporalInadmissibleError`) se traduce a `SlotSeed(status="unavailable", reason_code=...)` con la causa exacta — **en ningún caso** se reintenta con `load_operational_bundle` sobre la ruta single-model del mismo horizonte, ni se devuelve un resultado simulado como si fuera real.

Ambos caminos conviven en la misma función, sin pipeline paralelo ni backend duplicado.

### 3.5 Esquema de respuesta y persistencia (aditivo, compatibilidad preservada)

`schemas_v2.py`: nuevos modelos `EnsembleComponentVote` (`family`, `model_reference: ModelReference`, `score`, `decision_threshold`, `alert`) y `EnsembleDetail` (`policy_version`, `components: list[EnsembleComponentVote]`, `probabilidad_combinada`, `decision_binaria_combinada`, `votos_positivos`, `categoria_acuerdo`). `ForecastResponse` gana `ensemble: EnsembleDetail | None = None` — `None` cuando el sensor/horizonte no está en modo ensamble (comportamiento actual sin cambios).

Cuando el modo ensamble está activo, los campos existentes de nivel superior (`alert`, `score`, `score_kind`, `model_reference`) se completan **desde la vista combinada** (nunca desde el conteo de votos): `alert=decision_binaria_combinada`, `score=probabilidad_combinada`, `model_reference.model_version="ensemble/<policy_version>"`, `model_reference.trained_through` = el más antiguo (más conservador) de los 3 componentes. Así los consumidores existentes (incluida la UI futura, si la leyera hoy) siguen funcionando sin cambios; el detalle explicativo completo vive en `ensemble`.

`human_feedback/operational_repository.py::SlotSeed` gana los mismos campos opcionales (`ensemble_policy_version`, `ensemble_components`, `ensemble_probability`, `ensemble_agreement_category`, `ensemble_votes_positive`), todos `None` cuando no aplica, con un invariante nuevo en `__post_init__`: o todos son `None`, o todos están presentes juntos (coherencia). El registro persistido (dict) y `_render_forecast` ganan los mismos campos — la predicción original y su explicación completa quedan reproducibles junto al registro existente, sin sobrescribir nada.

### 3.6 Pruebas (Hito 1)

Fixtures sintéticas: 3 bundles de familia por sensor/horizonte, construidos con el helper ya existente `operational_run_artifacts.persist_operational_run`-equivalente (llamado 3 veces con identidades de familia distintas) más un `ensemble_manifest.json` de prueba — nunca datos reales, nunca artefactos v4 reales (no existen).

- Las 4 combinaciones de voto (3/3, 2/3, 1/3, 0/3) → categoría de acuerdo correcta.
- Límite de umbral: probabilidad combinada exactamente en 0.5 → decisión binaria determinística y documentada (`>=`, coherente con el resto del sistema).
- Componente faltante → `unavailable` con `reason_code` específico, sin fallback ni renormalización.
- Componente con contrato incompatible (ej. distinto `decision_threshold` o distintas `feature_columns`) → `unavailable`, causa exacta.
- Caso donde promedio y mayoría discrepan (ej. dos probabilidades muy altas + una muy baja dan voto 2/3 pero probabilidad combinada podría caer bajo 0.5, o viceversa) → verificar que `decision_binaria_combinada` y `categoria_acuerdo` se reporten ambos, sin que uno se calcule a partir del otro.
- Trazabilidad/persistencia: el registro guardado permite reconstruir la explicación completa (todas las probabilidades, pesos, votos, versión de política).
- Compatibilidad: sensores/horizontes sin directorio `ensemble/` producen exactamente la misma respuesta que hoy (test de regresión explícito, single-model intencional).
- Directorio `ensemble/` presente pero `ensemble_manifest.json` ausente o inválido → `unavailable` con causa exacta, **incluso si además existe un `model.joblib` single-model válido en la ruta del horizonte** — verificar explícitamente que ese bundle single-model NO se usa como fallback.
- **Test de integración** del endpoint `POST /producer_v2/forecasts` (o el que corresponda) de punta a punta con las fixtures sintéticas.
- Identificar por separado qué se pudo verificar con artefactos reales: **nada** — no existen artefactos v4 reales; se documenta explícitamente como limitación, no como cobertura lograda.

## 4. Documentación y trazabilidad a actualizar

- `openspec/specs/predictive-modeling/spec.md` (o el spec correspondiente): nuevo requirement para el modo ensamble, marcado `[implementado, verificado con fixtures — sin artefactos reales]`.
- `openspec/specs/experiment-runner/spec.md`: nota cruzada — el contrato operativo existe y está probado; los artefactos reales de v4 siguen sin producirse (Hito 2).
- Capítulo 3 (memoria técnica): describir la nueva política operativa (acuerdo por votos) como una decisión de arquitectura de esta integración, explícitamente separada de los resultados científicos de v4 ya reportados (Stage A/B sintéticos) — nunca presentar la política de acuerdo como si fuera, en sí misma, un resultado científico nuevo.

## 5. Hito 2 — Plan de habilitación real (documentar; NO ejecutar)

**Este hito es una entrega documental de esta etapa, no una tarea de código.** Queda explícitamente pendiente de ejecución posterior — esa ejecución (con las autorizaciones que correspondan) es necesaria para completar el objetivo del ensamble real en la aplicación; el Hito 1 por sí solo únicamente deja el contrato verificado con fixtures. Se entrega como documento separado (`docs/design/ensemble-real-enablement-plan.md`), sin ejecutar nada, cubriendo:

- **Dataset:** cuál dataset real (Pergamino, ya referenciado en `controlled_daily_v4_external_pergamino`) y su fingerprint/hash verificable.
- **Particiones temporales:** Stage A (selección/freeze) → Stage B (aceptación 2023) → Stage C (evaluación 2024-2025), tal como ya define `controlled_daily_v4`, sin alterar los cortes existentes.
- **Entrenamiento:** ejecutar Stage A real (nunca hecho, solo sintético hoy) para obtener `frozen_config.json` real; refit vía `freezing.fit_final_estimator` por familia sobre el `eligible_frame` real.
- **Calibración:** qué método/partición de calibración usar para producir `calibrator.joblib` por familia — coherente con el patrón ya usado por `operational_run.py` para v2.
- **Umbrales:** confirmar que `decision_threshold=0.5` se mantiene (no se optimiza) para las 3 familias, documentando explícitamente esa decisión como no-tuneada.
- **Horizontes compatibles:** cuáles de horizonte 1/2/3 tienen soporte real en v4 hoy (a verificar — no asumir que los 3 existen igual que en v2).
- **Período admisible para demostración histórica:** qué ventana de fechas sería causalmente válida para una demo tipo `historical_replay` con estos artefactos, sin tocar `replay_packages/` existentes ni mezclar este ensamble con el paquete `base-seed4` ya custodiado.
- **Autorizaciones científicas requeridas:** qué rol/autoridad debe aprobar antes de ejecutar Stage A real sobre Pergamino (protocolo de cierre científico, `openspec/scientific-closure/`), y qué difiere del protocolo experimental v3/v4 vigente (ej. v4 nunca se ejecutó sobre datos reales; hacerlo por primera vez para fines operativos, no solo científicos, es una decisión que excede este PR).

## 6. Restricciones globales (heredadas, aplican a todo el Hito 1)

- No modificar `_verify_file_integrity`/`_sha256_of` ni ningún archivo bajo `replay_packages/`.
- No modificar `load_operational_bundle`/`predict_operational_bundle` — solo reutilizarlas.
- No introducir un nuevo mecanismo de umbral; reutilizar `decision_threshold` existente.
- No renormalizar pesos ante componentes faltantes.
- No conflar probabilidad promedio con conteo de votos en ningún campo.
- No tocar UI, `controlled_daily_v3`, ni memoria técnica más allá de lo señalado en la sección 4.
- No entrenar, no ejecutar A/B/C, no abrir holdout.

## 7. Foco de revisión (riesgos que las pruebas propias podrían no cubrir)

- Un componente cuya probabilidad calibrada cae exactamente en el límite de `decision_threshold` bajo redondeo de punto flotante — verificar que la comparación sea consistente (`>=`) en los 3 componentes y en la combinada.
- Un manifiesto de ensamble con `policy_version` no reconocida (versión futura) — debe fallar explícitamente, no ignorarse ni interpretarse como la versión actual.
- Persistencia parcial: un registro guardado a mitad del ciclo de emisión (entre calcular el ensamble y persistir) no debe dejar campos `ensemble_*` inconsistentes con los campos de nivel superior.
- Un consumidor existente que lea `model_reference.trained_through` esperando una fecha única — confirmar que el valor conservador (el más antiguo) no rompe ninguna validación existente aguas abajo (ej. checks de "trained_through no posterior a as_of_date").
- La combinación 2/3 con probabilidades muy dispares (ej. 0.9, 0.9, 0.05) — confirmar que `categoria_acuerdo="posible_alerta_acuerdo_parcial"` y `probabilidad_combinada≈0.62` (por encima del umbral) se reportan ambos coherentemente, sin que ninguno "gane" sobre el otro en la respuesta.

## 8. Autorrevisión del spec

- Sin placeholders: cada sección tiene contenido concreto, no "TBD".
- Consistencia interna: nombres de campos (`probabilidad_combinada`, `votos_positivos`, `categoria_acuerdo`, `decision_binaria_combinada`) usados igual en 3.3, 3.5 y 3.6.
- Alcance: Hito 1 es implementable en un solo plan; Hito 2 es explícitamente un documento de planificación, no una tarea de código — no se decompone más.
- Ambigüedad resuelta: "decisión binaria por su umbral" (encargo original) se interpretó como el umbral ya existente (0.5, común a las 3 familias, comparador `>=`), nunca uno nuevo — documentado explícitamente en 3.3, con la cita exacta del código que ya lo declara no-validado.
- Ambigüedad resuelta (ronda de revisión 2026-09-25): "single-model intencional" vs. "ensamble configurado con manifiesto faltante/inválido" se distinguen por la existencia del directorio `ensemble/` (señal de intención, independiente de la validez de su contenido) — nunca por la sola presencia/ausencia del manifiesto, que por sí sola no alcanzaría a distinguir "nunca configurado" de "configurado mal". Verificado que no existe ningún mecanismo de configuración por sensor preexistente (`catalog.py`) para reutilizar en su lugar; se reutiliza la convención de rutas ya existente (`PRODUCER_BUNDLE_ROOT/<sensor_id>/horizon_<h>/`), extendida un nivel, en vez de crear un eje de configuración nuevo.

## 9. Trazabilidad

- **HU:** integra capacidades de `predictive-modeling` (HU4) y `experiment-runner` (HU7), expuesto para consumo futuro por `alerting-ui`.
- **Impacto en configuración experimental:** ninguno — no se ejecuta ningún experimento; Hito 2 es un plan, no una ejecución.
- **Impacto en hipótesis/alcance/arquitectura:** ampliación explícita y autorizada del alcance original (integración operativa del ensamble), con advertencia explícita del usuario en esta sesión — no una decisión unilateral.
