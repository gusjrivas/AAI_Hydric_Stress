#!/usr/bin/env python
"""Empaqueta, verifica y restaura los artefactos externos de la entrega.

Solo copia bytes de una selección explícita (docs/delivery/artifact-selection.json),
calcula SHA-256 y no ejecuta entrenamiento ni inferencia. Las rutas de origen se
pasan por variables de entorno AAI_SRC_<ROOT>; no se escriben en el manifiesto.

  build   --out DIR            crea paquete (zip + manifiesto + SHA256SUMS)
  verify  PACKAGE              comprueba un .zip o un directorio extraído
  restore PACKAGE --target DIR restaura (verifica antes y después)
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

SELECTION = Path(__file__).resolve().parents[1] / "docs" / "delivery" / "artifact-selection.json"
MANIFEST = "PACKAGE_MANIFEST.json"
SUMS = "SHA256SUMS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _match(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or (p.endswith("/**") and rel.startswith(p[:-2])) or p == "**" for p in patterns)


def expand(selection: dict, roots: dict[str, Path]) -> tuple[list[dict], list[str]]:
    entries, problems = [], []
    for g in selection["groups"]:
        base = roots[g["root"]] / g["dir"]
        if not base.is_dir():
            problems.append(f"{g['id']}: falta el directorio de origen ({g['root']}/{g['dir']})")
            continue
        found = 0
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            if _match(rel, g["include"]) and not _match(rel, g["exclude"]):
                found += 1
                entries.append({
                    "group": g["id"], "category": g["category"], "required": g["required"],
                    "package_path": f"payload/{g['restore_to']}/{rel}",
                    "restore_path": f"{g['restore_to']}/{rel}",
                    "size": p.stat().st_size, "sha256": sha256(p), "_src": p,
                })
        if not found:
            problems.append(f"{g['id']}: la selección no encontró archivos")
    return entries, problems


def build(out: Path, commit: str) -> int:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    roots = {}
    for key in selection["roots"]:
        value = os.environ.get(f"AAI_SRC_{key}")
        if not value:
            print(f"Falta la variable AAI_SRC_{key}", file=sys.stderr)
            return 2
        roots[key] = Path(value)
    entries, problems = expand(selection, roots)
    out.mkdir(parents=True, exist_ok=True)
    partial = bool(problems) or bool(selection["known_missing"])
    manifest = {
        "schema": "aai_delivery_package.v1",
        "repository_commit": commit,
        "package_status": "PARTIAL" if partial else "COMPLETE",
        "build_problems": problems,
        "known_missing": selection["known_missing"],
        "excluded_on_purpose": selection["excluded_on_purpose"],
        "tracked_in_git": selection["tracked_in_git"],
        "compatible_environment": {
            "python": "3.13.x", "numpy": "2.5.1", "pandas": "2.3.3", "pyarrow": "19.0.1", "scikit-learn": "1.9.0",
            "source": "run_manifest.json de los bundles (los .joblib requieren la misma versión de scikit-learn)",
        },
        "files": [{k: v for k, v in e.items() if k != "_src"} for e in entries],
    }
    name = f"aai-hydric-stress-delivery-package-{commit[:7]}"
    zpath = out / f"{name}.zip"
    sums = "".join(f"{e['sha256']}  {e['package_path']}\n" for e in entries)
    mtext = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    restore_md = Path(__file__).resolve().parents[1] / "docs" / "delivery" / "RESTORE.md"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, mtext)
        z.writestr(SUMS, sums)
        z.write(restore_md, "RESTORE.md")
        for e in entries:
            z.write(e["_src"], e["package_path"])
    (out / f"{name}.zip.sha256").write_text(f"{sha256(zpath)}  {zpath.name}\n", encoding="utf-8")
    Path(os.environ.get("AAI_PORTABLE_MANIFEST", out / "package-manifest.json")).write_text(mtext, encoding="utf-8")
    print(f"{zpath} {zpath.stat().st_size} bytes, {len(entries)} archivos, estado={manifest['package_status']}")
    for p in problems:
        print("PROBLEMA:", p)
    return 0


def _open(package: Path):
    if package.is_dir():
        return lambda rel: (package / rel).read_bytes(), lambda: [p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()]
    z = zipfile.ZipFile(package)
    return z.read, z.namelist


def verify(package: Path) -> int:
    read, names = _open(package)
    manifest = json.loads(read(MANIFEST))
    bad = 0
    listed = {f["package_path"]: f for f in manifest["files"]}
    present = {n for n in names() if n.startswith("payload/")}
    for path, f in listed.items():
        if path not in present:
            print(f"FAIL falta {path}"); bad += 1; continue
        data = read(path)
        if hashlib.sha256(data).hexdigest() != f["sha256"] or len(data) != f["size"]:
            print(f"FAIL hash/tamaño {path}"); bad += 1
    for extra in sorted(present - set(listed)):
        print(f"FAIL archivo no declarado {extra}"); bad += 1
    sums = dict(reversed(line.split("  ", 1)) for line in read(SUMS).decode().splitlines())
    if {k: v["sha256"] for k, v in listed.items()} != sums:
        print("FAIL SHA256SUMS no coincide con el manifiesto"); bad += 1
    print(f"{'PASS' if not bad else 'FAIL'}: {len(listed)} archivos verificados, estado del paquete={manifest['package_status']}")
    return 1 if bad else 0


def restore(package: Path, target: Path) -> int:
    if verify(package):
        return 1
    if target.exists() and any(target.iterdir()):
        print("El destino existe y no está vacío; usar un directorio nuevo.", file=sys.stderr)
        return 2
    read, _ = _open(package)
    manifest = json.loads(read(MANIFEST))
    for f in manifest["files"]:
        dest = target / f["restore_path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(read(f["package_path"]))
    bad = sum(sha256(target / f["restore_path"]) != f["sha256"] for f in manifest["files"])
    print(f"{'PASS' if not bad else 'FAIL'}: restaurados {len(manifest['files'])} archivos en {target}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--out", type=Path, required=True); b.add_argument("--commit", required=True)
    v = sub.add_parser("verify"); v.add_argument("package", type=Path)
    r = sub.add_parser("restore"); r.add_argument("package", type=Path); r.add_argument("--target", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return build(a.out, a.commit)
    if a.cmd == "verify":
        return verify(a.package)
    return restore(a.package, a.target)


if __name__ == "__main__":
    raise SystemExit(main())
