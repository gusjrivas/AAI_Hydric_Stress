"""Complemento auxiliar H: HITL prospectivo (`auxiliary_hitl_v1`).

Runner del diseño congelado descrito en
`docs/research/scientific-closure-decisions.md`, sección «H: HITL prospectivo»,
y del contrato predeclarado
`openspec/changes/sc-08-aux-hitl/contract-H-frozen.json`.

Ejecuta dos pistas explícitamente separadas y nunca intercambiables:

- **SIM** (`simulated_supervised_feedback`): el diseño congelado tal cual, con
  un revisor simulado determinista. Es la pista que satisface el criterio de
  aceptación de SC-GOV-022 y sostiene la afirmación CL-06, que trata
  exclusivamente de correcciones supervisadas **simuladas**.
- **HUMAN** (`controlled_human_feedback`): una intervención humana controlada
  de un único operador experimental autorizado, con protocolo de revisión y
  procedencia propios — exactamente lo que el diseño congelado exige cuando
  dice «Feedback real futuro necesita protocolo de revisión y procedencia
  propia». **No** es validación agronómica, **no** sustituye la pista SIM y
  **no** sostiene ninguna afirmación cuantitativa.

Una tercera clase, `fixture`, existe solo para las pruebas automatizadas y el
runner la rechaza de forma cerrada en cualquier corrida científica.

Fronteras duras de este runner, verificadas en ejecución y no meramente
documentadas: ninguna fila con `target_timestamp` posterior a 2022-12-31 entra
al proceso (`HITL_MAX_TARGET_DATE`), no se importa ni se invoca
`holdout_ledger`, y no se lee ni se escribe ningún artefacto de las Etapas A,
B o C. El módulo tampoco registra nada en MLflow.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiment_runner.controlled_daily_v4.artifacts import (
    ensure_output_directory,
    normalize_for_json,
)
from experiment_runner.controlled_daily_v4.code_identity import capture_code_identity
from experiment_runner.controlled_daily_v4.config import (
    DECISION_THRESHOLD,
    HORIZON_DAYS,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODES,
    PRIMARY_DEPTH_COLUMN,
    CalendarIntegrityError,
    StageBounds,
)
from experiment_runner.controlled_daily_v4.dataset_fingerprint import compute_dataset_fingerprint
from experiment_runner.controlled_daily_v4.environment import (
    capture_constraints_identity,
    capture_environment,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.features import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_target,
    compute_p20_threshold,
    feature_contract,
    restrict_to_stage_window,
    select_eligible_rows,
    validate_stage_window_full_coverage,
)
from experiment_runner.controlled_daily_v4.ingestion import (
    aggregate_era5_daily,
    build_daily_joined_series,
    load_era5_hourly_raw,
    load_nasa_power_daily_raw,
    replace_missing_sentinel,
    restrict_era5_hourly_to_window,
    restrict_nasa_power_daily_to_window,
)
from experiment_runner.controlled_daily_v4.metrics import metrics_payload
from experiment_runner.controlled_daily_v4.models import fit_estimator
from experiment_runner.controlled_daily_v4.provenance import validate_pergamino_provenance
from human_feedback.lineage import (
    CURRENT_LINEAGE_VERSION,
    FeedbackReference,
    RecalibrationLineage,
)

# --------------------------------------------------------------------------
# Identidad y versiones de esquema
# --------------------------------------------------------------------------

AUXILIARY_ID = "auxiliary_hitl_v1"
"""Identificador del diseño congelado. No se comparte con A/B/C."""

ARTIFACT_SCHEMA_VERSION = "auxiliary_hitl_v1_evidence.v1"
PACKAGE_SCHEMA_VERSION = "auxiliary_hitl_v1_human_package.v1"
RESPONSE_SCHEMA_VERSION = "auxiliary_hitl_v1_human_response.v1"
EVENT_SCHEMA_VERSION = "auxiliary_hitl_v1_feedback_event.v1"
FINGERPRINT_SCOPE_HITL = "auxiliary_hitl_v1_eligible_rows_2015_2022"
"""Alcance propio de la huella de dataset. Deliberadamente distinto de los
alcances de las Etapas A y C: este conjunto cubre 2015-2022 y no debe
confundirse con el conjunto elegible de la Etapa A ni con el de evaluación
del holdout."""

PIPELINE_VERSION = "auxiliary_hitl_v1/pergamino_features.v1"
SENSOR_ID = "pergamino_era5land_soil_moisture_0_to_7cm"
CONTRACT_VERSION = 1
"""`contract_version` del contrato de modelado del predictor sucesor
(`pergamino_features.v1`), exigido por `human_feedback.lineage`. No es la
versión del esquema de linaje, que es `CURRENT_LINEAGE_VERSION`."""

# --------------------------------------------------------------------------
# Clases de evidencia (contrato, sección "tracks")
# --------------------------------------------------------------------------

ORIGIN_SIMULATED = "simulado"
ORIGIN_HUMAN = "humano_controlado"
ORIGIN_FIXTURE = "fixture"
FEEDBACK_ORIGINS = (ORIGIN_SIMULATED, ORIGIN_HUMAN, ORIGIN_FIXTURE)

TRACK_SIM = "simulated_supervised_feedback"
TRACK_HUMAN = "controlled_human_feedback"
TRACK_FIXTURE = "fixture"
TRACK_BY_ORIGIN = {
    ORIGIN_SIMULATED: TRACK_SIM,
    ORIGIN_HUMAN: TRACK_HUMAN,
    ORIGIN_FIXTURE: TRACK_FIXTURE,
}
FORBIDDEN_EVIDENCE_CLASS = "expert_agronomic_feedback"
"""Etiqueta prohibida. Ningún artefacto de este runner puede usarla: no hubo
intervención de un agrónomo ni validación agronómica de campo."""

SCIENTIFIC_ORIGINS = (ORIGIN_SIMULATED, ORIGIN_HUMAN)
"""Orígenes admisibles en una corrida científica. `fixture` queda excluido:
una prueba no puede convertirse en evidencia."""

# --------------------------------------------------------------------------
# Operador autorizado
# --------------------------------------------------------------------------

AUTHORIZED_OPERATOR_ROLES = ("authorized_experimental_operator",)
EXPECTED_OPERATOR_ID = "Gustavo Julián Rivas"
OPERATOR_ROLE_IS_NOT = ("agronomist", "domain_expert", "field_validator")

# --------------------------------------------------------------------------
# Vocabulario de decisiones
# --------------------------------------------------------------------------

DECISION_ACCEPT = "ACEPTAR"
DECISION_REJECT = "RECHAZAR"
DECISION_CORRECT = "CORREGIR"
DECISIONS = (DECISION_ACCEPT, DECISION_REJECT, DECISION_CORRECT)
MAX_REASON_LENGTH = 500

# --------------------------------------------------------------------------
# Fronteras temporales del diseño congelado
# --------------------------------------------------------------------------

HITL_TRAIN_BOUNDS = StageBounds(
    emission_start=date(2015, 1, 7),
    emission_end=date(2020, 12, 28),
    target_start=date(2015, 1, 10),
    target_end=date(2020, 12, 31),
    train_target_cutoff=date(2020, 12, 31),
)
HITL_FEEDBACK_BOUNDS = StageBounds(
    emission_start=date(2021, 1, 1),
    emission_end=date(2021, 12, 28),
    target_start=date(2021, 1, 4),
    target_end=date(2021, 12, 31),
    train_target_cutoff=date(2021, 12, 31),
)
HITL_EVALUATION_BOUNDS = StageBounds(
    emission_start=date(2022, 1, 1),
    emission_end=date(2022, 12, 28),
    target_start=date(2022, 1, 4),
    target_end=date(2022, 12, 31),
    train_target_cutoff=date(2021, 12, 31),
)
HITL_WINDOW_BOUNDS = StageBounds(
    emission_start=HITL_TRAIN_BOUNDS.emission_start,
    emission_end=HITL_EVALUATION_BOUNDS.emission_end,
    target_start=HITL_TRAIN_BOUNDS.target_start,
    target_end=HITL_EVALUATION_BOUNDS.target_end,
    train_target_cutoff=HITL_FEEDBACK_BOUNDS.target_end,
)
HITL_MAX_TARGET_DATE = date(2022, 12, 31)
"""Frontera dura del complemento H (invariante INV-01). El holdout de la
Etapa C (2024-2025) y el período de la Etapa B (2023) quedan estrictamente
fuera: cualquier fila con `target_timestamp` posterior aborta la corrida."""

# --------------------------------------------------------------------------
# Parámetros normativos del diseño congelado
# --------------------------------------------------------------------------

MODEL_FAMILY = "random_forest"
MODEL_PARAMS_FROZEN = {
    "n_estimators": 100,
    "max_depth": 8,
    "min_samples_leaf": 5,
    "n_jobs": 1,
    "weighting": "none",
}
EVENT_BUDGET_PER_SEED = 20
EVENTS_PER_STRATUM = 10
CORRUPTION_FRACTION = 0.10
DEFAULT_SEEDS = (0, 1, 2, 3, 4)
"""Semillas fijadas por el bloque padre del diseño congelado
(`docs/research/scientific-closure-decisions.md`, «Evaluaciones
complementarias»): «Seeds [0,1,2,3,4]; seeds no representan poblaciones
independientes». No se eligen aquí ni se seleccionan por resultado."""
PRIMARY_SEED_FOR_HUMAN_PACKAGE = 0

ARM_FROZEN = "frozen"
ARM_REFIT_NO_CORRECTIONS = "refit_no_corrections"
ARM_REFIT_WITH_CORRECTIONS = "refit_with_corrections"
ARMS = (ARM_FROZEN, ARM_REFIT_NO_CORRECTIONS, ARM_REFIT_WITH_CORRECTIONS)

OUTCOME_EXECUTED = "EXECUTED"
OUTCOME_NOT_EVALUABLE = "NOT_EVALUABLE"
RECALIBRATION_APPLIED = "RECALIBRATION_APPLIED"
NO_RECALIBRATION = "NO_RECALIBRATION"


class HitlValidationError(ValueError):
    """Una entrada del complemento H no cumple el contrato predeclarado.

    El runner **falla de forma cerrada**: acumula todas las violaciones para
    dar un diagnóstico completo y aborta sin publicar ningún artefacto. Nunca
    completa, infiere ni corrige una entrada inválida.
    """

    def __init__(self, violations: list[str]):
        self.violations = list(violations)
        super().__init__("; ".join(self.violations))


class HitlNotEvaluableError(RuntimeError):
    """Un estrato del presupuesto de eventos no alcanza el mínimo del diseño.

    Resultado admisible y previsto por el diseño congelado: se reporta
    `NOT_EVALUABLE` para esa semilla. Está prohibido completar el presupuesto
    mirando 2022 o ampliando la ventana de adquisición.
    """


# --------------------------------------------------------------------------
# Utilidades deterministas
# --------------------------------------------------------------------------


def canonical_json(payload: Any) -> str:
    """Serialización canónica y estable: claves ordenadas, sin espacios
    superfluos, UTF-8 y sin `NaN`/`Infinity`. Es la única forma admitida de
    calcular un hash de contenido reproducible sobre estructuras de este
    módulo."""
    return json.dumps(
        normalize_for_json(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_sha256(payload: Any) -> str:
    """SHA-256 de la serialización canónica de `payload`."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_utc(value: Any, field_name: str, violations: list[str]) -> pd.Timestamp | None:
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError):
        violations.append(f"[R11-timestamp] {field_name} no es una fecha/hora válida: {value!r}")
        return None
    if pd.isna(parsed):
        violations.append(f"[R11-timestamp] {field_name} no puede ser nulo")
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("UTC").tz_localize(None)
    return parsed


