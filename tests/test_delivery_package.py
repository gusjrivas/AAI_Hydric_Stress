"""Pruebas de scripts/delivery_package.py con datos mínimos (sin artefactos reales)."""

import json
import zipfile
from pathlib import Path

import pytest

from scripts import delivery_package as dp


@pytest.fixture()
def package(tmp_path, monkeypatch):
    src = tmp_path / "src" / "grp"
    (src / "sub").mkdir(parents=True)
    (src / "a.bin").write_bytes(b"\x00\r\nbytes")
    (src / "sub" / "b.json").write_bytes(b'{"x": 1}\r\n')
    (src / "skip.lock").write_bytes(b"1")
    selection = {
        "roots": {"R": "x"},
        "groups": [
            {
                "id": "g",
                "category": "demo",
                "required": True,
                "root": "R",
                "dir": "grp",
                "include": ["**"],
                "exclude": ["**/*.lock", "*.lock"],
                "restore_to": "demo/grp",
            }
        ],
        "tracked_in_git": [],
        "known_missing": [{"id": "m"}],
        "excluded_on_purpose": [],
    }
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps(selection), encoding="utf-8")
    monkeypatch.setattr(dp, "SELECTION", sel)
    monkeypatch.setenv("AAI_SRC_R", str(tmp_path / "src"))
    monkeypatch.setenv("AAI_PORTABLE_MANIFEST", str(tmp_path / "pm.json"))
    monkeypatch.setattr(dp, "MANIFEST", dp.MANIFEST)
    restore_md = Path(dp.__file__).resolve().parents[1] / "docs" / "delivery" / "RESTORE.md"
    assert restore_md.exists()
    assert dp.build(tmp_path / "out", "abcdef1234567") == 0
    return tmp_path / "out" / "aai-hydric-stress-delivery-package-abcdef1.zip", tmp_path


def test_build_excludes_locks_and_marks_partial(package):
    zpath, _ = package
    with zipfile.ZipFile(zpath) as z:
        manifest = json.loads(z.read("PACKAGE_MANIFEST.json"))
        assert not [n for n in z.namelist() if n.endswith(".lock")]
    assert manifest["package_status"] == "PARTIAL"
    assert len(manifest["files"]) == 2


def test_restore_preserves_bytes(package):
    zpath, tmp = package
    target = tmp / "restored"
    assert dp.restore(zpath, target) == 0
    assert (target / "demo/grp/a.bin").read_bytes() == b"\x00\r\nbytes"
    assert (target / "demo/grp/sub/b.json").read_bytes() == b'{"x": 1}\r\n'


def test_restore_refuses_non_empty_target(package):
    zpath, tmp = package
    (tmp / "busy").mkdir()
    (tmp / "busy" / "f").write_text("x")
    assert dp.restore(zpath, tmp / "busy") == 2


def test_verify_detects_tampering(package):
    zpath, tmp = package
    bad = tmp / "bad.zip"
    with zipfile.ZipFile(zpath) as zin, zipfile.ZipFile(bad, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith("a.bin"):
                data = b"tampered"
            zout.writestr(item.filename, data)
    assert dp.verify(bad) == 1
