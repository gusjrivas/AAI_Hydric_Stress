"""Tests de `code_identity.capture_code_identity` (hallazgo H-05; revisión
externa 2026-09-13, punto 1: identidad de código dentro de Docker).

Nunca ejecuta la Etapa A real; opera exclusivamente sobre directorios
temporales sintéticos y sobre este mismo repositorio (para el caso
"Git disponible"). Para el caso "checkout limpio" usa repositorios Git
temporales creados por el test -- nunca depende de que este repositorio de
trabajo esté limpio, ni hace commit del proyecto real."""

from __future__ import annotations

import json
import subprocess

import pytest

from experiment_runner.controlled_daily_v4.code_identity import (
    BUILD_IDENTITY_SCHEMA_VERSION,
    SOURCE_BUILD_METADATA_FILE,
    SOURCE_BUILD_METADATA_INVALID,
    SOURCE_GIT,
    SOURCE_UNAVAILABLE,
    capture_code_identity,
    is_valid_full_sha,
)

VALID_SHA1 = "a" * 40
VALID_SHA256 = "b" * 64


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True, timeout=5)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


def _write_identity(path, **overrides):
    payload = {
        "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
        "commit": VALID_SHA1,
        "dirty": False,
        "captured_at_utc": "2026-09-13T00:00:00+00:00",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# `is_valid_full_sha`
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", [VALID_SHA1, VALID_SHA256])
def test_is_valid_full_sha_accepts_full_sha1_and_sha256(value):
    assert is_valid_full_sha(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "this-is-not-a-commit",
        "a" * 39,  # abreviado
        "a" * 41,  # demasiado largo
        "A" * 40,  # mayúsculas: git nunca las devuelve así
        "",
        None,
        123,
    ],
)
def test_is_valid_full_sha_rejects_anything_else(value):
    assert is_valid_full_sha(value) is False


# --------------------------------------------------------------------------
# Fuente 1: Git real (repos temporales, nunca este árbol de trabajo)
# --------------------------------------------------------------------------


@pytest.mark.skipif(not _git_available(), reason="git no disponible en este entorno")
def test_a_clean_temporary_checkout_reports_dirty_false(tmp_path):
    """Un checkout de prueba limpio (repositorio Git temporal, commiteado
    únicamente en ese repo aislado -- nunca el repositorio real del
    proyecto) debe satisfacer el requisito de identidad completa."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "file.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    identity = capture_code_identity(repo_root=repo, build_identity_file=repo / "nope.json")

    assert identity.available is True
    assert identity.source == SOURCE_GIT
    assert is_valid_full_sha(identity.commit)
    assert identity.dirty is False


@pytest.mark.skipif(not _git_available(), reason="git no disponible en este entorno")
def test_a_modified_temporary_checkout_reports_dirty_true(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "file.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    (repo / "file.txt").write_text("modificado", encoding="utf-8")

    identity = capture_code_identity(repo_root=repo, build_identity_file=repo / "nope.json")

    assert identity.available is True
    assert identity.source == SOURCE_GIT
    assert identity.dirty is True


@pytest.mark.skipif(not _git_available(), reason="git no disponible en este entorno")
def test_captures_a_full_commit_sha_from_this_repository():
    from experiment_runner.controlled_daily_v4 import code_identity as module

    repo_root = module._REPO_ROOT
    identity = capture_code_identity(
        repo_root=repo_root, build_identity_file=repo_root / "nope.json"
    )
    assert identity.available is True
    assert identity.source == SOURCE_GIT
    assert is_valid_full_sha(identity.commit)
    assert identity.dirty in (True, False)


# --------------------------------------------------------------------------
# Ausencia total (ni Git ni metadato de build)
# --------------------------------------------------------------------------


def test_reports_unavailable_explicitly_when_neither_git_nor_build_file_exist(tmp_path):
    identity = capture_code_identity(
        repo_root=tmp_path, build_identity_file=tmp_path / ".build_identity.json"
    )
    assert identity.available is False
    assert identity.source == SOURCE_UNAVAILABLE
    assert identity.commit is None
    assert identity.dirty is None
    assert identity.reason


def test_never_falls_back_to_a_directory_that_merely_looks_like_a_repo(tmp_path):
    """Un directorio cualquiera sin `.git` (y por lo tanto sin repositorio real)
    nunca debe inventar un commit."""
    (tmp_path / "some_file.txt").write_text("x", encoding="utf-8")
    identity = capture_code_identity(
        repo_root=tmp_path, build_identity_file=tmp_path / ".build_identity.json"
    )
    assert identity.available is False


# --------------------------------------------------------------------------
# Fuente 2: archivo de metadatos de build (caso contenedor, sin `.git`)
# --------------------------------------------------------------------------


def test_a_clean_build_reports_dirty_false_not_none(tmp_path):
    """Regresión directa del hallazgo: un build de checkout limpio ya no debe
    quedar marcado con `dirty=None` (y por lo tanto no normativo) por el
    solo hecho de correr en contenedor."""
    build_file = _write_identity(tmp_path / ".build_identity.json", dirty=False)
    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is True
    assert identity.source == SOURCE_BUILD_METADATA_FILE
    assert identity.commit == VALID_SHA1
    assert identity.dirty is False
    assert identity.reason is None


def test_a_dirty_build_reports_dirty_true(tmp_path):
    build_file = _write_identity(tmp_path / ".build_identity.json", dirty=True)
    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is True
    assert identity.dirty is True


def test_a_build_unable_to_determine_dirty_state_stays_none_not_false(tmp_path):
    """El mecanismo de build puede, en principio, declarar `dirty: null`
    cuando no pudo determinarlo -- eso nunca debe leerse como limpio."""
    build_file = _write_identity(tmp_path / ".build_identity.json", dirty=None)
    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is True
    assert identity.dirty is None
    assert identity.reason


@pytest.mark.parametrize(
    "overrides",
    [
        {"commit": "this-is-not-a-commit"},
        {"commit": "a" * 39},
        {"commit": ""},
        {"commit": None},
        {"dirty": "yes"},
        {"dirty": 1},
        {"schema_version": "some-other-version"},
        {"schema_version": None},
    ],
)
def test_malformed_build_metadata_is_explicitly_invalid_not_silently_unavailable(
    tmp_path, overrides
):
    """Un SHA inválido/abreviado, un `dirty` con tipo inválido, o una versión
    de esquema inesperada deben producir una condición explícita y
    distinguible de 'no hay metadato' -- nunca aceptarse a ciegas ni
    confundirse con la ausencia total del archivo."""
    build_file = _write_identity(tmp_path / ".build_identity.json", **overrides)
    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is False
    assert identity.source == SOURCE_BUILD_METADATA_INVALID
    assert identity.reason


def test_a_build_metadata_file_with_invalid_json_is_explicitly_invalid(tmp_path):
    build_file = tmp_path / ".build_identity.json"
    build_file.write_text("{not valid json", encoding="utf-8")

    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is False
    assert identity.source == SOURCE_BUILD_METADATA_INVALID


def test_a_build_metadata_file_that_is_a_json_list_is_explicitly_invalid(tmp_path):
    build_file = tmp_path / ".build_identity.json"
    build_file.write_text("[1, 2, 3]", encoding="utf-8")

    identity = capture_code_identity(repo_root=tmp_path, build_identity_file=build_file)

    assert identity.available is False
    assert identity.source == SOURCE_BUILD_METADATA_INVALID