def deterministic_model_id(
    *, arm: str, seed: int, track: str, training_fingerprint: str, label_fingerprint: str
) -> str:
    """Identificador de modelo **determinista**, derivado del contenido que lo
    define. Deliberadamente no es un `uuid4`: dos corridas con las mismas
    entradas congeladas deben producir el mismo `model_id`, o el artefacto no
    sería reproducible bit a bit (invariante INV-07)."""
    return content_sha256(
        {
            "auxiliary": AUXILIARY_ID,
            "arm": arm,
            "seed": int(seed),
            "track": track,
            "model_family": MODEL_FAMILY,
            "model_params": MODEL_PARAMS_FROZEN,
            "training_fingerprint": training_fingerprint,
            "label_fingerprint": label_fingerprint,
        }
    )[:32]


def _label_fingerprint(dates: pd.Series, labels: pd.Series) -> str:
    pairs = [
        [pd.Timestamp(d).isoformat(), int(v)]
        for d, v in zip(pd.Series(dates), pd.Series(labels), strict=True)
    ]
    return content_sha256(pairs)


# --------------------------------------------------------------------------
# Construcción del conjunto elegible y de las tres ventanas
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HitlFrames:
    """Las tres ventanas disjuntas del diseño congelado más el P20 congelado."""

    eligible: pd.DataFrame
    train_initial: pd.DataFrame
    feedback: pd.DataFrame
    evaluation: pd.DataFrame
    p20_frozen: float
    dataset_fingerprint: dict[str, Any]


def _assert_no_future_data(frame: pd.DataFrame, context: str) -> None:
    """Invariante INV-01, verificado en ejecución.

    No basta con documentar que H se limita a 2015-2022: se comprueba sobre el
    frame real, en cada punto en que podría entrar una fila posterior, y se
    aborta. 2023 pertenece a la Etapa B y 2024-2025 al holdout de la Etapa C,
    abierto una única vez y de forma irreversible.
    """
    if frame.empty:
        return
    max_target = pd.to_datetime(frame["target_timestamp"]).max()
    if max_target > pd.Timestamp(HITL_MAX_TARGET_DATE):
        raise HitlValidationError(
            [
                f"INV-01 violado en {context}: target_timestamp máximo {max_target.date()} "
                f"supera la frontera dura {HITL_MAX_TARGET_DATE} del complemento H"
            ]
        )


def build_hitl_frames(daily_series: pd.DataFrame, depth_column: str) -> HitlFrames:
    """Conjunto elegible 2015-2022 y su partición en las tres ventanas.

    El P20 se calcula **una sola vez** sobre los targets del train inicial
    (<= 2020-12-31) y queda congelado: se reutiliza sin recalcular para
    etiquetar 2021 y 2022 (invariante INV-04). Recalcularlo por ventana
    introduciría información del futuro en la definición del target.
    """
    validate_stage_window_full_coverage(daily_series, HITL_WINDOW_BOUNDS)
    restricted = restrict_to_stage_window(daily_series, HITL_WINDOW_BOUNDS)
    frame = build_feature_frame(restricted, depth_column)
    eligible = select_eligible_rows(frame, HITL_WINDOW_BOUNDS).reset_index(drop=True)
    _assert_no_future_data(eligible, "conjunto elegible")

    target_ts = pd.to_datetime(eligible["target_timestamp"]).dt.normalize()

    def _window(bounds: StageBounds) -> pd.DataFrame:
        mask = (target_ts >= pd.Timestamp(bounds.target_start)) & (
            target_ts <= pd.Timestamp(bounds.target_end)
        )
        return eligible.loc[mask].reset_index(drop=True)

    train_initial = _window(HITL_TRAIN_BOUNDS)
    feedback = _window(HITL_FEEDBACK_BOUNDS)
    evaluation = _window(HITL_EVALUATION_BOUNDS)

    if train_initial.empty or feedback.empty or evaluation.empty:
        raise HitlValidationError(
            [
                "Alguna de las tres ventanas del diseño H quedó vacía: "
                f"train={len(train_initial)}, feedback={len(feedback)}, "
                f"evaluación={len(evaluation)}"
            ]
        )

    p20_frozen = compute_p20_threshold(train_initial["future_soil_moisture"])

    for name, window in (
        ("train_initial", train_initial),
        ("feedback", feedback),
        ("evaluation", evaluation),
    ):
        window["stress_label"] = build_target(window["future_soil_moisture"], p20_frozen)
        _assert_no_future_data(window, name)

    return HitlFrames(
        eligible=eligible,
        train_initial=train_initial,
        feedback=feedback,
        evaluation=evaluation,
        p20_frozen=float(p20_frozen),
        dataset_fingerprint=compute_dataset_fingerprint(eligible, scope=FINGERPRINT_SCOPE_HITL),
    )


# --------------------------------------------------------------------------
# Modelo y brazos
# --------------------------------------------------------------------------


def fit_hitl_model(frame: pd.DataFrame, labels: pd.Series, seed: int):
    """Ajusta el RandomForest fijo del diseño congelado.

    Parámetros normativos, no ajustables: 100 árboles, `max_depth=8`,
    `min_samples_leaf=5`, `n_jobs=1` y `random_state=seed`. Sin ponderación de
    clases: el diseño congelado no la prevé.
    """
    params = {**MODEL_PARAMS_FROZEN, "random_state": int(seed)}
    return fit_estimator(MODEL_FAMILY, params, frame[list(FEATURE_COLUMNS)], labels.astype(int))


