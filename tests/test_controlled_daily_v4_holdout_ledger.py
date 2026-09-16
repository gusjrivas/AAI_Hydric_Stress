"""Pruebas sintéticas del ledger de protección del holdout (`holdout_ledger.py`).

Nunca lee datos reales de Pergamino/holdout: ejercita exclusivamente el
mecanismo de persistencia/concurrencia con archivos SQLite temporales."""

from __future__ import annotations

import multiprocessing

import pytest

from experiment_runner.controlled_daily_v4 import holdout_ledger as hl


def _key(depth="soil_moisture_0_to_7cm"):
    return hl.compute_holdout_identity_key(
        protocol_id="controlled_daily_v4_external_pergamino",
        site="pergamino",
        depth_column=depth,
        period_start="2024-01-04",
        period_end="2025-12-31",
    )


def test_identity_key_independent_of_commit_candidate_or_output_dir():
    """La identidad del holdout depende solo de protocolo/sitio/profundidad/
    período -- la función ni siquiera acepta esos otros datos como parámetro."""
    key_a = _key()
    key_b = _key()
    assert key_a == key_b
    # Cambiar la profundidad SÍ cambia la identidad (son holdouts distintos).
    assert _key("soil_moisture_7_to_28cm") != key_a


def test_init_ledger_creates_absent_state(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_ABSENT
    assert not state.finalized


def test_init_ledger_rejects_replacing_existing_ledger(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    with pytest.raises(hl.HoldoutLedgerAlreadyInitializedError):
        hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)


def test_missing_ledger_file_is_indeterminate_never_absent(tmp_path):
    """Un ledger que nunca se inicializó nunca se trata como AUSENTE."""
    path = tmp_path / "never_created.sqlite3"
    state = hl.read_holdout_state(path, _key(), expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE


def test_corrupt_ledger_file_is_indeterminate(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    path.write_bytes(b"not a sqlite database at all")
    state = hl.read_holdout_state(path, _key(), expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE


def test_mode_mismatch_is_rejected_explicitly(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SCIENTIFIC, holdout_key=key)
    with pytest.raises(hl.HoldoutLedgerModeMismatchError):
        hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    with pytest.raises(hl.HoldoutLedgerModeMismatchError):
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")


def test_reserve_then_confirm_then_finalize_happy_path(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)

    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1")
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1", authorized_by="tester"
    )
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_CONFIRMED
    assert state.authorized_by == "tester"
    assert not state.finalized

    hl.finalize_holdout(
        path,
        key,
        mode=hl.LEDGER_MODE_SYNTHETIC,
        attempt_id="attempt-1",
        result_reference="/tmp/stage_c_out",
    )
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_CONFIRMED
    assert state.finalized
    assert state.finalized_result_reference == "/tmp/stage_c_out"


def test_reservation_rejects_second_reservation_when_confirmed(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")
    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", authorized_by="tester"
    )

    with pytest.raises(hl.HoldoutAlreadyProtectedError) as exc_info:
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a2")
    assert exc_info.value.state == hl.STATE_CONFIRMED


def test_changing_attempt_id_never_bypasses_a_confirmed_holdout(tmp_path):
    """Cambiar el 'intento' (equivalente a cambiar commit/candidato/output-dir
    en la CLI real) nunca habilita otra apertura del MISMO holdout."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-original")
    hl.confirm_holdout_open(
        path,
        key,
        mode=hl.LEDGER_MODE_SYNTHETIC,
        attempt_id="attempt-original",
        authorized_by="tester",
    )
    for other_attempt in ("attempt-different-commit", "attempt-different-candidate", "retry"):
        with pytest.raises(hl.HoldoutAlreadyProtectedError):
            hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id=other_attempt)


def test_indeterminate_reservation_blocks_access_and_is_not_reset(tmp_path):
    """Simula una interrupción entre reserva (paso 2) y confirmación (paso 3):
    el registro queda INDETERMINADA, bloquea el acceso igual que CONFIRMADA,
    y no se borra ni se reinicializa por una nueva reserva."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-crashed")
    # Nunca se llama a confirm_holdout_open: simula la caída exactamente aquí.

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutAlreadyProtectedError) as exc_info:
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-retry")
    assert exc_info.value.state == hl.STATE_INDETERMINATE

    # El estado sigue INDETERMINADA después del intento de reintento -- nunca
    # se borró ni se reinicializó automáticamente.
    state_after = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state_after.state == hl.STATE_INDETERMINATE


def test_confirm_with_wrong_attempt_id_leaves_indeterminate(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-real")

    with pytest.raises(hl.HoldoutReservationLostError):
        hl.confirm_holdout_open(
            path,
            key,
            mode=hl.LEDGER_MODE_SYNTHETIC,
            attempt_id="attempt-impostor",
            authorized_by="tester",
        )
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE


def test_reserve_without_init_raises_not_initialized(tmp_path):
    path = tmp_path / "never_initialized.sqlite3"
    with pytest.raises(hl.HoldoutLedgerNotInitializedError):
        hl.reserve_holdout(path, _key(), mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")


def test_confirm_requires_nonempty_authorized_by(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")
    with pytest.raises(ValueError):
        hl.confirm_holdout_open(
            path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", authorized_by=""
        )


def test_finalize_requires_confirmed_state(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    with pytest.raises(hl.HoldoutLedgerError):
        hl.finalize_holdout(
            path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", result_reference="/x"
        )


def _tamper_ledger_meta(path, **columns):
    import sqlite3 as _sqlite3

    assignments = ", ".join(f"{col} = ?" for col in columns)
    with _sqlite3.connect(str(path)) as conn:
        conn.execute(f"UPDATE ledger_meta SET {assignments}", list(columns.values()))
        conn.commit()


def test_unknown_schema_version_is_indeterminate_and_blocks_reservation(tmp_path):
    """Revisión dirigida (hallazgo 4): un `schema_version` desconocido nunca
    habilita `read_holdout_state` a devolver AUSENTE ni `reserve_holdout` a
    reservar -- ambas deben rechazar/bloquear explícitamente."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    _tamper_ledger_meta(path, schema_version="UNKNOWN_SCHEMA")

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutLedgerSchemaError):
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")


def test_incoherent_mode_metadata_is_indeterminate_and_blocks_reservation(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    _tamper_ledger_meta(path, mode="not_a_real_mode")

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutLedgerSchemaError):
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")


def test_incoherent_registry_state_is_indeterminate(tmp_path):
    """Un valor de `state` fuera de `STATES` (registro corrupto/tamperado) se
    trata como INDETERMINADA, nunca como uno de los estados válidos."""
    import sqlite3 as _sqlite3

    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    with _sqlite3.connect(str(path)) as conn:
        conn.execute("UPDATE holdout_registry SET state = ? WHERE holdout_key = ?", ("BOGUS", key))
        conn.commit()

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE


def _tamper_registry_row(path, key, **columns):
    import sqlite3 as _sqlite3

    assignments = ", ".join(f"{col} = ?" for col in columns)
    with _sqlite3.connect(str(path)) as conn:
        conn.execute(
            f"UPDATE holdout_registry SET {assignments} WHERE holdout_key = ?",
            [*columns.values(), key],
        )
        conn.commit()


def test_absent_state_with_populated_confirmation_fields_is_incoherent(tmp_path):
    """Revisión dirigida (hallazgo 4, segunda ronda): un registro AUSENTE con
    `confirmed_at`/`finalized_at`/`finalized_result_reference` ya poblados es
    contradictorio -- nunca se trata como AUSENTE real, y nunca habilita una
    nueva reserva."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    _tamper_registry_row(
        path,
        key,
        confirmed_at=1.0,
        finalized_at=2.0,
        finalized_result_reference="/tmp/stale_result",
        authorized_by="nobody",
    )

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutRegistryCoherenceError):
        hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")

    # No se reparó ni se reseteó ninguna columna por el intento de reserva.
    state_after = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state_after.state == hl.STATE_INDETERMINATE


def test_indeterminate_state_with_confirmation_fields_is_incoherent(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1")
    _tamper_registry_row(path, key, confirmed_at=1.0, authorized_by="nobody")

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutRegistryCoherenceError):
        hl.confirm_holdout_open(
            path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1", authorized_by="tester"
        )


def test_confirmed_state_missing_confirmation_columns_is_incoherent(tmp_path):
    """Un estado CONFIRMADA sin las columnas que una confirmación real deja
    pobladas (por ejemplo, sin `authorized_by`) nunca se finaliza."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1")
    _tamper_registry_row(path, key, state=hl.STATE_CONFIRMED, confirmed_at=1.0, authorized_by=None)

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE

    with pytest.raises(hl.HoldoutRegistryCoherenceError):
        hl.finalize_holdout(
            path,
            key,
            mode=hl.LEDGER_MODE_SYNTHETIC,
            attempt_id="attempt-1",
            result_reference="/tmp/x",
        )


def test_confirmed_state_with_partial_finalization_is_incoherent(tmp_path):
    """`finalized_at` poblado sin `finalized_result_reference` (o viceversa)
    es una finalización parcial, incoherente por sí misma -- se bloquea como
    INDETERMINADA en lectura."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1")
    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1", authorized_by="tester"
    )
    _tamper_registry_row(path, key, finalized_at=1.0, finalized_result_reference=None)

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE


def test_confirm_and_finalize_never_create_ledger_implicitly_when_missing(tmp_path):
    """Ni `confirm_holdout_open` ni `finalize_holdout` deben crear un archivo
    de ledger vacío cuando el esperado no existe (`sqlite3.connect` lo haría
    de forma implícita si no se verifica antes)."""
    path = tmp_path / "never_initialized.sqlite3"
    with pytest.raises(hl.HoldoutLedgerNotInitializedError):
        hl.confirm_holdout_open(
            path, _key(), mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", authorized_by="tester"
        )
    assert not path.exists()

    with pytest.raises(hl.HoldoutLedgerNotInitializedError):
        hl.finalize_holdout(
            path, _key(), mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", result_reference="/x"
        )
    assert not path.exists()


def test_finalize_rejects_wrong_attempt_id(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")
    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", authorized_by="tester"
    )
    with pytest.raises(hl.HoldoutFinalizationOwnershipError):
        hl.finalize_holdout(
            path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a2", result_reference="/x"
        )
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert not state.finalized


def test_second_finalization_never_silently_replaces_reference(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1")
    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", authorized_by="tester"
    )
    hl.finalize_holdout(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", result_reference="/original"
    )
    with pytest.raises(hl.HoldoutAlreadyFinalizedError):
        hl.finalize_holdout(
            path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="a1", result_reference="/replaced"
        )
    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.finalized_result_reference == "/original"


# --------------------------------------------------------------------------
# Concurrencia real: dos procesos separados contendiendo por el mismo ledger.
# No se sustituye por mocks del ledger -- procesos reales, mismo archivo.
# --------------------------------------------------------------------------


def _concurrent_reserve_worker(path_str: str, key: str, attempt_id: str, result_queue) -> None:
    try:
        hl.reserve_holdout(path_str, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id=attempt_id)
        result_queue.put(("ok", attempt_id))
    except hl.HoldoutAlreadyProtectedError:
        result_queue.put(("rejected", attempt_id))
    except Exception as exc:  # pragma: no cover - solo para diagnóstico de fallos de test
        result_queue.put(("error", f"{attempt_id}: {exc!r}"))


def test_two_concurrent_processes_only_one_wins_the_reservation(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)

    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    proc_a = ctx.Process(
        target=_concurrent_reserve_worker, args=(str(path), key, "process-a", queue)
    )
    proc_b = ctx.Process(
        target=_concurrent_reserve_worker, args=(str(path), key, "process-b", queue)
    )
    proc_a.start()
    proc_b.start()
    proc_a.join(timeout=30)
    proc_b.join(timeout=30)
    assert proc_a.exitcode == 0
    assert proc_b.exitcode == 0

    outcomes = [queue.get(timeout=5), queue.get(timeout=5)]
    statuses = sorted(status for status, _ in outcomes)
    assert statuses == ["ok", "rejected"], outcomes

    state = hl.read_holdout_state(path, key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_INDETERMINATE  # reservado, todavía sin confirmar


def test_process_restart_reservation_still_protects_holdout(tmp_path):
    """Reinicio del proceso (nueva conexión sqlite desde cero, como ocurriría
    tras reiniciar el runner): la reserva/apertura sigue protegiendo el
    holdout, sin ningún estado en memoria que sobreviva entre invocaciones."""
    path = tmp_path / "ledger.sqlite3"
    key = _key()
    hl.init_ledger(path, mode=hl.LEDGER_MODE_SYNTHETIC, holdout_key=key)
    hl.reserve_holdout(path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1")
    hl.confirm_holdout_open(
        path, key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-1", authorized_by="tester"
    )

    # Simula un "reinicio": ninguna variable Python sobrevive, solo el archivo.
    state = hl.read_holdout_state(str(path), key, expected_mode=hl.LEDGER_MODE_SYNTHETIC)
    assert state.state == hl.STATE_CONFIRMED
    with pytest.raises(hl.HoldoutAlreadyProtectedError):
        hl.reserve_holdout(str(path), key, mode=hl.LEDGER_MODE_SYNTHETIC, attempt_id="attempt-2")
