#!/usr/bin/env python
"""Empaqueta, verifica y restaura los artefactos externos de la entrega.

Solo copia bytes de una selección explícita (docs/delivery/artifact-selection.json),
calcula SHA-256 y no ejecuta entrenamiento ni inferencia. Las rutas de origen se
pasan por variables de entorno AAI_SRC_<ROOT>; no se escriben en el manifiesto.

  build   --out DIR --commit SHA [--version V]   crea paquete (zip + manifiesto + SHA256SUMS)
  verify  PACKAGE                  comprueba un .zip o un directorio extraído
  restore PACKAGE --target DIR     restaura (valida rutas y hashes antes y después)

Las rutas del manifiesto son datos no confiables: se validan todas antes de
escribir cualquier archivo (sin rutas absolutas, de unidad, UNC, ".." ni enlaces).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path

SELECTION = Path(__file__).resolve().parents[1] / "docs" / "delivery" / "artifact-selection.json"
MANIFEST = "PACKAGE_MANIFEST.json"
SUMS = "SHA256SUMS"
TOP_LEVEL = {MANIFEST, SUMS, "RESTORE.md"}
_WILDCARDS = re.compile(r"[*?\[]")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _match(rel: str, patterns: list[str]) -> bool:
    for p in patterns:
        if p == "**":
            return True
        if p.endswith("/**") and rel.startswith(p[:-2]):
            return True
        if fnmatch.fnmatchcase(rel, p):
            return True
        # fnmatch exige el "/" de "**/": tambien debe coincidir un archivo en la raiz.
        if p.startswith("**/") and fnmatch.fnmatchcase(rel, p[3:]):
            return True
    return False


def unsafe_path_reason(value: object) -> str | None:
    """Devuelve el motivo por el que una ruta relativa del manifiesto no es segura."""
    if not isinstance(value, str) or not value:
        return "vacía o no es texto"
    if "\\" in value or "\x00" in value:
        return "contiene barra invertida o NUL"
    if value.startswith("/") or value.startswith("//"):
        return "absoluta o UNC"
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return "contiene componentes vacíos, '.' o '..'"
    if any(":" in p for p in parts):
        return "contiene ':' (unidad o flujo alterno)"
    if any(p.endswith((".", " ")) for p in parts):
        return "componente con punto o espacio final"
    return None


def manifest_errors(manifest: dict) -> list[str]:
    """Valida todas las rutas del manifiesto sin tocar el disco."""
    errors: list[str] = []
    seen_package: set[str] = set()
    seen_restore: set[str] = set()
    for item in manifest.get("files", []):
        pp, rp = item.get("package_path"), item.get("restore_path")
        for label, value in (("package_path", pp), ("restore_path", rp)):
            reason = unsafe_path_reason(value)
            if reason:
                errors.append(f"{label} {value!r} rechazada: {reason}")
        if isinstance(pp, str) and not pp.startswith("payload/"):
            errors.append(f"package_path {pp!r} fuera de payload/")
        for value, seen, label in (
            (pp, seen_package, "package_path"),
            (rp, seen_restore, "restore_path"),
        ):
            if isinstance(value, str):
                key = value.casefold()
                if key in seen:
                    errors.append(f"{label} duplicada o ambigua: {value!r}")
                seen.add(key)
    folded = {p.casefold() for p in seen_restore}
    for p in folded:
        if any(q.startswith(p + "/") for q in folded):
            errors.append(f"restore_path {p!r} es archivo y directorio a la vez")
    return errors


def expand(selection: dict, roots: dict[str, Path]) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    problems: list[str] = []
    for g in selection["groups"]:
        base = roots[g["root"]] / g["dir"]
        if not base.is_dir():
            problems.append(f"{g['id']}: falta el directorio de origen ({g['root']}/{g['dir']})")
            continue
        found: set[str] = set()
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            if _match(rel, g["include"]) and not _match(rel, g["exclude"]):
                found.add(rel)
                entries.append(
                    {
                        "group": g["id"],
                        "category": g["category"],
                        "required": g["required"],
                        "package_path": f"payload/{g['restore_to']}/{rel}",
                        "restore_path": f"{g['restore_to']}/{rel}",
                        "size": p.stat().st_size,
                        "sha256": sha256(p),
                        "_src": p,
                    }
                )
        if not found:
            problems.append(f"{g['id']}: la selección no encontró archivos")
        if g["required"]:
            required = list(g.get("required_files", [])) + [
                i for i in g["include"] if not _WILDCARDS.search(i)
            ]
            if not required:
                problems.append(f"{g['id']}: grupo obligatorio sin requisitos mínimos declarados")
            for rel in sorted(set(required) - found):
                problems.append(f"{g['id']}: falta el archivo obligatorio {rel}")
    return entries, problems


def build(out: Path, commit: str, version: str = "") -> int:
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
        "artifact_base_commit": commit,
        "tooling_note": "delivery_package.py llega con el PR 239, posterior a la base",
        "package_status": "PARTIAL" if partial else "COMPLETE",
        "build_problems": problems,
        "package_version": version or "v1",
        "known_missing": selection["known_missing"],
        "limitations": selection.get("limitations", []),
        "excluded_on_purpose": selection["excluded_on_purpose"],
        "tracked_in_git": selection["tracked_in_git"],
        "compatible_environment": {
            "python": "3.13.14",
            "numpy": "2.5.1",
            "pandas": "2.3.3",
            "pyarrow": "19.0.1",
            "scikit-learn": "1.9.0",
            "source": "bundle.json de cada componente; coincidencia exacta exigida por el cargador",
        },
        "files": [{k: v for k, v in e.items() if k != "_src"} for e in entries],
    }
    errors = manifest_errors(manifest)
    if errors:
        print("Manifiesto inválido:", *errors, sep="\n  ", file=sys.stderr)
        return 2
    name = f"aai-hydric-stress-delivery-package-{commit[:7]}" + (f"-{version}" if version else "")
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
    line = f"{sha256(zpath)}  {zpath.name}" + chr(10)
    (out / f"{name}.zip.sha256").write_bytes(line.encode("utf-8"))
    portable = Path(os.environ.get("AAI_PORTABLE_MANIFEST", out / "package-manifest.json"))
    portable.write_bytes(mtext.encode("utf-8"))
    print(
        f"{zpath} {zpath.stat().st_size} bytes, {len(entries)} archivos, "
        f"{manifest['package_status']}"
    )
    for p in problems:
        print("PROBLEMA:", p)
    return 0


def _open(package: Path):
    """Devuelve (leer, nombres, problemas_estructurales) para un zip o un directorio."""
    issues: list[str] = []
    if package.is_dir():
        root = package.resolve()
        names = []
        for p in sorted(package.rglob("*")):
            if p.is_symlink():
                issues.append(f"enlace simbólico no permitido: {p.relative_to(package).as_posix()}")
            elif p.is_file():
                names.append(p.relative_to(package).as_posix())

        def read(rel: str) -> bytes:
            target = package / rel
            if target.is_symlink() or root not in target.resolve().parents:
                raise ValueError(f"ruta fuera del paquete: {rel}")
            return target.read_bytes()

        return read, names, issues
    z = zipfile.ZipFile(package)
    names = []
    for info in z.infolist():
        if info.is_dir():
            continue
        if stat.S_ISLNK(info.external_attr >> 16):
            issues.append(f"enlace simbólico no permitido: {info.filename}")
        names.append(info.filename)
    if len(names) != len(set(names)):
        issues.append("nombres duplicados en el zip")
    return z.read, names, issues


def verify(package: Path) -> int:
    read, names, issues = _open(package)
    bad = len(issues)
    for issue in issues:
        print("FAIL", issue)
    for n in names:
        if n not in TOP_LEVEL and not n.startswith("payload/"):
            print(f"FAIL archivo fuera de payload/: {n}")
            bad += 1
        elif unsafe_path_reason(n):
            print(f"FAIL nombre inseguro: {n!r}")
            bad += 1
    manifest = json.loads(read(MANIFEST))
    errors = manifest_errors(manifest)
    for error in errors:
        print("FAIL", error)
    if errors or bad:
        print("FAIL: estructura o rutas del paquete inválidas; no se leyó ni escribió contenido")
        return 1
    listed = {f["package_path"]: f for f in manifest["files"]}
    present = {n for n in names if n.startswith("payload/")}
    for path, f in listed.items():
        if path not in present:
            print(f"FAIL falta {path}")
            bad += 1
            continue
        data = read(path)
        if hashlib.sha256(data).hexdigest() != f["sha256"] or len(data) != f["size"]:
            print(f"FAIL hash/tamaño {path}")
            bad += 1
    for extra in sorted(present - set(listed)):
        print(f"FAIL archivo no declarado {extra}")
        bad += 1
    sums = dict(reversed(line.split("  ", 1)) for line in read(SUMS).decode().splitlines())
    if {k: v["sha256"] for k, v in listed.items()} != sums:
        print("FAIL SHA256SUMS no coincide con el manifiesto")
        bad += 1
    verdict = "PASS" if not bad else "FAIL"
    print(f"{verdict}: {len(listed)} archivos verificados, estado={manifest['package_status']}")
    return 1 if bad else 0


def restore(package: Path, target: Path) -> int:
    if verify(package):  # valida rutas y hashes antes de escribir nada
        return 1
    if target.is_symlink():
        print("El destino no puede ser un enlace simbólico.", file=sys.stderr)
        return 2
    if target.exists() and any(target.iterdir()):
        print("El destino existe y no está vacío; usar un directorio nuevo.", file=sys.stderr)
        return 2
    read, _, _ = _open(package)
    manifest = json.loads(read(MANIFEST))
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    destinations = []
    for f in manifest["files"]:
        dest = (target / f["restore_path"]).resolve()
        if root not in dest.parents:
            print(f"FAIL destino fuera de la raíz de restauración: {f['restore_path']!r}")
            return 1
        destinations.append((dest, f))
    for dest, f in destinations:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if root not in dest.parent.resolve().parents and dest.parent.resolve() != root:
            print(f"FAIL escape por enlace en {f['restore_path']!r}")
            return 1
        dest.write_bytes(read(f["package_path"]))
    bad = sum(sha256(d) != f["sha256"] for d, f in destinations)
    print(f"{'PASS' if not bad else 'FAIL'}: restaurados {len(destinations)} archivos en {target}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--commit", required=True)
    b.add_argument("--version", default="")
    v = sub.add_parser("verify")
    v.add_argument("package", type=Path)
    r = sub.add_parser("restore")
    r.add_argument("package", type=Path)
    r.add_argument("--target", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return build(a.out, a.commit, a.version)
    if a.cmd == "verify":
        return verify(a.package)
    return restore(a.package, a.target)


if __name__ == "__main__":
    raise SystemExit(main())