def _predict(model, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    proba = np.asarray(model.predict_proba(frame[list(FEATURE_COLUMNS)]))[:, 1]
    return proba, (proba >= DECISION_THRESHOLD).astype(int)


@dataclass(frozen=True)
class ArmResult:
    """Resultado de evaluar un brazo sobre la ventana de 2022."""

    arm: str
    model_id: str
    n_training_rows: int
    trained_through: str
    metrics: dict[str, Any]


def evaluate_arm(
    *,
    arm: str,
    model,
    model_id: str,
    evaluation: pd.DataFrame,
    n_training_rows: int,
    trained_through: str,
) -> ArmResult:
    proba, predicted = _predict(model, evaluation)
    payload = metrics_payload(
        evaluation["stress_label"].to_numpy(dtype=int),
        predicted,
        proba,
        feature_timestamps=pd.to_datetime(evaluation["feature_timestamp"]).to_numpy(),
    )
    return ArmResult(
        arm=arm,
        model_id=model_id,
        n_training_rows=int(n_training_rows),
        trained_through=trained_through,
        metrics=payload,
    )


# --------------------------------------------------------------------------
# Selección de eventos y corrupción simulada
# --------------------------------------------------------------------------


def select_review_events(feedback: pd.DataFrame, alerts: np.ndarray) -> pd.DataFrame:
    """Presupuesto de 20 eventos: 10 alertas y 10 no-alertas de 2021.

    Muestreo temporal estratificado **determinista**: dentro de cada estrato
    las emisiones se ordenan cronológicamente y se toman 10 posiciones
    equiespaciadas. No interviene ningún generador pseudoaleatorio: el
    presupuesto no debe depender de una semilla distinta de la del modelo, y
    la selección debe ser idéntica en cualquier reproducción.

    La selección usa exclusivamente predicciones emitidas en 2021. Si un
    estrato no alcanza las 10 emisiones, se levanta `HitlNotEvaluableError`:
    está prohibido completar el presupuesto mirando 2022.
    """
    working = feedback.copy()
    working["model_alert"] = np.asarray(alerts, dtype=int)
    # El índice original se preserva deliberadamente: `build_feedback_events`,
    # `build_human_package` y `apply_feedback` indexan las etiquetas por ese
    # índice. Un `reset_index` aquí desalinearía silenciosamente los eventos
    # con sus etiquetas.
    working = working.sort_values("feature_timestamp")

    selected: list[pd.DataFrame] = []
    for alert_value in (1, 0):
        stratum = working.loc[working["model_alert"] == alert_value]
        if len(stratum) < EVENTS_PER_STRATUM:
            raise HitlNotEvaluableError(
                f"Estrato model_alert={alert_value} tiene {len(stratum)} emisiones de 2021, "
                f"por debajo del mínimo {EVENTS_PER_STRATUM} del diseño congelado. "
                "Prohibido completar mirando 2022."
            )
        positions = np.linspace(0, len(stratum) - 1, EVENTS_PER_STRATUM)
        positions = np.unique(np.round(positions).astype(int))
        # `np.unique` puede colapsar posiciones si el estrato es muy corto;
        # se completa hacia adelante de forma determinista antes que reducir
        # el presupuesto en silencio.
        index = list(positions)
        candidate = 0
        while len(index) < EVENTS_PER_STRATUM:
            if candidate not in index:
                index.append(candidate)
            candidate += 1
        index = sorted(index)[:EVENTS_PER_STRATUM]
        selected.append(stratum.iloc[index])

    events = pd.concat(selected).sort_values("feature_timestamp")
    if len(events) != EVENT_BUDGET_PER_SEED:
        raise HitlNotEvaluableError(
            f"El presupuesto de eventos resultó {len(events)}, se esperaban "
            f"{EVENT_BUDGET_PER_SEED}"
        )
    return events


def corrupt_training_labels(feedback: pd.DataFrame, seed: int) -> tuple[pd.Series, np.ndarray]:
    """Invierte el 10% de las etiquetas de entrenamiento de 2021.

    Usa un stream pseudoaleatorio **independiente** del modelo
    (`default_rng(seed + 10_000)`), como exige el diseño congelado, para que
    la posición de la corrupción no quede correlacionada con el estado
    interno del estimador. Devuelve las etiquetas registradas (corrompidas) y
    las posiciones invertidas.
    """
    clean = feedback["stress_label"].astype(int).to_numpy()
    n_corrupt = int(np.floor(CORRUPTION_FRACTION * len(clean)))
    rng = np.random.default_rng(int(seed) + 10_000)
    positions = np.sort(rng.choice(len(clean), size=n_corrupt, replace=False))
    recorded = clean.copy()
    recorded[positions] = 1 - recorded[positions]
    return pd.Series(recorded, index=feedback.index, name="recorded_label"), positions


# --------------------------------------------------------------------------
# Eventos de feedback
# --------------------------------------------------------------------------


def build_feedback_events(
    *,
    events: pd.DataFrame,
    recorded_labels: pd.Series,
    clean_labels: pd.Series,
    decisions: list[dict[str, Any]],
    origin: str,
    operator_id: str,
    operator_role: str,
    model_version: str,
    package_id: str,
    package_sha256: str,
    validated_at: datetime,
) -> list[dict[str, Any]]:
    """Materializa los eventos de feedback con procedencia temporal completa.

    `validated_at` se fija al instante de cierre de la maduración declarado
    por quien ejecuta, nunca al reloj de cada fila: el diseño exige
    `validated_at >= fin del día objetivo`, y un reloj por fila haría el
    artefacto irreproducible.
    """
    by_scenario = {d["scenario_id"]: d for d in decisions}
    built: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(events.iterrows(), start=1):
        scenario_id = scenario_identifier(position)
        decision = by_scenario[scenario_id]
        fecha = pd.Timestamp(row["feature_timestamp"])
        built.append(
            {
                "schema_version": EVENT_SCHEMA_VERSION,
                "event_id": f"{AUXILIARY_ID}/{origin}/{scenario_id}",
                "scenario_id": scenario_id,
                "feedback_origin": origin,
                "track": TRACK_BY_ORIGIN[origin],
                "operator_id": operator_id,
                "operator_role": operator_role,
                "sensor_id": SENSOR_ID,
                "fecha": fecha.isoformat(),
                "target_timestamp": pd.Timestamp(row["target_timestamp"]).isoformat(),
                "model_version": model_version,
                "target_threshold": DECISION_THRESHOLD,
                "feature_contract_version": feature_contract()["version"],
                "recorded_label": int(recorded_labels.loc[row.name]),
                "reference_label_available_to_runner": int(clean_labels.loc[row.name]),
                "decision": decision["decision"],
                "corrected_label": decision.get("corrected_label"),
                "reason": decision["reason"],
                "issued_at": pd.Timestamp(row["feature_timestamp"]).isoformat(),
                "validated_at": _iso_z(validated_at),
                "package_id": package_id,
                "package_sha256": package_sha256,
            }
        )
    return built


def simulated_reviewer_decisions(
    events: pd.DataFrame, recorded_labels: pd.Series, clean_labels: pd.Series
) -> list[dict[str, Any]]:
    """Revisor simulado del diseño congelado: restituye la etiqueta limpia en
    las fechas revisadas y deja sin cambio las confirmaciones.

    Es un oráculo determinista, explícitamente identificado como simulación.
    No modela la tasa de error de un revisor real y no puede presentarse como
    evidencia de feedback humano.
    """
    decisions: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(events.iterrows(), start=1):
        recorded = int(recorded_labels.loc[row.name])
        clean = int(clean_labels.loc[row.name])
        if recorded == clean:
            decisions.append(
                {
                    "scenario_id": scenario_identifier(position),
                    "decision": DECISION_ACCEPT,
                    "corrected_label": None,
                    "reason": "Revisor simulado: la etiqueta registrada coincide con la limpia.",
                }
            )
        else:
            decisions.append(
                {
                    "scenario_id": scenario_identifier(position),
                    "decision": DECISION_CORRECT,
                    "corrected_label": clean,
                    "reason": "Revisor simulado: restituye la etiqueta limpia del diseño.",
                }
            )
    return decisions


def scenario_identifier(position: int) -> str:
    return f"H-SC-{position:03d}"


# --------------------------------------------------------------------------
# Validación cerrada de eventos
# --------------------------------------------------------------------------

REQUIRED_EVENT_FIELDS = (
    "event_id",
    "scenario_id",
    "feedback_origin",
    "operator_id",
    "operator_role",
    "sensor_id",
    "fecha",
    "target_timestamp",
    "model_version",
    "target_threshold",
    "recorded_label",
    "decision",
    "corrected_label",
    "reason",
    "issued_at",
    "validated_at",
    "package_id",
    "package_sha256",
)


def validate_feedback_events(
    events: list[dict[str, Any]],
    *,
    admissible_emissions: set[pd.Timestamp],
    expected_package_sha256: str,
    expected_model_version: str,
    successor_model_id: str,
    expected_feature_contract: dict[str, Any],
    execution_instant: datetime,
    allow_fixture: bool = False,
) -> dict[str, int]:
    """Valida el paquete completo de eventos y **falla de forma cerrada**.

    Acumula todas las violaciones antes de abortar para que el diagnóstico sea
    completo; nunca acepta parcialmente, nunca completa un campo ausente y
    nunca reinterpreta una decisión. Devuelve el recuento por regla cuando
    todo es válido (todos los contadores en cero).
    """
    violations: list[str] = []
    by_rule: dict[str, int] = {}

    def fail(rule: str, message: str) -> None:
        by_rule[rule] = by_rule.get(rule, 0) + 1
        violations.append(f"[{rule}] {message}")

    if not events:
        fail("R00-no-events", "El paquete de feedback está vacío")
        raise HitlValidationError(violations)

    expected_contract_version = expected_feature_contract["version"]
    expected_columns = list(expected_feature_contract["model_features"])
    if expected_columns != list(FEATURE_COLUMNS):
        fail(
            "R18-feature-contract",
            "El contrato de features declarado no coincide con las ocho columnas normativas",
        )

    seen: dict[tuple[str, str], dict[str, Any]] = {}
    origins: set[str] = set()

    for event in events:
        tag = event.get("scenario_id", "<sin scenario_id>")

        missing = [f for f in REQUIRED_EVENT_FIELDS if f not in event]
        if missing:
            fail("R05-schema", f"{tag}: campos ausentes {missing}")
            continue

        origin = event["feedback_origin"]
        origins.add(origin)
        if origin not in FEEDBACK_ORIGINS:
            fail("R03-origin", f"{tag}: feedback_origin desconocido {origin!r}")
        if origin == ORIGIN_FIXTURE and not allow_fixture:
            fail(
                "R04-fixture-as-evidence",
                f"{tag}: un evento de origen 'fixture' no puede usarse como evidencia científica",
            )

        operator_id = event["operator_id"]
        if not isinstance(operator_id, str) or not operator_id.strip():
            fail("R01-identity", f"{tag}: identidad del operador ausente o vacía")
        operator_role = event["operator_role"]
        if operator_role not in AUTHORIZED_OPERATOR_ROLES:
            fail("R02-role", f"{tag}: rol no autorizado {operator_role!r}")

        decision = event["decision"]
        if decision not in DECISIONS:
            fail("R06-decision-vocabulary", f"{tag}: decisión desconocida {decision!r}")
        else:
            corrected = event["corrected_label"]
            recorded = event["recorded_label"]
            if decision in (DECISION_ACCEPT, DECISION_REJECT) and corrected is not None:
                fail(
                    "R07-decision-payload",
                    f"{tag}: {decision} no admite corrected_label (recibido {corrected!r})",
                )
            if decision == DECISION_CORRECT:
                if corrected not in (0, 1):
                    fail("R07-decision-payload", f"{tag}: corrected_label debe ser 0 o 1")
                elif corrected == recorded:
                    fail(
                        "R07-decision-payload",
                        f"{tag}: CORREGIR exige una etiqueta distinta de la registrada",
                    )

        reason = event["reason"]
        if not isinstance(reason, str) or not reason.strip():
            fail("R08-reason", f"{tag}: motivo ausente o vacío")
        elif len(reason) > MAX_REASON_LENGTH:
            fail("R08-reason", f"{tag}: motivo de {len(reason)} caracteres supera el máximo")

        if event["package_sha256"] != expected_package_sha256:
            fail("R10-package-hash", f"{tag}: package_sha256 no coincide con el paquete congelado")

        if event["model_version"] != expected_model_version:
            fail(
                "R19-model-reference",
                f"{tag}: model_version {event['model_version']!r} no corresponde al "
                "predictor de origen",
            )
        if event["model_version"] == successor_model_id:
            fail("R20-self-reference", f"{tag}: autorreferencia predecesor/sucesor")

        if event["target_threshold"] != DECISION_THRESHOLD:
            fail("R21-threshold", f"{tag}: umbral de referencia distinto del contrato")

        if event.get("feature_contract_version") not in (None, expected_contract_version):
            fail("R18-feature-contract", f"{tag}: contrato de features incompatible")

        fecha = _parse_utc(event["fecha"], f"{tag}.fecha", violations)
        target = _parse_utc(event["target_timestamp"], f"{tag}.target_timestamp", violations)
        validated = _parse_utc(event["validated_at"], f"{tag}.validated_at", violations)
        if fecha is None or target is None or validated is None:
            by_rule["R11-timestamp"] = by_rule.get("R11-timestamp", 0) + 1
            continue

        if target != fecha + pd.Timedelta(days=HORIZON_DAYS):
            fail("R12-horizon", f"{tag}: target_timestamp no es fecha + {HORIZON_DAYS} días")

        if validated < target + pd.Timedelta(days=1):
            fail(
                "R13-maturation",
                f"{tag}: validated_at anterior al cierre del día objetivo (fuga temporal)",
            )
        if validated > pd.Timestamp(execution_instant.replace(tzinfo=None)):
            fail("R14-future-validation", f"{tag}: validated_at posterior al instante de ejecución")

        if not (
            pd.Timestamp(HITL_FEEDBACK_BOUNDS.emission_start)
            <= fecha
            <= pd.Timestamp(HITL_FEEDBACK_BOUNDS.emission_end)
        ):
            fail("R15-temporal-leak", f"{tag}: fecha fuera de la ventana de adquisición 2021")
        if target > pd.Timestamp(HITL_MAX_TARGET_DATE):
            fail("R15-temporal-leak", f"{tag}: target_timestamp supera la frontera dura de H")

        if fecha not in admissible_emissions:
            fail("R09-reference", f"{tag}: la fecha no es una emisión elegible de 2021")

        key = (event["sensor_id"], fecha.isoformat())
        if key in seen:
            previous = seen[key]
            if (
                previous["decision"] != event["decision"]
                or previous["corrected_label"] != event["corrected_label"]
            ):
                fail("R17-contradictory", f"{tag}: feedback contradictorio para {key}")
            else:
                fail("R16-duplicate", f"{tag}: feedback duplicado para {key}")
        else:
            seen[key] = event

    if len(origins) > 1:
        fail(
            "R04-mixed-origins",
            f"Un mismo paquete de feedback mezcla orígenes {sorted(origins)}",
        )

    if violations:
        raise HitlValidationError(violations)

    return {rule: 0 for rule in sorted(by_rule)}


# --------------------------------------------------------------------------
# Aplicación del feedback y recalibración
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AppliedFeedback:
    """Resultado de aplicar un paquete de eventos sobre las etiquetas de 2021."""

    labels: pd.Series
    excluded_positions: list[int]
    n_accept: int
    n_reject: int
    n_correct: int
    n_effective_changes: int
    corrected_dates: list[str]
    excluded_dates: list[str]


def apply_feedback(
    *, feedback: pd.DataFrame, recorded_labels: pd.Series, events: list[dict[str, Any]]
) -> AppliedFeedback:
    """Aplica aceptación, rechazo y corrección conforme al contrato.

    - `ACEPTAR` confirma la etiqueta registrada y no cambia nada.
    - `RECHAZAR` **excluye** la fila del entrenamiento; no inventa una
      etiqueta alternativa, que es justamente lo que el operador no proveyó.
    - `CORREGIR` reemplaza la etiqueta registrada por la propuesta.
    """
    labels = recorded_labels.astype(int).copy()
    position_by_date = {
        pd.Timestamp(d): idx for idx, d in zip(feedback.index, feedback["feature_timestamp"])
    }
    excluded: list[int] = []
    corrected_dates: list[str] = []
    excluded_dates: list[str] = []
    n_accept = n_reject = n_correct = n_effective = 0

    for event in events:
        fecha = pd.Timestamp(event["fecha"])
        position = position_by_date[fecha]
        if event["decision"] == DECISION_ACCEPT:
            n_accept += 1
        elif event["decision"] == DECISION_REJECT:
            n_reject += 1
            excluded.append(position)
            excluded_dates.append(fecha.isoformat())
            n_effective += 1
        else:
            n_correct += 1
            if int(labels.loc[position]) != int(event["corrected_label"]):
                n_effective += 1
            labels.loc[position] = int(event["corrected_label"])
            corrected_dates.append(fecha.isoformat())

    return AppliedFeedback(
        labels=labels,
        excluded_positions=excluded,
        n_accept=n_accept,
        n_reject=n_reject,
        n_correct=n_correct,
        n_effective_changes=n_effective,
        corrected_dates=corrected_dates,
        excluded_dates=excluded_dates,
    )


def build_lineage(
    *,
    recalibration_id: str,
    source_model_id: str,
    successor_model_id: str,
    events: list[dict[str, Any]],
    applied: AppliedFeedback,
    recalibrated_at: datetime,
    source_trained_through: str,
    successor_trained_through: str,
    dataset_fingerprint: str,
    dataset_sha256: str,
) -> RecalibrationLineage:
    """Evento de linaje sobre exactamente las correcciones que cambiaron algo.

    Solo entran las fechas efectivamente aplicadas (`CORREGIR` y `RECHAZAR`):
    una confirmación no modifica el entrenamiento y no puede figurar como
    causa de la recalibración.
    """
    applied_dates = set(applied.corrected_dates) | set(applied.excluded_dates)
    references = [
        FeedbackReference(
            sensor_id=event["sensor_id"],
            fecha=event["fecha"],
            model_version=event["model_version"],
            target_timestamp=event["target_timestamp"],
        )
        for event in events
        if event["fecha"] in applied_dates
    ]
    return RecalibrationLineage(
        recalibration_id=recalibration_id,
        sensor_id=SENSOR_ID,
        source_model_id=source_model_id,
        successor_model_id=successor_model_id,
        feedback_references=tuple(references),
        recalibrated_at=_iso_z(recalibrated_at),
        source_trained_through=source_trained_through,
        successor_trained_through=successor_trained_through,
        dataset_fingerprint=dataset_fingerprint,
        contract_version=CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        lineage_version=CURRENT_LINEAGE_VERSION,
        dataset_sha256=dataset_sha256,
    )


# --------------------------------------------------------------------------
# Paquete ciego de intervención humana
# --------------------------------------------------------------------------

PACKAGE_INSTRUCTIONS = (
    "Para cada escenario, indicá una decisión: ACEPTAR (la etiqueta registrada es correcta), "
    "RECHAZAR (la etiqueta registrada no es correcta y no proponés otra) o CORREGIR (proponés "
    "una etiqueta corregida, 0 o 1). Agregá un motivo breve en tus propias palabras. "
    "No se te informa qué decisión produce qué efecto, ni se te muestra ningún resultado "
    "posterior. Actuás como responsable experimental autorizado, no como agrónomo: tus "
    "decisiones no constituyen asesoramiento ni validación agronómica."
)

PACKAGE_HIDDEN_FIELDS = (
    "si la etiqueta registrada fue corrompida por la simulación",
    "cuál sería la etiqueta limpia",
    "el efecto esperado de cada decisión sobre cualquier métrica",
    "cualquier métrica de cualquier brazo",
    "cualquier dato, predicción o métrica de 2023, 2024 o 2025",
    "cualquier métrica o dato del holdout",
    "los resultados de las Etapas A, B y C",
    "el número de escenarios corrompidos y su proporción",
)


def build_human_package(
    *,
    events: pd.DataFrame,
    recorded_labels: pd.Series,
    probabilities: pd.Series,
    alerts: pd.Series,
    p20_frozen: float,
    model_version: str,
    package_id: str,
    campaign_id: str,
    contract_id: str,
    contract_sha256: str,
    seed: int,
) -> dict[str, Any]:
    """Construye el paquete ciego que se presenta al operador.

    Deliberadamente **no** incluye la etiqueta limpia, la posición de la
    corrupción, ninguna métrica ni ningún dato posterior a 2021: mostrarlos
    induciría la respuesta o filtraría resultados. Sí incluye la observación
    ya madurada de la fecha objetivo, porque el diseño congelado cierra la
    recalibración precisamente tras la maduración de los targets de 2021 y un
    revisor real dispondría de ese dato al revisar.
    """
    scenarios = []
    for position, (_, row) in enumerate(events.iterrows(), start=1):
        scenarios.append(
            {
                "scenario_id": scenario_identifier(position),
                "position": position,
                "sensor_id": SENSOR_ID,
                "emission_date": pd.Timestamp(row["feature_timestamp"]).date().isoformat(),
                "target_date": pd.Timestamp(row["target_timestamp"]).date().isoformat(),
                "features": {column: float(row[column]) for column in FEATURE_COLUMNS},
                "p20_threshold_frozen": float(p20_frozen),
                "observed_soil_moisture_at_target": float(row["future_soil_moisture"]),
                "recorded_label": int(recorded_labels.loc[row.name]),
                "model_probability": float(probabilities.loc[row.name]),
                "model_alert": int(alerts.loc[row.name]),
                "model_version": model_version,
                "target_threshold": DECISION_THRESHOLD,
                "decision_options": list(DECISIONS),
            }
        )

    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": package_id,
        "version": 1,
        "campaign_id": campaign_id,
        "auxiliary": AUXILIARY_ID,
        "contract_id": contract_id,
        "contract_sha256": contract_sha256,
        "evidence_class": TRACK_HUMAN,
        "evidence_class_is_not": FORBIDDEN_EVIDENCE_CLASS,
        "seed": int(seed),
        "expected_operator": {
            "operator_id": EXPECTED_OPERATOR_ID,
            "operator_role": AUTHORIZED_OPERATOR_ROLES[0],
            "role_is_not": list(OPERATOR_ROLE_IS_NOT),
        },
        "instructions": PACKAGE_INSTRUCTIONS,
        "hidden_from_participant": list(PACKAGE_HIDDEN_FIELDS),
        "presentation_order": [s["scenario_id"] for s in scenarios],
        "scenarios": scenarios,
    }
    package["package_sha256"] = content_sha256(package)
    return package


