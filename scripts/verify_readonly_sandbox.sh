#!/usr/bin/env bash
# Comprobacion negativa reproducible del enforcement de solo lectura
# (scripts/readonly_role_sandbox.sh). Emite un registro JSON en stdout.
#
# Comprueba, dentro del sandbox:
#   1. que una lectura del repositorio funciona;
#   2. que una escritura en el repositorio falla con EROFS;
#   3. que una escritura en $HOME real falla con EROFS;
#   4. que una escritura en el /tmp efimero funciona;
#   4b. que /dev dentro del sandbox es tmpfs efimero: lo escrito alli NO
#       sobrevive fuera (no es un escape, pero se comprueba en vez de
#       afirmarse);
#   5. que no hay resolucion DNS (sin red);
# y, fuera del sandbox:
#   6. que ninguna de las rutas de prueba (repositorio, $HOME real, /dev)
#      existe despues.
#
# Salida: exit 0 si TODAS las condiciones se cumplen; 1 en caso contrario.
# Un fallo aqui significa que el enforcement NO esta acreditado; nunca debe
# reinterpretarse como conducta de solo lectura aceptable.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="$REPO_ROOT/scripts/readonly_role_sandbox.sh"
STAMP="$$-$(date -u +%s)"
REPO_PROBE="$REPO_ROOT/.readonly-sandbox-probe-$STAMP"
HOME_PROBE="$HOME/.readonly-sandbox-probe-$STAMP"

inner=$(cat <<INNER
read_ok=0
if head -c 1 "\$REPO/AGENTS.md" >/dev/null 2>&1; then read_ok=1; fi
echo "read_repo_ok=\$read_ok"

err=\$( { echo probe > "$REPO_PROBE"; } 2>&1 ); echo "write_repo_exit=\$?"
echo "write_repo_stderr=\$err"

err=\$( { echo probe > "$HOME_PROBE"; } 2>&1 ); echo "write_home_exit=\$?"
echo "write_home_stderr=\$err"

{ echo probe > /tmp/readonly-sandbox-probe; } 2>/dev/null; echo "write_tmp_exit=\$?"

{ echo probe > /dev/readonly-sandbox-probe-$STAMP; } 2>/dev/null; echo "write_dev_exit=\$?"

getent hosts pypi.org >/dev/null 2>&1; echo "dns_exit=\$?"
INNER
)

out=$("$SANDBOX" /bin/bash -c "$inner" 2>&1)
sandbox_exit=$?

get() { printf '%s\n' "$out" | grep -m1 "^$1=" | cut -d= -f2-; }

read_repo_ok=$(get read_repo_ok)
write_repo_exit=$(get write_repo_exit)
write_repo_stderr=$(get write_repo_stderr)
write_home_exit=$(get write_home_exit)
write_tmp_exit=$(get write_tmp_exit)
write_dev_exit=$(get write_dev_exit)
dns_exit=$(get dns_exit)

repo_probe_absent=true; [ -e "$REPO_PROBE" ] && repo_probe_absent=false
home_probe_absent=true; [ -e "$HOME_PROBE" ] && home_probe_absent=false
dev_probe_absent=true; [ -e "/dev/readonly-sandbox-probe-$STAMP" ] && dev_probe_absent=false

pass=true
[ "$read_repo_ok" = "1" ] || pass=false
[ "${write_repo_exit:-0}" != "0" ] || pass=false
[ "${write_home_exit:-0}" != "0" ] || pass=false
[ "${write_tmp_exit:-1}" = "0" ] || pass=false
[ "${dns_exit:-0}" != "0" ] || pass=false
[ "$repo_probe_absent" = "true" ] || pass=false
[ "$home_probe_absent" = "true" ] || pass=false
[ "$dev_probe_absent" = "true" ] || pass=false
case "$write_repo_stderr" in *"Read-only file system"*) ;; *) pass=false ;; esac

verdict=FAIL; [ "$pass" = "true" ] && verdict=PASS

cat <<JSON
{
  "schema_version": "1.0",
  "record": "readonly_role_sandbox_enforcement_probe",
  "checked_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "sandbox_wrapper": "scripts/readonly_role_sandbox.sh",
  "bwrap_version": "$(bwrap --version 2>/dev/null || echo ABSENT)",
  "sandbox_launch_exit_code": $sandbox_exit,
  "checks": {
    "read_repository_succeeds": $( [ "$read_repo_ok" = "1" ] && echo true || echo false ),
    "write_repository_fails": $( [ "${write_repo_exit:-0}" != "0" ] && echo true || echo false ),
    "write_repository_stderr": "$write_repo_stderr",
    "write_real_home_fails": $( [ "${write_home_exit:-0}" != "0" ] && echo true || echo false ),
    "write_ephemeral_tmp_succeeds": $( [ "${write_tmp_exit:-1}" = "0" ] && echo true || echo false ),
    "network_dns_unavailable": $( [ "${dns_exit:-0}" != "0" ] && echo true || echo false ),
    "repository_probe_absent_after": $repo_probe_absent,
    "home_probe_absent_after": $home_probe_absent,
    "ephemeral_dev_write_exit_code": ${write_dev_exit:-null},
    "dev_probe_absent_after": $dev_probe_absent
  },
  "probe_paths": {
    "repository": "$REPO_PROBE",
    "home": "$HOME_PROBE"
  },
  "verdict": "$verdict",
  "limitation": "Acredita que el mecanismo impone solo lectura y ausencia de red. No acredita, por si solo, que un agente revisor concreto haya sido ejecutado a traves de el; eso exige registrar el comando exacto de esa sesion."
}
JSON

[ "$verdict" = "PASS" ] && exit 0 || exit 1
