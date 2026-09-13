"""Identidad del código en ejecución (hallazgo H-05, reproducibilidad).

Captura el SHA completo del commit y si el árbol de trabajo está limpio o
modificado, ANTES de entrenar, igual que `environment.capture_environment()`.
Nunca inventa un valor: si ni Git ni el metadato de build están disponibles
(por ejemplo, dentro de un contenedor sin `.git`), el resultado lo declara
explícitamente en `source`/`available`, para que quien audite la corrida no
confunda "desconocido" con "reproducible".

Revisión externa (2026-09-13), hallazgo 1: dentro de un contenedor, el
archivo de metadatos de build antes solo llevaba el commit como texto plano,
sin estado limpio/modificado (`dirty` quedaba siempre `None`, marcando toda
corrida en contenedor como no normativa aunque el checkout de origen
estuviera limpio) y sin validar su formato (aceptaba literalmente cualquier
texto no vacío como si fuera un commit). Corregido: el mecanismo de build
(`docker/experiment-v4/build.py`) captura y valida el SHA y el estado
limpio/modificado del MISMO checkout que se usa como contexto de build, y
escribe un archivo JSON versionado (`BUILD_IDENTITY_SCHEMA_VERSION`) que este
módulo valida estrictamente: un commit con formato inválido, un campo
`dirty` con tipo inválido, o una versión de esquema inesperada producen
`available=False` con un motivo explícito (`SOURCE_BUILD_METADATA_INVALID`),
nunca una identidad aceptada a ciegas. Ver `capture_code_identity` para los
límites documentados de esta captura.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_BUILD_IDENTITY_FILE = _REPO_ROOT / ".build_identity.json"

SOURCE_GIT = "git"
SOURCE_GIT_INVALID = "git_invalid"
SOURCE_BUILD_METADATA_FILE = "build_metadata_file"
SOURCE_BUILD_METADATA_INVALID = "build_metadata_invalid"
SOURCE_UNAVAILABLE = "unavailable"

BUILD_IDENTITY_SCHEMA_VERSION = "controlled_daily_v4_build_identity.v1"
"""Versión del esquema que `docker/experiment-v4/build.py` escribe y que
este módulo exige al leerlo. Un archivo con otra versión (o sin ella) se
trata como metadato inválido, no como una versión "compatible por defecto"."""

# Git admite objetos SHA-1 (40 hex) o, en repositorios migrados, SHA-256 (64
# hex). No se asume uno fijo: `build.py` valida contra el que este
# repositorio usa realmente (`git rev-parse --show-object-format`), y este
# módulo acepta cualquiera de los dos formatos completos -- nunca un SHA
# abreviado ni un valor con otro largo/alfabeto.
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_valid_full_sha(value: object) -> bool:
    """`True` únicamente si `value` es un `str` con la forma exacta de un
    SHA-1 (40 hex) o SHA-256 (64 hex) completo de Git -- nunca abreviado."""
    if not isinstance(value, str):
        return False
    return bool(_SHA1_RE.fullmatch(value) or _SHA256_RE.fullmatch(value))


@dataclass(frozen=True)
class CodeIdentity:
    available: bool
    source: str
    commit: str | None
    dirty: bool | None
    reason: str | None = None


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip()


def _capture_from_git(repo_root: Path) -> CodeIdentity | None:
    commit = _run_git(["rev-parse", "HEAD"], repo_root)
    if not commit:
        return None
    if not is_valid_full_sha(commit):
        # Defensivo: `git rev-parse HEAD` no debería devolver nunca un valor
        # con esta forma, pero si ocurriera, no se acepta a ciegas.
        return CodeIdentity(
            available=False,
            source=SOURCE_GIT_INVALID,
            commit=None,
            dirty=None,
            reason=f"'git rev-parse HEAD' devolvió un valor con formato inesperado: '{commit}'",
        )
    status = _run_git(["status", "--porcelain"], repo_root)
    if status is None:
        return None
    return CodeIdentity(available=True, source=SOURCE_GIT, commit=commit, dirty=bool(status))


def _invalid(build_identity_file: Path, reason: str) -> CodeIdentity:
    return CodeIdentity(
        available=False,
        source=SOURCE_BUILD_METADATA_INVALID,
        commit=None,
        dirty=None,
        reason=f"'{build_identity_file}': {reason}",
    )


def _capture_from_build_metadata_file(build_identity_file: Path) -> CodeIdentity | None:
    if not build_identity_file.exists():
        return None

    try:
        payload = json.loads(build_identity_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _invalid(build_identity_file, f"no es JSON válido ({exc})")
    if not isinstance(payload, dict):
        return _invalid(build_identity_file, "el JSON raíz debe ser un objeto")

    schema_version = payload.get("schema_version")
    if schema_version != BUILD_IDENTITY_SCHEMA_VERSION:
        return _invalid(
            build_identity_file,
            f"schema_version={schema_version!r} inesperado "
            f"(se esperaba {BUILD_IDENTITY_SCHEMA_VERSION!r})",
        )

    commit = payload.get("commit")
    if not is_valid_full_sha(commit):
        return _invalid(
            build_identity_file,
            f"'commit'={commit!r} no es un SHA completo válido (40 o 64 hex)",
        )

    dirty = payload.get("dirty")
    if dirty is not None and not isinstance(dirty, bool):
        return _invalid(build_identity_file, f"'dirty'={dirty!r} debe ser bool o null")

    return CodeIdentity(
        available=True,
        source=SOURCE_BUILD_METADATA_FILE,
        commit=commit,
        dirty=dirty,
        reason=(
            "El mecanismo de build no pudo determinar si el árbol estaba limpio o "
            "modificado en el momento de capturar esta identidad."
            if dirty is None
            else None
        ),
    )


def capture_code_identity(
    repo_root: str | Path = _REPO_ROOT,
    build_identity_file: str | Path = DEFAULT_BUILD_IDENTITY_FILE,
) -> CodeIdentity:
    """Identidad del código de la corrida actual.

    Orden de resolución:

    1. `git rev-parse HEAD` + `git status --porcelain` sobre `repo_root`
       (caso local con `.git` presente).
    2. El archivo de metadatos de build `build_identity_file`
       (`.build_identity.json`, esquema `BUILD_IDENTITY_SCHEMA_VERSION`),
       escrito por `docker/experiment-v4/build.py` a partir del MISMO
       checkout que se envía como contexto de build (caso contenedor, sin
       `.git` en tiempo de ejecución; ver ese script para el mecanismo
       exacto y sus límites documentados). Un archivo presente pero
       malformado (JSON inválido, commit con formato inválido, `dirty` con
       tipo inválido, o versión de esquema inesperada) se distingue
       explícitamente de "no hay metadato" — `source=SOURCE_BUILD_METADATA_INVALID`
       — en vez de tratarse como ausencia silenciosa.
    3. Si ninguna fuente está disponible, se declara `available=False` en
       vez de inventar un commit o un estado.

    Límites documentados: la fuente (2) certifica el estado del checkout en
    el instante en que `build.py` lo capturó, inmediatamente antes de
    invocar `docker build` sobre ese mismo directorio -- no hay forma de
    certificar, desde dentro de la imagen ya construida, que el contexto
    enviado a Docker fue exactamente ese y no uno modificado a último
    momento; ese riesgo se acota (no se elimina) ejecutando la captura y el
    build en el mismo proceso, ver `build.py`."""
    repo_root = Path(repo_root)
    build_identity_file = Path(build_identity_file)

    identity = _capture_from_git(repo_root)
    if identity is not None:
        return identity

    identity = _capture_from_build_metadata_file(build_identity_file)
    if identity is not None:
        return identity

    return CodeIdentity(
        available=False,
        source=SOURCE_UNAVAILABLE,
        commit=None,
        dirty=None,
        reason=(
            "No se encontró un repositorio Git en "
            f"'{repo_root}' ni un archivo de metadatos de build en "
            f"'{build_identity_file}'."
        ),
    )


__all__ = [
    "BUILD_IDENTITY_SCHEMA_VERSION",
    "DEFAULT_BUILD_IDENTITY_FILE",
    "SOURCE_BUILD_METADATA_FILE",
    "SOURCE_BUILD_METADATA_INVALID",
    "SOURCE_GIT",
    "SOURCE_GIT_INVALID",
    "SOURCE_UNAVAILABLE",
    "CodeIdentity",
    "capture_code_identity",
    "is_valid_full_sha",
]
