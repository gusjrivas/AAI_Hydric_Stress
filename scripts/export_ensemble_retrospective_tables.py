"""Export versioned CSV tables from the canonical aggregate evaluation JSON.

This extractor never reads predictions or runs inference. It fails closed on
the two predeclared canonical source hashes and preserves JSON numeric precision
by parsing floating-point numbers as ``Decimal`` and never rounding CSV cells.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

CANONICAL_EXECUTION = "pergamino-ensemble-retrospective-2023-20260927T062026Z"
CANONICAL_SOURCE_DIR = (
    Path(r"C:\Repo\AAI_Hydric_Stress_ensemble_retrospective_runtime") / CANONICAL_EXECUTION
)
EXPECTED_METRICS_SHA256 = "6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732"
EXPECTED_MANIFEST_SHA256 = "780386ff58b490a452d77f968e61efcd15b998a97d28de2f908ab1a346d9d33b"
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "research"
    / "tables"
    / "ensemble-retrospective-2023"
)
METHOD_ORDER = (
    "hist_gradient_boosting_classifier",
    "logistic_regression",
    "random_forest",
    "average",
    "persistence",
    "majority",
)
PROBABILISTIC_METHODS = set(METHOD_ORDER[:4])
OUTPUT_FILES = (
    "evaluation_support.csv",
    "classification_metrics.csv",
    "paired_mcc_comparisons.csv",
    "episode_onset.csv",
    "reliability_bins.csv",
    "README.md",
)


class ExportError(RuntimeError):
    """The canonical aggregate source or output contract is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_exact(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream, parse_float=Decimal)
    if not isinstance(value, dict):
        raise ExportError(f"JSON raiz no es objeto: {path}")
    return value


def verify_source(path: Path, expected_sha256: str) -> str:
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise ExportError(
            f"SHA-256 inesperado para {path.name}: {observed}; esperado {expected_sha256}"
        )
    return observed


