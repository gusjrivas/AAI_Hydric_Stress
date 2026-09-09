"""Configuración y contratos normativos de controlled_daily_v4_external_pergamino.

Toda constante de este módulo proviene del protocolo formal (ADR-0011,
docs/research/controlled-daily-v4-external-pergamino-protocol.md). No debe
alterarse por conveniencia de implementación: fechas, horizonte, features,
grillas, margen y semillas son normativos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

HORIZON_DAYS = 3
GAP = 3
OUTER_N_SPLITS = 3
INNER_N_SPLITS = 3

PRIMARY_DEPTH_COLUMN = "soil_moisture_0_to_7cm"
SENSITIVITY_DEPTH_COLUMN = "soil_moisture_7_to_28cm"
EXCLUDED_DEPTH_COLUMNS = (
    "soil_moisture_28_to_100cm",
    "soil_moisture_100_to_255cm",
)
ALL_SOIL_MOISTURE_COLUMNS = (
    PRIMARY_DEPTH_COLUMN,
    SENSITIVITY_DEPTH_COLUMN,
    *EXCLUDED_DEPTH_COLUMNS,
)

LAGS = (1, 2, 3)
ROLLING_WINDOWS = (3, 7)

RELATIVE_HUMIDITY_COLUMN = "RH2M"
SOLAR_RADIATION_COLUMN = "ALLSKY_SFC_SW_DWN"
# Fuera del protocolo principal (protocolo, sección 4): solo para sensibilidad separada.
TEMPERATURE_COLUMN = "T2M"
PRECIPITATION_COLUMN = "PRECTOTCORR"

NASA_POWER_MISSING_SENTINEL = -999

DECISION_THRESHOLD = 0.5
PRACTICAL_MARGIN_DELTA_MCC = 0.05

BOOTSTRAP_BLOCK_DAYS = 30
BOOTSTRAP_REPLICAS_DEFAULT = 5000
BOOTSTRAP_SEED = 20250109

RANDOM_STATE = 42

# Nombres de familia, en el orden de simplicidad usado para el desempate
# predeclarado (protocolo, sección 8): LR < RF < HGB < Soft Voting.
FAMILY_LOGISTIC_REGRESSION = "logistic_regression"
FAMILY_RANDOM_FOREST = "random_forest"
FAMILY_HIST_GRADIENT_BOOSTING = "hist_gradient_boosting_classifier"
FAMILY_SOFT_VOTING = "soft_voting"
FAMILY_SIMPLICITY_ORDER = (
    FAMILY_LOGISTIC_REGRESSION,
    FAMILY_RANDOM_FOREST,
    FAMILY_HIST_GRADIENT_BOOSTING,
    FAMILY_SOFT_VOTING,
)

WEIGHTING_NONE = "none"
WEIGHTING_BALANCED = "sample_weight_balanced"
WEIGHTING_MODES = (WEIGHTING_NONE, WEIGHTING_BALANCED)

STAGE_A = "A"
STAGE_B = "B"
STAGE_C = "C"
SUPPORTED_STAGES = (STAGE_A,)
"""Únicas etapas que este runner puede ejecutar. B y C deben rechazarse
explícitamente en configuración/CLI (protocolo, alcance de esta tarea)."""


@dataclass(frozen=True)
class StageBounds:
    """Fronteras temporales autorizadas de una etapa (protocolo, sección 5)."""

    emission_start: date
    emission_end: date
    target_start: date
    target_end: date
    train_target_cutoff: date


STAGE_A_BOUNDS = StageBounds(
    emission_start=date(2015, 1, 7),
    emission_end=date(2022, 12, 28),
    target_start=date(2015, 1, 10),
    target_end=date(2022, 12, 31),
    train_target_cutoff=date(2022, 12, 31),
)

# Documentadas únicamente para que el runner pueda rechazar explícitamente
# cualquier intento de configurarlas (protocolo, secciones 5 y 10-11).
# No se usan para ejecutar nada en esta implementación.
STAGE_B_BOUNDS = StageBounds(
    emission_start=date(2023, 1, 1),
    emission_end=date(2023, 12, 28),
    target_start=date(2023, 1, 4),
    target_end=date(2023, 12, 31),
    train_target_cutoff=date(2022, 12, 31),
)
STAGE_C_BOUNDS = StageBounds(
    emission_start=date(2024, 1, 1),
    emission_end=date(2025, 12, 28),
    target_start=date(2024, 1, 4),
    target_end=date(2025, 12, 31),
    train_target_cutoff=date(2023, 12, 31),
)


@dataclass(frozen=True)
class LogisticRegressionGridSpec:
    C: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0)
    weighting: tuple[str, ...] = WEIGHTING_MODES
    solver: str = "lbfgs"
    penalty: str = "l2"
    max_iter: int = 2000

    @property
    def n_configs(self) -> int:
        return len(self.C) * len(self.weighting)


@dataclass(frozen=True)
class RandomForestGridSpec:
    n_estimators: tuple[int, ...] = (100, 300)
    max_depth: tuple[int | None, ...] = (4, 8, None)
    min_samples_leaf: tuple[int, ...] = (5, 20)
    weighting: tuple[str, ...] = WEIGHTING_MODES
    random_state: int = RANDOM_STATE
    n_jobs: int = 1

    @property
    def n_configs(self) -> int:
        return (
            len(self.n_estimators)
            * len(self.max_depth)
            * len(self.min_samples_leaf)
            * len(self.weighting)
        )


@dataclass(frozen=True)
class HistGradientBoostingGridSpec:
    learning_rate: tuple[float, ...] = (0.03, 0.1)
    max_iter: tuple[int, ...] = (100, 300)
    max_leaf_nodes: tuple[int, ...] = (15, 31)
    l2_regularization: tuple[float, ...] = (0.0, 1.0)
    max_depth: int | None = None
    weighting: tuple[str, ...] = WEIGHTING_MODES
    early_stopping: bool = False
    random_state: int = RANDOM_STATE

    @property
    def n_configs(self) -> int:
        return (
            len(self.learning_rate)
            * len(self.max_iter)
            * len(self.max_leaf_nodes)
            * len(self.l2_regularization)
            * len(self.weighting)
        )


@dataclass(frozen=True)
class ProtocolConfig:
    """Agrupa la configuración normativa completa de la Etapa A."""

    stage_bounds: StageBounds = STAGE_A_BOUNDS
    horizon_days: int = HORIZON_DAYS
    gap: int = GAP
    outer_n_splits: int = OUTER_N_SPLITS
    inner_n_splits: int = INNER_N_SPLITS
    lags: tuple[int, ...] = LAGS
    rolling_windows: tuple[int, ...] = ROLLING_WINDOWS
    decision_threshold: float = DECISION_THRESHOLD
    practical_margin_delta_mcc: float = PRACTICAL_MARGIN_DELTA_MCC
    bootstrap_block_days: int = BOOTSTRAP_BLOCK_DAYS
    bootstrap_replicas: int = BOOTSTRAP_REPLICAS_DEFAULT
    bootstrap_seed: int = BOOTSTRAP_SEED
    logistic_regression_grid: LogisticRegressionGridSpec = field(
        default_factory=LogisticRegressionGridSpec
    )
    random_forest_grid: RandomForestGridSpec = field(default_factory=RandomForestGridSpec)
    hist_gradient_boosting_grid: HistGradientBoostingGridSpec = field(
        default_factory=HistGradientBoostingGridSpec
    )


class UnsupportedStageError(ValueError):
    """Se solicitó una etapa distinta de A (B/C no implementadas en este runner)."""


def require_stage_a(stage: str) -> None:
    if stage not in SUPPORTED_STAGES:
        raise UnsupportedStageError(
            f"Etapa '{stage}' no soportada por este runner. Únicamente '{STAGE_A}' está "
            "implementada; B y C requieren un candidato ya congelado y autorización "
            "explícita de apertura de holdout (ver protocolo, secciones 10-11)."
        )
