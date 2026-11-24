#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .env ]; then set -a; source .env; set +a; fi
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-campus_app}"
DB_NAME="${DB_NAME:-campus_helpdesk}"
if [ -z "${DB_PASSWORD:-}" ]; then
  read -rsp "MySQL password for ${DB_USER}: " DB_PASSWORD
  echo
fi
command -v mysqldump >/dev/null || { echo "mysqldump is not installed." >&2; exit 1; }
BACKUP_DIR="../database-backups"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/${DB_NAME}_${STAMP}.sql"
MYSQL_PWD="$DB_PASSWORD" mysqldump --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" \
  --single-transaction --routines --triggers --hex-blob "$DB_NAME" > "$OUT"
unset DB_PASSWORD
chmod 600 "$OUT"
echo "Database backup saved: $OUT"
