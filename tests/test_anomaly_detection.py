import numpy as np
import pandas as pd

from data_ingestion.schema import normalize_to_schema
from data_quality.anomaly_detection import (
    apply_anomaly_detector,
    detect_anomalies,
    evaluate_with_injected_anomalies,
    fit_anomaly_detector,
)


def _stable_series_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="D")
    temperature = 20.0 + rng.normal(0, 1.0, size=n)
    relative_humidity = 60.0 + rng.normal(0, 3.0, size=n)
    return normalize_to_schema(
        pd.DataFrame(
            {
                "timestamp": timestamps,
                "temperature": temperature,
                "relative_humidity": relative_humidity,
            }
        ),
        provenance="real",
    )


def test_detect_anomalies_adds_boolean_column_without_labels():
    df = _stable_series_df()

    result = detect_anomalies(df, columns=["temperature", "relative_humidity"])

    assert "is_anomaly" in result.columns
    assert result["is_anomaly"].dtype == bool
    assert len(result) == len(df)


def test_detect_anomalies_flags_an_extreme_injected_value():
    df = _stable_series_df().copy()
    df.loc[10, "temperature"] = 200.0  # anomalía evidente respecto de la serie estable

    result = detect_anomalies(df, columns=["temperature", "relative_humidity"], contamination=0.05)

    assert bool(result.loc[10, "is_anomaly"]) is True


def test_evaluate_with_injected_anomalies_reports_detection_rate():
    df = _stable_series_df(n=100)

    detection_rate = evaluate_with_injected_anomalies(
        df,
        columns=["temperature", "relative_humidity"],
        n_injected=5,
        random_state=0,
    )

    assert 0.0 <= detection_rate <= 1.0
    assert detection_rate > 0.5  # anomalías extremas inyectadas deberían detectarse en su mayoría


def test_apply_anomaly_detector_uses_train_boundaries_not_test_own_distribution():
    train_df = _stable_series_df(n=60, seed=0)
    detector = fit_anomaly_detector(train_df, columns=["temperature", "relative_humidity"])

    shifted_test_df = _stable_series_df(n=20, seed=1).copy()
    shifted_test_df["temperature"] = shifted_test_df["temperature"] + 100.0

    result = apply_anomaly_detector(
        shifted_test_df, columns=["temperature", "relative_humidity"], detector=detector
    )

    # Con un detector fiteado en train, todo el test desplazado queda fuera de
    # los límites aprendidos: la mayoría se marca anómala. Si en cambio se
    # fiteara un detector nuevo sobre el propio test (comportamiento viejo),
    # `contamination=0.05` forzaría ~5% marcado, sin importar el desplazamiento.
    assert result["is_anomaly"].mean() > 0.5


def test_fit_anomaly_detector_returns_a_fitted_isolation_forest():
    train_df = _stable_series_df(n=60, seed=0)

    detector = fit_anomaly_detector(train_df, columns=["temperature", "relative_humidity"])

    assert hasattr(detector, "predict")
    predictions = detector.predict(train_df[["temperature", "relative_humidity"]])
    assert set(predictions) <= {-1, 1}
