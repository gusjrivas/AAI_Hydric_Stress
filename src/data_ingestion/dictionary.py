"""Diccionario de datos versionado por fuente (spec data-ingestion,
requirement 'Diccionario de datos versionado por fuente'; gobernanza de
datos, sección 12.1 del plan de tesis).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DICTIONARIES_DIR = Path(__file__).resolve().parents[2] / "data" / "dictionaries"


def write_data_dictionary(
    source_name: str,
    provenance: str,
    license_: str,
    limitations: str,
    dictionaries_dir: Path = DEFAULT_DICTIONARIES_DIR,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Escribe el diccionario de datos de una fuente como JSON versionado
    junto al dataset correspondiente.
    """
    dictionaries_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "source_name": source_name,
        "provenance": provenance,
        "license": license_,
        "limitations": limitations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)

    path = dictionaries_dir / f"{source_name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_data_dictionary(
    source_name: str, dictionaries_dir: Path = DEFAULT_DICTIONARIES_DIR
) -> dict[str, Any]:
    path = dictionaries_dir / f"{source_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No existe diccionario de datos para '{source_name}' en {path}")
    return json.loads(path.read_text(encoding="utf-8"))
