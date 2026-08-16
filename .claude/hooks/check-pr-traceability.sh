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

if [[ "${SKIP_PR_TRACEABILITY:-}" == "1" ]]; then
  echo "check-pr-traceability.sh: bypass explícito vía SKIP_PR_TRACEABILITY=1" >&2
  allow
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "check-pr-traceability.sh: jq no está instalado, se omite la verificación de trazabilidad (fail-open)" >&2
  allow
fi

input="$(cat)"
command_str="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"

if [[ -z "$command_str" ]]; then
  allow
fi

if ! [[ "$command_str" =~ gh[[:space:]]+pr[[:space:]]+create ]]; then
  allow
fi

base_branch="main"
if ! git rev-parse --verify "origin/${base_branch}" >/dev/null 2>&1; then
  allow
fi

diff_files="$(git diff --name-only "origin/${base_branch}...HEAD" 2>/dev/null || true)"
commit_messages="$(git log "origin/${base_branch}..HEAD" --format=%B 2>/dev/null || true)"

references_plan=false
if [[ "$command_str" =~ HU[1-8] ]] || [[ "$commit_messages" =~ HU[1-8] ]] || printf '%s' "$diff_files" | grep -q '^openspec/changes/'; then
  references_plan=true
fi

if [[ "$references_plan" == false ]]; then
  deny "El PR no referencia ningún change de openspec/changes/ ni menciona una HU (HU1-HU8) en el título/cuerpo del comando o en los mensajes de commit. Agregá esa referencia antes de abrir el PR (ver openspec/project.md, sección 'Convenciones para changes')."
fi

touches_src_or_research=false
if printf '%s' "$diff_files" | grep -qE '^(src/|docs/research/)'; then
  touches_src_or_research=true
fi

touches_seguimiento=false
if printf '%s' "$diff_files" | grep -q '^docs/seguimiento-tareas.md$'; then
  touches_seguimiento=true
fi

if [[ "$touches_src_or_research" == true && "$touches_seguimiento" == false ]]; then
  deny "El PR modifica src/ o docs/research/ pero no actualiza docs/seguimiento-tareas.md. Actualizá el seguimiento de tareas antes de abrir el PR."
fi

allow