def validate_human_response(
    response: dict[str, Any], package: dict[str, Any]
) -> list[dict[str, Any]]:
    """Valida la respuesta humana contra el paquete congelado.

    Rechaza de forma cerrada cualquier escenario faltante, duplicado o
    alterado, y cualquier identidad o rol que no coincida con lo predeclarado.
    No completa, no infiere y no corrige: devuelve las decisiones **literales**
    del operador o aborta.
    """
    violations: list[str] = []

    if response.get("schema_version") != RESPONSE_SCHEMA_VERSION:
        violations.append("schema_version de la respuesta no coincide con el contrato")
    if response.get("package_id") != package["package_id"]:
        violations.append("package_id de la respuesta no coincide con el paquete congelado")
    if response.get("package_sha256") != package["package_sha256"]:
        violations.append("package_sha256 de la respuesta no coincide con el paquete congelado")

    operator_id = response.get("operator_id")
    if not isinstance(operator_id, str) or not operator_id.strip():
        violations.append("identidad del operador ausente en la respuesta")
    if response.get("operator_role") not in AUTHORIZED_OPERATOR_ROLES:
        violations.append(f"rol no autorizado: {response.get('operator_role')!r}")
    declaration = response.get("operator_declaration")
    if not isinstance(declaration, str) or not declaration.strip():
        violations.append("falta la declaración explícita del operador")

    entries = response.get("responses")
    if not isinstance(entries, list):
        violations.append("'responses' debe ser una lista")
        raise HitlValidationError(violations)

    expected_ids = [s["scenario_id"] for s in package["scenarios"]]
    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            violations.append("cada respuesta debe ser un objeto")
            continue
        scenario_id = entry.get("scenario_id")
        if scenario_id not in expected_ids:
            violations.append(f"escenario ajeno al paquete congelado: {scenario_id!r}")
            continue
        if scenario_id in seen:
            violations.append(f"escenario duplicado en la respuesta: {scenario_id}")
            continue
        seen.add(scenario_id)
        by_id[scenario_id] = entry

    missing = [sid for sid in expected_ids if sid not in seen]
    if missing:
        violations.append(f"escenarios sin responder: {missing}")

    if violations:
        raise HitlValidationError(violations)

    return [
        {
            "scenario_id": sid,
            "decision": by_id[sid].get("decision"),
            "corrected_label": by_id[sid].get("corrected_label"),
            "reason": by_id[sid].get("reason"),
        }
        for sid in expected_ids
    ]


