"""Pruebas de scripts/delivery_package.py con datos mínimos (sin artefactos reales)."""

import hashlib
import json
import zipfile

import pytest

from scripts import delivery_package as dp


def _selection(tmp_path, monkeypatch, group_extra=None, include=None):
    group = {
        "id": "g",
        "category": "demo",
        "required": True,
        "root": "R",
        "dir": "grp",
        "include": include or ["**"],
        "exclude": ["**/*.lock"],
        "restore_to": "demo/grp",
        "required_files": ["a.bin", "sub/b.json"],
    }
    group.update(group_extra or {})
    selection = {
        "roots": {"R": "x"},
        "groups": [group],
        "tracked_in_git": [],
        "known_missing": [{"id": "m"}],
        "excluded_on_purpose": [],
    }
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps(selection), encoding="utf-8")
    monkeypatch.setattr(dp, "SELECTION", sel)
    monkeypatch.setenv("AAI_SRC_R", str(tmp_path / "src"))
    monkeypatch.setenv("AAI_PORTABLE_MANIFEST", str(tmp_path / "pm.json"))
    return selection


@pytest.fixture()
def package(tmp_path, monkeypatch):
    src = tmp_path / "src" / "grp"
    (src / "sub").mkdir(parents=True)
    (src / "a.bin").write_bytes(b"\x00\r\nbytes")
    (src / "sub" / "b.json").write_bytes(b'{"x": 1}\r\n')
    (src / "root.lock").write_bytes(b"1")
    (src / "sub" / "deep.lock").write_bytes(b"1")
    _selection(tmp_path, monkeypatch)
    assert dp.build(tmp_path / "out", "abcdef1234567") == 0
    return tmp_path / "out" / "aai-hydric-stress-delivery-package-abcdef1.zip", tmp_path


def _forge(zpath, dest, restore_path=None, package_path=None, extra=None):
    """Crea un zip con manifiesto y SHA256SUMS coherentes pero con rutas manipuladas."""
    with zipfile.ZipFile(zpath) as zin:
        manifest = json.loads(zin.read(dp.MANIFEST))
        blobs = {i.filename: zin.read(i.filename) for i in zin.infolist()}
    first = manifest["files"][0]
    data = blobs[first["package_path"]]
    if package_path:
        del blobs[first["package_path"]]
        first["package_path"] = package_path
        blobs[package_path] = data
    if restore_path is not None:
        first["restore_path"] = restore_path
    for name, payload in (extra or {}).items():
        blobs[name] = payload
    blobs[dp.MANIFEST] = json.dumps(manifest).encode()
    sums = "".join(f"{f['sha256']}  {f['package_path']}\n" for f in manifest["files"])
    blobs[dp.SUMS] = sums.encode()
    with zipfile.ZipFile(dest, "w") as zout:
        for name, payload in blobs.items():
            zout.writestr(name, payload)
    return dest


def test_build_excludes_locks_at_any_depth_and_marks_partial(package):
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


@pytest.mark.parametrize(
    "restore_path",
    [
        "../outside.txt",
        "demo/../../outside.txt",
        "/abs/outside.txt",
        "C:/outside.txt",
        "C:outside.txt",
        "//server/share/outside.txt",
        "demo\\..\\outside.txt",
        "demo/./x.txt",
        "demo//x.txt",
        "",
    ],
)
def test_restore_rejects_unsafe_paths_without_writing(package, restore_path):
    zpath, tmp = package
    forged = _forge(zpath, tmp / "forged.zip", restore_path=restore_path)
    target = tmp / "dest"
    assert dp.restore(forged, target) != 0
    assert dp.verify(forged) == 1
    assert not (tmp / "outside.txt").exists()
    assert not target.exists() or not any(target.rglob("*"))


def test_restore_rejects_duplicate_and_ambiguous_destinations(package):
    zpath, tmp = package
    with zipfile.ZipFile(zpath) as z:
        manifest = json.loads(z.read(dp.MANIFEST))
    other = manifest["files"][1]["restore_path"]
    same = _forge(zpath, tmp / "dup.zip", restore_path=other)
    assert dp.restore(same, tmp / "d1") != 0
    case = _forge(zpath, tmp / "case.zip", restore_path=other.upper())
    assert dp.restore(case, tmp / "d2") != 0
    prefix = _forge(zpath, tmp / "pre.zip", restore_path=other + "/child")
    assert dp.restore(prefix, tmp / "d3") != 0
    for name in ("d1", "d2", "d3"):
        assert not (tmp / name).exists()


