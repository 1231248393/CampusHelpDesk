#!/usr/bin/env bash
set -Eeuo pipefail
PATCH_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$HOME/CampusHelpDesk}"

if [[ ! -d "$TARGET" || ! -f "$TARGET/backend/app.py" || ! -f "$TARGET/frontend/src/App.jsx" || ! -f "$TARGET/admin-frontend/src/components/AdminDashboard.jsx" ]]; then
  echo "ERROR: Target does not look like a CampusHelpDesk project: $TARGET" >&2
  echo "Usage: $0 /path/to/CampusHelpDesk" >&2
  exit 2
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$TARGET/backups/phase7-safe-patch-$STAMP"
mkdir -p "$BACKUP"
FILES=(
  backend/app.py
  backend/migrations/004_phase7_foundation.sql
  frontend/src/App.jsx
  frontend/src/App.css
  admin-frontend/src/components/AdminDashboard.jsx
  admin-frontend/src/styles.css
)

for rel in "${FILES[@]}"; do
  if [[ -f "$TARGET/$rel" ]]; then
    mkdir -p "$BACKUP/$(dirname "$rel")"
    cp -a "$TARGET/$rel" "$BACKUP/$rel"
  fi
done

for rel in "${FILES[@]}"; do
  mkdir -p "$TARGET/$(dirname "$rel")"
  cp -a "$PATCH_DIR/$rel" "$TARGET/$rel"
done

printf '\nPhase 7 safe patch copied.\nBackup: %s\n' "$BACKUP"
printf 'No database migration was run. Back up MySQL, then apply migration 004 only if it is not already installed.\n'
