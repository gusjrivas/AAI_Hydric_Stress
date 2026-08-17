#!/usr/bin/env bash
set -euo pipefail

allow() {
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}'
  exit 0
}

deny() {
  local reason="$1"
  local reason_escaped="${reason//\\/\\\\}"
  reason_escaped="${reason_escaped//\"/\\\"}"
  printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "%s"}}\n' \
    "$reason_escaped"
  exit 0
}

if [[ "${SKIP_ISSUE_EVIDENCE:-}" == "1" ]]; then
  echo "check-issue-close-evidence.sh: bypass explícito vía SKIP_ISSUE_EVIDENCE=1" >&2
  allow
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "check-issue-close-evidence.sh: jq no está instalado, se omite la verificación de evidencia (fail-open)" >&2
  allow
fi

input="$(cat)"
command_str="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"

if [[ -z "$command_str" ]]; then
  allow
fi

if ! [[ "$command_str" =~ gh[[:space:]]+issue[[:space:]]+close ]]; then
  allow
fi

if ! [[ "$command_str" =~ --comment ]]; then
  deny "El cierre de issue no incluye --comment con la evidencia de por qué se considera terminado. Agregá --comment citando el archivo/PR/test concreto que lo demuestra (ver openspec/project.md y docs/seguimiento-tareas.md)."
fi

# Heurística mínima: la evidencia debe referenciar algo concreto (una ruta
# de archivo, un PR, o un test), no ser un comentario vacío de trámite
# ("listo", "hecho"). No valida el contenido semánticamente, solo que haya
# una referencia con forma de evidencia verificable.
if ! [[ "$command_str" =~ (docs/|src/|tests/|openspec/|\.md|\.py|#[0-9]+) ]]; then
  deny "El --comment del cierre de issue no parece referenciar evidencia concreta (una ruta de archivo, un PR con #, o un test). Citá el archivo/sección o PR exacto que demuestra que la tarea está terminada, no una confirmación genérica."
fi

allow
