# Integración operativa del ensamble v4 — diseño (Hito 1: contrato técnico; Hito 2: plan de habilitación real)

**Revisión 3 (2026-09-25):** reemplaza íntegramente las revisiones anteriores (`e3b4b6b`, `5c2eff9`) tras la devolución de Codex sobre `5c2eff9`. Todas las citas de código de este documento están verificadas contra el árbol actual del worktree (`feat/ensemble-operational-integration`), no contra memoria de sesión.

**HU/capacidad:** integra `predictive-modeling` (bundles operativos v2, `backend/app/routers/producer_v2.py`) con `experiment-runner` (familias de `controlled_daily_v4`). Trazabilidad detallada en la sección 10.

**Fase CRISP-DM:** despliegue (Hito 1: contrato técnico verificable); planificación de modelado (Hito 2: plan, sin ejecución).

**Autorización:** amplía explícitamente el objetivo original del Trabajo Final (integrar el ensamble con el backend/UI; la UI se implementa después, sobre este contrato), instrucción directa del usuario en esta sesión, posterior al cierre técnico preparatorio de PR #216 (mergeado, SHA `0b9d25a3bc6a3cf00c9964f7afcb50202181b40f`, CI verde).

## 1. Objetivo, alcance y los dos hitos

**Objetivo de este cambio:** dejar un contrato técnico operativo, probado, que permita evaluar el ensamble de tres familias (regresión logística, Random Forest, HistGradientBoosting) con una política de acuerdo explícita — **sin** reingeniería del backend existente y **sin** ejecutar ningún entrenamiento real.

**Hito 1 no cierra el objetivo del ensamble operativo real.** Cubre exactamente:
1. **Single-model disponible** — comportamiento actual, sin cambios, para cualquier sensor sin configuración de ensamble.
2. **Ensemble configurado pero `unavailable`** — cuando hay evidencia de intención de ensamble (sección 3.1) pero los artefactos están incompletos/inválidos/ausentes (que es el caso de todo sensor real hoy, sección 2).
3. **Integración probada con datos sintéticos** — el contrato de código completo (carga, agregación, persistencia, HTTP) verificado con fixtures y con las tres familias reales de v4 ajustadas sobre datos sintéticos (sección 6).

**Hito 2 (sección 7) es exclusivamente un documento de planificación, sin ejecutar nada.** Su ejecución posterior (con las autorizaciones que correspondan) es la única vía hacia el cuarto estado, **fuera de alcance de este cambio**:
4. **Ensemble habilitado con artefactos reales admisibles** — no alcanzado por este trabajo.

**Fuera de alcance de este cambio (explícito):**
- La UI.
- `historical_replay`/`replay_packages/` — estructuralmente inalcanzable desde este cambio.
- Optimización de umbrales.
- Cualquier entrenamiento sobre datos reales, experimento A/B/C, apertura de holdout.
- Recalibración del ensamble — este trabajo no introduce ningún mecanismo que reajuste pesos, umbrales o calibradores a partir de feedback; el feedback existente (`ReviewCreate`) sigue siendo validación humana informativa, igual que hoy.
- `controlled_daily_v3`, memoria técnica existente más allá de lo señalado en la sección 8.

## 2. Hallazgo de inventario (resumen — investigación completa ya realizada; no se repite)

**No se encontraron artefactos v4 utilizables en las ubicaciones inspeccionadas** (git; 2 MLflow — sin experimentos/modelos de v4; 2 buckets MinIO — sin objetos `v4`/`joblib`; 3 contenedores con bundles reales en `/workspace/data/operational_bundles/` — son del pipeline legacy v3 de un solo modelo, no de las tres familias de v4; CI `experiment-v4-container` — efímero, sin persistencia). **Esto no demuestra que v4 nunca se haya ejecutado en ningún otro lugar** — no se pudo inspeccionar almacenamiento externo a esta máquina, y "no encontrado en lo inspeccionado" no equivale a "nunca ejecutado". El Hito 2 (sección 7) exige verificar antecedentes adicionales antes de proponer repetir cualquier experimento.

`controlled_daily_v4` nunca serializa un estimador ajustado (decisión de diseño explícita, hallazgo H-05 de una auditoría previa): solo persiste `frozen_config.json` y evidencia JSON/CSV. Reconstruir un modelo real exige refit vía `freezing.fit_final_estimator` sobre el mismo `eligible_frame`.

## 3. Hito 1 — Integración técnica

### 3.1 Activación y distinción single-model / ensemble incompleto (sin fallback silencioso)