def cell(value: Any) -> str:
    """Exact CSV representation; missing values stay empty, never zero."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def metric_triplet(container: dict[str, Any], name: str) -> tuple[str, str, str]:
    item = container.get(name)
    if item is None:
        return "", "not_applicable", "non_probabilistic_method"
    if not isinstance(item, dict):
        raise ExportError(f"Metrica {name} no tiene objeto status/value/reason")
    return cell(item.get("value")), cell(item.get("status")), cell(item.get("reason"))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: cell(row.get(name)) for name in fieldnames})


def support_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for horizon in ("1", "2", "3"):
        result = metrics["horizons"][horizon]
        base = result["metrics"]["average"]
        availability = result["individual_availability"]
        rows.append(
            {
                "horizon_days": horizon,
                "candidate_emissions": result["candidate_emissions"],
                "common_cases": result["common_cases"],
                "coverage_fraction": result["coverage_fraction"],
                "physical_threshold_p20": result["physical_threshold_p20"],
                "decision_threshold": result["decision_threshold"],
                "positives": base["positives"],
                "negatives": base["negatives"],
                "prevalence": base["prevalence"],
                "case_b_n": result["case_b_nondry_at_t_dry_at_target"]["n"],
                "episodes_total": result["episodes"]["episodes_total"],
                "starts_determinable": result["episodes"]["starts_determinable"],
                "left_censored": result["episodes"]["left_censored"],
                "right_censored": result["episodes"]["right_censored"],
                "evaluable_episodes": result["episodes"]["evaluable_for_horizon"],
                "hgb_available": availability["hist_gradient_boosting_classifier"]["available"],
                "lr_available": availability["logistic_regression"]["available"],
                "rf_available": availability["random_forest"]["available"],
                "exclusions": ";".join(
                    f"{key}:{value}" for key, value in sorted(result["exclusions"].items())
                ),
            }
        )
    return rows


def classification_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for horizon in ("1", "2", "3"):
        for method in METHOD_ORDER:
            item = metrics["horizons"][horizon]["metrics"][method]
            row = {
                "horizon_days": horizon,
                "method": method,
                "n": item["n"],
                "positives": item["positives"],
                "negatives": item["negatives"],
                "prevalence": item["prevalence"],
                **item["confusion_matrix"],
            }
            for name in ("precision", "recall", "f1", "mcc", "average_precision", "brier"):
                value, status, reason = metric_triplet(item, name)
                row[f"{name}_value"] = value
                row[f"{name}_status"] = status
                row[f"{name}_reason"] = reason
            rows.append(row)
    return rows


def comparison_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for horizon in ("1", "2", "3"):
        result = metrics["horizons"][horizon]
        methods = result["metrics"]
        for comparison, uncertainty in result["uncertainty"]["comparisons"].items():
            if comparison == "average_minus_majority":
                delta = methods["average"]["mcc"]["value"] - methods["majority"]["mcc"]["value"]
            else:
                method = comparison.removesuffix("_minus_persistence")
                delta = methods[method]["delta_mcc_vs_persistence"]["value"]
            interval = uncertainty.get("delta_mcc_ci95")
            rows.append(
                {
                    "horizon_days": horizon,
                    "comparison": comparison,
                    "delta_mcc": delta,
                    "status": uncertainty["status"],
                    "reason": uncertainty.get("reason"),
                    "ci95_lower": interval[0] if interval is not None else None,
                    "ci95_upper": interval[1] if interval is not None else None,
                    "replicates_defined": uncertainty["replicates_defined"],
                    "replicates_discarded_undefined": uncertainty["replicates_discarded_undefined"],
                    "block_length_days": result["uncertainty"]["block_length_days"],
                    "seed": result["uncertainty"]["seed"],
                    "replicates_requested": result["uncertainty"]["replicates_requested"],
                }
            )
    return rows


def episode_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for horizon in ("1", "2", "3"):
        result = metrics["horizons"][horizon]
        episodes = result["episodes"]
        case_b = result["case_b_nondry_at_t_dry_at_target"]
        for method in METHOD_ORDER:
            item = episodes["methods"][method]
            recall_value, recall_status, recall_reason = metric_triplet(item, "recall")
            rows.append(
                {
                    "horizon_days": horizon,
                    "method": method,
                    "episodes_total": episodes["episodes_total"],
                    "starts_determinable": episodes["starts_determinable"],
                    "left_censored": episodes["left_censored"],
                    "right_censored": episodes["right_censored"],
                    "evaluable_episodes": item["evaluable_episodes"],
                    "detected_episodes": item["detected_episodes"],
                    "missed_episodes": item["missed_episodes"],
                    "episode_recall_value": recall_value,
                    "episode_recall_status": recall_status,
                    "episode_recall_reason": recall_reason,
                    "case_b_n": case_b["n"],
                    "case_b_detected": case_b["detected"][method],
                }
            )
    return rows


def reliability_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for horizon in ("1", "2", "3"):
        for method in METHOD_ORDER:
            item = metrics["horizons"][horizon]["metrics"][method]
            bins = item.get("reliability_bins")
            if method not in PROBABILISTIC_METHODS:
                if bins is not None:
                    raise ExportError(f"Metodo no probabilistico con bins: {method}")
                continue
            if not isinstance(bins, list) or len(bins) != 10:
                raise ExportError(f"Se esperaban 10 bins para {horizon}/{method}")
            for index, bin_item in enumerate(bins):
                mean = bin_item.get("mean_score")
                observed = bin_item.get("observed_fraction")
                rows.append(
                    {
                        "horizon_days": horizon,
                        "method": method,
                        "bin_index": index,
                        "lower": bin_item["lower"],
                        "upper": bin_item["upper"],
                        "right_inclusive": bin_item["right_inclusive"],
                        "n": bin_item["n"],
                        "positives": bin_item["positives"],
                        "mean_score_value": mean,
                        "mean_score_status": "defined" if mean is not None else "undefined",
                        "mean_score_reason": "" if mean is not None else "empty_bin",
                        "observed_fraction_value": observed,
                        "observed_fraction_status": (
                            "defined" if observed is not None else "undefined"
                        ),
                        "observed_fraction_reason": ("" if observed is not None else "empty_bin"),
                    }
                )
    return rows


def readme_text(
    manifest: dict[str, Any],
    source_dir: Path,
    metrics_sha256: str,
    manifest_sha256: str,
) -> str:
    command = (
        "python scripts/export_ensemble_retrospective_tables.py "
        f'--source-dir "{source_dir}" '
        '--output-dir "docs/research/tables/ensemble-retrospective-2023"'
    )
    return f"""# Tablas agregadas de la evaluacion retrospectiva 2023