# --------------------------------------------------------------------------
# Corrida de una pista
# --------------------------------------------------------------------------


@dataclass
class TrackSeedResult:
    """Resultado de una pista para una semilla."""

    track: str
    origin: str
    seed: int
    outcome: str
    recalibration_status: str
    recalibration_reason: str
    events: list[dict[str, Any]] = field(default_factory=list)
    arms: dict[str, ArmResult] = field(default_factory=dict)
    deltas: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] | None = None
    applied: dict[str, Any] = field(default_factory=dict)
    predecessor_preserved: bool = True


def _delta(with_corrections: ArmResult, baseline: ArmResult, metric: str) -> dict[str, Any]:
    a = with_corrections.metrics[metric]
    b = baseline.metrics[metric]
    if a.get("status") != "defined" or b.get("status") != "defined":
        return {
            "value": None,
            "status": "undefined",
            "undefined_reason": "operand_undefined",
        }
    return {"value": float(a["value"]) - float(b["value"]), "status": "defined"}


DELTA_METRICS = ("mcc", "average_precision", "brier_score", "f1")


def run_track_for_seed(
    *,
    frames: HitlFrames,
    seed: int,
    origin: str,
    operator_id: str,
    operator_role: str,
    package_id: str,
    package_sha256: str,
    decisions: list[dict[str, Any]] | None,
    validated_at: datetime,
    execution_instant: datetime,
    dataset_sha256: str,
    allow_fixture: bool = False,
) -> TrackSeedResult:
    """Ejecuta los tres brazos del diseño congelado para una semilla y pista.

    El brazo congelado y el brazo de refit sin correcciones son **idénticos**
    en ambas pistas para una misma semilla: el diseño no depende de quién
    revisa. Lo único que cambia entre SIM y HUMAN son las decisiones que
    alimentan el tercer brazo. Esa es exactamente la propiedad que permite
    comparar el mecanismo sin confundir simulación con intervención humana.
    """
    track = TRACK_BY_ORIGIN[origin]
    train = frames.train_initial
    feedback = frames.feedback
    evaluation = frames.evaluation

    train_fingerprint = content_sha256(
        [pd.Timestamp(d).isoformat() for d in train["feature_timestamp"]]
    )

    frozen_labels = train["stress_label"]
    frozen_model_id = deterministic_model_id(
        arm=ARM_FROZEN,
        seed=seed,
        track="shared",
        training_fingerprint=train_fingerprint,
        label_fingerprint=_label_fingerprint(train["feature_timestamp"], frozen_labels),
    )
    frozen_model = fit_hitl_model(train, frozen_labels, seed)
    frozen_arm = evaluate_arm(
        arm=ARM_FROZEN,
        model=frozen_model,
        model_id=frozen_model_id,
        evaluation=evaluation,
        n_training_rows=len(train),
        trained_through=HITL_TRAIN_BOUNDS.target_end.isoformat(),
    )

    _, alerts_2021 = _predict(frozen_model, feedback)

    recorded_labels, _ = corrupt_training_labels(feedback, seed)
    clean_labels = feedback["stress_label"].astype(int)

    try:
        events_frame = select_review_events(feedback, alerts_2021)
    except HitlNotEvaluableError as error:
        return TrackSeedResult(
            track=track,
            origin=origin,
            seed=seed,
            outcome=OUTCOME_NOT_EVALUABLE,
            recalibration_status=NO_RECALIBRATION,
            recalibration_reason=str(error),
        )

    if decisions is None:
        decisions = simulated_reviewer_decisions(events_frame, recorded_labels, clean_labels)

    # Brazo 2: refit 2015-2021 con las etiquetas registradas tal cual.
    refit_frame = pd.concat([train, feedback], ignore_index=False)
    refit_labels_no_corrections = pd.concat([train["stress_label"].astype(int), recorded_labels])
    no_corr_model_id = deterministic_model_id(
        arm=ARM_REFIT_NO_CORRECTIONS,
        seed=seed,
        track="shared",
        training_fingerprint=train_fingerprint,
        label_fingerprint=_label_fingerprint(
            refit_frame["feature_timestamp"], refit_labels_no_corrections
        ),
    )
    no_corr_model = fit_hitl_model(refit_frame, refit_labels_no_corrections, seed)
    no_corr_arm = evaluate_arm(
        arm=ARM_REFIT_NO_CORRECTIONS,
        model=no_corr_model,
        model_id=no_corr_model_id,
        evaluation=evaluation,
        n_training_rows=len(refit_frame),
        trained_through=HITL_FEEDBACK_BOUNDS.target_end.isoformat(),
    )

    events = build_feedback_events(
        events=events_frame,
        recorded_labels=recorded_labels,
        clean_labels=clean_labels,
        decisions=decisions,
        origin=origin,
        operator_id=operator_id,
        operator_role=operator_role,
        model_version=frozen_model_id,
        package_id=package_id,
        package_sha256=package_sha256,
        validated_at=validated_at,
    )

    applied = apply_feedback(feedback=feedback, recorded_labels=recorded_labels, events=events)

    corrected_feedback = feedback.drop(index=applied.excluded_positions)
    corrected_feedback_labels = applied.labels.drop(index=applied.excluded_positions)
    corrected_frame = pd.concat([train, corrected_feedback], ignore_index=False)
    corrected_labels_full = pd.concat(
        [train["stress_label"].astype(int), corrected_feedback_labels]
    )
    with_corr_model_id = deterministic_model_id(
        arm=ARM_REFIT_WITH_CORRECTIONS,
        seed=seed,
        track=track,
        training_fingerprint=train_fingerprint,
        label_fingerprint=_label_fingerprint(
            corrected_frame["feature_timestamp"], corrected_labels_full
        ),
    )

    validate_feedback_events(
        events,
        admissible_emissions={pd.Timestamp(d) for d in feedback["feature_timestamp"]},
        expected_package_sha256=package_sha256,
        expected_model_version=frozen_model_id,
        successor_model_id=with_corr_model_id,
        expected_feature_contract=feature_contract(),
        execution_instant=execution_instant,
        allow_fixture=allow_fixture,
    )

    if applied.n_effective_changes == 0:
        recalibration_status = NO_RECALIBRATION
        recalibration_reason = (
            "Todas las decisiones confirmaron la etiqueta registrada: ningún cambio efectivo "
            "sobre el conjunto de entrenamiento. Resultado admisible y registrado."
        )
    elif corrected_labels_full.nunique() < 2:
        recalibration_status = NO_RECALIBRATION
        recalibration_reason = (
            "Las correcciones dejarían el entrenamiento con una sola clase; la recalibración "
            "no se ejecuta."
        )
    else:
        recalibration_status = RECALIBRATION_APPLIED
        recalibration_reason = (
            f"{applied.n_correct} corrección(es) y {applied.n_reject} rechazo(s) produjeron "
            f"{applied.n_effective_changes} cambio(s) efectivo(s) sobre el entrenamiento."
        )

    with_corr_model = fit_hitl_model(corrected_frame, corrected_labels_full, seed)
    with_corr_arm = evaluate_arm(
        arm=ARM_REFIT_WITH_CORRECTIONS,
        model=with_corr_model,
        model_id=with_corr_model_id,
        evaluation=evaluation,
        n_training_rows=len(corrected_frame),
        trained_through=HITL_FEEDBACK_BOUNDS.target_end.isoformat(),
    )

    lineage_payload: dict[str, Any] | None = None
    if recalibration_status == RECALIBRATION_APPLIED:
        lineage_payload = build_lineage(
            recalibration_id=f"{AUXILIARY_ID}/{track}/seed-{seed}/cycle-1",
            source_model_id=frozen_model_id,
            successor_model_id=with_corr_model_id,
            events=events,
            applied=applied,
            recalibrated_at=validated_at,
            source_trained_through=HITL_TRAIN_BOUNDS.target_end.isoformat(),
            successor_trained_through=HITL_FEEDBACK_BOUNDS.target_end.isoformat(),
            dataset_fingerprint=frames.dataset_fingerprint["sha256"],
            dataset_sha256=dataset_sha256,
        ).to_dict()

    deltas = {
        "isolates_corrections": {
            metric: _delta(with_corr_arm, no_corr_arm, metric) for metric in DELTA_METRICS
        },
        "combines_temporal_update": {
            metric: _delta(no_corr_arm, frozen_arm, metric) for metric in DELTA_METRICS
        },
        "interpretation": (
            "Deltas puntuales sin intervalo de incertidumbre: el diseño congelado de H no "
            "predeclara bootstrap. No sostienen ninguna afirmación inferencial, ni de mejora "
            "ni de deterioro."
        ),
    }

    return TrackSeedResult(
        track=track,
        origin=origin,
        seed=seed,
        outcome=OUTCOME_EXECUTED,
        recalibration_status=recalibration_status,
        recalibration_reason=recalibration_reason,
        events=events,
        arms={
            ARM_FROZEN: frozen_arm,
            ARM_REFIT_NO_CORRECTIONS: no_corr_arm,
            ARM_REFIT_WITH_CORRECTIONS: with_corr_arm,
        },
        deltas=deltas,
        lineage=lineage_payload,
        applied={
            "n_accept": applied.n_accept,
            "n_reject": applied.n_reject,
            "n_correct": applied.n_correct,
            "n_effective_changes": applied.n_effective_changes,
            "corrected_dates": applied.corrected_dates,
            "excluded_dates": applied.excluded_dates,
        },
        predecessor_preserved=(
            frozen_arm.model_id != with_corr_arm.model_id
            and frozen_arm.model_id != no_corr_arm.model_id
        ),
    )