**Señal de intención de ensamble = existe `.../horizon_<h>/ensemble/` O existe `.../horizon_<h>/ensemble_manifest.json`** (unión de ambas condiciones — cualquiera de las dos, sola, ya es evidencia de intención). Verificado: no existe hoy ningún mecanismo de configuración por sensor reutilizable (`src/data_ingestion/catalog.py::CatalogRepository` solo guarda sector/cultivo); se reutiliza la convención de rutas ya existente (`PRODUCER_BUNDLE_ROOT/<sensor_id>/horizon_<h>/`), extendida un nivel — sin eje de configuración nuevo.

- **Ninguna de las dos existe** → single-model intencional. Camino actual exacto, sin ninguna verificación adicional.
- **Cualquiera de las dos existe**, y la estructura completa (manifiesto válido + 3 familias cargables + cross-checks de 3.2) no valida en su totalidad → `unavailable`, con `reason_code` específico (ver 3.4). **Nunca** se cae al bundle single-model que pudiera existir en la misma ruta de horizonte, **nunca** se recalculan pesos sobre las familias disponibles.

**Límite documentado explícitamente:** esta convención no puede distinguir "nunca configurado" de "configurado y luego se eliminaron `ensemble/` y `ensemble_manifest.json` a la vez" — ambos casos se ven idénticos (ninguna señal presente) y ambos producen single-model. Se documenta como limitación conocida del mecanismo de detección, no como comportamiento a corregir en este cambio.

**Propagación de errores por componente, sin bloquear otros horizontes:** `load_ensemble_bundle`/`predict_ensemble_bundle` (3.2, 3.3) capturan cualquier `BundleUnavailable` que levante `load_operational_bundle`/`predict_operational_bundle` para una familia individual, preservando **familia y causa exactas** (`reason_code` de `BundleUnavailable`, ej. `"model_not_available_at_date"`, `"incompatible_model"`, `"incompatible_features"`) en un `reason_code` compuesto (ej. `"ensemble_component_unavailable:random_forest:model_not_available_at_date"`). Esto ocurre **dentro del mismo bucle por horizonte que ya existe** en `producer_emission.py` (cada horizonte 1/2/3 se resuelve independientemente hoy) — una falla de ensamble en horizonte 2 no impide resolver 1 y 3 con su propio resultado (single-model, ensemble disponible, o unavailable, según corresponda a cada uno).

### 3.2 Contrato común, compatibilidad y temporalidad

`src/predictive_modeling/ensemble_bundle.py` (nuevo módulo). `is_ensemble_configured(bundle_root, *, sensor_id, horizon) -> bool` implementa exactamente la señal de 3.1 (existencia de `ensemble/` o `ensemble_manifest.json`) — única función que decide entre los dos caminos en 3.4.

`load_ensemble_bundle(bundle_root, *, sensor_id, horizon) -> EnsembleBundle` — llamada solo cuando `is_ensemble_configured` ya dio `True`; nunca devuelve `None`, o devuelve un `EnsembleBundle` válido o lanza una excepción tipada:

1. **Manifiesto** — leer `ensemble_manifest.json`; ausente o JSON inválido → `EnsembleManifestMissingError`/`EnsembleManifestInvalidError`. Validar: `format_version==1`, `mode=="ensemble"`, `sensor_id`/`horizon_days` coinciden con los parámetros, `policy_version` en `{"ensemble_agreement_v1"}` (conjunto soportado; una versión futura no reconocida falla explícitamente, nunca se interpreta como la actual), `families` es **exactamente** el conjunto `{logistic_regression, random_forest, hist_gradient_boosting_classifier}` (ni de más ni de menos, sin duplicados), `weights` son exactamente `1/3` para cada una (uniformes; un manifiesto con pesos distintos falla — este diseño no admite otra ponderación bajo `ensemble_agreement_v1`).
2. **Correspondencia manifiesto↔componentes** — para cada familia declarada debe existir `.../ensemble/<family>/` con los 4 archivos del bundle v2; un directorio de familia sobrante (no declarada en `families`) o faltante (declarada pero sin directorio) → `EnsembleComponentMissingError` con la familia exacta.
3. **Carga por familia** — `load_operational_bundle(bundle_root/sensor_id/f"horizon_{horizon}/ensemble/{family}", sensor_id=sensor_id, horizon=horizon)` **sin modificar esa función**. Cualquier `BundleUnavailable` se recolecta con la familia (3.1).
4. **Verificación cruzada entre las 3 familias ya cargadas** (lo que `load_operational_bundle` no puede ver por validar un solo bundle a la vez) — deben coincidir exactamente en:
   - `sensor_id`, `horizon_days`, `contract_version`, `decision_threshold` (ya contemplado).
   - **Mismo evento**: `contract["event"]["variable"]`, `["threshold"]`, `["unit"]`, `["comparison"]` — los 4 campos exactos que ya persiste `HorizonContract.to_dict()` (`src/predictive_modeling/operational_contract.py`), mismo patrón que `validate_horizon_contract_family` ya usa para comparar horizontes de una sola familia.
   - **Misma semántica de clase positiva**: cada componente ya fue validado por `load_operational_bundle` con `classes_ == [0, 1]` — la verificación cruzada solo confirma que los 3 pasaron ese chequeo (no hay nada adicional que comparar entre familias, la semántica ya es uniforme por construcción del loader existente).
   - **Preparación compatible**: `feature_columns`, `feature_names` (nombres **y orden**), `lags`, `rolling_windows`, `imputation` (`contract["imputation"]`) y `variables` (lista de `{name, unit}`) idénticos entre los 3 `bundle.json`.
   
   Cualquier discrepancia → `EnsembleBundleIncompatible` con el campo exacto y los valores en conflicto (ej. `"event.threshold: 0.30 (logistic_regression) != 0.28 (random_forest)"`).
