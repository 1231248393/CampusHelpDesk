#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT"

if [ ! -f backend/.env ]; then
  echo "ERROR: backend/.env is missing. Copy your existing local .env into backend/ first." >&2
  exit 1
fi

if [ ! -x backend/venv/bin/python ]; then
  echo "Creating backend virtual environment..."
  python3 -m venv backend/venv
fi
source backend/venv/bin/activate
python -m pip install -r backend/requirements.txt

# A SQL dump is created before any migration is attempted.
( cd backend && ./backup_database.sh )
python backend/apply_migrations.py
python backend/check_database.py

for app in frontend admin-frontend; do
  echo "Installing and building $app..."
  if command -v pnpm >/dev/null 2>&1; then
    ( cd "$app" && pnpm install && pnpm run build )
  else
    ( cd "$app" && npm install && npm run build )
  fi
done

echo
echo "Upgrade checks completed. Start the services with: ./start.sh"
echo "Student: http://localhost:5174"
echo "Admin:   http://localhost:5175"
echo "API:     http://127.0.0.1:5000/api/health"