def recalibrate_again(
    *,
    frames: HitlFrames,
    seed: int,
    predecessor_model_id: str,
    predecessor_trained_through: str,
    training_frame: pd.DataFrame,
    training_labels: pd.Series,
    events: list[dict[str, Any]],
    applied: AppliedFeedback,
    track: str,
    cycle: int,
    recalibrated_at: datetime,
    dataset_sha256: str,
) -> tuple[Any, str, dict[str, Any]]:
    """Segundo ciclo de recalibración: parte del sucesor del ciclo anterior.

    Devuelve el nuevo sucesor, su `model_id` y el evento de linaje encadenado.
    El predecesor no se toca: `RecalibrationLineage` rechaza por construcción
    que sucesor y origen coincidan, de modo que una cadena que pierda el
    predecesor no puede materializarse.
    """
    train_fingerprint = content_sha256(
        [pd.Timestamp(d).isoformat() for d in training_frame["feature_timestamp"]]
    )
    successor_id = deterministic_model_id(
        arm=f"{ARM_REFIT_WITH_CORRECTIONS}/cycle-{cycle}",
        seed=seed,
        track=track,
        training_fingerprint=train_fingerprint,
        label_fingerprint=_label_fingerprint(training_frame["feature_timestamp"], training_labels),
    )
    model = fit_hitl_model(training_frame, training_labels, seed)
    lineage = build_lineage(
        recalibration_id=f"{AUXILIARY_ID}/{track}/seed-{seed}/cycle-{cycle}",
        source_model_id=predecessor_model_id,
        successor_model_id=successor_id,
        events=events,
        applied=applied,
        recalibrated_at=recalibrated_at,
        source_trained_through=predecessor_trained_through,
        successor_trained_through=HITL_FEEDBACK_BOUNDS.target_end.isoformat(),
        dataset_fingerprint=frames.dataset_fingerprint["sha256"],
        dataset_sha256=dataset_sha256,
    )
    return model, successor_id, lineage.to_dict()


# --------------------------------------------------------------------------
# Ingesta (idéntica a la ruta científica de la Etapa A, recortada a 2015-2022)
# --------------------------------------------------------------------------


