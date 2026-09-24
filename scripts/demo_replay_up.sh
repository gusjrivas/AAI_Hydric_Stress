#!/usr/bin/env bash
# Arranque reproducible de la demo "Reproducción histórica" (Paso 4.1,
# cerrado en el Paso 4.1.1 §2), usando el procedimiento Docker que ya se
# verificó funcionando (dos contenedores desechables de las imágenes
# `aai-hydric-stress-backend`/`aai-hydric-stress-frontend`, publicados en
# puertos aislados de los operativos 8000/5173) — no procesos locales
# (Python/Node no están disponibles en este host fuera de Docker).
#
# - Código y paquete científico se montan de solo lectura (`:ro`); el
#   backend nunca puede escribirlos.
# - El feedback de esta sesión vive en un directorio nuevo (`replay_feedback/
#   demo-session-<id>/`), montado aparte con lectura/escritura — las
#   sesiones anteriores no se tocan.
# - Un `<session_id>` ya usado se rechaza explícitamente (no se sobrescribe
#   ni se reutiliza en silencio); se valida su forma (letras/números/guion/
#   guion bajo) antes de usarlo en cualquier ruta o nombre de contenedor.
# - Los puertos se publican solo en 127.0.0.1 (demo local, nunca expuesta en
#   una interfaz de red accesible desde fuera de esta máquina).
# - No modifica ningún `.env` ni servicio compartido (nunca usa
#   `aai-hydric-stress-backend-1`/`...-frontend-1`, ni sus puertos ni sus
#   nombres de contenedor).
# - Antes de anunciar éxito, comprueba que el backend y el frontend
#   realmente respondan (no solo que el proceso haya arrancado).
# - Si el arranque falla en cualquier paso, retira únicamente los
#   contenedores y el directorio de ESTA sesión — nunca otros.
# - `demo_replay_down.sh` detiene por nombre de contenedor (derivado del
#   `session_id`), nunca por PID.
#
# Uso: scripts/demo_replay_up.sh <session_id>
# No entrena, no infiere, no recalibra, no recalcula métricas ni accede al
# holdout v4. No regenera el paquete científico.

set -euo pipefail
export MSYS_NO_PATHCONV=1

SESSION_ID="${1:?Uso: scripts/demo_replay_up.sh <session_id>}"

