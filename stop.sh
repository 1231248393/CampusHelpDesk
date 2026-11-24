#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$PROJECT/.campus-run"
for name in admin student backend; do
  pid_file="$RUN_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "Stopped $name (PID $pid)"
    fi
    rm -f "$pid_file"
  fi
done
echo "CampusHelpDesk stop signal sent. Check ports 5000, 5174 and 5175 if a process remains."