5. **Temporalidad** — se reutiliza exactamente la validación ya existente en `predict_operational_bundle` (`operational_inference.py:146-151`, verificado): `max(trained_through, calibrated_through) <= as_of_date`, aplicada sin cambios por cada componente al momento de predecir (3.3). `load_ensemble_bundle` en sí no valida temporalidad (esa lógica vive en la predicción, igual que en el camino single-model); **se conservan ambas fechas por componente** (`trained_through` y `calibrated_through`, nunca conflar una con otra) en el detalle persistido (3.5).

`EnsembleBundle` (`@dataclass(frozen=True)`): `manifest: dict`, `components: dict[str, OperationalBundle]`.

### 3.3 Predicción y agregación — umbrales, comparador, calibración

`predict_ensemble_bundle(ensemble, dataframe, *, sensor_id, units, as_of_date) -> dict`. Llama a `predict_operational_bundle` (sin modificar) una vez por familia — el corte causal y el chequeo temporal ya existentes en esa función se reutilizan sin cambios para cada componente.

**Precisión exacta (verificada, `operational_inference.py:171,178-186`):**
- Cada componente produce `score = positive_probability(bundle.calibrator, row)` — siempre calibrado (`score_kind` interno siempre `"calibrated_probability"`; no existe hoy ningún camino que produzca `"raw_model_score"`).
- Voto individual, ya existente sin cambios: `alert = score >= decision_threshold` (comparador **`>=`**, línea 181), con el `decision_threshold` propio de ese bundle (validado idéntico entre los 3 en 3.2.4).
- `decision_threshold=0.5` para esta versión de política (`ensemble_agreement_v1`): **política operativa heredada, no umbral validado científicamente** para ninguna de las 3 familias ni para el ensamble — cita textual ya presente en el código (`operational_run_artifacts.py`): "0.5 is the existing operational alert threshold; never selected on test". El mismo comparador `>=` se usa para individual y combinado — nunca dos criterios distintos.

**Campos derivados — cuatro, siempre separados, nunca combinados entre sí. Sin redondeo antes de decidir; las 3 probabilidades de entrada son finitas en `[0,1]` (ya garantizado por la validación de `load_operational_bundle`):**
- `combined_probability`: promedio aritmético de las 3 probabilidades calibradas, pesos fijos `1/3`.
- `combined_alert`: `combined_probability >= decision_threshold` — mismo comparador, mismo umbral ya validado idéntico entre las 3.
- `positive_votes`: cuenta de componentes con `alert=True` (voto propio, ya calculado por `predict_operational_bundle`).
- `agreement_category`: `3→"alerta_por_unanimidad"`, `2→"posible_alerta_acuerdo_parcial"`, `1→"sin_alerta_por_mayoria_con_discrepancia"`, `0→"sin_alerta_por_unanimidad"`.

**Casos de prueba inequívocos, exactos (sin redondear), a implementar literalmente:**
- `0.51, 0.51, 0.01` → `positive_votes=2` (`0.51>=0.5`, `0.51>=0.5`, `0.01<0.5`), `agreement_category="posible_alerta_acuerdo_parcial"`, `combined_probability = 1.03/3 = 0.3433333...`, `combined_alert=False` — **discrepancia: mayoría dice posible alerta, combinada dice que no.**
- `0.99, 0.49, 0.49` → `positive_votes=1` (`0.99>=0.5`, ambos `0.49<0.5`), `agreement_category="sin_alerta_por_mayoria_con_discrepancia"`, `combined_probability = 1.97/3 = 0.6566666...`, `combined_alert=True` — **discrepancia en la otra dirección: minoría, pero combinada dice alerta.**

También probar límites individuales (una probabilidad exactamente `0.5`) y del promedio (`combined_probability` exactamente `0.5`).

