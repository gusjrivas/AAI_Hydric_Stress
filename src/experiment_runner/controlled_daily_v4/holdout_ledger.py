"""Ledger transaccional de protección del holdout de la Etapa C (2024-2025).

Decisión operativa de este encargo (2026-09-15, no atribuida a una
aprobación académica externa -- ver
`docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`,
Decisión 2, y las "Decisiones operativas autorizadas" del encargo que
implementó este módulo): un ledger SQLite (biblioteca estándar `sqlite3`)
local, en una ubicación EXPLÍCITA y persistente, siempre fuera de cualquier
`--output-dir` de artefactos -- nunca inferido, nunca creado implícitamente.
En Docker, esa ubicación debe montarse en un volumen persistente compartido
por todas las ejecuciones que protegen el mismo holdout (documentado en
`docker/experiment-v4/README` / guía de ejecución, no en este módulo).

Alcance REAL de la garantía (léase antes de asumir más de lo que este código
ofrece): este ledger impide la reapertura ACCIDENTAL del holdout a través del
flujo normal de `stage_c_runner`/`cli.py`, para procesos que comparten el
MISMO archivo de ledger sobre un almacenamiento que soporta `fsync` real
(un volumen local o un volumen Docker respaldado por un sistema de archivos
POSIX/NTFS con `fsync` funcional). No es una garantía criptográfica ni a
prueba de manipulación deliberada: no impide que alguien con acceso de
escritura al archivo lo edite a mano, lo borre, o inicie una evaluación
completamente al margen de este módulo. Tampoco impide que existan dos
ledgers INDEPENDIENTES (dos archivos distintos) protegiendo, cada uno por su
cuenta y sin saberlo, el mismo holdout -- la exclusión solo es efectiva entre
procesos que apuntan al mismo archivo.

Tres estados por identidad de holdout (nunca solo dos -- ver el documento de
decisiones): `AUSENTE` (nunca abierto), `CONFIRMADA` (apertura durable ya
confirmada, permanente) e `INDETERMINADA` (reserva en curso o interrumpida;
bloquea el acceso exactamente igual que `CONFIRMADA`, nunca se borra ni se
reinicializa sola). La inicialización del ledger es una operación EXPLÍCITA
(`init_ledger`), separada de la ejecución, que rechaza reemplazar un ledger
ya existente y deja, desde su creación, un registro con estado inicial
`AUSENTE` para la identidad de holdout dada -- nunca inferido de la ausencia
de una fila.

Ledgers sintético y científico: separados e identificados por su propio
`mode` (`synthetic`/`scientific`), persistido en el propio archivo desde la
inicialización. Toda operación posterior debe declarar el `mode` esperado;
un cruce (abrir un ledger científico con `mode='synthetic'` o viceversa) se
rechaza explícitamente, nunca se tolera en silencio.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

LEDGER_SCHEMA_VERSION = "controlled_daily_v4_holdout_ledger.v1"

LEDGER_MODE_SYNTHETIC = "synthetic"
LEDGER_MODE_SCIENTIFIC = "scientific"
LEDGER_MODES = (LEDGER_MODE_SYNTHETIC, LEDGER_MODE_SCIENTIFIC)

STATE_ABSENT = "AUSENTE"
STATE_CONFIRMED = "CONFIRMADA"
STATE_INDETERMINATE = "INDETERMINADA"
STATES = (STATE_ABSENT, STATE_CONFIRMED, STATE_INDETERMINATE)

_BUSY_TIMEOUT_MS = 30_000


class HoldoutLedgerError(RuntimeError):
    """Error base de este módulo."""


class HoldoutLedgerAlreadyInitializedError(HoldoutLedgerError):
    """`init_ledger` rechaza reemplazar un archivo de ledger ya existente."""


class HoldoutLedgerNotInitializedError(HoldoutLedgerError):
    """No existe ningún archivo de ledger en la ruta esperada. Nunca se crea
    uno implícitamente: la inicialización es una operación explícita y
    separada (`init_ledger`)."""


class HoldoutLedgerModeMismatchError(HoldoutLedgerError):
    """El `mode` (`synthetic`/`scientific`) solicitado no coincide con el
    `mode` con el que este archivo de ledger fue inicializado -- un ledger
    sintético nunca protege (ni puede confundirse con) el holdout científico,
    y viceversa."""


class HoldoutAlreadyProtectedError(HoldoutLedgerError):
    """El registro para esta identidad de holdout ya está en estado
    `CONFIRMADA` o `INDETERMINADA`: la reserva se rechaza de inmediato, sin
    haber accedido a ningún dato de 2024-2025."""

    def __init__(self, state: str, detail: str):
        self.state = state
        self.detail = detail
        super().__init__(
            f"Holdout ya protegido (estado={state}): {detail}. No se reserva ni se accede a "
            "ningún dato del holdout."
        )


class HoldoutReservationLostError(HoldoutLedgerError):
    """La reserva obtenida por este intento ya no es válida al momento de
    confirmar la apertura (otro proceso la modificó, o el registro cambió de
    forma inesperada). El registro queda en `INDETERMINADA`, sin
    reintento automático: requiere revisión humana explícita."""


class HoldoutLedgerSchemaError(HoldoutLedgerError):
    """`ledger_meta.schema_version` no es el esquema reconocido por este
    módulo (`LEDGER_SCHEMA_VERSION`), o el registro persistido es incoherente
    de otra forma verificable (por ejemplo, `mode` con un valor fuera de
    `LEDGER_MODES`). Revisión dirigida: un esquema desconocido NUNCA puede
    habilitar `reserve_holdout`/`confirm_holdout_open`/`finalize_holdout` --
    se rechaza explícitamente en cada una de las cuatro operaciones (lectura
    incluida, donde se traduce a `INDETERMINADA`, nunca a `AUSENTE`)."""


class HoldoutFinalizationOwnershipError(HoldoutLedgerError):
    """`finalize_holdout` exige el mismo `attempt_id` que ganó la reserva (y
    la confirmación): un intento distinto nunca puede finalizar -- ni
    reemplazar -- el resultado de otro intento."""


class HoldoutAlreadyFinalizedError(HoldoutLedgerError):
    """Ya existe una finalización persistida (`finalized_at` no nulo) para
    este `holdout_key`. Una segunda llamada a `finalize_holdout` nunca
    reemplaza en silencio la referencia de un resultado ya finalizado --
    incluso si la invoca el mismo `attempt_id`."""


def compute_holdout_identity_key(
    *, protocol_id: str, site: str, depth_column: str, period_start: str, period_end: str
) -> str:
    """Identidad ESTABLE del holdout protegido: protocolo + sitio + profundidad
    + período reservado (protocolo, sección 11; documento de decisiones,
    Decisión 2). Deliberadamente NO recibe commit, candidato congelado,
    `--output-dir` ni identificador de intento como parámetro -- ninguno de
    esos datos puede influir en esta clave, para que cambiarlos nunca
    produzca, ni siquiera por accidente, una identidad de holdout distinta."""
    canonical = "|".join(
        [
            "controlled_daily_v4_holdout_identity.v1",
            protocol_id,
            site,
            depth_column,
            period_start,
            period_end,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fsync_path(path: Path) -> None:
    """`fsync` explícito del archivo y, cuando el mecanismo lo permite, del
    directorio que lo contiene (documento de decisiones, Decisión 2, paso 3):
    `os.replace`/el commit de SQLite por sí solos no garantizan que el
    contenido sobreviva a una caída exactamente en ese instante sin este paso
    adicional. El `fsync` de directorio no está soportado en todas las
    plataformas (por ejemplo, Windows no lo expone de la misma forma que
    POSIX): se intenta, y su ausencia se tolera explícitamente sin fallar la
    operación completa -- documentado como límite real de la garantía, nunca
    ocultado."""
    fd = os.open(str(path), os.O_RDWR)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        # Límite documentado: no todas las plataformas permiten fsync de
        # directorio (p. ej. Windows). Se tolera explícitamente.
        pass
    finally:
        os.close(dir_fd)


@contextmanager
def _connect(path: Path):
    conn = sqlite3.connect(str(path), timeout=_BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        yield conn
    finally:
        conn.close()


def init_ledger(path: str | Path, *, mode: str, holdout_key: str) -> None:
    """Inicialización EXPLÍCITA y separada de la ejecución. Rechaza reemplazar
    un archivo de ledger ya existente en `path` (`HoldoutLedgerAlreadyInitializedError`):
    nunca se crea, ni se reinicializa, un ledger vacío de forma implícita
    porque falte el archivo esperado -- ver `read_holdout_state`.

    Deja, desde la creación, una fila con estado inicial `AUSENTE` para
    `holdout_key` -- nunca inferido de la ausencia de una fila en una tabla
    vacía (documento de decisiones, Decisión 2)."""
    if mode not in LEDGER_MODES:
        raise ValueError(f"mode inválido: '{mode}' (válidos: {LEDGER_MODES})")
    path = Path(path)
    if path.exists():
        raise HoldoutLedgerAlreadyInitializedError(
            f"Ya existe un archivo de ledger en '{path}'; init_ledger nunca reemplaza un ledger "
            "existente. Si se pretende reinicializar deliberadamente, es una intervención "
            "humana explícita y documentada fuera de este módulo, nunca un efecto automático."
        )
    path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(path) as conn:
        conn.execute(
            "CREATE TABLE ledger_meta ("
            " schema_version TEXT NOT NULL,"
            " mode TEXT NOT NULL,"
            " created_at REAL NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE TABLE holdout_registry ("
            " holdout_key TEXT PRIMARY KEY,"
            " state TEXT NOT NULL,"
            " reserved_by_attempt_id TEXT,"
            " reserved_at REAL,"
            " confirmed_at REAL,"
            " authorized_by TEXT,"
            " finalized_at REAL,"
            " finalized_result_reference TEXT,"
            " detail TEXT"
            ")"
        )
        conn.execute(
            "INSERT INTO ledger_meta (schema_version, mode, created_at) VALUES (?, ?, ?)",
            (LEDGER_SCHEMA_VERSION, mode, time.time()),
        )
        conn.execute(
            "INSERT INTO holdout_registry (holdout_key, state, detail) VALUES (?, ?, ?)",
            (holdout_key, STATE_ABSENT, "Inicializado explícitamente por init_ledger."),
        )
        conn.commit()
    _fsync_path(path)


@dataclass(frozen=True)
class HoldoutLedgerState:
    state: str
    detail: str
    authorized_by: str | None = None
    confirmed_at: float | None = None
    finalized_at: float | None = None
    finalized_result_reference: str | None = None
    reserved_by_attempt_id: str | None = None
    """`attempt_id` que ganó la reserva/confirmación vigente (revisión
    dirigida, hallazgo 2): quien recupera un resultado finalizado lo usa para
    verificar que el manifiesto de integridad persistido corresponde
    exactamente al intento que abrió y finalizó este holdout, no a otro."""

    @property
    def finalized(self) -> bool:
        return self.finalized_at is not None


def _validate_ledger_meta(conn: sqlite3.Connection, path: Path, expected_mode: str) -> None:
    """Validación CENTRALIZADA de esquema + metadatos + modo, aplicada por
    igual en lectura, reserva, confirmación y finalización (revisión
    dirigida, hallazgo 4): un `schema_version` desconocido, o un `mode`
    persistido fuera de `LEDGER_MODES`, nunca habilita ninguna de las cuatro
    operaciones -- se levanta `HoldoutLedgerSchemaError` antes de examinar
    el registro de `holdout_registry`."""
    row = conn.execute("SELECT schema_version, mode FROM ledger_meta").fetchone()
    if row is None:
        raise HoldoutLedgerSchemaError(f"'{path}': tabla 'ledger_meta' sin fila -- ledger corrupto")
    schema_version, stored_mode = row
    if schema_version != LEDGER_SCHEMA_VERSION:
        raise HoldoutLedgerSchemaError(
            f"'{path}': schema_version persistido ('{schema_version}') no es el esquema "
            f"reconocido por este módulo ('{LEDGER_SCHEMA_VERSION}'). Un esquema desconocido "
            "nunca habilita la apertura del holdout ni se trata como equivalente a AUSENTE."
        )
    if stored_mode not in LEDGER_MODES:
        raise HoldoutLedgerSchemaError(
            f"'{path}': mode persistido ('{stored_mode}') no es uno de los valores válidos "
            f"{LEDGER_MODES} -- registro de ledger_meta incoherente."
        )
    if stored_mode != expected_mode:
        raise HoldoutLedgerModeMismatchError(
            f"'{path}' fue inicializado con mode='{stored_mode}', pero esta operación exige "
            f"mode='{expected_mode}': ledgers sintético y científico están deliberadamente "
            "separados, no se permite cruzarlos."
        )


def read_holdout_state(
    path: str | Path, holdout_key: str, *, expected_mode: str
) -> HoldoutLedgerState:
    """Lee el estado actual del registro para `holdout_key`.

    Un archivo AUSENTE, corrupto, ilegible, con un esquema no reconocido, o
    sin una fila para `holdout_key`, se trata SIEMPRE como `INDETERMINADA`
    -- nunca como `AUSENTE` -- para no confundir "nunca se inicializó/quedó
    dañado" con "nunca se abrió" (documento de decisiones, Decisión 2). Un
    cruce de `mode` se rechaza explícitamente (`HoldoutLedgerModeMismatchError`),
    sin degradarse a `INDETERMINADA`: es un error de configuración de quien
    invoca, no una condición del propio holdout."""
    path = Path(path)
    if not path.exists():
        return HoldoutLedgerState(
            state=STATE_INDETERMINATE,
            detail=(
                f"No existe ningún archivo de ledger en '{path}'. Un ledger inexistente nunca "
                "se trata como 'nunca abierto' (AUSENTE): se bloquea el acceso hasta que se "
                "inicialice explícitamente (init_ledger) o se confirme, por revisión humana, "
                "que en efecto nunca se accedió al holdout."
            ),
        )
    try:
        with _connect(path) as conn:
            _validate_ledger_meta(conn, path, expected_mode)
            row = conn.execute(
                "SELECT state, authorized_by, confirmed_at, finalized_at, "
                "finalized_result_reference, detail, reserved_by_attempt_id FROM "
                "holdout_registry WHERE holdout_key = ?",
                (holdout_key,),
            ).fetchone()
    except HoldoutLedgerModeMismatchError:
        raise
    except HoldoutLedgerSchemaError as exc:
        return HoldoutLedgerState(
            state=STATE_INDETERMINATE,
            detail=f"'{path}': esquema/metadatos de ledger no reconocidos: {exc}",
        )
    except sqlite3.DatabaseError as exc:
        return HoldoutLedgerState(
            state=STATE_INDETERMINATE,
            detail=f"'{path}' no es una base SQLite legible/válida: {exc}",
        )

    if row is None:
        return HoldoutLedgerState(
            state=STATE_INDETERMINATE,
            detail=(
                f"'{path}' no tiene ninguna fila para la identidad de holdout '{holdout_key}': "
                "un ledger válido para este holdout debe haberse inicializado explícitamente "
                "con esa identidad ya presente (estado inicial AUSENTE)."
            ),
        )
    state, authorized_by, confirmed_at, finalized_at, finalized_ref, detail, owner_attempt_id = row
    if state not in STATES:
        return HoldoutLedgerState(
            state=STATE_INDETERMINATE,
            detail=f"'{path}': estado persistido no reconocido ('{state}')",
        )
    return HoldoutLedgerState(
        state=state,
        detail=detail or "",
        authorized_by=authorized_by,
        confirmed_at=confirmed_at,
        finalized_at=finalized_at,
        finalized_result_reference=finalized_ref,
        reserved_by_attempt_id=owner_attempt_id,
    )


def reserve_holdout(path: str | Path, holdout_key: str, *, mode: str, attempt_id: str) -> None:
    """Reserva atómica y durable de la apertura (documento de decisiones,
    Decisión 2, paso 2): procede ÚNICAMENTE si el estado actual es `AUSENTE`.
    Marca el registro como `INDETERMINADA` (con `reserved_by_attempt_id`) y
    fuerza esa escritura a almacenamiento persistente ANTES de retornar --
    una interrupción justo después de esta llamada deja el holdout protegido
    (nunca vuelve a `AUSENTE` por sí solo).

    Rechaza de inmediato (`HoldoutAlreadyProtectedError`), sin modificar el
    registro, si el estado ya es `CONFIRMADA` o `INDETERMINADA` -- esta
    función es también el mecanismo que impide dos reservas concurrentes:
    solo un proceso puede ganar la transacción `BEGIN IMMEDIATE`."""
    path = Path(path)
    if not path.exists():
        raise HoldoutLedgerNotInitializedError(
            f"No existe ningún ledger en '{path}': init_ledger debe ejecutarse explícitamente "
            "antes de poder reservar cualquier apertura."
        )
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _validate_ledger_meta(conn, path, mode)
            row = conn.execute(
                "SELECT state FROM holdout_registry WHERE holdout_key = ?", (holdout_key,)
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                raise HoldoutLedgerError(
                    f"'{path}': no hay fila para la identidad de holdout '{holdout_key}' -- "
                    "el ledger no fue inicializado con esta identidad."
                )
            state = row[0]
            if state != STATE_ABSENT:
                conn.execute("ROLLBACK")
                raise HoldoutAlreadyProtectedError(
                    state,
                    f"holdout_key='{holdout_key}' en '{path}' ya no está AUSENTE",
                )
            conn.execute(
                "UPDATE holdout_registry SET state = ?, reserved_by_attempt_id = ?, "
                "reserved_at = ?, detail = ? WHERE holdout_key = ?",
                (
                    STATE_INDETERMINATE,
                    attempt_id,
                    time.time(),
                    "Reserva en curso (paso 2): pendiente de confirmación durable (paso 3).",
                    holdout_key,
                ),
            )
            conn.commit()
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
    _fsync_path(path)


def confirm_holdout_open(
    path: str | Path,
    holdout_key: str,
    *,
    mode: str,
    attempt_id: str,
    authorized_by: str,
) -> None:
    """Confirma de forma durable la apertura (documento de decisiones,
    Decisión 2, paso 3), ÚNICAMENTE si esta misma llamada previa a
    `reserve_holdout` (mismo `attempt_id`) sigue siendo la reserva vigente.
    Fuerza la escritura a almacenamiento persistente antes de retornar.

    Debe invocarse ANTES de acceder a cualquier dato de 2024-2025 (nunca
    después): recién cuando esta función retorna sin excepción el runner
    tiene permiso para cargar y evaluar el holdout."""
    if not authorized_by:
        raise ValueError(
            "confirm_holdout_open exige 'authorized_by' explícito (nombre/rol de quien "
            "autoriza la apertura, protocolo sección 11) -- sin valor por defecto."
        )
    path = Path(path)
    if not path.exists():
        # `sqlite3.connect` crea un archivo vacío de forma implícita si no
        # existe -- revisión dirigida (hallazgo 4): nunca se crea una base
        # vacía por la ausencia del archivo esperado durante una operación.
        raise HoldoutLedgerNotInitializedError(
            f"No existe ningún ledger en '{path}': init_ledger debe ejecutarse explícitamente "
            "antes de poder confirmar cualquier apertura."
        )
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _validate_ledger_meta(conn, path, mode)
            row = conn.execute(
                "SELECT state, reserved_by_attempt_id FROM holdout_registry WHERE holdout_key = ?",
                (holdout_key,),
            ).fetchone()
            if row is None or row[0] != STATE_INDETERMINATE or row[1] != attempt_id:
                conn.execute("ROLLBACK")
                raise HoldoutReservationLostError(
                    f"'{path}': la reserva de holdout_key='{holdout_key}' para attempt_id="
                    f"'{attempt_id}' ya no es válida (estado actual={row[0] if row else None!r}, "
                    f"reservado por={row[1] if row else None!r}). El registro queda en "
                    "INDETERMINADA -- requiere revisión humana, sin reintento automático."
                )
            conn.execute(
                "UPDATE holdout_registry SET state = ?, confirmed_at = ?, authorized_by = ?, "
                "detail = ? WHERE holdout_key = ?",
                (
                    STATE_CONFIRMED,
                    time.time(),
                    authorized_by,
                    "Apertura confirmada de forma durable (paso 3). Evento único e irreversible.",
                    holdout_key,
                ),
            )
            conn.commit()
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
    _fsync_path(path)


def finalize_holdout(
    path: str | Path,
    holdout_key: str,
    *,
    mode: str,
    attempt_id: str,
    result_reference: str,
) -> None:
    """Marca de finalización (documento de decisiones, Decisión 2, paso 5),
    separada de la apertura: exige que el estado actual sea `CONFIRMADA`
    (nunca finaliza un registro que no llegó a confirmarse). Su ausencia no
    significa que el holdout siga cerrado -- la confirmación (paso 3) ya lo
    abrió de forma permanente -- significa únicamente que todavía no hay un
    resultado recuperable.

    Revisión dirigida (hallazgo 4): exige el mismo `attempt_id` que ganó la
    reserva/confirmación (`HoldoutFinalizationOwnershipError` si no coincide
    -- un intento distinto nunca finaliza el resultado de otro), y rechaza
    una segunda finalización (`HoldoutAlreadyFinalizedError` si
    `finalized_at` ya está presente) en vez de reemplazar en silencio la
    referencia de un resultado ya finalizado."""
    path = Path(path)
    if not path.exists():
        # Mismo motivo que en `confirm_holdout_open`: `sqlite3.connect` crea
        # un archivo vacío si no existe -- nunca se crea una base vacía por
        # la ausencia del archivo esperado durante una operación.
        raise HoldoutLedgerNotInitializedError(
            f"No existe ningún ledger en '{path}': init_ledger debe ejecutarse explícitamente "
            "antes de poder finalizar cualquier apertura."
        )
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _validate_ledger_meta(conn, path, mode)
            row = conn.execute(
                "SELECT state, reserved_by_attempt_id, finalized_at FROM holdout_registry "
                "WHERE holdout_key = ?",
                (holdout_key,),
            ).fetchone()
            if row is None or row[0] != STATE_CONFIRMED:
                conn.execute("ROLLBACK")
                raise HoldoutLedgerError(
                    f"'{path}': no se puede finalizar holdout_key='{holdout_key}' -- estado "
                    f"actual={row[0] if row else None!r} (se exige CONFIRMADA)"
                )
            owner_attempt_id, finalized_at = row[1], row[2]
            if owner_attempt_id != attempt_id:
                conn.execute("ROLLBACK")
                raise HoldoutFinalizationOwnershipError(
                    f"'{path}': finalize_holdout invocado con attempt_id='{attempt_id}', pero "
                    f"la reserva/confirmación vigente pertenece a attempt_id="
                    f"'{owner_attempt_id}'. Un intento distinto nunca finaliza el resultado de "
                    "otro."
                )
            if finalized_at is not None:
                conn.execute("ROLLBACK")
                raise HoldoutAlreadyFinalizedError(
                    f"'{path}': holdout_key='{holdout_key}' ya fue finalizado en "
                    f"{finalized_at!r}. Una segunda finalización nunca reemplaza en silencio "
                    "la referencia de un resultado ya finalizado."
                )
            conn.execute(
                "UPDATE holdout_registry SET finalized_at = ?, finalized_result_reference = ? "
                "WHERE holdout_key = ?",
                (time.time(), result_reference, holdout_key),
            )
            conn.commit()
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
    _fsync_path(path)


__all__ = [
    "LEDGER_MODE_SCIENTIFIC",
    "LEDGER_MODE_SYNTHETIC",
    "LEDGER_MODES",
    "LEDGER_SCHEMA_VERSION",
    "STATE_ABSENT",
    "STATE_CONFIRMED",
    "STATE_INDETERMINATE",
    "STATES",
    "HoldoutAlreadyFinalizedError",
    "HoldoutAlreadyProtectedError",
    "HoldoutFinalizationOwnershipError",
    "HoldoutLedgerAlreadyInitializedError",
    "HoldoutLedgerError",
    "HoldoutLedgerModeMismatchError",
    "HoldoutLedgerNotInitializedError",
    "HoldoutLedgerSchemaError",
    "HoldoutLedgerState",
    "HoldoutReservationLostError",
    "compute_holdout_identity_key",
    "confirm_holdout_open",
    "finalize_holdout",
    "init_ledger",
    "read_holdout_state",
    "reserve_holdout",
]
