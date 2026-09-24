"""Reconstruct the per-row imputation marker (`<column>_imputado`) for the
pre-cutoff measurement history shown by the replay (spec `historical-replay`,
requirement RH-05; design.md §4.3, §9).

This is a deterministic, pure re-application of the same causal imputation
already used by the original pipeline (`data_quality.imputation.interpolate_missing_causal`,
`data_quality.temporal.validate_daily_series`), over the same raw dataset
(verified by hash). It never trains, infers, or recalculates any scientific
metric — it only reproduces a data-quality transform that was always part of
feature preparation, so the replay can distinguish `medida` from `imputada`
in the history it shows, instead of declaring `no_determinado` for a value
that is in fact knowable.

**Equivalence with the historical version, verified, not assumed:** importing
the current `data_quality.imputation`/`data_quality.temporal` under their
current name is not, by itself, evidence that they behave as the version
that actually ran in the candidate commit
(`2a40ee68c52d2eb5e2040a36b1029f756f9c048a`). That equivalence was checked
directly (`git diff 2a40ee68c52d2eb5e2040a36b1029f756f9c048a HEAD --
src/data_quality/imputation.py src/data_quality/temporal.py`, empty diff,
2026-09-23) and is enforced here at runtime: `verify_imputation_source_matches_verified_commit`
hashes the exact source bytes of the modules actually imported and compares
them against the hashes captured at that verification. If either module's
source ever changes without updating `_VERIFIED_SOURCE_SHA256`, this raises
instead of silently reusing a changed function under the same name.
"""

from __future__ import annotations

import hashlib
import inspect

import pandas as pd

from data_quality import imputation as _imputation_module
from data_quality import temporal as _temporal_module
from data_quality.imputation import interpolate_missing_causal
from data_quality.temporal import validate_daily_series

VERIFIED_AGAINST_COMMIT = "2a40ee68c52d2eb5e2040a36b1029f756f9c048a"

# SHA-256 of the file contents at the commit above (`git show <commit>:<path>
# | sha256sum`, i.e. the canonical LF blob git actually stores), confirmed
# identical to HEAD via `git diff` on 2026-09-23
# (paso2-correccion-validaciones.md). Hashed after CRLF normalization (see
# `_hash_module_source`) so the check is independent of the checkout's line
# ending policy — a Windows checkout with `core.autocrlf=true` (used during
# development, via a Docker bind mount) converts these files to CRLF on
# disk, while a Linux CI checkout keeps them LF; hashing raw bytes would
# make this check fail on a real content match purely from that difference
# (found by a real CI run on this same change, not anticipated in advance).
_VERIFIED_SOURCE_SHA256 = {
    "data_quality.imputation": ("0d658e829d60b3f3841638cb0db4cf94e76b2f6b56c6b65f064d1c2128a4522e"),
    "data_quality.temporal": ("5d9b0e02dc96255aadc539f0f908201448fc974d7815a0490571a36725d3a9fb"),
}


class ImputationSourceDriftError(RuntimeError):
    """`data_quality.imputation`/`data_quality.temporal` no longer match the
    exact source verified against the commit that produced the candidate
    run — the equivalence this module relies on can no longer be assumed."""


def _hash_module_source(module) -> str:
    """Hash the module's source after normalizing CRLF to LF: the check is
    about the *content* actually running, not about which line-ending
    convention this particular checkout happens to use."""
    source_path = inspect.getsourcefile(module)
    with open(source_path, "rb") as handle:
        content = handle.read()
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def verify_imputation_source_matches_verified_commit() -> None:
    """Raise `ImputationSourceDriftError` if the actually-imported
    `data_quality.imputation`/`data_quality.temporal` source differs from
    the one verified against `VERIFIED_AGAINST_COMMIT`."""
    modules = {
        "data_quality.imputation": _imputation_module,
        "data_quality.temporal": _temporal_module,
    }
    for name, module in modules.items():
        actual = _hash_module_source(module)
        expected = _VERIFIED_SOURCE_SHA256[name]
        if actual != expected:
            raise ImputationSourceDriftError(
                f"{name} ya no coincide con la fuente verificada contra "
                f"{VERIFIED_AGAINST_COMMIT}: esperado sha256={expected}, "
                f"obtenido sha256={actual}. La equivalencia con la versión "
                "histórica ya no puede asumirse; no se reconstruyen "
                "marcadores de imputación hasta revisar este cambio."
            )


def reconstruct_imputation_markers(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return a copy of `df` with `<column>_imputado` markers for `columns`,
    reproducing exactly the same order the original pipeline used:
    `validate_daily_series` (canonical daily calendar) followed by
    `interpolate_missing_causal` over the whole series at once — never per
    partition, matching `architecture_integration.pipeline.prepare_daily_features`
    (design.md §6). Verifies source equivalence with the historical commit
    before running (see module docstring)."""
    verify_imputation_source_matches_verified_commit()
    ordered = validate_daily_series(df)
    return interpolate_missing_causal(ordered, columns)
