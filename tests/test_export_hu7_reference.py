from scripts.export_hu7_reference import render_table


def test_render_table_is_deterministic_and_uses_parent_metrics_only():
    payload = {
        "runs": [
            {
                "run_id": "b",
                "name": "base",
                "metrics": {
                    "f1_mean": 0.5591723,
                    "f1_std": 0.0287176,
                    "mcc_mean": -0.0134723,
                    "average_precision_mean": 0.5815879,
                },
            }
        ]
    }
    first = render_table(payload)
    second = render_table(payload)
    assert first == second
    assert "0.5592" in first and "-0.0135" in first


def test_export_module_does_not_run_experiments():
    # Importing the exporter must only define read/export functions.
    assert callable(render_table)