**Fechas agregadas — no conflar `trained_through` con `calibrated_through`:**
- `trained_through` agregado = **máximo** de los `trained_through` de los 3 componentes (no el mínimo). Este valor pasa a `model_reference.trained_through` en la respuesta combinada.
- `calibrated_through` agregado = **máximo** de los `calibrated_through` de los 3 componentes — campo separado, expuesto en `EnsembleDetail.calibrated_through` (no existe en `ModelReference` hoy; ver 3.5).
- Ambas fechas se conservan además **por componente**, sin agregar, en `EnsembleDetail.components[i]` (ver 3.5).

**`score_kind` del agregado — resuelto explícitamente:** el esquema actual (`schemas_v2.py::ForecastResponse.score_kind`) solo admite `Literal["raw_model_score", "calibrated_probability"]`. Un promedio de 3 probabilidades ya calibradas **no es** un puntaje crudo, pero tampoco acredita que el promedio en sí esté calibrado (no hay evidencia de eso). Se extiende el `Literal` con un tercer valor explícito: `"ensemble_mean_of_calibrated_components"` — aditivo, no reemplaza ni reinterpreta los dos valores existentes. `score_kind` en la respuesta combinada es siempre este tercer valor cuando el modo ensamble está activo; nunca `"calibrated_probability"` (evitaría implicar una calibración del agregado que no existe) ni `"raw_model_score"` (sería falso, las entradas sí están calibradas).

**Presentación de probabilidad — sin habilitar nada nuevo:** verificado que `predict_operational_bundle` hoy retorna, **sin ninguna condición** (`operational_inference.py:178-186`, una única rama, sin `if`/`else`): `display_probability=None`, `probability_status="not_qualified"`, `probability_reason_code="incompatible_assessment"`, siempre, para cualquier bundle. El camino ensamble **reutiliza exactamente estos mismos tres valores literales, sin ninguna lógica de calificación nueva** — agregar el ensamble no habilita ningún porcentaje al productor que no existiera antes. Si en el futuro se implementa el "adaptador de evaluación/dominio" que el docstring de `operational_inference.py` menciona como pendiente, se aplicará igual a single-model y a ensemble; no es parte de este cambio.

### 3.4 Integración en el punto único existente

`producer_emission.py::emit_forecasts` (o la función interna que resuelve un horizonte) — antes de llamar a `load_operational_bundle`:
```
if is_ensemble_configured(bundle_root, sensor_id=sensor_id, horizon=horizon):
    # exclusivamente load_ensemble_bundle / predict_ensemble_bundle;
    # cualquier excepción -> SlotSeed(status="unavailable", reason_code=<causa exacta>)
    # NUNCA se reintenta con load_operational_bundle sobre la misma ruta de horizonte
else:
    # camino actual, exacto, sin cambios
```
Ambos caminos conviven en la misma función, sin pipeline paralelo ni backend duplicado. Se preserva el comportamiento ya existente de que la ausencia/no-disponibilidad de un horizonte no impide resolver los otros (3.1).

**No se recalculan slots ya disponibles al activar el ensamble:** `emit_snapshot`/`record_batch` ya resuelven, antes de predecir, qué horizontes están "missing" para el `as_of_date` dado (patrón existente: solo se predice lo ausente; lo ya emitido se preserva). Si un sensor tiene un slot single-model ya persistido para `(as_of_date, horizon)` y luego se configura `ensemble/` para ese sensor/horizonte, una nueva emisión para la **misma** `(as_of_date, horizon)` encuentra el slot ya presente y **no lo recalcula, no lo reemplaza, no cambia su `forecast_id`** — la transición a ensamble solo afecta emisiones **nuevas** (fechas/horizontes todavía no resueltos). Se agrega un test explícito para esto (3.6).

### 3.5 Identidad, esquema de respuesta y persistencia

**Identidad determinista del ensamble (nueva; la versión de política, por sí sola, no identifica los artefactos concretos):**
```python
def compute_ensemble_identity(manifest: dict, components: dict[str, OperationalBundle]) -> str:
    payload = {
        "policy_version": manifest["policy_version"],
        "weights": manifest["weights"],
        "components": {
            family: {
                "model_sha256": bundle.metadata["files"]["model.joblib"],
                "calibrator_sha256": bundle.metadata["files"]["calibrator.joblib"],
            }
            for family, bundle in sorted(components.items())
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
```
Este hash es `ensemble_identity_sha256` — identifica exactamente qué 3 artefactos concretos (por su propio sha256, ya presente en cada `bundle.json["files"]`) y qué política se usaron. Dos ensambles con la misma política pero un modelo distinto tienen identidades distintas.

