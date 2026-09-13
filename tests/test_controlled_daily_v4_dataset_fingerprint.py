"""Tests de `dataset_fingerprint.compute_dataset_fingerprint` (hallazgo H-05;
revisión externa 2026-09-13, punto 2: huella sin pérdida de precisión).

Exclusivamente sobre fixtures sintéticas de la ventana de la Etapa A -- nunca
sobre B/C ni sobre los CSV reales de Pergamino."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiment_runner.controlled_daily_v4.config import PRIMARY_DEPTH_COLUMN
from experiment_runner.controlled_daily_v4.dataset_fingerprint import (
    DATASET_FINGERPRINT_FORMAT_VERSION,
    FINGERPRINT_COLUMNS,
    compute_dataset_fingerprint,
)
from experiment_runner.controlled_daily_v4.features import build_target, compute_p20_threshold
from experiment_runner.controlled_daily_v4.stage_a_runner import build_eligible_frame
from tests.controlled_daily_v4_fixtures import make_synthetic_daily_frame


def _eligible(seed: int = 11, n_days: int = 400):
    daily = make_synthetic_daily_frame(n_days=n_days, seed=seed)
    return build_eligible_frame(daily, PRIMARY_DEPTH_COLUMN)


def _minimal_frame(future_soil_moisture: list[float]) -> pd.DataFrame:
    """Frame mínimo con exactamente las columnas de `FINGERPRINT_COLUMNS`,
    para reproducir escenarios puntuales sin depender de todo el pipeline de
    features. Todas las columnas menos `future_soil_moisture` quedan
    constantes -- solo importa el valor bajo prueba."""
    n = len(future_soil_moisture)
    ts = pd.date_range("2015-01-07", periods=n, freq="D")
    data = {
        "feature_timestamp": ts,
        "target_timestamp": ts + pd.Timedelta(days=3),
        "soil_moisture": [0.35] * n,
        "RH2M": [70.0] * n,
        "ALLSKY_SFC_SW_DWN": [18.0] * n,
        "lag1": [0.35] * n,
        "lag2": [0.35] * n,
        "lag3": [0.35] * n,
        "roll_mean_3": [0.35] * n,
        "roll_mean_7": [0.35] * n,
        "future_soil_moisture": future_soil_moisture,
    }
    assert set(FINGERPRINT_COLUMNS).issubset(data), "el fixture debe cubrir todas las columnas"
    return pd.DataFrame(data)


def test_fingerprint_is_stable_across_repeated_calls_on_the_same_frame():
    eligible = _eligible()
    a = compute_dataset_fingerprint(eligible)
    b = compute_dataset_fingerprint(eligible.copy(deep=True))
    assert a["sha256"] == b["sha256"]
    assert a["n_rows"] == len(eligible)


def test_fingerprint_is_stable_under_row_order_shuffling():
    """El orden de filas de entrada no debería importar: la huella ordena
    explícitamente por `feature_timestamp` antes de calcular el hash."""
    eligible = _eligible()
    shuffled = eligible.sample(frac=1.0, random_state=123)
    assert (
        compute_dataset_fingerprint(eligible)["sha256"]
        == compute_dataset_fingerprint(shuffled)["sha256"]
    )


def test_fingerprint_changes_when_a_stage_a_value_changes():
    eligible = _eligible()
    mutated = eligible.copy(deep=True)
    first_index = mutated.index[0]
    mutated.loc[first_index, "soil_moisture"] = mutated.loc[first_index, "soil_moisture"] + 1.0

    original = compute_dataset_fingerprint(eligible)
    changed = compute_dataset_fingerprint(mutated)
    assert original["sha256"] != changed["sha256"]


def test_fingerprint_differs_between_independent_synthetic_seeds():
    a = compute_dataset_fingerprint(_eligible(seed=1))
    b = compute_dataset_fingerprint(_eligible(seed=2))
    assert a["sha256"] != b["sha256"]


def test_fingerprint_source_never_calls_pythons_hash_builtin():
    """Regresión directa del hallazgo H-05: `hash()` de Python no es estable
    entre procesos (afectado por `PYTHONHASHSEED`) y no debe usarse para
    calcular la huella -- se exige `hashlib.sha256` explícitamente.

    Nota: no se puede parchear `builtins.hash` en runtime para verificar esto,
    porque pandas lo usa internamente para operaciones no relacionadas (p.ej.
    validar que una etiqueta de columna es hasheable) antes de llegar a
    cualquier código de este módulo -- de ahí la verificación estática."""
    import inspect

    from experiment_runner.controlled_daily_v4 import dataset_fingerprint as module

    source = inspect.getsource(module.compute_dataset_fingerprint)
    assert "hashlib.sha256" in source
    assert " hash(" not in source and not source.strip().startswith("hash(")


def test_fingerprint_declares_columns_order_and_missing_value_policy():
    payload = compute_dataset_fingerprint(_eligible())
    assert payload["columns"][0] == "feature_timestamp"
    assert payload["row_order"] == "feature_timestamp_ascending"
    assert "missing_value_policy" in payload
    assert payload["scope"] == "stage_a_eligible_rows_only"


def test_fingerprint_persists_its_format_schema_version():
    payload = compute_dataset_fingerprint(_eligible())
    assert payload["schema_version"] == DATASET_FINGERPRINT_FORMAT_VERSION
    assert payload["float_encoding"] == "python_repr_round_trip"
    assert payload["timestamp_encoding"] == "iso_8601"


# --------------------------------------------------------------------------
# Regresión directa del hallazgo 2 (revisión externa 2026-09-13): precisión
# --------------------------------------------------------------------------


def test_fingerprint_distinguishes_the_exact_pair_reported_by_the_external_review():
    """`0.36482934020882524` y `0.3648293402088253` colisionaban con
    `"%.12g"` (12 dígitos significativos) -- deben producir huellas
    distintas si son valores `float64` distintos."""
    a_value = 0.36482934020882524
    b_value = 0.3648293402088253
    assert a_value != b_value, "el fixture requiere dos float64 realmente distintos"

    frame_a = _minimal_frame([a_value] * 30)
    frame_b = _minimal_frame([b_value] * 30)

    assert (
        compute_dataset_fingerprint(frame_a)["sha256"]
        != compute_dataset_fingerprint(frame_b)["sha256"]
    )


def test_fingerprint_distinguishes_a_value_from_its_adjacent_float64_via_nextafter():
    base = 0.3
    adjacent = np.nextafter(base, 0)
    assert adjacent != base

    frame_a = _minimal_frame([base] * 30)
    frame_b = _minimal_frame([adjacent] + [base] * 29)

    assert (
        compute_dataset_fingerprint(frame_a)["sha256"]
        != compute_dataset_fingerprint(frame_b)["sha256"]
    )


def test_fingerprint_changes_when_a_nextafter_mutation_flips_the_resulting_label():
    """Reproducción exacta de la revisión externa: con `future_soil_moisture`
    constante en `0.3`, cambiar únicamente la primera fila a
    `numpy.nextafter(0.3, 0)` deja `P20_train` en `0.3` pero hace que esa
    fila pase de etiqueta 0 a etiqueta 1 (target estrictamente `<`). La
    huella debe cambiar en consecuencia -- con `"%.12g"` no lo hacía."""
    n = 40
    clean = _minimal_frame([0.3] * n)
    mutated = _minimal_frame([float(np.nextafter(0.3, 0))] + [0.3] * (n - 1))

    p20_clean = compute_p20_threshold(clean["future_soil_moisture"])
    p20_mutated = compute_p20_threshold(mutated["future_soil_moisture"])
    assert p20_clean == pytest.approx(0.3)
    assert p20_mutated == pytest.approx(0.3)

    labels_clean = build_target(clean["future_soil_moisture"], p20_clean)
    labels_mutated = build_target(mutated["future_soil_moisture"], p20_mutated)
    assert labels_clean.sum() == 0
    assert labels_mutated.sum() == 1, "la mutación debe cambiar la etiqueta resultante"

    assert (
        compute_dataset_fingerprint(clean)["sha256"]
        != compute_dataset_fingerprint(mutated)["sha256"]
    )
