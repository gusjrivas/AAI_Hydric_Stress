#!/usr/bin/env bash
# Enforcement tecnico de solo lectura para los roles lectores del cierre
# cientifico (explorador, verificador de evidencia, critico, auditor).
#
# Motivacion: AUD-READ03 / LNX-03 / CRIT-SUB-01 registran que hasta ahora el
# caracter de solo lectura de los roles lectores era una CONDUCTA observada,
# no un aislamiento impuesto por el sistema. Este envoltorio convierte esa
# conducta en una restriccion verificable: el proceso hijo ve todo el sistema
# de archivos montado de solo lectura, sin red, y con un /tmp efimero propio.
#
# Qué garantiza (verificable con scripts/verify_readonly_sandbox.sh):
#   - toda escritura a rutas persistentes del host (repositorio, $HOME real,
#     cualquier ruta de /) falla con EROFS;
#   - el proceso no tiene acceso de red;
#   - nada de lo escrito dentro sobrevive ni es visible fuera.
#
# Precisión deliberada: ademas del /tmp efimero, /dev y /dev/shm dentro del
# sandbox son tmpfs escribibles. No son un escape — mueren con el sandbox y no
# son visibles desde fuera — pero decir "toda escritura fuera de /tmp falla"
# seria falso. verify_readonly_sandbox.sh comprueba explicitamente que lo
# escrito en /dev no sobrevive.
#
# ESCAPE CONOCIDO Y CERRADO (hallazgo A-01 de la auditoria independiente):
# en WSL, la interoperabilidad con Windows permite invocar binarios PE
# (`/mnt/c/Windows/System32/curl.exe`, `cmd.exe`, ...). Esos procesos NO
# corren dentro de los namespaces de Linux: se ejecutan en el host Windows,
# con red completa y con escritura al repositorio a traves de
# `\\wsl.localhost\...`. Ni `--unshare-net` ni `--ro-bind / /` los alcanzan.
# El auditor lo demostro creando un archivo en la raiz del repositorio desde
# dentro del sandbox. Mitigacion aplicada aqui: `--tmpfs /mnt` oculta las
# unidades de Windows, `--ro-bind /dev/null /init` neutraliza el ayudante de interop registrado en binfmt_misc, y se
# limpian `WSL_INTEROP`, `WSL_DISTRO_NAME`, `WSLENV` y `WSL2_GUI_APPS_ENABLED`,
# ademas de fijar un PATH sin rutas de Windows.
# Limite honesto: esto elimina la via conocida, no demuestra que no exista
# otra. La afirmacion correcta es "impone solo lectura y ausencia de red a
# procesos Linux, y cierra la via de interop WSL conocida", nunca un
# aislamiento absoluto.
#
# Qué NO garantiza:
#   - no sustituye la independencia de sesion/contexto del revisor;
#   - no acredita que un agente concreto haya sido ejecutado a traves de el:
#     eso debe registrarse por separado, con el comando exacto usado;
#   - no impone limites de CPU ni de memoria.
#
# Uso:
#   scripts/readonly_role_sandbox.sh <comando> [args...]
#   scripts/readonly_role_sandbox.sh bash -c 'git -C "$REPO" status --porcelain'
#
# Requiere bubblewrap (bwrap) y espacios de nombres de usuario sin privilegios.

set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "uso: $0 <comando> [args...]" >&2
    exit 2
fi

if ! command -v bwrap >/dev/null 2>&1; then
    echo "ERROR: bwrap (bubblewrap) no esta disponible; no se puede imponer solo lectura." >&2
    echo "No degradar a ejecucion sin aislamiento: registrar el bloqueo." >&2
    exit 3
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --unshare-all incluye --unshare-net: el proceso queda sin red.
# --ro-bind / / monta la raiz completa de solo lectura; /dev y /proc se
# reconstruyen; /tmp es un tmpfs efimero exclusivo del hijo.
exec bwrap \
    --ro-bind / / \
    --dev /dev \
    --proc /proc \
    --tmpfs /tmp \
    --tmpfs /mnt \
    --ro-bind /dev/null /init \
    --unshare-all \
    --die-with-parent \
    --new-session \
    --unsetenv WSL_INTEROP \
    --unsetenv WSL_DISTRO_NAME \
    --unsetenv WSLENV \
    --unsetenv WSL2_GUI_APPS_ENABLED \
    --setenv REPO "$REPO_ROOT" \
    --setenv HOME /tmp \
    --setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    --chdir "$REPO_ROOT" \
    -- "$@"
