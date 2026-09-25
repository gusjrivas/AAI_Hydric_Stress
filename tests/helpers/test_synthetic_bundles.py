from predictive_modeling.operational_inference import load_operational_bundle
from tests.helpers.synthetic_bundles import (
    DEFAULT_FEATURE_COLUMNS,
    StubEstimator,
    write_single_bundle,
)


def test_write_single_bundle_is_loadable_by_the_real_unmodified_loader(tmp_path):
    import numpy as np

    model = StubEstimator(
        positive_probability=0.7, feature_names_in_=np.array(DEFAULT_FEATURE_COLUMNS, dtype=object)
    )
    calibrator = StubEstimator(
        positive_probability=0.7, feature_names_in_=np.array(DEFAULT_FEATURE_COLUMNS, dtype=object)
    )
    write_single_bundle(
        tmp_path,
        sensor_id="s1",
        horizon=1,
        model=model,
        calibrator=calibrator,
        model_identity_label="stub_model",
        calibrator_identity_label="stub_calibrator",
    )

    bundle = load_operational_bundle(tmp_path, sensor_id="s1", horizon=1)

    assert bundle.metadata["decision_threshold"] == 0.5
    assert bundle.metadata["contract"]["sensor_id"] == "s1"