**`schemas_v2.py` (aditivo):**
```python
class EnsembleComponentVote(StrictModel):
    family: Literal["logistic_regression", "random_forest", "hist_gradient_boosting_classifier"]
    model_reference: ModelReference
    calibrated_through: date
    score: float
    decision_threshold: float
    alert: bool

class EnsembleDetail(StrictModel):
    policy_version: str
    ensemble_identity_sha256: str
    components: list[EnsembleComponentVote]
    combined_probability: float
    combined_alert: bool
    positive_votes: int
    agreement_category: Literal[
        "alerta_por_unanimidad",
        "posible_alerta_acuerdo_parcial",
        "sin_alerta_por_mayoria_con_discrepancia",
        "sin_alerta_por_unanimidad",
    ]
    calibrated_through: date  # máximo agregado — separado de model_reference.trained_through
```
`ModelReference` gana un campo aditivo `calibrated_through: date | None = None` (para exponerlo por componente sin duplicar el tipo; en single-model queda `None`, sin tocar `predict_operational_bundle`).
`ForecastResponse` gana `ensemble: EnsembleDetail | None = None` — `None` cuando el sensor/horizonte no está en modo ensamble. `score_kind` gana el tercer valor de 3.3.

Cuando el ensamble está activo, los campos de nivel superior existentes se completan **desde la vista combinada** (nunca desde el voto): `alert=combined_alert`, `score=combined_probability`, `score_kind="ensemble_mean_of_calibrated_components"`, `model_reference.model_version=ensemble_identity_sha256`, `model_reference.trained_through=`máximo agregado (3.3), `model_reference.calibration_version=None` (no hay una única versión de calibración con 3 calibradores distintos — el detalle real vive en `ensemble.components[i].model_reference.calibration_version`, sin perderse), `model_reference.calibrated_through=None` a nivel superior (el agregado vive en `EnsembleDetail.calibrated_through`, para no duplicar semántica en dos lugares). Así los consumidores existentes siguen funcionando sin cambios; el detalle completo vive en `ensemble`.

**Persistencia (`src/human_feedback/operational_repository.py`) — todo aditivo, con lectura retrocompatible:**

`SlotSeed` gana (todos opcionales, `None` por defecto):
```python
ensemble_policy_version: str | None = None
ensemble_identity_sha256: str | None = None
ensemble_components: list[dict[str, Any]] | None = None
ensemble_combined_probability: float | None = None
ensemble_combined_alert: bool | None = None
ensemble_positive_votes: int | None = None
ensemble_agreement_category: str | None = None
ensemble_calibrated_through: str | None = None
```
Nuevo invariante en `__post_init__`: o los 8 campos son `None` juntos, o están presentes juntos; y si están presentes, `self.alert == self.ensemble_combined_alert` y `self.score == self.ensemble_combined_probability` (coherencia entre la vista combinada de nivel superior y el detalle — nunca deben divergir).

**Sitios de persistencia/lectura que deben incluir estos campos (los 5 puntos exigidos explícitamente):**
1. **`request_payload` de idempotencia** (`record_batch`, `operational_repository.py:263-286` — construcción literal del dict por slot, verificada): agregar los 8 campos `ensemble_*` al dict por slot que ya se serializa y hashea (`_request_hash`). Sin este cambio, dos emisiones con el mismo `as_of_date`/`snapshot_id` pero composición de ensamble distinta no se detectarían como conflicto de idempotencia — con el cambio, sí (el hash cambia si cambia cualquier campo de ensamble).
2. **`forecast_record`** (`operational_repository.py:332-352` — construcción literal, verificada): agregar los mismos 8 campos.
3. **`_render_forecast`** (`operational_repository.py:592-627` — verificada, alimenta emisión, listado y consulta individual por ser la única función de renderizado): agregar los mismos 8 campos usando `forecast.get("ensemble_policy_version")` etc. (con `.get`, **nunca** acceso directo `forecast["..."]`) — **los registros persistidos antes de este cambio no tienen estas claves; deben seguir siendo legibles**, devolviendo `ensemble=None` en la respuesta para esos registros antiguos.
4. **`input_snapshot`** (`operational_repository.py:442-455`, `producer_emission.py:97` — verificado: `captured["artifact"].setdefault("bundles", {})[str(horizon)] = bundle.metadata`, un bundle por horizonte hoy): cuando el horizonte está en modo ensamble, ese valor pasa a ser `{"mode": "ensemble", "ensemble_manifest": manifest, "components": {family: component.metadata for family, component in ...}}` en lugar del `bundle.metadata` plano de un solo bundle — mismo lugar (`bundles[str(horizon)]`), forma enriquecida. Un lector que no conozca `"mode"` sigue viendo un dict válido; no se restructura el nivel superior de `input_snapshot`.
5. **Respuesta HTTP de emisión, listado y consulta individual**: las 3 usan `_render_forecast` (punto 3) — un solo cambio cubre las 3 superficies.

