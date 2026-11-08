"""Pruebas de las comprobaciones auxiliares de scripts/verify_delivery_evidence.py."""

import hashlib

from scripts import verify_delivery_evidence as ve


def _sums(base, files):
    lines = [f"{hashlib.sha256((base / n).read_bytes()).hexdigest()}  ./{n}" for n in files]
    (base / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return base / "SHA256SUMS"


def test_check_sums_pass_and_detects_changes(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"uno")
    (tmp_path / "b.txt").write_bytes(b"dos")
    sums = _sums(tmp_path, ["a.txt", "b.txt"])
    ve.results.clear()
    ve.check_sums(tmp_path, sums, "ok")
    assert ve.results[-1][0] == "PASS"
    (tmp_path / "b.txt").write_bytes(b"alterado")
    ve.check_sums(tmp_path, sums, "alterado")
    assert ve.results[-1][0] == "FAIL"
    (tmp_path / "a.txt").unlink()
    ve.check_sums(tmp_path, sums, "falta")
    assert ve.results[-1][0] == "FAIL"


def test_missing_sums_is_blocked_not_pass(tmp_path):
    ve.results.clear()
    ve.check_sums(tmp_path, tmp_path / "SHA256SUMS", "sin manifiesto")
    assert ve.results[-1][0] == "BLOCKED"


def test_same_text_ignores_only_line_endings(tmp_path):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    a.write_bytes(b"x\r\ny\r\n")
    b.write_bytes(b"x\ny\n")
    c.write_bytes(b"x\ny!\n")
    assert ve.same_text(a, b)
    assert not ve.same_text(a, c)
