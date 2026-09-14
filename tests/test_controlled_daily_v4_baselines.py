from __future__ import annotations

import numpy as np

from experiment_runner.controlled_daily_v4.baselines import (
    MAJORITY_CLASS_TIE_BREAK,
    predict_constant_stress_baseline,
    predict_majority_class_baseline,
    predict_persistence_baseline_v4,
)


def test_majority_class_baseline_matches_argmax_of_train_counts():
    y_train = np.array([0, 0, 0, 1, 1])
    preds = predict_majority_class_baseline(y_train, n_predictions=4)
    assert (preds == 0).all()

    y_train_positive_majority = np.array([1, 1, 1, 0])
    preds2 = predict_majority_class_baseline(y_train_positive_majority, n_predictions=3)
    assert (preds2 == 1).all()


def test_majority_class_baseline_tie_break_is_deterministic_and_documented():
    y_train = np.array([0, 1, 0, 1])
    preds = predict_majority_class_baseline(y_train, n_predictions=5)
    assert (preds == MAJORITY_CLASS_TIE_BREAK).all()
    assert MAJORITY_CLASS_TIE_BREAK == 0


def test_majority_class_baseline_requires_nonempty_train_labels():
    import pytest

    with pytest.raises(ValueError):
        predict_majority_class_baseline(np.array([]), n_predictions=3)


def test_majority_class_baseline_never_uses_evaluation_labels():
    """El baseline se fija exclusivamente con `train`: cambiar solo las
    etiquetas de evaluación (que este baseline ni siquiera recibe como
    argumento) no puede alterar su predicción."""
    y_train = np.array([0, 0, 0, 1])
    preds_a = predict_majority_class_baseline(y_train, n_predictions=10)
    preds_b = predict_majority_class_baseline(y_train, n_predictions=10)
    assert np.array_equal(preds_a, preds_b)


def test_persistence_baseline_predicts_stress_when_strictly_below_p20():
    soil_moisture = np.array([0.1, 0.2, 0.3, 0.4])
    p20 = 0.3
    preds = predict_persistence_baseline_v4(soil_moisture, p20)
    assert list(preds) == [1, 1, 0, 0]


def test_persistence_baseline_exact_equality_to_p20_train_produces_class_0():
    soil_moisture = np.array([0.3])
    preds = predict_persistence_baseline_v4(soil_moisture, p20_train=0.3)
    assert preds[0] == 0


def test_persistence_baseline_never_looks_at_future_soil_moisture():
    """La firma de la función solo acepta la humedad ACTUAL: no hay forma de
    pasarle accidentalmente `future_soil_moisture`. Este test documenta la
    invariancia verificando que, dado el mismo `soil_moisture` actual, la
    predicción no cambia sin importar qué otro valor (simulando humedad
    futura) exista en el contexto de quien llama."""
    soil_moisture_current = np.array([0.1, 0.5])
    p20 = 0.3
    preds_1 = predict_persistence_baseline_v4(soil_moisture_current, p20)
    # Ningún parámetro de "futuro" existe en la firma -- se documenta la
    # ausencia estructural de esa posibilidad, no solo el resultado numérico.
    import inspect

    sig = inspect.signature(predict_persistence_baseline_v4)
    assert "future" not in " ".join(sig.parameters) and list(preds_1) == [1, 0]


def test_constant_stress_baseline_always_predicts_one():
    preds = predict_constant_stress_baseline(7)
    assert (preds == 1).all()
    assert len(preds) == 7


def test_constant_stress_baseline_ignores_any_training_or_evaluation_state():
    assert list(predict_constant_stress_baseline(3)) == [1, 1, 1]