**Replay idempotente y resultados originales inmutables:** sin cambios de comportamiento — el hash de idempotencia (punto 1) ahora también protege la composición del ensamble; los registros ya persistidos nunca se sobrescriben por una reemisión con el mismo `as_of_date`/horizonte (3.4).

### 3.6 API real y feedback

**Ruta real, verificada (no la ruta ficticia usada en una revisión anterior de este documento):** `POST /api/v2/sensors/{sensor_id}/forecasts` (`backend/app/routers/producer_v2.py:380-385`, montado sin prefijo adicional en `backend/app/main.py:152`, prefijo del router `/api/v2`). También `GET /api/v2/sensors/{sensor_id}/forecasts` (listado) y `GET /api/v2/sensors/{sensor_id}/forecasts/{forecast_id}` (individual) — ambas renderizan vía `_render_forecast` (3.5), sin necesitar cambios propios más allá de que el modelo de respuesta acepte el campo `ensemble` nuevo.

**Feedback (`POST /api/v2/sensors/{sensor_id}/forecasts/{forecast_id}/reviews`, `ReviewCreate`):** verificado — no recibe `alert` en el request; la revisión usa el `alert` **ya persistido** del forecast (`operational_repository.py:706`: `observed_label = forecast["alert"] if action == "confirm" else not forecast["alert"]`). En modo ensamble, `forecast["alert"]` es exactamente `combined_alert` (3.5) — **confirmar/rechazar valida la decisión binaria combinada, nunca la categoría de acuerdo por votos.** Sin cambios de código en el router de reviews: esto ya funciona correctamente en cuanto `forecast["alert"]` se llena con `combined_alert` (3.5). Test explícito con un caso de discrepancia: usar el caso `0.99, 0.49, 0.49` (3.3) — `combined_alert=True` pero `agreement_category="sin_alerta_por_mayoria_con_discrepancia"` (voto minoritario) — confirmar ese forecast y verificar `observed_label=True` (coincide con `combined_alert`, no con lo que sugeriría la categoría de mayoría).

**Sin recalibración:** ningún camino de este cambio ajusta pesos, umbrales o calibradores a partir de `ReviewCreate` ni de ningún otro feedback — se declara explícitamente en el PR para no sugerir lo contrario.

### 3.7 Compatibilidad de las tres familias — el problema de `feature_names_in_`

**Hallazgo verificado, crítico para que las 3 familias sean cargables por `load_operational_bundle` sin modificarlo:**
- `load_operational_bundle` exige `estimator.feature_names_in_ == metadata["feature_names"]` para **modelo y calibrador** (`operational_inference.py:108-113`) — atributo que scikit-learn solo autopuebla cuando `.fit()` recibe un `DataFrame` (con `.columns`).
- El pipeline v2/v3 existente ya cumple esto porque `operational_run.py::fit_seed` ajusta con `X_train = train[list(feature_columns)]` (**DataFrame**, sin `.to_numpy()`), verificado línea por línea.
- `controlled_daily_v4` ajusta con `X = eligible_frame[list(FEATURE_COLUMNS)].to_numpy()` (**ndarray**, verificado en `freezing.py`, `tuning.py`, y los 3 stage runners, para las 3 familias y para las bases del `SoftVotingClassifier`) — **deliberado y congelado**, no se modifica.
- `ScaledLogisticRegression.fit` (`models.py:131-159`) solo asigna `self.classes_`, nunca `feature_names_in_`.
- Verificado en todo el repo: no existe **ningún código de producción** que reasigne `feature_names_in_`/`classes_` a un estimador ya ajustado sobre un array — las únicas dos ocurrencias de esa asignación son fixtures de test (`backend/tests/test_pipeline.py:21`, `tests/test_architecture_integration_pipeline.py:67`), que fabrican objetos falsos para pruebas aisladas, no modelos reales.

**Resolución — adaptador mínimo de empaquetado, sin alterar la lógica experimental congelada ni falsear metadatos:**
Nuevo módulo pequeño `src/predictive_modeling/bundle_packaging.py::attach_feature_names(estimator, feature_columns: list[str]) -> None` — asigna `estimator.feature_names_in_ = np.array(feature_columns, dtype=object)` sobre un estimador **ya ajustado** (modelo o calibrador), reconstruyendo el atributo que sklearn hubiera puesto solo si el `.fit()` hubiera recibido un DataFrame. **Esto no es falsificar metadatos**: el estimador efectivamente fue ajustado con esas columnas, en ese orden exacto (`eligible_frame[list(FEATURE_COLUMNS)].to_numpy()` preserva el orden de `FEATURE_COLUMNS`) — solo se restituye el atributo convencional que el camino de ajuste por array no generó automáticamente. **Se aplica exclusivamente en tiempo de empaquetado** (al construir un bundle, nunca dentro de `controlled_daily_v4`, `freezing.py`, `tuning.py` ni los stage runners, que permanecen sin ningún cambio) — usado tanto por los fixtures de prueba de este Hito 1 (3.8) como, en el futuro, por el pipeline de empaquetado real que Hito 2 (sección 7) debe especificar.

