#!/usr/bin/env python
"""Verifica la evidencia restaurada desde el paquete de entrega (solo lectura).

No ejecuta modelos ni genera predicciones: comprueba manifiestos y SHA256SUMS
históricos, los congelados de sc-08-aux-hitl del repositorio y contrasta cifras
publicadas agregando predicciones originales ya existentes.

  python scripts/verify_delivery_evidence.py --root <AAI_ARTIFACT_ROOT>

Cada comprobación se informa como PASS, FAIL o NOT_RUN. Código de salida 1 si hay FAIL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    print(f"{status} {name}" + (f": {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sums(base: Path, sums: Path, label: str) -> None:
    if not sums.exists():
        record("BLOCKED", label, f"falta {sums.name}")
        return
    ok = bad = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        target = base / rel.removeprefix("./")
        if target.is_file() and sha(target) == digest:
            ok += 1
        else:
            bad += 1
    record("PASS" if not bad else "FAIL", label, f"{ok} OK, {bad} con diferencias")


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
    pairs += [(f, HITL_FREEZE / "reviews" / f.name) for f in sorted((h / "reviews").glob("*"))]
    diffs = [a.name for a, b in pairs if not b.exists() or not same_text(a, b)]
    record(
        "PASS" if not diffs else "FAIL",
        "H: congelados y revisiones idénticos a los del repositorio (salvo CR/LF)",
        ", ".join(diffs),
    )


def check_closure(root: Path) -> Path:
    c = root / "closure-campaign-2026-09-21"
    check_sums(c, c / "manifest" / "SHA256SUMS", "Campaña: manifest/SHA256SUMS")
    snap = c / "evidence-snapshots" / "final"
    check_sums(snap, snap / "SHA256SUMS", "A/B/C: SHA256SUMS de la instantánea final")
    integrity = json.loads((snap / "evidence" / "C" / "integrity_manifest.json").read_text("utf-8"))
    entries = integrity["files"]
    items = (
        entries.items()
        if isinstance(entries, dict)
        else [(e["path"], e["sha256"]) for e in entries]
    )
    good = bad = 0
    for rel, digest in items:
        digest = digest.get("sha256") if isinstance(digest, dict) else digest
        target = snap / "evidence" / "C" / rel
        if target.is_file() and sha(target) == digest:
            good += 1
        else:
            bad += 1
    record(
        "PASS" if not bad else "FAIL",
        "C: integrity_manifest.json",
        f"{good} OK, {bad} con diferencias",
    )
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


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", type=Path, required=True)
    root = ap.parse_args().root
    for step in (check_hitl,):
        try:
            step(root)
        except (OSError, KeyError, ValueError) as error:
            record("BLOCKED", step.__name__, f"{type(error).__name__}: {error}")
    try:
        ev = check_closure(root)
        check_figures(ev)
    except (OSError, KeyError, ValueError) as error:
        record("BLOCKED", "campaña A/B/C", f"{type(error).__name__}: {error}")
    failed = [r for r in results if r[0] == "FAIL"]
    summary = {
        s: sum(1 for r in results if r[0] == s) for s in ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
    }
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
