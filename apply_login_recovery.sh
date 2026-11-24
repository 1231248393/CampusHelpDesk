#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATCH="$ROOT/recovery"
BACKEND="$ROOT/backend"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/.recovery-backups/$STAMP"

echo "CampusHelpDesk login recovery"
[[ -d "$BACKEND" ]] || { echo "ERROR: Run this from the existing CampusHelpDesk root."; exit 1; }
[[ -f "$PATCH/app.py" ]] || { echo "ERROR: recovery/app.py not found. Extract the whole patch ZIP first."; exit 1; }
[[ -x "$BACKEND/venv/bin/python" ]] || { echo "ERROR: backend/venv/bin/python is missing."; exit 1; }
[[ -f "$BACKEND/.env" ]] || { echo "ERROR: backend/.env is missing; refusing to create credentials."; exit 1; }
[[ -f "$BACKEND/complaint_ai.py" ]] || { echo "ERROR: backend/complaint_ai.py is missing."; exit 1; }

mkdir -p "$BACKUP"
if [[ -f "$BACKEND/app.py" ]]; then
  cp -a "$BACKEND/app.py" "$BACKUP/app.py.before-recovery"
fi
if [[ -f "$ROOT/start.sh" ]]; then
  cp -a "$ROOT/start.sh" "$BACKUP/start.sh.before-recovery"
fi

cp "$PATCH/app.py" "$BACKEND/app.py"
cp "$PATCH/start.sh" "$ROOT/start.sh"
chmod +x "$ROOT/start.sh"

echo "[1/4] Python syntax check..."
"$BACKEND/venv/bin/python" -m py_compile "$BACKEND/app.py"

echo "[2/4] Required Python imports..."
(
  cd "$BACKEND"
  "$BACKEND/venv/bin/python" - <<'PY'
import flask, flask_bcrypt, flask_cors, flask_jwt_extended
import mysql.connector, dotenv
import complaint_ai
print("All required backend imports: OK")
PY
)

echo "[3/4] Checking database connection and login tables..."
(
  cd "$BACKEND"
  "$BACKEND/venv/bin/python" - <<'PY'
import os, sys
import mysql.connector
from dotenv import load_dotenv

load_dotenv(".env", override=True)
required_env = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "JWT_SECRET_KEY"]
missing = [key for key in required_env if not os.getenv(key)]
if missing:
    print("Missing required backend/.env keys:", ", ".join(missing))
    sys.exit(2)

try:
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=5,
    )
    cur = db.cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    cur.execute("SHOW TABLES")
    tables = {row[0] for row in cur.fetchall()}
    required = {"admins", "students", "revoked_tokens", "complaints"}
    missing_tables = sorted(required - tables)
    phase6 = {"notifications", "complaint_status_history", "complaint_ai_reviews"}
    missing_phase6 = sorted(phase6 - tables)
    print("MySQL connection: OK")
    print("Required login/data tables:", "OK" if not missing_tables else "MISSING " + ", ".join(missing_tables))
    print("Optional Phase 6 tables:", "OK" if not missing_phase6 else "MISSING " + ", ".join(missing_phase6))
    cur.close()
    db.close()
    if missing_tables:
        sys.exit(3)
except Exception as exc:
    print("MySQL connection failed:", type(exc).__name__, str(exc))
    sys.exit(4)
PY
)

echo "[4/4] Starting backend and both frontends..."
"$ROOT/start.sh"

echo
echo "Checking authentication endpoints (empty payload must return HTTP 400)..."
for endpoint in student admin; do
  status="$(curl -sS -o /dev/null -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d '{}' "http://127.0.0.1:5000/api/$endpoint/login" || true)"
  echo "$endpoint login route: HTTP $status"
done

echo
echo "Recovery complete. Open:"
echo "Student: http://localhost:5174"
echo "Admin:   http://localhost:5175"
echo "Backup:  $BACKUP"
