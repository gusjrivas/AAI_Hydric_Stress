"""Idempotent, read-only-on-bundles refresh of the Melchor Romero
historical-demonstration READINGS file (`sensor__<sensor-id>.parquet` under
an existing, already-prepared `--data-dir`) -- F01, `data-ingestion`.

Context: the bug this fixes (see `docs/research/...` / the PR that added
this file) was exclusively that `data_ingestion.history.query_readings`
never read the per-variable `<variable>_imputado` flags that
`data_quality.imputation.interpolate_missing_causal` (via
`experiment_runner.melchor_romero_historical_demo_runner
.build_daily_frame_from_repo_dataset`) already computes and
`scripts/prepare_melchor_romero_historical_demo.py` already saves into the
readings file. In other words: any directory already prepared with THAT
script already carries the correct per-variable imputation flags on disk --
this script exists as a defense-in-depth repair path for a readings file
that may have lost or never carried them (e.g. hand-edited, or prepared by
a differently-modified script), never as a required migration step.

Never touches bundles, `run_manifest.json`, prepared emissions, or feedback
-- only rewrites the readings (`sensor__<sensor-id>.parquet`) file, and
only the `<variable>_imputado` columns of rows it already had. Never adds,
removes, or reorders rows/dates.

Verification, never inference: for every date already present in the
existing readings file, this script requires (a) that same date to exist
in the CURRENT versioned source dataset (`build_daily_frame_from_repo_dataset`,
reading `data/melchor_romero_2024_consolidado.parquet` fresh), and (b) the
existing file's own `soil_moisture`/`relative_humidity`/`solar_radiation`
value at that date to numerically match (or both be missing) the value the
source produces today. This is an identity check against the same date's
value in the authoritative source -- never an inference of provenance from
two DIFFERENT dates happening to hold equal values (the pattern F01
explicitly forbids). If any date or value cannot be verified this way, the
script raises `RefreshError` and writes nothing.

Idempotent: running it twice in a row on the same `--data-dir` (with an
unchanged source dataset) produces a byte-identical readings file the
second time.

Usage:
    python scripts/refresh_melchor_romero_historical_demo_readings.py \\
        --data-dir "<existing prepared --data-dir>" \\
        [--sensor-id melchor-romero-demo]
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

DEFAULT_SENSOR_ID = "melchor-romero-demo"
_TRACKED_VARIABLES: tuple[str, ...] = ("soil_moisture", "relative_humidity", "solar_radiation")


class RefreshError(ValueError):
    """The existing readings file could not be verified against the
    current versioned source; nothing was written."""


def _values_match(existing: Any, fresh: Any) -> bool:
    existing_missing = pd.isna(existing)
    fresh_missing = pd.isna(fresh)
    if existing_missing and fresh_missing:
        return True
    if existing_missing != fresh_missing:
        return False
    return math.isclose(float(existing), float(fresh), rel_tol=1e-9, abs_tol=1e-12)


def refresh_readings(*, sensor_id: str, data_dir: Path) -> dict[str, Any]:
    from data_ingestion.sensor_naming import dataset_name_for
    from data_ingestion.storage import (
        atomic_write_bytes,
        dataset_lock_path,
        interprocess_lock,
        load_dataset_snapshot,
    )
    from experiment_runner.melchor_romero_historical_demo_runner import (
        build_daily_frame_from_repo_dataset,
    )

    name = dataset_name_for(sensor_id)
    path = data_dir / f"{name}.parquet"

    # The entire load -> verify -> write cycle runs under the SAME
    # interprocess lock `save_dataset` uses internally for this dataset
    # (the documented pattern for a load-modify-save cycle spanning
    # multiple `data_ingestion.storage` calls, `dataset_lock_path`'s own
    # docstring, already used by `human_feedback.registry
    # .update_feedback_log_atomically`). Without this, a concurrent writer
    # could save a correction between this script's read and its write,
    # and the write below would silently discard it (lost update). Writing
    # via `atomic_write_bytes` directly, never `save_dataset`, avoids
    # nesting a second acquisition of this same, non-reentrant lock inside
    # this one.
    with interprocess_lock(dataset_lock_path(name, data_dir)):
        existing_snapshot = load_dataset_snapshot(name, data_dir=data_dir)
        existing = existing_snapshot.dataframe.copy()
        if "timestamp" not in existing.columns:
            raise RefreshError(f"{name}: no contiene la columna 'timestamp'.")

        existing_dates = pd.to_datetime(existing["timestamp"]).dt.normalize()

        fresh_frame, dataset_sha256 = build_daily_frame_from_repo_dataset()
        fresh_indexed = fresh_frame.set_index(fresh_frame["timestamp"].dt.normalize())

        missing_in_source = sorted(set(existing_dates) - set(fresh_indexed.index))
        if missing_in_source:
            raise RefreshError(
                "Hay fechas en el archivo de lecturas preparado que no existen en la fuente "
                f"versionada actual: {[d.date().isoformat() for d in missing_in_source]}. No se "
                "puede verificar la correspondencia; no se sobrescribió nada."
            )

        for column in _TRACKED_VARIABLES:
            for reading_date, existing_value in zip(existing_dates, existing[column]):
                fresh_value = fresh_indexed.loc[reading_date, column]
                if not _values_match(existing_value, fresh_value):
                    raise RefreshError(
                        f"{column} en {reading_date.date().isoformat()} no coincide con la "
                        f"fuente versionada actual (archivo={existing_value!r}, "
                        f"fuente={fresh_value!r}). No se puede verificar la procedencia con "
                        "certeza; no se sobrescribió nada."
                    )

        # Re-verify the on-disk snapshot is still the exact one just read
        # and checked, BEFORE writing -- still inside the same lock. This
        # is the concurrency guard itself (never redundant with the
        # per-value check above, which only validates against the versioned
        # SOURCE dataset, not against a possible writer of THIS readings
        # file that could have run between our read and this point). A
        # mismatch means another writer saved a change concurrently; abort
        # without overwriting it.
        current_snapshot = load_dataset_snapshot(name, data_dir=data_dir)
        if current_snapshot.dataset_sha256 != existing_snapshot.dataset_sha256:
            raise RefreshError(
                f"{name}: el archivo de lecturas cambió concurrentemente mientras se "
                "verificaba (otro escritor guardó una corrección). No se sobrescribió nada; "
                "reintentar."
            )

        updated = existing.copy()
        changed_flags = 0
        for column in _TRACKED_VARIABLES:
            flag_column = f"{column}_imputado"
            fresh_flags = [
                bool(fresh_indexed.loc[reading_date, flag_column])
                for reading_date in existing_dates
            ]
            if flag_column not in updated.columns or list(updated[flag_column]) != fresh_flags:
                changed_flags += 1
            updated[flag_column] = fresh_flags

        buffer = io.BytesIO()
        updated.to_parquet(buffer, index=False)
        atomic_write_bytes(path, buffer.getvalue())

    return {
        "sensor_id": sensor_id,
        "rows_verified": int(len(existing)),
        "dataset_sha256": dataset_sha256,
        "imputation_flag_columns_updated": changed_flags,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--sensor-id", default=DEFAULT_SENSOR_ID)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = refresh_readings(sensor_id=args.sensor_id, data_dir=args.data_dir)
    except RefreshError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"lecturas verificadas y actualizadas: {result['rows_verified']} filas, "
        f"dataset_sha256={result['dataset_sha256'][:16]}..., "
        f"columnas de imputación tocadas={result['imputation_flag_columns_updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