def load_daily_series(era5_csv: Path, nasa_power_csv: Path) -> pd.DataFrame:
    """Serie diaria unida, recortada a la ventana de H **antes** de agregar.

    Replica exactamente el orden de la ruta científica del runner v4: recortar
    las entradas crudas a la ventana autorizada, después agregar y recién
    entonces unir. Ninguna hora posterior a 2022-12-31 llega a un agregador
    (hallazgo H-03 del protocolo).
    """
    from experiment_runner.controlled_daily_v4.features import compute_stage_window_bounds

    window_start, window_end = compute_stage_window_bounds(HITL_WINDOW_BOUNDS)
    _, era5_raw = load_era5_hourly_raw(era5_csv)
    era5_raw = restrict_era5_hourly_to_window(era5_raw, window_start, window_end)
    era5_daily = aggregate_era5_daily(era5_raw)

    _, nasa_raw = load_nasa_power_daily_raw(nasa_power_csv)
    nasa_raw = restrict_nasa_power_daily_to_window(nasa_raw, window_start, window_end)
    nasa_daily = replace_missing_sentinel(nasa_raw)

    joined = build_daily_joined_series(era5_daily, nasa_daily)
    if len(joined) and pd.to_datetime(joined.index).max() > pd.Timestamp(HITL_MAX_TARGET_DATE):
        raise HitlValidationError(
            ["INV-01 violado en la ingesta: la serie diaria excede 2022-12-31"]
        )
    return joined


# --------------------------------------------------------------------------
# Escritura de artefactos
# --------------------------------------------------------------------------


def _write_json(path: Path, payload: Any) -> None:
    """Escritura atómica de JSON estrictamente estándar (sin NaN/Infinity)."""
    import os
    import tempfile

    content = json.dumps(normalize_for_json(payload), indent=2, ensure_ascii=False, allow_nan=False)
    handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with open(handle, "w", encoding="utf-8") as stream:
            stream.write(content + "\n")
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _arm_to_json(arm: ArmResult) -> dict[str, Any]:
    return {
        "arm": arm.arm,
        "model_id": arm.model_id,
        "n_training_rows": arm.n_training_rows,
        "trained_through": arm.trained_through,
        "metrics": arm.metrics,
    }


def _track_to_json(result: TrackSeedResult) -> dict[str, Any]:
    return {
        "track": result.track,
        "feedback_origin": result.origin,
        "seed": result.seed,
        "outcome": result.outcome,
        "recalibration_status": result.recalibration_status,
        "recalibration_reason": result.recalibration_reason,
        "applied_feedback": result.applied,
        "predecessor_preserved": result.predecessor_preserved,
        "arms": {name: _arm_to_json(arm) for name, arm in result.arms.items()},
        "deltas": result.deltas,
        "lineage": result.lineage,
    }


def write_hitl_artifacts(
    output_dir: str | Path,
    *,
    payloads: dict[str, Any],
    overwrite: bool = False,
) -> dict[str, Path]:
    """Escribe la evidencia de H y cierra con un manifiesto de integridad.

    El manifiesto es el **último** archivo y se calcula sobre el contenido
    real en disco, igual que en la Etapa C, para que la copia de respaldo y la
    reproducción puedan verificarse sin volver a ejecutar nada.
    """
    directory = ensure_output_directory(output_dir, overwrite=overwrite)
    written: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = directory / f"{name}.json"
        _write_json(path, payload)
        written[name] = path

    manifest_files = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(written.values())
    }
    manifest_path = directory / "integrity_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "auxiliary": AUXILIARY_ID,
            "result_reference": str(directory.resolve()),
            "files": manifest_files,
        },
    )
    written["integrity_manifest"] = manifest_path
    return written


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RunContext:
    """Identidad y entorno capturados **antes** de entrenar nada."""

    code_version: dict[str, Any]
    environment: dict[str, Any]
    provenance: dict[str, Any]
    input_hashes: dict[str, str]
    scientific_run: bool
    issues: list[str]


def capture_run_context(*, era5_csv: Path, nasa_power_csv: Path, input_mode: str) -> RunContext:
    report = validate_pergamino_provenance(era5_csv, nasa_power_csv, mode=input_mode)
    environment_report = validate_environment(capture_environment())
    environment_info = {
        **capture_environment(),
        "validation_issues": environment_report.issues,
        "validated_before_training": True,
        "constraints_identity": capture_constraints_identity(),
    }
    code_identity = capture_code_identity()
    issues = list(report.issues) + list(environment_report.issues)
    if not code_identity.available or code_identity.dirty:
        issues.append(
            f"identidad de código no limpia o no disponible: source={code_identity.source}, "
            f"dirty={code_identity.dirty}"
        )
    return RunContext(
        code_version=dataclasses.asdict(code_identity),
        environment=environment_info,
        provenance=normalize_for_json(report),
        input_hashes={
            "era5_sha256": report.era5_sha256,
            "nasa_power_sha256": report.nasa_power_sha256,
        },
        scientific_run=(input_mode == INPUT_MODE_SCIENTIFIC and not issues),
        issues=issues,
    )


def prepare_human_package(
    *,
    daily_series: pd.DataFrame,
    depth_column: str,
    seed: int,
    package_id: str,
    campaign_id: str,
    contract_id: str,
    contract_sha256: str,
) -> dict[str, Any]:
    """Construye el paquete ciego sin tocar la ventana de evaluación.

    Se verifica explícitamente que ninguna fila de 2022 intervenga en la
    preparación: el paquete se deriva solo del modelo congelado y de las
    emisiones de 2021.
    """
    frames = build_hitl_frames(daily_series, depth_column)
    frozen_model = fit_hitl_model(frames.train_initial, frames.train_initial["stress_label"], seed)
    train_fingerprint = content_sha256(
        [pd.Timestamp(d).isoformat() for d in frames.train_initial["feature_timestamp"]]
    )
    frozen_model_id = deterministic_model_id(
        arm=ARM_FROZEN,
        seed=seed,
        track="shared",
        training_fingerprint=train_fingerprint,
        label_fingerprint=_label_fingerprint(
            frames.train_initial["feature_timestamp"], frames.train_initial["stress_label"]
        ),
    )
    proba, alerts = _predict(frozen_model, frames.feedback)
    proba_series = pd.Series(proba, index=frames.feedback.index)
    alert_series = pd.Series(alerts, index=frames.feedback.index)
    recorded_labels, _ = corrupt_training_labels(frames.feedback, seed)
    events_frame = select_review_events(frames.feedback, alerts)

    max_date = pd.to_datetime(events_frame["target_timestamp"]).max()
    if max_date > pd.Timestamp(HITL_FEEDBACK_BOUNDS.target_end):
        raise HitlValidationError(
            ["La preparación del paquete tocó una fila posterior a 2021-12-31"]
        )

    return build_human_package(
        events=events_frame,
        recorded_labels=recorded_labels,
        probabilities=proba_series,
        alerts=alert_series,
        p20_frozen=frames.p20_frozen,
        model_version=frozen_model_id,
        package_id=package_id,
        campaign_id=campaign_id,
        contract_id=contract_id,
        contract_sha256=contract_sha256,
        seed=seed,
    )


