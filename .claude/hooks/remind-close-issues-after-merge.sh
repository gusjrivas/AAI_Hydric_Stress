#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "remind-close-issues-after-merge.sh: jq no está instalado, se omite el recordatorio" >&2
  exit 0
fi

input="$(cat)"
command_str="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"

if [[ -z "$command_str" ]]; then
  exit 0
fi

if ! [[ "$command_str" =~ gh[[:space:]]+pr[[:space:]]+merge ]]; then
  exit 0
fi

reason='Este comando mergeó un PR. Antes de seguir: revisá docs/seguimiento-tareas.md para ver si alguna tarea quedó completa (✅) con este merge, y si corresponde, usá la skill closing-issues (.claude/skills/closing-issues/SKILL.md) para cerrar los issues de GitHub correspondientes con `gh issue close <N> --comment "..."` citando evidencia real (archivo/PR/test). No cierres issues marcados 🟡 o ⬜ en ese documento.'

printf '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": %s}}\n' \
  "$(printf '%s' "$reason" | jq -Rs .)"
