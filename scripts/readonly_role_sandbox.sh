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
#   - toda escritura fuera del /tmp efimero falla con EROFS;
#   - el proceso no tiene acceso de red;
#   - nada de lo escrito dentro sobrevive ni es visible fuera.
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
    --unshare-all \
    --die-with-parent \
    --new-session \
    --setenv REPO "$REPO_ROOT" \
    --setenv HOME /tmp \
    --chdir "$REPO_ROOT" \
    -- "$@"