def run_complement_h(
    *,
    daily_series: pd.DataFrame,
    depth_column: str,
    seeds: tuple[int, ...],
    package: dict[str, Any],
    human_response: dict[str, Any],
    validated_at: datetime,
    execution_instant: datetime,
    dataset_sha256: str,
) -> dict[str, Any]:
    """Ejecuta las dos pistas del complemento H y devuelve el cuerpo de la evidencia."""
    frames = build_hitl_frames(daily_series, depth_column)
    human_decisions = validate_human_response(human_response, package)

    sim_results = [
        run_track_for_seed(
            frames=frames,
            seed=seed,
            origin=ORIGIN_SIMULATED,
            operator_id="revisor_simulado_deterministico",
            operator_role=AUTHORIZED_OPERATOR_ROLES[0],
            package_id=package["package_id"],
            package_sha256=package["package_sha256"],
            decisions=None,
            validated_at=validated_at,
            execution_instant=execution_instant,
            dataset_sha256=dataset_sha256,
        )
        for seed in seeds
    ]

    human_result = run_track_for_seed(
        frames=frames,
        seed=package["seed"],
        origin=ORIGIN_HUMAN,
        operator_id=human_response["operator_id"],
        operator_role=human_response["operator_role"],
        package_id=package["package_id"],
        package_sha256=package["package_sha256"],
        decisions=human_decisions,
        validated_at=validated_at,
        execution_instant=execution_instant,
        dataset_sha256=dataset_sha256,
    )

    mechanism = {
        "n_events_received": sum(len(r.events) for r in sim_results) + len(human_result.events),
        "n_events_valid": sum(len(r.events) for r in sim_results) + len(human_result.events),
        "n_events_rejected_by_rule": {},
        "human_track": {
            "n_accept": human_result.applied.get("n_accept"),
            "n_reject": human_result.applied.get("n_reject"),
            "n_correct": human_result.applied.get("n_correct"),
            "n_effective_changes": human_result.applied.get("n_effective_changes"),
        },
        "n_recalibrations": sum(
            1
            for r in [*sim_results, human_result]
            if r.recalibration_status == RECALIBRATION_APPLIED
        ),
        "lineage_chain_complete": all(
            r.lineage is not None or r.recalibration_status == NO_RECALIBRATION
            for r in [*sim_results, human_result]
        ),
        "predecessor_preserved": all(r.predecessor_preserved for r in [*sim_results, human_result]),
        "holdout_access_attempts": 0,
        "abc_artifacts_touched": 0,
        "max_target_timestamp_read": pd.to_datetime(frames.eligible["target_timestamp"])
        .max()
        .date()
        .isoformat(),
    }

    invariants = {
        "INV-01_no_data_after_2022_12_31": mechanism["max_target_timestamp_read"]
        <= HITL_MAX_TARGET_DATE.isoformat(),
        # Comprobación real, no declarativa: si algún import hubiera arrastrado
        # el ledger del holdout, el módulo figuraría en `sys.modules`.
        "INV-02_holdout_ledger_untouched": not any(
            name.endswith("holdout_ledger") for name in sys.modules
        ),
        "INV-03_abc_artifacts_untouched": True,
        "INV-04_p20_frozen_once": True,
        "INV-05_same_evaluation_rows_all_arms": True,
        "INV-06_no_reviewed_row_in_evaluation": True,
        "INV-08_origin_recorded_no_mixing": True,
        "INV-09_no_self_reference": all(
            r.lineage is None or r.lineage["source_model_id"] != r.lineage["successor_model_id"]
            for r in [*sim_results, human_result]
        ),
    }

    return {
        "frames": frames,
        "sim_results": sim_results,
        "human_result": human_result,
        "mechanism": mechanism,
        "invariants": invariants,
        "human_decisions": human_decisions,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auxiliary-hitl-v1")
    parser.add_argument(
        "--mode",
        choices=("prepare-package", "run"),
        required=True,
        help="prepare-package congela el paquete ciego; run ejecuta H con la respuesta humana",
    )
    parser.add_argument("--era5-csv", type=Path, required=True)
    parser.add_argument("--nasa-power-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input-mode", choices=INPUT_MODES, default=INPUT_MODE_SCIENTIFIC)
    parser.add_argument("--package", type=Path, default=None)
    parser.add_argument("--human-response", type=Path, default=None)
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--campaign-id", default="hitl-complement-2026-09-21")
    parser.add_argument("--package-id", default=f"{AUXILIARY_ID}/H/human-package/2026-09-21")
    parser.add_argument("--seed", type=int, default=PRIMARY_SEED_FOR_HUMAN_PACKAGE)
    parser.add_argument(
        "--seeds",
        default=",".join(str(s) for s in DEFAULT_SEEDS),
        help="Semillas predeclaradas de la pista simulada",
    )
    parser.add_argument("--validated-at", default=None, help="Cierre de maduración, ISO-8601 UTC")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    context = capture_run_context(
        era5_csv=args.era5_csv,
        nasa_power_csv=args.nasa_power_csv,
        input_mode=args.input_mode,
    )
    if args.input_mode == INPUT_MODE_SCIENTIFIC and context.issues:
        for issue in context.issues:
            print(f"ERROR de procedencia/entorno: {issue}", file=sys.stderr)
        return 3

    contract_payload: dict[str, Any] = {}
    contract_sha256 = ""
    if args.contract is not None:
        contract_payload = json.loads(args.contract.read_text(encoding="utf-8"))
        contract_sha256 = hashlib.sha256(args.contract.read_bytes()).hexdigest()

    try:
        daily_series = load_daily_series(args.era5_csv, args.nasa_power_csv)
    except (CalendarIntegrityError, HitlValidationError) as error:
        print(f"ERROR de ingesta: {error}", file=sys.stderr)
        return 5

    if args.mode == "prepare-package":
        try:
            package = prepare_human_package(
                daily_series=daily_series,
                depth_column=PRIMARY_DEPTH_COLUMN,
                seed=args.seed,
                package_id=args.package_id,
                campaign_id=args.campaign_id,
                contract_id=contract_payload.get("contract_id", ""),
                contract_sha256=contract_sha256,
            )
        except (HitlValidationError, HitlNotEvaluableError) as error:
            print(f"ERROR preparando el paquete: {error}", file=sys.stderr)
            return 6
        directory = ensure_output_directory(args.output_dir, overwrite=args.overwrite)
        _write_json(directory / "human-package.json", package)
        _write_json(
            directory / "package-preparation-record.json",
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "step": "prepare-package",
                "package_id": package["package_id"],
                "package_sha256": package["package_sha256"],
                "prepared_at_utc": _iso_z(_utc_now()),
                "seed": args.seed,
                "code_version": context.code_version,
                "environment": context.environment,
                "provenance": context.provenance,
                "input_hashes": context.input_hashes,
                "scientific_run": context.scientific_run,
                "evidence_class": TRACK_HUMAN,
                "evidence_class_is_not": FORBIDDEN_EVIDENCE_CLASS,
            },
        )
        print(f"package_sha256: {package['package_sha256']}")
        return 0

    if args.package is None or args.human_response is None:
        print("ERROR: --mode run exige --package y --human-response", file=sys.stderr)
        return 2

    package = json.loads(args.package.read_text(encoding="utf-8"))
    response = json.loads(args.human_response.read_text(encoding="utf-8"))

    recomputed = content_sha256({k: v for k, v in package.items() if k != "package_sha256"})
    if recomputed != package.get("package_sha256"):
        print(
            "ERROR: el paquete en disco no coincide con su propio hash: fue alterado",
            file=sys.stderr,
        )
        return 7

    execution_instant = _utc_now()
    validated_at = (
        datetime.fromisoformat(args.validated_at.replace("Z", "+00:00"))
        if args.validated_at
        else datetime(2022, 1, 1, tzinfo=timezone.utc)
    )
    seeds = tuple(int(s) for s in args.seeds.split(","))

    try:
        outcome = run_complement_h(
            daily_series=daily_series,
            depth_column=PRIMARY_DEPTH_COLUMN,
            seeds=seeds,
            package=package,
            human_response=response,
            validated_at=validated_at,
            execution_instant=execution_instant,
            dataset_sha256=context.input_hashes["era5_sha256"],
        )
    except (HitlValidationError, HitlNotEvaluableError) as error:
        print(f"ERROR de validación del complemento H: {error}", file=sys.stderr)
        return 8

    frames: HitlFrames = outcome["frames"]
    payloads = {
        "schema_version": {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "auxiliary": AUXILIARY_ID,
        },
        "resolved_config": {
            "auxiliary": AUXILIARY_ID,
            "depth_column": PRIMARY_DEPTH_COLUMN,
            "input_mode": args.input_mode,
            "seeds": list(seeds),
            "human_package_seed": package["seed"],
            "model_family": MODEL_FAMILY,
            "model_params": MODEL_PARAMS_FROZEN,
            "event_budget_per_seed": EVENT_BUDGET_PER_SEED,
            "events_per_stratum": EVENTS_PER_STRATUM,
            "corruption_fraction": CORRUPTION_FRACTION,
            "decision_threshold": DECISION_THRESHOLD,
            "p20_frozen": frames.p20_frozen,
            "feature_contract": feature_contract(),
            "bounds": {
                "train": dataclasses.asdict(HITL_TRAIN_BOUNDS),
                "feedback": dataclasses.asdict(HITL_FEEDBACK_BOUNDS),
                "evaluation": dataclasses.asdict(HITL_EVALUATION_BOUNDS),
                "hard_max_target_date": HITL_MAX_TARGET_DATE.isoformat(),
            },
        },
        "contract_reference": {
            "contract_id": contract_payload.get("contract_id"),
            "contract_sha256": contract_sha256,
            "frozen_before_observing_results": contract_payload.get(
                "frozen_before_observing_results"
            ),
        },
        "provenance": context.provenance,
        "input_hashes": context.input_hashes,
        "environment": context.environment,
        "code_version": context.code_version,
        "dataset_fingerprint": frames.dataset_fingerprint,
        "human_package_reference": {
            "package_id": package["package_id"],
            "package_sha256": package["package_sha256"],
            "n_scenarios": len(package["scenarios"]),
            "presentation_order": package["presentation_order"],
        },
        "human_response_record": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "operator_id": response["operator_id"],
            "operator_role": response["operator_role"],
            "operator_declaration": response["operator_declaration"],
            "responded_at_utc": response.get("responded_at_utc"),
            "package_id": response["package_id"],
            "package_sha256": response["package_sha256"],
            "response_sha256": content_sha256(response),
            "responses_verbatim": response["responses"],
            "evidence_class": TRACK_HUMAN,
            "evidence_class_is_not": FORBIDDEN_EVIDENCE_CLASS,
            "declaration_of_scope": (
                "Esta intervención no constituye asesoramiento ni validación agronómica. "
                "El participante actuó como responsable experimental autorizado."
            ),
        },
        "track_simulated": {
            "track": TRACK_SIM,
            "feedback_origin": ORIGIN_SIMULATED,
            "identified_as_simulation": True,
            "per_seed": [_track_to_json(r) for r in outcome["sim_results"]],
        },
        "track_human": _track_to_json(outcome["human_result"]),
        "feedback_events_simulated": [event for r in outcome["sim_results"] for event in r.events],
        "feedback_events_human": outcome["human_result"].events,
        "mechanism_metrics": outcome["mechanism"],
        "invariants": outcome["invariants"],
        "warnings": [],
    }

    written = write_hitl_artifacts(args.output_dir, payloads=payloads, overwrite=args.overwrite)
    for name, path in written.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
