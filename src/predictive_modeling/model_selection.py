"""Selección automática del mejor modelo candidato por validación
cruzada temporal (spec predictive-modeling, requirement "Selección
automática del mejor modelo candidato, con evidencia insuficiente
informada explícitamente").
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from predictive_modeling.models import DEFAULT_HYPERPARAMETER_GRIDS, build_candidate_models
from predictive_modeling.training import diagnose_time_series_folds, tune_hyperparameters


def select_best_candidate(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    candidates: dict[str, object] | None = None,
    param_grids: dict[str, dict[str, list]] | None = None,
    n_splits: int = 5,
    scoring: str = "f1",
    gap: int = 0,
    random_state: int = 42,
) -> dict[str, Any]:
    """Ajusta cada modelo de `candidates` con `tune_hyperparameters`
    (validación cruzada temporal, con `gap` para evitar que el target de
    un fold de entrenamiento se solape con su fold de validación) y
    devuelve el de mayor `cv_mean_score`, ya entrenado sobre
    `X_train`/`y_train` completos. Si no se especifican
    `candidates`/`param_grids`, usa `build_candidate_models` y
    `DEFAULT_HYPERPARAMETER_GRIDS` (HU4) por defecto.

    El desempate entre candidatos con `cv_mean_score` idéntico prefiere
    el de menor `cv_std_score` (más estable) — nunca un nombre de modelo
    específico. Si aun así persiste un empate exacto, se resuelve de
    forma determinística (orden alfabético del nombre) y se documenta en
    `selection_warning`, en vez de ocultarlo. `selection_warning` también
    se completa cuando uno o más folds de validación no tienen ningún
    ejemplo positivo (`fold_diagnostics`, vía
    `predictive_modeling.training.diagnose_time_series_folds`) — en ese
    caso `cv_mean_score` puede no ser informativo para distinguir
    candidatos, y el sistema lo informa en vez de elegir en silencio.
    `selection_warning` es `None` cuando no aplica ninguno de los dos casos.
    """
    candidates = candidates if candidates is not None else build_candidate_models(random_state)
    param_grids = param_grids if param_grids is not None else DEFAULT_HYPERPARAMETER_GRIDS

    fold_diagnostics = diagnose_time_series_folds(y_train, n_splits=n_splits, gap=gap)
    invalid_folds = [
        fold
        for fold in fold_diagnostics
        if fold["train_positives"] == 0
        or fold["train_negatives"] == 0
        or fold["val_positives"] == 0
        or fold["val_negatives"] == 0
    ]
    if invalid_folds:
        details = "; ".join(
            f"fold {fold['fold']}: train(+/-)={fold['train_positives']}/{fold['train_negatives']}, "
            f"val(+/-)={fold['val_positives']}/{fold['val_negatives']}"
            for fold in invalid_folds
        )
        raise ValueError(
            "Selección automática no evaluable: folds sin ambas clases bajo la política común. "
            + details
        )

    results = {}
    for name, model in candidates.items():
        try:
            result = tune_hyperparameters(
                model,
                param_grids[name],
                X_train,
                y_train,
                n_splits=n_splits,
                scoring=scoring,
                gap=gap,
            )
        except ValueError:
            continue
        if math.isfinite(result["cv_mean_score"]) and math.isfinite(result["cv_std_score"]):
            results[name] = result

    if not results:
        raise ValueError("Ningún candidato tiene validación temporal evaluable; ampliar los datos.")

    best_name = max(
        results,
        key=lambda name: (results[name]["cv_mean_score"], -results[name]["cv_std_score"]),
    )
    best = results[best_name]

    tied_names = sorted(
        name
        for name, result in results.items()
        if result["cv_mean_score"] == best["cv_mean_score"]
        and result["cv_std_score"] == best["cv_std_score"]
    )

    warnings: list[str] = []
    if len(results) != len(candidates):
        warnings.append(
            "Candidatos sin validación finita: " + str(sorted(set(candidates) - set(results)))
        )
    if len(tied_names) > 1:
        warnings.append(
            f"Empate exacto en cv_mean_score y cv_std_score entre {tied_names}; se eligió "
            f"'{tied_names[0]}' de forma determinística (orden alfabético), no por evidencia "
            "de que sea mejor que los demás."
        )
        best_name = tied_names[0]
        best = results[best_name]

    return {
        "model": best["best_estimator"],
        "model_name": best_name,
        "cv_mean_score": best["cv_mean_score"],
        "cv_std_score": best["cv_std_score"],
        "fold_diagnostics": fold_diagnostics,
        "selection_warning": " ".join(warnings) if warnings else None,
    }
