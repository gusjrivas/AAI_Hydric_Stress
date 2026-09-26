"""Arranque reproducible del backend v2 para revisar la UI de productor
contra artefactos reales ya preparados (Hito 2, PR #221).

Nunca usa `data/` del repositorio, nunca hardcodea una ruta de una
maquina particular: toma los directorios externos por variable de
entorno, valida que contengan lo esperado y falla con un diagnostico
concreto si falta algo -- nunca sustituye silenciosamente por fixtures
ni por datos sinteticos generados sobre la marcha.

Variables de entorno requeridas:

- `PRODUCER_DATA_DIR`: directorio externo con el catalogo, las lecturas
  (`sensor__<sensor_id>.parquet`) y las emisiones ya preparadas
  (`ui_metadata/operational_v2__<sensor_id>.json`) del recorrido real de
  Pergamino ya ejecutado (Hito 2, PR #219/#220). Nunca `data/` del
  repositorio, nunca `replay_packages/` (eso es `historical_replay`, un
  sistema distinto). El feedback de la demostracion (`HistoricalReviewStore`)
  se aisla automaticamente dentro de este mismo directorio, en su propio
  subdirectorio (`historical_feedback/`), separado de
  `ui_metadata/operational_v2__*.json`.
- `PRODUCER_BUNDLE_ROOT`: directorio con los 9 bundles reales del
  ensamble (3 familias x 3 horizontes) generados por la ejecucion real
  autorizada (PR #219). Se pasa tal cual a la variable de entorno
  homonima que ya lee `backend.app.dependencies.get_producer_bundle_root`.

Variables opcionales:

- `PRODUCER_PREVIEW_HOST` (default 127.0.0.1)
- `PRODUCER_PREVIEW_PORT` (default 8000)
- `CORS_EXTRA_ORIGINS`: se reenvia tal cual a la app (ver
  `backend/app/main.py`); necesaria si el frontend de desarrollo no
  corre en el puerto 5173 por defecto.

Este script deliberadamente NO es `docker-compose.producer-preview.yml`:
ese flujo (si existe en el repositorio) prepara datos sinteticos y no
debe presentarse como evidencia del recorrido real de Pergamino.

Uso (PowerShell):
    $env:PRODUCER_DATA_DIR = "<tu directorio con catalogo/lecturas/emisiones reales>"
    $env:PRODUCER_BUNDLE_ROOT = "<tu directorio con los 9 bundles reales>"
    python scripts/run_producer_preview_backend.py

Uso (bash):
    PRODUCER_DATA_DIR=<...> PRODUCER_BUNDLE_ROOT=<...> \
        python scripts/run_producer_preview_backend.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _fail(message: str) -> None:
    print(f"[run_producer_preview_backend] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _require_env(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        _fail(
            f"falta la variable de entorno {name}. Este script nunca sustituye "
            "un insumo real por un fixture: definila antes de continuar."
        )
    path = Path(value)
    if not path.is_dir():
        _fail(f"{name}={value!r} no es un directorio existente.")
    return path


def _validate_data_dir(data_dir: Path) -> None:
    readings = list(data_dir.glob("sensor__*.parquet"))
    if not readings:
        _fail(
            f"PRODUCER_DATA_DIR={data_dir} no contiene ninguna lectura "
            "(sensor__*.parquet). ¿Es el directorio correcto del recorrido "
            "real ya preparado?"
        )
    metadata_dir = data_dir / "ui_metadata"
    emissions = list(metadata_dir.glob("operational_v2__*.json")) if metadata_dir.is_dir() else []
    if not emissions:
        _fail(
            f"PRODUCER_DATA_DIR={data_dir} no tiene emisiones preparadas en "
            "ui_metadata/operational_v2__*.json. Sin al menos una emision ya "
            "persistida, el recorrido historico solo puede responder "
            "'No hay una emisión preparada para esta fecha' para cualquier "
            "fecha -- si esperabas datos reales, revisá que apunte al "
            "directorio correcto."
        )
    print(f"[run_producer_preview_backend] Lecturas encontradas: {[p.name for p in readings]}")
    print(f"[run_producer_preview_backend] Emisiones preparadas: {[p.name for p in emissions]}")


def _validate_bundle_root(bundle_root: Path) -> None:
    manifests = list(bundle_root.rglob("ensemble_manifest.json"))
    if not manifests:
        _fail(
            f"PRODUCER_BUNDLE_ROOT={bundle_root} no contiene ningún "
            "ensemble_manifest.json. Sin los 9 bundles reales, la emisión "
            "en vivo (POST) fallaría al cargar el ensamble -- la reproducción "
            "histórica de lecturas y emisiones ya persistidas no los necesita, "
            "pero igual se exige este directorio para no arrancar en un "
            "estado a medias sin avisar."
        )
    print(f"[run_producer_preview_backend] Manifiestos de ensamble encontrados: {len(manifests)}")


def main() -> None:
    data_dir = _require_env("PRODUCER_DATA_DIR")
    bundle_root = _require_env("PRODUCER_BUNDLE_ROOT")
    _validate_data_dir(data_dir)
    _validate_bundle_root(bundle_root)

    os.environ["PRODUCER_V2_ENABLED"] = "true"
    os.environ["PRODUCER_BUNDLE_ROOT"] = str(bundle_root)

    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT / "backend"))

    from app.config import get_dataset_data_dir  # noqa: E402
    from app.main import app  # noqa: E402

    app.dependency_overrides[get_dataset_data_dir] = lambda: data_dir

    import uvicorn

    host = os.environ.get("PRODUCER_PREVIEW_HOST", "127.0.0.1")
    port = int(os.environ.get("PRODUCER_PREVIEW_PORT", "8000"))
    print(f"[run_producer_preview_backend] PRODUCER_DATA_DIR={data_dir}")
    print(f"[run_producer_preview_backend] PRODUCER_BUNDLE_ROOT={bundle_root}")
    print(f"[run_producer_preview_backend] Sirviendo en http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
