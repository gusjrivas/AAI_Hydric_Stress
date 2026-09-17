import scripts.demo_simulation.cli as cli_module
from scripts.demo_simulation.manifest import load_manifest


def test_prepare_and_run_via_cli(live_backend, reference_session_kwargs, capsys):
    exit_code = cli_module.main(
        [
            "prepare",
            "--start",
            reference_session_kwargs["start_date"].isoformat(),
            "--days",
            str(reference_session_kwargs["days"]),
            "--history-days",
            str(reference_session_kwargs["history_days"]),
            "--seed",
            str(reference_session_kwargs["seed"]),
            "--backend-url",
            live_backend.base_url,
            "--sessions-dir",
            str(live_backend.sessions_dir),
            "--data-dir",
            str(live_backend.data_dir),
            "--id",
            "demo-cli-session",
        ]
    )
    assert exit_code == 0
    assert "demo-cli-session" in capsys.readouterr().out

    exit_code = cli_module.main(
        [
            "run",
            "--id",
            "demo-cli-session",
            "--steps",
            "2",
            "--sessions-dir",
            str(live_backend.sessions_dir),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "días completados=2/5" in out

    exit_code = cli_module.main(
        ["status", "--id", "demo-cli-session", "--sessions-dir", str(live_backend.sessions_dir)]
    )
    assert exit_code == 0
    manifest = load_manifest(live_backend.sessions_dir, "demo-cli-session")
    assert manifest.cursor == 2


def test_prepare_cli_reports_invalid_config_without_crashing(
    live_backend, reference_session_kwargs, capsys
):
    exit_code = cli_module.main(
        [
            "prepare",
            "--start",
            reference_session_kwargs["start_date"].isoformat(),
            "--days",
            "0",
            "--history-days",
            str(reference_session_kwargs["history_days"]),
            "--seed",
            str(reference_session_kwargs["seed"]),
            "--backend-url",
            live_backend.base_url,
            "--sessions-dir",
            str(live_backend.sessions_dir),
            "--data-dir",
            str(live_backend.data_dir),
            "--id",
            "demo-cli-invalid",
        ]
    )
    assert exit_code == 1
    assert "No se preparó la sesión" in capsys.readouterr().err
