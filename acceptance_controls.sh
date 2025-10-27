#!/usr/bin/env bash
# Acceptance controls script for Mini GCS (SIM mode)
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$ROOT_DIR/backend"

# Start backend in SIM mode
export SIM_MODE=SIM
export TELEMETRY_RATE=5
export PORT=${PORT:-5000}

# Ensure venv
if [ ! -d "$BACKEND_DIR/venv" ]; then
  python3 -m venv "$BACKEND_DIR/venv"
fi
source "$BACKEND_DIR/venv/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"

# Launch server
python -m app.server &
SERVER_PID=$!
trap 'kill $SERVER_PID >/dev/null 2>&1 || true' EXIT

# Wait for server
sleep 2
curl -sS http://localhost:${PORT}/health | grep '"status"' >/dev/null

# Run acceptance client
python "$ROOT_DIR/scripts/acceptance_client.py"

# If we reach here, success
kill $SERVER_PID >/dev/null 2>&1 || true
trap - EXIT
exit 0
