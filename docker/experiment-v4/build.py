#!/usr/bin/env python3
"""Wrapper de build para `docker/experiment-v4` (hallazgo H-05, revisión
externa 2026-09-13, punto 1: identidad de código dentro de Docker).

Captura el SHA completo y el estado limpio/modificado del MISMO checkout que
se envía como contexto de build, inmediatamente antes de invocar
`docker build` sobre ese mismo directorio, y escribe esa identidad en
`<repo_root>/.build_identity.json` -- que el Dockerfile copia a la imagen
(`COPY .build_identity.json`). Nunca copia `.git` completo a la imagen.

Uso:
    python docker/experiment-v4/build.py -t experiment-v4-controlled-daily-v4
    (acepta cualquier argumento adicional de "docker build"; el Dockerfile y
    el contexto ya quedan fijados por este script).

Qué certifica y qué NO certifica:
- Certifica el `HEAD` y el resultado de `git status --porcelain` de
  `repo_root` en el instante en que se ejecuta este script.
- NO certifica que el contexto de build que Docker realmente empaqueta
  segundos después sea bit a bit idéntico: existe una ventana entre esta
  captura y el envío del contexto al daemon de Docker en la que, en teoría,
  alguien podría modificar el árbol. Esa ventana se acota ejecutando la
  captura y la invocación de `docker build` en el mismo proceso (este
  script), no eliminándola: no hay forma de que un script externo al motor
  de Docker garantice más que eso.
- Requiere `git` disponible en el host que construye la imagen. Si no lo
  está, o si el repositorio no puede resolverse, el script aborta con un
  error explícito -- nunca escribe una identidad "unknown" ambigua.
- El estado limpio/modificado se calcula con `git status --porcelain`, que
  incluye archivos sin seguimiento (no solo cambios a archivos rastreados).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = Path(__file__).resolve().parent / "Dockerfile"
IDENTITY_FILE = REPO_ROOT / ".build_identity.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from experiment_runner.controlled_daily_v4.code_identity import (  # noqa: E402
    BUILD_IDENTITY_SCHEMA_VERSION,
    is_valid_full_sha,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BuildIdentityError(RuntimeError):
    """No se pudo capturar una identidad de código confiable para el build."""


def _run_git(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise BuildIdentityError("git no está disponible en este host de build") from exc
    except subprocess.CalledProcessError as exc:
        raise BuildIdentityError(
            f"'git {' '.join(args)}' falló (código {exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise BuildIdentityError(f"'git {' '.join(args)}' no respondió a tiempo") from exc
    return completed.stdout.strip()


def capture_build_identity() -> dict:
    """Identidad del checkout actual: SHA completo + limpio/modificado.

    El estado limpio/modificado se calcula ANTES de escribir cualquier
    archivo -- incluido el propio archivo de metadatos -- para que ese
    archivo nunca contamine el estado del árbol que describe."""
    object_format = _run_git(["rev-parse", "--show-object-format"])
    expected_pattern = _SHA256_RE if object_format == "sha256" else _SHA1_RE

    commit = _run_git(["rev-parse", "HEAD"])
    if not expected_pattern.fullmatch(commit) or not is_valid_full_sha(commit):
        raise BuildIdentityError(
            f"'git rev-parse HEAD' devolvió un valor con formato inesperado: '{commit}'"
        )

    # `git status --porcelain` ANTES de escribir el archivo de metadatos:
    # ese archivo todavía no existe en este punto, así que no puede
    # aparecer como "sin seguimiento" y alterar el resultado.
    status = _run_git(["status", "--porcelain"])
    dirty = bool(status)

    return {
        "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
        "commit": commit,
        "dirty": dirty,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str]) -> int:
    try:
        identity = capture_build_identity()
    except BuildIdentityError as exc:
        print(
            f"ERROR: no se pudo capturar la identidad de código del build: {exc}",
            file=sys.stderr,
        )
        return 1

    IDENTITY_FILE.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    print(f"Identidad de build capturada en {IDENTITY_FILE}: {identity}")

    cmd = ["docker", "build", "-f", str(DOCKERFILE), *argv, str(REPO_ROOT)]
    print("Ejecutando:", " ".join(cmd))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
