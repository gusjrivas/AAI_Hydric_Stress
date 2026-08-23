import pytest


@pytest.fixture(autouse=True)
def _reset_selection_cache():
    import app.pipeline as pipeline_module

    pipeline_module._selection_cache = None
    yield
    pipeline_module._selection_cache = None