### 3.8 Pruebas (Hito 1)

**Dos niveles, explícitamente distintos y ambos requeridos:**

**Nivel 1 — dobles controlados**, para los casos exactos de probabilidad (3.3): estimadores/calibradores *stub* (no `sklearn` real) que devuelven probabilidades fijas — rápido, determinístico, para fijar exactamente las 4 combinaciones de voto (3/3, 2/3, 1/3, 0/3), los dos casos de discrepancia promedio/mayoría (`0.51,0.51,0.01` y `0.99,0.49,0.49`), límites individuales y del promedio en `0.5`, componente faltante, componente con contrato incompatible (evento distinto, `decision_threshold` distinto, `feature_names` en otro orden), fallo de admisibilidad temporal, y el caso de "slot ya disponible no se recalcula" (3.4).

**Nivel 2 — integración con las tres familias reales de v4 ajustadas sobre datos sintéticos**, con calibradores reales y serialización/carga real a través de `load_ensemble_bundle`/`load_operational_bundle` sin mocks: instanciar y ajustar **las 3 clases reales** (`ScaledLogisticRegression`, `sklearn.ensemble.RandomForestClassifier`, `sklearn.ensemble.HistGradientBoostingClassifier`, vía `controlled_daily_v4.models.build_estimator`/`fit_estimator` reutilizados sin modificar) sobre un `eligible_frame` sintético pequeño y fijo (nunca datos reales, nunca Pergamino), aplicar `attach_feature_names` (3.7) a cada modelo y calibrador antes de serializar con `joblib.dump`, y verificar que el bundle resultante carga y predice correctamente por el camino real. **Nunca tres copias de `RandomForestClassifier` renombradas como si fueran las 3 familias** — deben ser instancias reales y distintas de las 3 clases. Este ajuste es sintético, acotado, y **parte de las pruebas**: no autoriza entrenamiento con datos reales, A/B/C, ni holdouts, y no valida científicamente a v4 (una corrida sintética no es un resultado de investigación).

**Test de integración HTTP de punta a punta**, contra `POST /api/v2/sensors/{sensor_id}/forecasts` (3.6), con fixtures del nivel 1 o 2 montadas en un `bundle_root` temporal.

**Compatibilidad/regresión:** sensores/horizontes sin `ensemble/` ni `ensemble_manifest.json` producen exactamente la misma respuesta que hoy — test de regresión explícito, sobre el camino HTTP real, no solo a nivel de función.

**Identificar qué se verificó con artefactos reales de v4: nada** — no existen (sección 2); se documenta como limitación, no como cobertura lograda.

## 4. Documentación y trazabilidad a actualizar

- `openspec/specs/predictive-modeling/spec.md`: nuevo requirement para el modo ensamble, marcado `[implementado, verificado con fixtures y con las 3 familias ajustadas sobre datos sintéticos — sin artefactos reales]`.
- `openspec/specs/experiment-runner/spec.md`: nota cruzada — el contrato operativo existe y está probado; los artefactos reales de v4 siguen sin producirse (Hito 2).
- Capítulo 3 (memoria técnica): describir la política de acuerdo como una decisión de arquitectura de esta integración, explícitamente separada de los resultados científicos de v4 ya reportados (Stage A/B sintéticos). **No se modifica la memoria técnica existente más allá de agregar esta sección nueva; no se atribuye a esta integración ningún resultado científico previo.**

## 5. Restricciones globales (heredadas)

- No modificar `_verify_file_integrity`/`_sha256_of` ni ningún archivo bajo `replay_packages/`.
- No modificar `load_operational_bundle`/`predict_operational_bundle`, ni `freezing.py`/`tuning.py`/los stage runners de `controlled_daily_v4` — solo reutilizarlos.
- No introducir un nuevo mecanismo de umbral; reutilizar `decision_threshold` existente (0.5, política no validada científicamente, documentado como tal).
- No renormalizar pesos ante componentes faltantes.
- No conflar probabilidad combinada con conteo de votos, ni `trained_through` con `calibrated_through`, en ningún campo.
- No habilitar `display_probability`/`probability_status` distinto de lo que ya produce el código hoy.
- No tocar UI, `controlled_daily_v3`, ni memoria técnica más allá de la sección 4.
- No entrenar con datos reales, no ejecutar A/B/C, no abrir holdout, no recalibrar el ensamble.

## 6. Foco de revisión

