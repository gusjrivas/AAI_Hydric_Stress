"""Lectura y validación ESTRUCTURAL del contrato de transferencia A→B.

Reconstruye, a partir de `frozen_config.json` (serializado por
`artifacts.write_stage_a_artifacts`), el candidato congelado por la Etapa A
(familia, hiperparámetros, `P20_train` final) sin volver a ejecutar la
selección ni entrenar nada. Esta operación es exclusivamente estructural:
verifica que el artefacto tiene la forma esperada (`schema_version`
reconocido, campos requeridos presentes, tipos correctos, valores finitos,
coherencia interna entre modo/profundidad/candidato) -- nunca decide si ese
candidato es admisible para una ejecución concreta (ver `admissibility.py`
para esa decisión, deliberadamente separada). Funciona de forma idéntica
sobre un artefacto sintético o uno científico.

Ver `openspec/changes/implement-controlled-daily-v4-stage-b-c/specs/experiment-runner/spec.md`,
requirement "Lectura y validación estructural del contrato de transferencia A→B".
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4.artifacts import TRANSFER_CONTRACT_SCHEMA_VERSION
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLES,
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_SIMPLICITY_ORDER,
    FAMILY_SOFT_VOTING,
    INPUT_MODE_SYNTHETIC,
    INPUT_MODES,
    WEIGHTING_MODES,
    depth_role_for_column,
)
from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
    DATASET_FINGERPRINT_FORMAT_VERSION,
)
from experiment_runner.controlled_daily_v4.metrics import (
    METRIC_STATUS_DEFINED,
    METRIC_STATUS_UNDEFINED,
)

SUPPORTED_TRANSFER_CONTRACT_SCHEMA_VERSIONS = (TRANSFER_CONTRACT_SCHEMA_VERSION,)
SUPPORTED_DATASET_FINGERPRINT_FORMAT_VERSIONS = (DATASET_FINGERPRINT_FORMAT_VERSION,)

SOFT_VOTING_BASE_FAMILIES = tuple(FAMILY_SIMPLICITY_ORDER[:-1])
"""Las tres familias de base de Soft Voting (excluye `soft_voting` en sí
misma), en el mismo orden normativo que `config.FAMILY_SIMPLICITY_ORDER`."""

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_positive_float(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) > 0


def _is_nonnegative_float(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) >= 0


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_int_or_none(value: Any) -> bool:
    return value is None or _is_positive_int(value)


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _is_valid_weighting(value: Any) -> bool:
    return value in WEIGHTING_MODES


# Claves y validadores de hiperparámetros requeridos por familia, derivados
# de los mismos campos que efectivamente serializan
# `models.iter_logistic_regression_configs`/`iter_random_forest_configs`/
# `iter_hist_gradient_boosting_configs` -- nunca se tocan esas grillas ni su
# algoritmo aquí, solo se exige que un artefacto leído los declare con el
# tipo esperado. `weighting` es obligatorio en las tres: un artefacto
# incompleto que lo omita se rechaza en vez de recibir un default inventado
# en la lectura (el default solo existe, legítimamente, en el punto de uso
# de `models.py` durante el ajuste real, nunca en la reconstrucción del
# contrato).
_FAMILY_PARAM_SPECS: dict[str, dict[str, Any]] = {
    FAMILY_LOGISTIC_REGRESSION: {
        "C": _is_positive_float,
        "weighting": _is_valid_weighting,
        "solver": _is_nonempty_str,
        "max_iter": _is_positive_int,
    },
    FAMILY_RANDOM_FOREST: {
        "n_estimators": _is_positive_int,
        "max_depth": _is_int_or_none,
        "min_samples_leaf": _is_positive_int,
        "weighting": _is_valid_weighting,
        "random_state": _is_int,
        "n_jobs": _is_int,
    },
    FAMILY_HIST_GRADIENT_BOOSTING: {
        "learning_rate": _is_positive_float,
        "max_iter": _is_positive_int,
        "max_leaf_nodes": _is_positive_int,
        "l2_regularization": _is_nonnegative_float,
        "weighting": _is_valid_weighting,
        "max_depth": _is_int_or_none,
        "early_stopping": _is_bool,
        "random_state": _is_int,
    },
}


class TransferContractSchemaError(ValueError):
    """`schema_version` del contrato no reconocido por este lector -- fallo
    estructural, previo a cualquier chequeo de admisibilidad."""


class TransferContractValidationError(ValueError):
    """Campo requerido ausente, tipo inválido, valor no finito, o
    incoherencia estructural entre modo/profundidad/candidato."""


@dataclass(frozen=True)
class FrozenCandidate:
    """Resumen estructural de una única configuración congelada (familia +
    hiperparámetros + MCC de la segunda pasada de congelamiento), tal como la
    serializa `artifacts._frozen_config_to_json`."""

    family: str
    params: dict[str, Any]
    median_mcc: dict[str, Any]
    fold_mcc: list[dict[str, Any]]


@dataclass(frozen=True)
class FrozenConfigContract:
    """Reconstrucción estructural completa de `frozen_config.json`."""

    schema_version: str
    input_mode: str
    scientific_run: bool
    depth_column: str
    depth_role: str
    candidate_produced: bool
    selected_family: str | None
    single_family: FrozenCandidate | None
    soft_voting_bases: dict[str, FrozenCandidate] | None
    final_p20_train: float | None
    final_estimator_details: dict[str, Any]
    producer_code_identity: dict[str, Any]
    producer_dataset_fingerprint_ref: dict[str, Any]
    raw: dict[str, Any]


def _validate_metric_envelope(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or "value" not in payload or "status" not in payload:
        raise TransferContractValidationError(
            f"{context}: se esperaba una envoltura de métrica ({{'value', 'status', ...}}), "
            f"se recibió {payload!r}"
        )
    status = payload["status"]
    value = payload["value"]
    if status == METRIC_STATUS_DEFINED:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TransferContractValidationError(
                f"{context}: status='defined' pero value={value!r} no es numérico"
            )
        if not math.isfinite(float(value)):
            raise TransferContractValidationError(
                f"{context}: status='defined' pero value={value!r} no es finito"
            )
    elif status == METRIC_STATUS_UNDEFINED:
        if value is not None:
            raise TransferContractValidationError(
                f"{context}: status='undefined' pero value={value!r} no es null"
            )
    else:
        raise TransferContractValidationError(f"{context}: status={status!r} desconocido")
    return payload


def _check_finite_recursive(value: Any, context: str) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise TransferContractValidationError(f"{context}: valor no finito ({value!r})")
        return
    if isinstance(value, dict):
        for key, sub in value.items():
            _check_finite_recursive(sub, f"{context}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, sub in enumerate(value):
            _check_finite_recursive(sub, f"{context}[{index}]")
        return
    raise TransferContractValidationError(
        f"{context}: tipo no serializable en un hiperparámetro ({type(value)})"
    )


def _validate_family_params(family: str, params: dict[str, Any], context: str) -> None:
    spec = _FAMILY_PARAM_SPECS.get(family)
    if spec is None:
        raise TransferContractValidationError(
            f"'{context}': familia desconocida '{family}' (válidas: "
            f"{tuple(_FAMILY_PARAM_SPECS)})"
        )
    for key, validator in spec.items():
        if key not in params:
            raise TransferContractValidationError(
                f"'{context}.params': falta el hiperparámetro requerido '{key}' de la familia "
                f"'{family}' -- no se infiere un default al leer un artefacto incompleto"
            )
        if not validator(params[key]):
            raise TransferContractValidationError(
                f"'{context}.params.{key}'={params[key]!r} no cumple el tipo/restricción "
                f"esperado para la familia '{family}'"
            )


def validate_fingerprint_reference(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TransferContractValidationError(f"'{context}' debe ser un objeto")
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_DATASET_FINGERPRINT_FORMAT_VERSIONS:
        raise TransferContractValidationError(
            f"'{context}.schema_version'={schema_version!r} no reconocido "
            f"(soportados: {SUPPORTED_DATASET_FINGERPRINT_FORMAT_VERSIONS})"
        )
    sha256 = payload.get("sha256")
    if not isinstance(sha256, str) or not _HEX64_RE.fullmatch(sha256):
        raise TransferContractValidationError(
            f"'{context}.sha256'={sha256!r} no es un SHA-256 hexadecimal completo (64 hex)"
        )
    n_rows = payload.get("n_rows")
    if not isinstance(n_rows, int) or isinstance(n_rows, bool) or n_rows < 0:
        raise TransferContractValidationError(
            f"'{context}.n_rows'={n_rows!r} debe ser un entero >= 0"
        )
    scope = payload.get("scope")
    if not isinstance(scope, str) or not scope:
        raise TransferContractValidationError(f"'{context}.scope' debe ser una cadena no vacía")
    return payload


def _parse_candidate(
    payload: Any, context: str, *, expected_family: str | None = None
) -> FrozenCandidate:
    if not isinstance(payload, dict):
        raise TransferContractValidationError(f"'{context}' debe ser un objeto")
    for key in ("family", "config", "median_mcc", "fold_mcc"):
        if key not in payload:
            raise TransferContractValidationError(f"'{context}': falta el campo requerido '{key}'")

    family = payload["family"]
    if not isinstance(family, str) or not family:
        raise TransferContractValidationError(f"'{context}.family' debe ser una cadena no vacía")
    if expected_family is not None and family != expected_family:
        raise TransferContractValidationError(
            f"'{context}.family'={family!r} no coincide con la clave esperada "
            f"{expected_family!r} -- incoherencia entre la familia declarada y su ubicación"
        )

    config = payload["config"]
    if not isinstance(config, dict) or "family" not in config or "params" not in config:
        raise TransferContractValidationError(
            f"'{context}.config' debe ser un objeto con 'family' y 'params'"
        )
    config_family = config["family"]
    if config_family != family:
        raise TransferContractValidationError(
            f"'{context}.family'={family!r} no coincide con '{context}.config.family'="
            f"{config_family!r}"
        )
    params = config["params"]
    if not isinstance(params, dict):
        raise TransferContractValidationError(f"'{context}.config.params' debe ser un objeto")
    _check_finite_recursive(params, f"{context}.config.params")
    _validate_family_params(family, params, context)

    median_mcc = _validate_metric_envelope(payload["median_mcc"], f"{context}.median_mcc")

    fold_mcc = payload["fold_mcc"]
    if not isinstance(fold_mcc, list):
        raise TransferContractValidationError(f"'{context}.fold_mcc' debe ser una lista")
    fold_mcc = [
        _validate_metric_envelope(entry, f"{context}.fold_mcc[{i}]")
        for i, entry in enumerate(fold_mcc)
    ]

    return FrozenCandidate(family=family, params=params, median_mcc=median_mcc, fold_mcc=fold_mcc)


def load_frozen_config_contract(output_dir: str | Path) -> FrozenConfigContract:
    """Carga tipada y sin entrenar de `<output_dir>/frozen_config.json`.

    Rechaza explícitamente (con un error controlado, nunca una excepción
    genérica no descriptiva) JSON inválido, un `schema_version` no
    reconocido, o un contrato con campos ausentes/tipos incorrectos/valores
    no finitos/incoherencia entre `candidate_produced` y el candidato
    efectivamente serializado. No abre ningún CSV crudo ni entrena nada."""
    path = Path(output_dir) / "frozen_config.json"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise TransferContractValidationError(
            f"No existe el contrato de transferencia '{path}'"
        ) from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TransferContractValidationError(f"'{path}' no es JSON válido: {exc}") from exc
    if not isinstance(raw, dict):
        raise TransferContractValidationError(f"'{path}': el JSON raíz debe ser un objeto")

    schema_version = raw.get("schema_version")
    if schema_version not in SUPPORTED_TRANSFER_CONTRACT_SCHEMA_VERSIONS:
        raise TransferContractSchemaError(
            f"'{path}': schema_version={schema_version!r} no reconocido "
            f"(soportados: {SUPPORTED_TRANSFER_CONTRACT_SCHEMA_VERSIONS})"
        )

    required_fields = (
        "input_mode",
        "scientific_run",
        "depth_column",
        "depth_role",
        "candidate_produced",
        "selected_family",
        "producer",
    )
    for key in required_fields:
        if key not in raw:
            raise TransferContractValidationError(f"'{path}': falta el campo requerido '{key}'")

    input_mode = raw["input_mode"]
    if input_mode not in INPUT_MODES:
        raise TransferContractValidationError(f"'{path}': input_mode={input_mode!r} inválido")

    scientific_run = raw["scientific_run"]
    if not isinstance(scientific_run, bool):
        raise TransferContractValidationError(f"'{path}': scientific_run debe ser bool")

    # Coherencia de modo: un artefacto sintético nunca puede declararse
    # `scientific_run=true` (mismo invariante ya exigido en tiempo de
    # escritura por `provenance.ProvenanceReport.scientific`) -- se
    # re-verifica aquí porque la lectura debe rechazar un JSON editado a
    # mano que rompa esa coherencia, no solo confiar en quien lo escribió.
    if input_mode == INPUT_MODE_SYNTHETIC and scientific_run:
        raise TransferContractValidationError(
            f"'{path}': input_mode='synthetic' con scientific_run=true es incoherente -- una "
            "corrida sintética nunca puede declararse científica"
        )

    depth_column = raw["depth_column"]
    if not isinstance(depth_column, str) or not depth_column:
        raise TransferContractValidationError(
            f"'{path}': depth_column debe ser una cadena no vacía"
        )

    depth_role = raw["depth_role"]
    if depth_role not in DEPTH_ROLES:
        raise TransferContractValidationError(
            f"'{path}': depth_role={depth_role!r} inválido (válidos: {DEPTH_ROLES})"
        )
    try:
        expected_depth_role = depth_role_for_column(depth_column)
    except ValueError as exc:
        raise TransferContractValidationError(f"'{path}': {exc}") from exc
    if depth_role != expected_depth_role:
        raise TransferContractValidationError(
            f"'{path}': depth_role={depth_role!r} no corresponde a depth_column={depth_column!r} "
            f"(se esperaba {expected_depth_role!r} según config.depth_role_for_column)"
        )

    candidate_produced = raw["candidate_produced"]
    if not isinstance(candidate_produced, bool):
        raise TransferContractValidationError(f"'{path}': candidate_produced debe ser bool")

    single_family_raw = raw.get("single_family")
    soft_voting_raw = raw.get("soft_voting_bases")
    selected_family = raw["selected_family"]

    if candidate_produced:
        if single_family_raw is None and not soft_voting_raw:
            raise TransferContractValidationError(
                f"'{path}': candidate_produced=true pero no hay 'single_family' ni "
                "'soft_voting_bases' serializados"
            )
        if selected_family is None:
            raise TransferContractValidationError(
                f"'{path}': candidate_produced=true pero selected_family es null"
            )
        if selected_family not in FAMILY_SIMPLICITY_ORDER:
            raise TransferContractValidationError(
                f"'{path}': selected_family={selected_family!r} no es una familia reconocida "
                f"(válidas: {FAMILY_SIMPLICITY_ORDER})"
            )
    else:
        if single_family_raw is not None or soft_voting_raw:
            raise TransferContractValidationError(
                f"'{path}': candidate_produced=false pero hay un candidato serializado -- "
                "la ausencia de candidato no debe fabricar una configuración congelada"
            )
        if selected_family is not None:
            raise TransferContractValidationError(
                f"'{path}': candidate_produced=false pero selected_family={selected_family!r} "
                "no es null"
            )

    single_family = (
        _parse_candidate(single_family_raw, "single_family", expected_family=selected_family)
        if single_family_raw is not None
        else None
    )
    if single_family is not None and selected_family != single_family.family:
        raise TransferContractValidationError(
            f"'{path}': selected_family={selected_family!r} no coincide con la familia del "
            f"candidato único congelado ({single_family.family!r})"
        )

    soft_voting_bases: dict[str, FrozenCandidate] | None = None
    if soft_voting_raw is not None:
        if not isinstance(soft_voting_raw, dict) or set(soft_voting_raw) != set(
            SOFT_VOTING_BASE_FAMILIES
        ):
            raise TransferContractValidationError(
                f"'{path}': soft_voting_bases debe declarar exactamente las familias base "
                f"{SOFT_VOTING_BASE_FAMILIES}"
            )
        if selected_family != FAMILY_SOFT_VOTING:
            raise TransferContractValidationError(
                f"'{path}': hay 'soft_voting_bases' serializado pero selected_family="
                f"{selected_family!r} no es {FAMILY_SOFT_VOTING!r}"
            )
        soft_voting_bases = {
            family_key: _parse_candidate(
                payload, f"soft_voting_bases.{family_key}", expected_family=family_key
            )
            for family_key, payload in soft_voting_raw.items()
        }

    if single_family is not None and soft_voting_bases is not None:
        raise TransferContractValidationError(
            f"'{path}': un contrato no puede declarar 'single_family' y 'soft_voting_bases' "
            "a la vez"
        )

    final_p20_train_raw = raw.get("final_p20_train")
    final_p20_train: float | None = None
    if candidate_produced:
        if (
            final_p20_train_raw is None
            or isinstance(final_p20_train_raw, bool)
            or not isinstance(final_p20_train_raw, (int, float))
        ):
            raise TransferContractValidationError(
                f"'{path}': final_p20_train debe ser numérico cuando candidate_produced=true "
                f"(recibido {final_p20_train_raw!r})"
            )
        final_p20_train = float(final_p20_train_raw)
        if not math.isfinite(final_p20_train):
            raise TransferContractValidationError(f"'{path}': final_p20_train no es finito")
    elif final_p20_train_raw is not None:
        raise TransferContractValidationError(
            f"'{path}': candidate_produced=false pero final_p20_train={final_p20_train_raw!r} "
            "no es null"
        )

    producer = raw["producer"]
    if (
        not isinstance(producer, dict)
        or "code_identity" not in producer
        or "dataset_fingerprint_ref" not in producer
    ):
        raise TransferContractValidationError(
            f"'{path}': 'producer' debe tener 'code_identity' y 'dataset_fingerprint_ref'"
        )
    producer_code_identity = producer["code_identity"]
    producer_dataset_fingerprint_ref = producer["dataset_fingerprint_ref"]
    if not isinstance(producer_code_identity, dict) or not isinstance(
        producer_dataset_fingerprint_ref, dict
    ):
        raise TransferContractValidationError(
            f"'{path}': 'producer.code_identity' y 'producer.dataset_fingerprint_ref' deben ser "
            "objetos"
        )
    # La huella del conjunto derivado de A siempre se calcula (aun sin
    # candidato seleccionado): un `{}` vacío o con formato inválido nunca es
    # una referencia válida -- se rechaza aquí, en la lectura estructural,
    # en lugar de dejar que una comparación posterior compare `None==None`.
    producer_dataset_fingerprint_ref = validate_fingerprint_reference(
        producer_dataset_fingerprint_ref, f"'{path}'.producer.dataset_fingerprint_ref"
    )

    final_estimator_details = raw.get("final_estimator_details", {})
    if not isinstance(final_estimator_details, dict):
        raise TransferContractValidationError(
            f"'{path}': final_estimator_details debe ser un objeto"
        )

    return FrozenConfigContract(
        schema_version=schema_version,
        input_mode=input_mode,
        scientific_run=scientific_run,
        depth_column=depth_column,
        depth_role=depth_role,
        candidate_produced=candidate_produced,
        selected_family=selected_family,
        single_family=single_family,
        soft_voting_bases=soft_voting_bases,
        final_p20_train=final_p20_train,
        final_estimator_details=final_estimator_details,
        producer_code_identity=producer_code_identity,
        producer_dataset_fingerprint_ref=producer_dataset_fingerprint_ref,
        raw=raw,
    )


__all__ = [
    "SUPPORTED_TRANSFER_CONTRACT_SCHEMA_VERSIONS",
    "SUPPORTED_DATASET_FINGERPRINT_FORMAT_VERSIONS",
    "SOFT_VOTING_BASE_FAMILIES",
    "TransferContractSchemaError",
    "TransferContractValidationError",
    "FrozenCandidate",
    "FrozenConfigContract",
    "load_frozen_config_contract",
    "validate_fingerprint_reference",
]
