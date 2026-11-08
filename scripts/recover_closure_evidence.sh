#!/usr/bin/env bash
# Copia de solo lectura de las salidas A/B/C protegidas a una carpeta NUEVA y legible.
#
# Solo lee el origen: no cambia permisos ni propietarios de los originales, no borra ni
# mueve nada, no ejecuta entrenamiento ni evaluación. Calcula SHA-256 del origen antes y
# después de copiar, compara ambos y verifica la copia contra el hash del origen.
# Los permisos/propietario se ajustan SOLO en la copia (DST).
#
# Variables (todas obligatorias):
#   SRC    directorio evidence/ de la campaña (origen)
#   DST    directorio NUEVO, inexistente y fuera de SRC (destino)
#   OWNER  usuario que será dueño de la copia
set -euo pipefail

fail() { echo "ERROR: $*" >&2; exit 1; }

SRC=${SRC:?definir SRC}
DST=${DST:?definir DST}
OWNER=${OWNER:?definir OWNER}
DIRS=(A A_sensitivity_7_28cm B C)

[ -d "$SRC" ] || fail "no existe SRC: $SRC"
[ ! -e "$DST" ] || fail "DST ya existe (usar una carpeta nueva): $DST"
case "$DST/" in "$SRC"/*) fail "DST no puede estar dentro de SRC" ;; esac
id "$OWNER" >/dev/null 2>&1 || fail "usuario inexistente: $OWNER"
for d in "${DIRS[@]}"; do [ -d "$SRC/$d" ] || fail "falta $SRC/$d"; done

mkdir -p "$DST"
cd "$SRC"
find "${DIRS[@]}" -type f -print0 | LC_ALL=C sort -z >"$DST/filelist.nul"
n=$(tr -cd '\0' <"$DST/filelist.nul" | wc -c)
[ "$n" -gt 0 ] || fail "el origen no contiene archivos"

xargs -0 sha256sum <"$DST/filelist.nul" >"$DST/SHA256SUMS.source-before"
tar --null -T "$DST/filelist.nul" -cf - | tar -xf - -C "$DST" --no-same-owner
xargs -0 sha256sum <"$DST/filelist.nul" >"$DST/SHA256SUMS.source-after"
cmp -s "$DST/SHA256SUMS.source-before" "$DST/SHA256SUMS.source-after" ||
  fail "el origen cambió durante la copia"

# Permisos y propietario solo de la copia.
chown -R "$OWNER" "$DST"
chmod -R u+rwX,go-rwx "$DST"

cd "$DST"
sha256sum -c SHA256SUMS.source-before >verify.log || fail "la copia no coincide con el origen (ver verify.log)"
copied=$(find "${DIRS[@]}" -type f | wc -l)
[ "$copied" -eq "$n" ] || fail "cantidad copiada $copied != origen $n"
echo "OK: $n archivos copiados y verificados en $DST (SHA256SUMS.source-before)"