- Redondeo de punto flotante exactamente en el límite del umbral — verificar `>=` consistente en los 3 componentes y en la combinada, con los casos exactos de 3.3.
- `policy_version` no reconocida (futura) — debe fallar explícitamente.
- Coherencia entre campos de nivel superior (`alert`, `score`) y el detalle `ensemble_*` persistido — nunca deben divergir (invariante de `SlotSeed.__post_init__`).
- Lectura de un registro persistido **antes** de este cambio (sin ninguna clave `ensemble_*`) — debe renderizar `ensemble=None` sin `KeyError`.
- El caso de discrepancia `0.99, 0.49, 0.49` en el flujo de feedback (3.6) — confirmar que valida `combined_alert`, no la categoría.
- Activar `ensemble/` para un sensor con un slot single-model ya emitido para la misma fecha/horizonte — ese slot no debe recalcularse ni cambiar de `forecast_id` (3.4).

## 7. Hito 2 — Plan de habilitación real (documentar; NO ejecutar)

Documento separado `docs/design/ensemble-real-enablement-plan.md`, sin ejecutar nada. **Antes de proponer repetir cualquier experimento, debe verificar antecedentes**: la sección 2 de este documento certifica solo "no encontrado en lo inspeccionado en esta máquina" — el plan debe incluir, como primer paso explícito, consultar con quien tenga autoridad normativa (director/a de tesis, protocolo de cierre científico) si existe una corrida real de Stage A sobre Pergamino en algún lugar no inspeccionado, antes de plantear ejecutarla por primera vez. Cubrir:

- **Dataset:** Pergamino (`controlled_daily_v4_external_pergamino`), fingerprint/hash verificable.
- **Particiones temporales:** Stage A → Stage B (2023) → Stage C (2024-2025), sin alterar los cortes existentes.
- **Entrenamiento:** Stage A real (nunca hecho, solo sintético hoy) para obtener `frozen_config.json` real; refit vía `freezing.fit_final_estimator` por familia sobre el `eligible_frame` real; empaquetado real usando el adaptador de 3.7 (sin alterar la lógica congelada).
- **Calibración:** método/partición de calibración por familia, coherente con el patrón ya usado por `operational_run.py`.
- **Umbrales:** confirmar `decision_threshold=0.5` sin optimizar, documentado como no-tuneado.
- **Horizontes compatibles:** verificar cuáles de horizonte 1/2/3 tienen soporte real en v4 (no asumir que los 3 existen igual que en v2).
- **Período admisible para demostración histórica:** ventana causalmente válida para una demo tipo `historical_replay`, sin tocar `replay_packages/` ni mezclar este ensamble con el paquete `base-seed4` custodiado.
- **Autorizaciones científicas requeridas:** rol/autoridad que debe aprobar Stage A real sobre Pergamino (protocolo de cierre científico, `openspec/scientific-closure/`), y diferencias respecto del protocolo v3/v4 vigente (v4 nunca se ejecutó sobre datos reales con fines operativos, no solo científicos — decisión que excede este cambio).
- Los cuatro estados de la sección 1, explícitamente diferenciados en el documento, para que quede claro cuál de ellos deja resuelto cada paso del plan.

## 8. Plan de implementación (Hito 1)

Ver documento separado `docs/superpowers/plans/2026-09-25-ensemble-operational-integration-plan.md` (mismo commit). Tareas, archivos, dependencias y pruebas de aceptación concretas — no se duplican aquí.

## 9. Autorrevisión

- Sin placeholders. Toda cita de código verificada contra el árbol actual (no memoria de sesión anterior).
- Consistencia de nombres: `combined_probability`, `combined_alert`, `positive_votes`, `agreement_category`, `ensemble_identity_sha256` usados idénticamente en 3.3, 3.5, 3.6 y en el plan (sección 8).
- Contradicciones resueltas respecto de la revisión anterior (`5c2eff9`): ruta HTTP corregida a la real; `trained_through` agregado corregido a máximo (no mínimo); `score_kind` del agregado resuelto explícitamente con un tercer valor; identidad del ensamble corregida a un hash determinista (no `"ensemble/<policy_version>"`); agregado el adaptador `attach_feature_names` para resolver la incompatibilidad real de las 3 familias con el loader v2; agregada la propagación de errores por componente sin bloquear otros horizontes; agregado el invariante de no-recálculo de slots ya disponibles.

## 10. Trazabilidad

- **HU:** integra `predictive-modeling` (HU4) y `experiment-runner` (HU7), expuesto para consumo futuro por `alerting-ui`.
- **Impacto en configuración experimental:** ninguno — no se ejecuta ningún experimento; Hito 2 es un plan, no una ejecución.
- **Impacto en hipótesis/alcance/arquitectura:** ampliación explícita y autorizada del alcance original, con advertencia explícita del usuario en esta sesión.