Tablas derivadas exclusivamente de los agregados de la ejecucion canonica
`{CANONICAL_EXECUTION}`. No se leyeron predicciones, no se ejecuto inferencia y
no se usa la corrida duplicada como replica.

- Fuente canonica: `{source_dir}`
- `metrics.json` SHA-256: `{metrics_sha256}`
- `execution_manifest.json` SHA-256: `{manifest_sha256}`
- SHA ejecutable: `{manifest['code_identity']['commit']}`
- Protocolo SHA-256: `{manifest['protocol_sha256']}`
- Estado: `{manifest['status']}`
- Inicio/fin UTC: `{manifest['started_at_utc']}` / `{manifest['completed_at_utc']}`

Los CSV preservan la precision numerica del JSON sin redondeo. Un valor no
disponible queda vacio y se acompana por columnas `status`/`reason`; nunca se
convierte `null` en cero. Persistencia y mayoria no reciben AP, Brier ni bins
porque no son modelos probabilisticos en este analisis.

Archivos: `evaluation_support.csv`, `classification_metrics.csv`,
`paired_mcc_comparisons.csv`, `episode_onset.csv` y `reliability_bins.csv`.

Regeneracion (solo agregados canonicos):

```powershell
{command}
```
"""


def export_tables(
    source_dir: Path,
    output_dir: Path,
    *,
    expected_metrics_sha256: str = EXPECTED_METRICS_SHA256,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
) -> None:
    metrics_path = source_dir / "metrics.json"
    manifest_path = source_dir / "execution_manifest.json"
    verify_source(metrics_path, expected_metrics_sha256)
    verify_source(manifest_path, expected_manifest_sha256)
    metrics = load_json_exact(metrics_path)
    manifest = load_json_exact(manifest_path)
    if manifest.get("status") != "completado":
        raise ExportError("La ejecucion canonica no esta completada")
    if set(metrics.get("horizons", {})) != {"1", "2", "3"}:
        raise ExportError("metrics.json no contiene exactamente horizontes 1/2/3")
    output_dir.mkdir(parents=True, exist_ok=True)

    support = support_rows(metrics)
    write_csv(output_dir / "evaluation_support.csv", list(support[0]), support)
    classifications = classification_rows(metrics)
    write_csv(output_dir / "classification_metrics.csv", list(classifications[0]), classifications)
    comparisons = comparison_rows(metrics)
    write_csv(output_dir / "paired_mcc_comparisons.csv", list(comparisons[0]), comparisons)
    episodes = episode_rows(metrics)
    write_csv(output_dir / "episode_onset.csv", list(episodes[0]), episodes)
    reliability = reliability_rows(metrics)
    write_csv(output_dir / "reliability_bins.csv", list(reliability[0]), reliability)
    (output_dir / "README.md").write_text(
        readme_text(
            manifest,
            source_dir,
            expected_metrics_sha256,
            expected_manifest_sha256,
        ),
        encoding="utf-8",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=CANONICAL_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    export_tables(args.source_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
