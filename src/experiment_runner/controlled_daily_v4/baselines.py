"""Baselines del protocolo (sección 13), reutilizables por las Etapas A, B y C.

Cada baseline tiene su propia regla de acceso a datos, ninguna ajusta su regla
usando etiquetas del conjunto de evaluación:

- Clase mayoritaria: aprendida exclusivamente de las etiquetas de `train`
  autorizado (acceso legítimo y requerido, no una fuga).
- Persistencia causal: usa `soil_moisture(feature_timestamp)` (el valor
  ACTUAL de la fila evaluada) frente a `P20_train` -- nunca
  `future_soil_moisture` de esa misma fila. Es además el baseline formal de
  comparación de la compuerta de la Etapa B (protocolo, sección 10).
- Estrés constante: predice `1` siempre, sin ajustar ningún parámetro.
"""

from __future__ import annotations

import numpy as np

MAJORITY_CLASS_TIE_BREAK = 0
"""Regla de desempate determinista para la clase mayoritaria.

El protocolo (sección 13) no documenta ninguna regla de desempate para un
conteo exactamente igual entre clase 0 y clase 1 en `train` -- este es un
caso borde infrecuente (el target se construye con un umbral P20, por lo que
un conteo balanceado 50/50 exacto no es el caso esperado), pero debe
resolverse de forma determinista y declarada ANTES de aplicarse, no elegida
según el resultado de ningún test. Se adopta como decisión de este encargo
(no atribuida a una aprobación externa) predecir la clase 0 (ausencia de
estrés) ante empate exacto, consistente con la convención ya usada por
`features.build_target` (una humedad futura exactamente igual a `P20_train`
produce clase 0, no clase 1: la igualdad nunca favorece la clase positiva)."""


def predict_majority_class_baseline(y_train: np.ndarray, n_predictions: int) -> np.ndarray:
    """`argmax` del conteo de clases de `y_train` (el `train` autorizado del
    fold/etapa correspondiente), repetido `n_predictions` veces. Nunca
    consulta ninguna etiqueta del conjunto de evaluación."""
    y_train = np.asarray(y_train)
    if y_train.size == 0:
        raise ValueError(
            "predict_majority_class_baseline: 'y_train' está vacío -- no se puede "
            "determinar la clase mayoritaria sin etiquetas de entrenamiento"
        )
    n_positive = int((y_train == 1).sum())
    n_negative = int((y_train == 0).sum())
    if n_positive > n_negative:
        majority = 1
    elif n_negative > n_positive:
        majority = 0
    else:
        majority = MAJORITY_CLASS_TIE_BREAK
    return np.full(int(n_predictions), majority, dtype=int)


def predict_persistence_baseline_v4(
    soil_moisture_current: np.ndarray, p20_train: float
) -> np.ndarray:
    """`stress = 1` si `soil_moisture_current < p20_train` (estrictamente) --
    exactamente la misma convención de igualdad que `features.build_target`
    (una igualdad exacta produce clase 0, nunca 1). `soil_moisture_current`
    debe ser el valor de humedad en `feature_timestamp` (el presente de la
    fila evaluada), nunca `future_soil_moisture` de esa misma fila."""
    soil_moisture_current = np.asarray(soil_moisture_current, dtype=float)
    return (soil_moisture_current < float(p20_train)).astype(int)


def predict_constant_stress_baseline(n_predictions: int) -> np.ndarray:
    """Predice `1` para toda fila, sin ajustar ningún parámetro a partir de
    ninguna etiqueta de entrenamiento ni de evaluación."""
    return np.ones(int(n_predictions), dtype=int)


__all__ = [
    "MAJORITY_CLASS_TIE_BREAK",
    "predict_constant_stress_baseline",
    "predict_majority_class_baseline",
    "predict_persistence_baseline_v4",
]
