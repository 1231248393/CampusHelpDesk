#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$PROJECT/.campus-run"
mkdir -p "$RUN_DIR"
cd "$PROJECT"

port_busy() {
  ss -ltnH "sport = :$1" 2>/dev/null | grep -q LISTEN
}

start_backend() {
  echo "[1/3] Checking Flask API on port 5000..."
  if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
    echo "Backend already healthy."
    return 0
  fi

  if port_busy 5000; then
    echo "ERROR: Port 5000 is occupied but /api/health is failing."
    echo "Inspect: $RUN_DIR/backend.log"
    return 1
  fi

  if [[ ! -x "$PROJECT/backend/venv/bin/python" ]]; then
    echo "ERROR: Missing backend/venv/bin/python"
    return 1
  fi
  if [[ ! -f "$PROJECT/backend/app.py" ]]; then
    echo "ERROR: backend/app.py is missing."
    return 1
  fi

  (
    cd "$PROJECT/backend"
    nohup "$PROJECT/backend/venv/bin/python" app.py \
      >> "$RUN_DIR/backend.log" 2>&1 </dev/null &
    echo $! > "$RUN_DIR/backend.pid"
  )

  echo "Waiting for API and database readiness..."
  for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
      echo "Backend and database are healthy."
      return 0
    fi
    if [[ -f "$RUN_DIR/backend.pid" ]] && ! kill -0 "$(cat "$RUN_DIR/backend.pid")" 2>/dev/null; then
      echo "ERROR: Flask stopped during startup. Last log lines:"
      tail -60 "$RUN_DIR/backend.log" || true
      return 1
    fi
    sleep 1
  done

  echo "ERROR: Backend did not become healthy within 30 seconds."
  echo "Last backend log lines:"
  tail -80 "$RUN_DIR/backend.log" || true
  return 1
}

start_frontend() {
  local name="$1" dir="$2" port="$3"
  echo "[$((port == 5174 ? 2 : 3))/3] Checking $name on port $port..."

  if curl -fsS "http://127.0.0.1:$port/" >/dev/null 2>&1; then
    echo "$name already running."
    return 0
  fi
  if port_busy "$port"; then
    echo "ERROR: Port $port is occupied but $name is not responding."
    return 1
  fi
  if [[ ! -d "$PROJECT/$dir/node_modules" ]]; then
    echo "ERROR: Dependencies missing in $dir/node_modules"
    return 1
  fi

  local pm="npm"
  command -v pnpm >/dev/null 2>&1 && pm="pnpm"

  (
    cd "$PROJECT/$dir"
    nohup "$pm" run dev -- --host 127.0.0.1 --port "$port" --strictPort \
      >> "$RUN_DIR/$name.log" 2>&1 </dev/null &
    echo $! > "$RUN_DIR/$name.pid"
  )

  for _ in $(seq 1 20); do
    if curl -fsS "http://127.0.0.1:$port/" >/dev/null 2>&1; then
      echo "$name is online."
      return 0
    fi
    sleep 1
  done

  echo "ERROR: $name did not start. Last log lines:"
  tail -60 "$RUN_DIR/$name.log" || true
  return 1
}

echo "=========================================="
echo " CAMPUS HELPDESK - SAFE START"
echo "=========================================="

if [[ ! -f "$PROJECT/backend/.env" ]]; then
  echo "ERROR: backend/.env is missing."
  exit 1
fi

start_backend
start_frontend "student" "frontend" 5174
start_frontend "admin" "admin-frontend" 5175

echo
echo "All services are responding:"
echo "Student : http://localhost:5174"
echo "Admin   : http://localhost:5175"
echo "API     : http://127.0.0.1:5000/api/health"
echo "Logs    : $RUN_DIR/"