def test_verify_rejects_unsafe_package_path_and_stray_entries(package):
    zpath, tmp = package
    assert dp.verify(_forge(zpath, tmp / "p.zip", package_path="payload/../evil.txt")) == 1
    assert dp.verify(_forge(zpath, tmp / "q.zip", extra={"../evil.txt": b"x"})) == 1
    assert dp.verify(_forge(zpath, tmp / "r.zip", extra={"other/file.txt": b"x"})) == 1


def test_verify_directory_applies_same_rules(package):
    zpath, tmp = package
    forged = _forge(zpath, tmp / "forged.zip", restore_path="../outside.txt")
    out = tmp / "extracted"
    zipfile.ZipFile(forged).extractall(out)
    assert dp.verify(out) == 1
    good = tmp / "good"
    zipfile.ZipFile(zpath).extractall(good)
    assert dp.verify(good) == 0


def test_verify_directory_rejects_symlinks(package):
    zpath, tmp = package
    out = tmp / "extracted"
    zipfile.ZipFile(zpath).extractall(out)
    secret = tmp / "secret.txt"
    secret.write_bytes(b"s")
    link = out / "payload" / "demo" / "grp" / "link.txt"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("sin permiso para crear enlaces simbólicos")
    assert dp.verify(out) == 1


def test_restore_rejects_symlinked_target(package):
    zpath, tmp = package
    real = tmp / "real"
    real.mkdir()
    link = tmp / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("sin permiso para crear enlaces simbólicos")
    assert dp.restore(zpath, link) == 2
    assert not any(real.rglob("*"))


def test_expand_reports_each_missing_required_file(tmp_path, monkeypatch):
    (tmp_path / "src" / "grp").mkdir(parents=True)
    (tmp_path / "src" / "grp" / "present.txt").write_bytes(b"1")
    sel = _selection(
        tmp_path,
        monkeypatch,
        group_extra={"required_files": []},
        include=["present.txt", "missing.txt"],
    )
    _, problems = dp.expand(sel, {"R": tmp_path / "src"})
    assert problems == ["g: falta el archivo obligatorio missing.txt"]


def test_one_file_does_not_complete_a_wildcard_group(tmp_path, monkeypatch):
    (tmp_path / "src" / "grp").mkdir(parents=True)
    (tmp_path / "src" / "grp" / "only.txt").write_bytes(b"1")
    roots = {"R": tmp_path / "src"}
    extra = {"required_files": ["only.txt", "need.txt"]}
    sel = _selection(tmp_path, monkeypatch, group_extra=extra)
    _, problems = dp.expand(sel, roots)
    assert problems == ["g: falta el archivo obligatorio need.txt"]
    sel = _selection(tmp_path, monkeypatch, group_extra={"required_files": []})
    _, problems = dp.expand(sel, roots)
    assert problems == ["g: grupo obligatorio sin requisitos mínimos declarados"]


def test_optional_group_does_not_require_files(tmp_path, monkeypatch):
    (tmp_path / "src" / "grp").mkdir(parents=True)
    (tmp_path / "src" / "grp" / "x.txt").write_bytes(b"1")
    extra = {"required": False, "required_files": []}
    sel = _selection(tmp_path, monkeypatch, group_extra=extra)
    _, problems = dp.expand(sel, {"R": tmp_path / "src"})
    assert problems == []


def test_root_lock_is_excluded():
    assert dp._match("root.lock", ["**/*.lock"])
    assert dp._match("a/b/c.lock", ["**/*.lock"])
    assert not dp._match("root.locked", ["**/*.lock"])


def test_real_selection_declares_minimum_requirements():
    selection = json.loads(dp.SELECTION.read_text(encoding="utf-8"))
    by_id = {g["id"]: g for g in selection["groups"]}
    assert len(by_id["demo-bundles-ensamble"]["required_files"]) == 40
    retro = set(by_id["evidencia-ensamble-retrospectivo-2023"]["required_files"])
    assert {"metrics.json", "execution_manifest.json"} <= retro
    for g in selection["groups"]:
        if g["required"]:
            explicit = [i for i in g["include"] if not dp._WILDCARDS.search(i)]
            assert g.get("required_files") or explicit, g["id"]


def test_sha256_matches_hashlib(tmp_path):
    p = tmp_path / "f"
    p.write_bytes(b"abc")
    assert dp.sha256(p) == hashlib.sha256(b"abc").hexdigest()
