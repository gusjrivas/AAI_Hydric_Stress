#!/usr/bin/env python
"""Verifica la evidencia restaurada desde el paquete de entrega (solo lectura).

No ejecuta modelos ni genera predicciones: comprueba manifiestos y SHA256SUMS
históricos, los congelados de sc-08-aux-hitl del repositorio y contrasta cifras
publicadas agregando predicciones originales ya existentes.

  python scripts/verify_delivery_evidence.py --root <AAI_ARTIFACT_ROOT>

Cada comprobación se informa como PASS, FAIL, BLOCKED o NOT_RUN. El código de salida
es 0 únicamente si TODAS las comprobaciones obligatorias se ejecutaron y aprobaron:
cualquier FAIL, BLOCKED o NOT_RUN (incluidas dependencias ausentes o una comprobación
obligatoria que no llegó a registrarse) da un código distinto de 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HITL_FREEZE = REPO / "openspec" / "changes" / "sc-08-aux-hitl"
FIGURES = {
    "A": {
        "soft_voting": 0.708028,
        "logistic_regression": 0.697968,
        "random_forest": 0.695372,
        "hist_gradient_boosting_classifier": 0.685799,
    }
}
REQUIRED = (
    "H: manifest/SHA256SUMS",
    "H: contract_sha256 congelado",
    "H: package_sha256 canónico",
    "H: response_sha256 congelado",
    "H: transcripción 1 congelada",
    "H: congelados y revisiones idénticos a los del repositorio (salvo CR/LF)",
    "Campaña: manifest/SHA256SUMS",
    "A/B/C: SHA256SUMS de la instantánea final",
    "C: integrity_manifest.json",
    *(f"A MCC {fam}" for fam in FIGURES["A"]),
    "A 2184 filas / 727 positivos",
    "B 362 filas / 96 positivos",
    "C MCC candidato",
    "C MCC persistencia",
    "C ROC-AUC candidato",
    "C Brier candidato",
    "C matriz del candidato",
    "C matriz de la persistencia",
)
STATES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
_LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    print(f"{status} {name}" + (f": {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(base: Path, rel: str) -> Path | None:
    """Resuelve rel dentro de base; None si es absoluta, sube con '..' o sale de base."""
    if not rel or rel.startswith(("/", "\\")) or ":" in rel or "\\" in rel:
        return None
    if any(part in ("", "..") for part in rel.split("/") if part != "."):
        return None
    target = (base / rel).resolve()
    return target if base.resolve() in target.parents else None


def check_sums(base: Path, sums: Path, label: str) -> None:
    if not sums.is_file():
        record("BLOCKED", label, f"falta {sums.name}")
        return
    ok = bad = malformed = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = _LINE.match(line)
        if not match:
            malformed += 1
            continue
        digest, rel = match.groups()
        target = _inside(base, rel.removeprefix("./"))
        if target is not None and target.is_file() and sha(target) == digest:
            ok += 1
        else:
            bad += 1
    if malformed or bad or not ok:
        reason = (
            "sin entradas válidas: no acredita integridad"
            if not ok and not (bad or malformed)
            else ""
        )
        record(
            "FAIL",
            label,
            f"{ok} OK, {bad} con diferencias, {malformed} líneas malformadas {reason}".strip(),
        )
        return
    record("PASS", label, f"{ok} OK, 0 con diferencias")


def same_text(a: Path, b: Path) -> bool:
    """Igualdad ignorando CR/LF: el repositorio puede estar en CRLF en Windows."""
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def check_hitl(root: Path) -> None:
    h = root / "hitl-complement-2026-09-21"
    check_sums(h, h / "manifest" / "SHA256SUMS", "H: manifest/SHA256SUMS")
    pf = json.loads((HITL_FREEZE / "human-package-freeze.json").read_text(encoding="utf-8"))
    rf = json.loads((HITL_FREEZE / "human-response-freeze.json").read_text(encoding="utf-8"))
    contract = h / "contract" / "contract-H-frozen.json"
    record(
        "PASS" if sha(contract) == pf["contract_sha256"] else "FAIL",
        "H: contract_sha256 congelado",
    )
    package = json.loads((h / "package" / "human-package.json").read_text(encoding="utf-8"))
    package.pop("package_sha256", None)
    canon = json.dumps(
        package, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    record(
        "PASS" if hashlib.sha256(canon).hexdigest() == pf["package_sha256"] else "FAIL",
        "H: package_sha256 canónico",
    )
    record(
        "PASS" if sha(h / "response" / "human-response.json") == rf["response_sha256"] else "FAIL",
        "H: response_sha256 congelado",
    )
    transcription = h / "response" / "human-response-transcription-1.json"
    record(
        "PASS" if sha(transcription) == rf["transcription_1_sha256"] else "FAIL",
        "H: transcripción 1 congelada",
    )
    pairs = [(contract, HITL_FREEZE / "contract-H-frozen.json")]
    pairs += [
        (h / "package" / "human-package-freeze.json", HITL_FREEZE / "human-package-freeze.json"),
        (h / "response" / "human-response-freeze.json", HITL_FREEZE / "human-response-freeze.json"),
    ]
    reviews = sorted((h / "reviews").glob("*"))
    pairs += [(f, HITL_FREEZE / "reviews" / f.name) for f in reviews]
    diffs = [a.name for a, b in pairs if not b.exists() or not same_text(a, b)]
    name = "H: congelados y revisiones idénticos a los del repositorio (salvo CR/LF)"
    if not reviews:
        record("FAIL", name, "sin informes de revisión")
    else:
        record("PASS" if not diffs else "FAIL", name, ", ".join(diffs))


def integrity_items(entries: object) -> list[tuple[str, str]]:
    """Normaliza files de un integrity_manifest; ValueError si está vacío o malformado."""
    if isinstance(entries, dict):
        raw = [(k, v.get("sha256") if isinstance(v, dict) else v) for k, v in entries.items()]
    elif isinstance(entries, list):
        raw = [(e.get("path"), e.get("sha256")) for e in entries]
    else:
        raise ValueError("files no es un objeto ni una lista")
    if not raw:
        raise ValueError("integrity_manifest sin archivos: no acredita integridad")
    for rel, digest in raw:
        if not isinstance(rel, str) or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("entrada malformada en integrity_manifest")
    return raw


def check_closure(root: Path) -> Path:
    c = root / "closure-campaign-2026-09-21"
    check_sums(c, c / "manifest" / "SHA256SUMS", "Campaña: manifest/SHA256SUMS")
    snap = c / "evidence-snapshots" / "final"
    check_sums(snap, snap / "SHA256SUMS", "A/B/C: SHA256SUMS de la instantánea final")
    stage_c = snap / "evidence" / "C"
    integrity = json.loads((stage_c / "integrity_manifest.json").read_text(encoding="utf-8"))
    label = "C: integrity_manifest.json"
    try:
        items = integrity_items(integrity["files"])
    except (KeyError, ValueError, AttributeError) as error:
        record("FAIL", label, str(error) or "sin 'files'")
        return snap / "evidence"
    good = bad = 0
    for rel, digest in items:
        target = _inside(stage_c, rel)
        if target is not None and target.is_file() and sha(target) == digest:
            good += 1
        else:
            bad += 1
    record("PASS" if not bad else "FAIL", label, f"{good} OK, {bad} con diferencias")
    return snap / "evidence"


def check_figures(ev: Path) -> None:
    try:
        import pandas as pd
        from sklearn.metrics import (
            brier_score_loss,
            confusion_matrix,
            matthews_corrcoef,
            roc_auc_score,
        )
    except ImportError:
        record("NOT_RUN", "Cifras publicadas", "faltan pandas/scikit-learn en el entorno")
        return

    def near(name: str, got: float, want: float) -> None:
        record("PASS" if abs(got - want) <= 5e-7 else "FAIL", name, f"{got:.6f} vs {want:.6f}")

    for fam, want in FIGURES["A"].items():
        df = pd.read_csv(ev / "A" / f"oof_predictions_{fam}.csv")
        near(f"A MCC {fam}", matthews_corrcoef(df.y_true, df.y_pred), want)
    a = pd.read_csv(ev / "A" / "oof_predictions_soft_voting.csv")
    record(
        "PASS" if (len(a), int(a.y_true.sum())) == (2184, 727) else "FAIL",
        "A 2184 filas / 727 positivos",
    )
    b = pd.read_csv(ev / "B" / "predictions_2023.csv")
    record(
        "PASS" if (len(b), int(b.y_true.sum())) == (362, 96) else "FAIL",
        "B 362 filas / 96 positivos",
    )
    c = pd.read_csv(ev / "C" / "predictions_2024_2025.csv")
    near("C MCC candidato", matthews_corrcoef(c.y_true, c.y_pred_candidate), 0.664770)
    near("C MCC persistencia", matthews_corrcoef(c.y_true, c.y_pred_persistence), 0.573438)
    near("C ROC-AUC candidato", roc_auc_score(c.y_true, c.y_score_candidate), 0.939049)
    near("C Brier candidato", brier_score_loss(c.y_true, c.y_score_candidate), 0.097512)
    cand = confusion_matrix(c.y_true, c.y_pred_candidate).tolist()
    pers = confusion_matrix(c.y_true, c.y_pred_persistence).tolist()
    record(
        "PASS" if cand == [[525, 75], [14, 114]] else "FAIL", "C matriz del candidato", str(cand)
    )
    record(
        "PASS" if pers == [[555, 45], [45, 83]] else "FAIL",
        "C matriz de la persistencia",
        str(pers),
    )


_ERRORS = (OSError, KeyError, ValueError, TypeError, AttributeError)


def run(root: Path) -> int:
    """Ejecuta todas las comprobaciones y devuelve el código de salida (0 solo si todo PASS)."""
    results.clear()
    steps = (
        ("H", lambda: check_hitl(root)),
        ("campaña A/B/C", lambda: check_figures(check_closure(root))),
    )
    for label, step in steps:
        try:
            step()
        except _ERRORS as error:
            record("BLOCKED", label, f"{type(error).__name__}: {error}")
    seen = {name for _, name, _ in results}
    for name in REQUIRED:
        if name not in seen:
            record("NOT_RUN", name, "comprobación obligatoria no ejecutada")
    status = {name: state for state, name, _ in results}
    bad = [s for s, _, _ in results if s != "PASS"]
    complete = all(status.get(name) == "PASS" for name in REQUIRED) and not bad
    summary = {s: sum(1 for r in results if r[0] == s) for s in STATES}
    print(summary, "->", "COMPLETA" if complete else "INCOMPLETA")
    return 0 if complete else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", type=Path, required=True)
    return run(ap.parse_args(argv).root)


if __name__ == "__main__":
    raise SystemExit(main())
