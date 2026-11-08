"""Pruebas de scripts/verify_delivery_evidence.py con datos sintéticos (sin campañas)."""

import hashlib
import json
import sys

import pytest

from scripts import verify_delivery_evidence as ve


def _h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sums(base, files, name="SHA256SUMS"):
    lines = [f"{_h((base / n).read_bytes())}  ./{n}" for n in files]
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _put(path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _fake_figures(ev):
    for name in ve.REQUIRED:
        if name.startswith(("A ", "B ", "C ")) and not name.startswith("C: "):
            ve.record("PASS", name)


@pytest.fixture()
def world(tmp_path, monkeypatch):
    """Raíz restaurada sintética y congelados sintéticos coherentes entre sí."""
    freeze = tmp_path / "freeze"
    monkeypatch.setattr(ve, "HITL_FREEZE", freeze)
    contract = b'{"contrato": 1}\n'
    package = {"datos": [1, 2], "package_sha256": "x"}
    body = {k: v for k, v in package.items() if k != "package_sha256"}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    response, transcription = b'{"respuesta": 1}\n', b'{"transcripcion": 1}\n'
    pfreeze = json.dumps({"contract_sha256": _h(contract), "package_sha256": _h(canon.encode())})
    rfreeze = json.dumps(
        {"response_sha256": _h(response), "transcription_1_sha256": _h(transcription)}
    )
    root = tmp_path / "root"
    h = root / "hitl-complement-2026-09-21"
    _put(freeze / "contract-H-frozen.json", contract)
    _put(freeze / "human-package-freeze.json", pfreeze.encode())
    _put(freeze / "human-response-freeze.json", rfreeze.encode())
    _put(freeze / "reviews" / "r.md", b"revision\n")
    _put(h / "contract" / "contract-H-frozen.json", contract)
    _put(h / "package" / "human-package.json", json.dumps(package).encode())
    _put(h / "package" / "human-package-freeze.json", pfreeze.encode())
    _put(h / "response" / "human-response.json", response)
    _put(h / "response" / "human-response-transcription-1.json", transcription)
    _put(h / "response" / "human-response-freeze.json", rfreeze.encode())
    _put(h / "reviews" / "r.md", b"revision\r\n")
    _sums(h, ["contract/contract-H-frozen.json", "reviews/r.md"], "manifest/SHA256SUMS")

    c = root / "closure-campaign-2026-09-21"
    _put(c / "code" / "HEAD.txt", b"abc\n")
    _sums(c, ["code/HEAD.txt"], "manifest/SHA256SUMS")
    snap = c / "evidence-snapshots" / "final"
    stage_c = snap / "evidence" / "C"
    _put(stage_c / "predictions.csv", b"a,b\n1,2\n")
    manifest = {"files": {"predictions.csv": _h(b"a,b\n1,2\n")}}
    _put(stage_c / "integrity_manifest.json", json.dumps(manifest).encode())
    _sums(snap, ["evidence/C/predictions.csv", "evidence/C/integrity_manifest.json"])
    return root


def test_complete_verification_returns_zero(world, monkeypatch):
    monkeypatch.setattr(ve, "check_figures", _fake_figures)
    assert ve.run(world) == 0
    assert {s for s, _, _ in ve.results} == {"PASS"}
    assert {n for _, n, _ in ve.results} >= set(ve.REQUIRED)


def test_empty_evidence_directory_is_not_a_pass(tmp_path):
    assert ve.run(tmp_path) == 1
    states = {s for s, _, _ in ve.results}
    assert "PASS" not in states and states <= {"BLOCKED", "NOT_RUN"}
    assert {n for _, n, _ in ve.results} >= set(ve.REQUIRED)


def test_blocked_mandatory_check_returns_nonzero(world, monkeypatch):
    monkeypatch.setattr(ve, "check_figures", _fake_figures)
    (world / "hitl-complement-2026-09-21" / "package" / "human-package.json").unlink()
    assert ve.run(world) == 1
    assert any(s == "BLOCKED" for s, _, _ in ve.results)
    assert any(s == "NOT_RUN" and n == "H: package_sha256 canónico" for s, n, _ in ve.results)


def test_missing_dependencies_prevent_figures_and_fail(world, monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", None)
    monkeypatch.setitem(sys.modules, "sklearn.metrics", None)
    assert ve.run(world) == 1
    assert (
        "NOT_RUN",
        "Cifras publicadas",
        "faltan pandas/scikit-learn en el entorno",
    ) in ve.results
    assert any(s == "NOT_RUN" and n == "C MCC candidato" for s, n, _ in ve.results)


@pytest.mark.parametrize("content", ["", "\n\n", "no es un hash\n", "abc  ./x\n"])
def test_empty_or_malformed_sums_fail(tmp_path, content):
    (tmp_path / "SHA256SUMS").write_text(content, encoding="utf-8")
    ve.results.clear()
    ve.check_sums(tmp_path, tmp_path / "SHA256SUMS", "malo")
    assert ve.results[-1][0] == "FAIL"
    assert " 0 OK" in ve.results[-1][2] or "malformadas" in ve.results[-1][2]


def test_sums_with_one_malformed_line_fail_even_if_others_match(tmp_path):
    _put(tmp_path / "a.txt", b"a")
    good = f"{_h(b'a')}  ./a.txt\n"
    (tmp_path / "SHA256SUMS").write_text(good + "basura\n", encoding="utf-8")
    ve.results.clear()
    ve.check_sums(tmp_path, tmp_path / "SHA256SUMS", "mixto")
    assert ve.results[-1][0] == "FAIL"


def test_sums_cannot_escape_the_base_directory(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    _put(tmp_path / "outside.txt", b"fuera")
    (base / "SHA256SUMS").write_text(f"{_h(b'fuera')}  ../outside.txt\n", encoding="utf-8")
    ve.results.clear()
    ve.check_sums(base, base / "SHA256SUMS", "escape")
    assert ve.results[-1][0] == "FAIL"


def test_sums_detect_alteration_and_missing_file(tmp_path):
    _put(tmp_path / "a.txt", b"uno")
    sums = _sums(tmp_path, ["a.txt"])
    ve.results.clear()
    ve.check_sums(tmp_path, sums, "ok")
    assert ve.results[-1][0] == "PASS"
    (tmp_path / "a.txt").write_bytes(b"alterado")
    ve.check_sums(tmp_path, sums, "alterado")
    assert ve.results[-1][0] == "FAIL"
    (tmp_path / "a.txt").unlink()
    ve.check_sums(tmp_path, sums, "falta")
    assert ve.results[-1][0] == "FAIL"


def test_missing_sums_is_blocked_not_pass(tmp_path):
    ve.results.clear()
    ve.check_sums(tmp_path, tmp_path / "SHA256SUMS", "sin manifiesto")
    assert ve.results[-1][0] == "BLOCKED"


@pytest.mark.parametrize("files", [{}, [], "texto", [{"path": "x"}], {"x": "corto"}])
def test_empty_or_malformed_integrity_manifest_fails(world, monkeypatch, files):
    monkeypatch.setattr(ve, "check_figures", _fake_figures)
    stage_c = world / "closure-campaign-2026-09-21/evidence-snapshots/final/evidence/C"
    (stage_c / "integrity_manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    assert ve.run(world) == 1
    entry = [r for r in ve.results if r[1] == "C: integrity_manifest.json"]
    assert entry and entry[0][0] == "FAIL"


def test_integrity_manifest_without_files_key_fails(world, monkeypatch):
    monkeypatch.setattr(ve, "check_figures", _fake_figures)
    stage_c = world / "closure-campaign-2026-09-21/evidence-snapshots/final/evidence/C"
    (stage_c / "integrity_manifest.json").write_text("{}", encoding="utf-8")
    assert ve.run(world) == 1


def test_altered_frozen_hash_fails(world, monkeypatch):
    monkeypatch.setattr(ve, "check_figures", _fake_figures)
    _put(world / "hitl-complement-2026-09-21/response/human-response.json", b"otra respuesta")
    assert ve.run(world) == 1
    assert any(s == "FAIL" and n == "H: response_sha256 congelado" for s, n, _ in ve.results)


def test_same_text_ignores_only_line_endings(tmp_path):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    a.write_bytes(b"x\r\ny\r\n")
    b.write_bytes(b"x\ny\n")
    c.write_bytes(b"x\ny!\n")
    assert ve.same_text(a, b)
    assert not ve.same_text(a, c)
