#!/usr/bin/env bash
# Detiene únicamente los contenedores de la sesión de demostración indicada
# (Paso 4.1.1 §2) — identificados por nombre (derivado del `session_id`),
# nunca por PID, que podría haber sido reutilizado por otro proceso desde
# que la sesión arrancó. No borra los registros de feedback de la sesión:
# quedan como evidencia en `replay_feedback/demo-session-<id>/`. No toca
# ningún contenedor ni servicio ajeno a esta sesión.

set -euo pipefail
export MSYS_NO_PATHCONV=1

SESSION_ID="${1:?Uso: scripts/demo_replay_down.sh <session_id>}"

# Misma validación que demo_replay_up.sh, antes de derivar ninguna ruta o
# nombre de contenedor a partir de session_id.
if ! [[ "$SESSION_ID" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
  echo "session_id inválido: '$SESSION_ID'. Solo letras, números, '-' y '_', empezando por letra o número." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_DIR="$REPO_ROOT/.demo_replay_sessions/$SESSION_ID"
BACKEND_NAME="hr-demo-backend-$SESSION_ID"
FRONTEND_NAME="hr-demo-frontend-$SESSION_ID"

if [ ! -d "$SESSION_DIR" ]; then
  echo "No existe una sesión registrada con id '$SESSION_ID' en $SESSION_DIR" >&2
  exit 1
fi

if docker rm -f "$BACKEND_NAME" >/dev/null 2>&1; then
  echo "Detenido $BACKEND_NAME."
else
  echo "$BACKEND_NAME ya no estaba en ejecución."
fi

if docker rm -f "$FRONTEND_NAME" >/dev/null 2>&1; then
  echo "Detenido $FRONTEND_NAME."
else
  echo "$FRONTEND_NAME ya no estaba en ejecución."
fi

echo "Sesión '$SESSION_ID' detenida. Feedback preservado en:"
grep FEEDBACK_DIR "$SESSION_DIR/session.env" | cut -d= -f2-