# Validar session_id ANTES de construir cualquier ruta o ejecutar Docker:
# solo letras, números, guion y guion bajo, empezando por letra o número.
# Rechaza vacío, separadores de ruta, ".."/"." y cualquier otro carácter que
# pudiera alterar una ruta de archivo o un nombre de contenedor.
if ! [[ "$SESSION_ID" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
  echo "session_id inválido: '$SESSION_ID'. Solo letras, números, '-' y '_', empezando por letra o número." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT_WIN="$(cd "$REPO_ROOT" && pwd -W 2>/dev/null || pwd)"

BACKEND_IMAGE="${DEMO_REPLAY_BACKEND_IMAGE:-aai-hydric-stress-backend}"
FRONTEND_IMAGE="${DEMO_REPLAY_FRONTEND_IMAGE:-aai-hydric-stress-frontend}"
BACKEND_PORT="${DEMO_REPLAY_BACKEND_PORT:-8100}"
FRONTEND_PORT="${DEMO_REPLAY_FRONTEND_PORT:-5190}"

BACKEND_NAME="hr-demo-backend-$SESSION_ID"
FRONTEND_NAME="hr-demo-frontend-$SESSION_ID"
SESSION_DIR="$REPO_ROOT/.demo_replay_sessions/$SESSION_ID"
FEEDBACK_DIR="$REPO_ROOT/replay_feedback/demo-session-$SESSION_ID"
PACKAGE_NAME="${DEMO_REPLAY_PACKAGE_NAME:-base-seed4-1157696b7b-v2}"

# Rechazar un session_id ya usado (directorio de sesión o contenedores con
# ese nombre) — nunca sobrescribirlo.
if [ -d "$SESSION_DIR" ]; then
  echo "La sesión '$SESSION_ID' ya existe ($SESSION_DIR). Elegí otro session_id." >&2
  exit 1
fi
if docker inspect "$BACKEND_NAME" >/dev/null 2>&1 || docker inspect "$FRONTEND_NAME" >/dev/null 2>&1; then
  echo "Ya existe un contenedor con el nombre de la sesión '$SESSION_ID'. Elegí otro session_id." >&2
  exit 1
fi
if [ ! -f "$REPO_ROOT/replay_packages/$PACKAGE_NAME/manifest.json" ]; then
  echo "Paquete no encontrado: replay_packages/$PACKAGE_NAME (no se regenera aquí)." >&2
  exit 1
fi

mkdir -p "$SESSION_DIR" "$FEEDBACK_DIR"

fail() {
  echo "$1" >&2
  echo "Arranque fallido: retirando únicamente los recursos de la sesión '$SESSION_ID'." >&2
  docker rm -f "$BACKEND_NAME" "$FRONTEND_NAME" >/dev/null 2>&1 || true
  rm -rf "$SESSION_DIR"
  exit 1
}

echo "Iniciando sesión '$SESSION_ID'..."

docker run -d --name "$BACKEND_NAME" \
  -v "${REPO_ROOT_WIN}:/tmp/hr_workspace:ro" \
  -v "${FEEDBACK_DIR}:/tmp/hr_feedback" \
  -w /tmp/hr_workspace/backend \
  -p "127.0.0.1:${BACKEND_PORT}:8000" \
  -e PYTHONPATH=/tmp/hr_workspace/src:/tmp/hr_workspace/backend \
  -e MLFLOW_TRACKING_URI="sqlite:////tmp/mlflow_demo_${SESSION_ID}.db" \
  -e HISTORICAL_REPLAY_ENABLED=true \
  -e HISTORICAL_REPLAY_PACKAGE_DIR="/tmp/hr_workspace/replay_packages/${PACKAGE_NAME}" \
  -e HISTORICAL_REPLAY_FEEDBACK_DIR=/tmp/hr_feedback \
  -e CORS_EXTRA_ORIGINS="http://localhost:${FRONTEND_PORT}" \
  "$BACKEND_IMAGE" \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >/dev/null \
  || fail "No se pudo arrancar el contenedor de backend ($BACKEND_NAME)."

docker run -d --name "$FRONTEND_NAME" \
  -v "${REPO_ROOT_WIN}/frontend/src:/app/src:ro" \
  -v "${REPO_ROOT_WIN}/frontend/index.html:/app/index.html:ro" \
  -p "127.0.0.1:${FRONTEND_PORT}:5173" \
  -e VITE_API_BASE_URL="http://localhost:${BACKEND_PORT}" \
  "$FRONTEND_IMAGE" \
  npm run dev -- --host 0.0.0.0 --port 5173 >/dev/null \
  || fail "No se pudo arrancar el contenedor de frontend ($FRONTEND_NAME)."

cat > "$SESSION_DIR/session.env" <<EOF
SESSION_ID=$SESSION_ID
BACKEND_NAME=$BACKEND_NAME
FRONTEND_NAME=$FRONTEND_NAME
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
FEEDBACK_DIR=$FEEDBACK_DIR
EOF

# El código HTTP se lee del propio texto impreso por `-w`, no del estado de
# salida de curl: en este entorno, `curl -f` a veces reporta fallo (p. ej.
# por un reset de conexión posterior a la respuesta) incluso habiendo
# recibido igual un 200 completo — comprobado empíricamente al construir
# este script. Comprobar el código impreso evita ese falso negativo.
http_code() {
  curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || true
}

echo "Esperando a que el backend responda (http://localhost:${BACKEND_PORT}/openapi.json)..."
backend_ready=""
for _ in $(seq 1 30); do
  if [ "$(http_code "http://localhost:${BACKEND_PORT}/openapi.json")" = "200" ]; then
    backend_ready=1
    break
  fi
  sleep 1
done
[ -n "$backend_ready" ] || fail "El backend no respondió a tiempo."

echo "Esperando a que el frontend responda (http://localhost:${FRONTEND_PORT}/)..."
frontend_ready=""
for _ in $(seq 1 60); do
  if [ "$(http_code "http://localhost:${FRONTEND_PORT}/")" = "200" ]; then
    frontend_ready=1
    break
  fi
  sleep 1
done
[ -n "$frontend_ready" ] || fail "El frontend no respondió a tiempo."

echo "Sesión '$SESSION_ID' lista:"
echo "  backend  -> http://localhost:${BACKEND_PORT} (contenedor $BACKEND_NAME)"
echo "  frontend -> http://localhost:${FRONTEND_PORT}/#reproduccion-historica (contenedor $FRONTEND_NAME)"
echo "  feedback (nuevo, exclusivo de esta sesión): $FEEDBACK_DIR"
echo "Detenerla con: scripts/demo_replay_down.sh $SESSION_ID"
