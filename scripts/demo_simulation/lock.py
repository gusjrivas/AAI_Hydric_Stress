"""Exclusión de proceso por sesión (diseño, sección 4: "un lock de
sistema operativo por sesión impide dos workers"). Usado tanto por la
ejecución directa de la CLI (`scripts.demo_simulation.worker.run_session`,
entrega 1) como por el worker de fondo del adaptador HTTP local
(`scripts.demo_simulation.control`, entrega 2), para que ambos caminos
de entrada no puedan avanzar la misma sesión al mismo tiempo.

Es un lock de archivo real (`fcntl.flock` en POSIX, `msvcrt.locking` en
Windows), sostenido mientras el descriptor permanece abierto: si el
proceso muere sin liberarlo explícitamente, el sistema operativo lo
libera igual al cerrar el proceso. No depende de un PID file leído a
mano ni de un booleano en memoria.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class SessionLockError(RuntimeError):
    """La sesión ya tiene un worker activo sosteniendo el lock."""


def lock_path(sessions_root: Path, session_id: str) -> Path:
    return sessions_root / session_id / "worker.lock"


class SessionLock:
    """Lock exclusivo, no bloqueante, de una sesión de demostración.

    `acquire()` levanta `SessionLockError` de inmediato si otro proceso
    ya sostiene el lock, en vez de esperar: quien detecta la colisión
    decide qué hacer (no reintenta ni bloquea la sesión ajena, ver
    `scripts.demo_simulation.control.run_controlled_worker`).
    """

    def __init__(self, path: Path):
        self._path = path
        self._fh = None

    def acquire(self) -> SessionLock:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self._path, "a+b")
        try:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                fh.write(b"0")
                fh.flush()
            fh.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            fh.close()
            raise SessionLockError(
                f"La sesión ya tiene un worker activo (lock en {self._path})."
            ) from error
        self._fh = fh
        return self

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> SessionLock:
        return self.acquire()

    def __exit__(self, *_exc: object) -> None:
        self.release()
