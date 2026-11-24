#!/usr/bin/env python3
"""Apply the minimal MySQL analytics alias fix. No database changes are made."""
from pathlib import Path
from datetime import datetime
import shutil
import sys

root = Path.cwd()
app = root / 'backend' / 'app.py'
if not app.is_file():
    print('ERROR: Run this script from the CampusHelpDesk project root (the folder containing backend/).')
    sys.exit(1)

source = app.read_text(encoding='utf-8')
old = "SUM(priority='High') AS high_priority "
new = "SUM(priority='High') AS `high_priority` "
count = source.count(old)
if count == 0:
    if new in source:
        print('No change needed: analytics SQL alias is already quoted.')
        sys.exit(0)
    print('ERROR: Expected analytics SQL fragment was not found. No files changed.')
    sys.exit(2)
if count != 1:
    print(f'ERROR: Found {count} matching fragments; refusing ambiguous edit.')
    sys.exit(2)

backup = app.with_name(f'app.py.before_analytics_alias_fix_{datetime.now():%Y%m%d_%H%M%S}.bak')
shutil.copy2(app, backup)
app.write_text(source.replace(old, new, 1), encoding='utf-8')
print('PATCH APPLIED')
print(f'Backup: {backup}')
print('Changed only the SQL alias to `high_priority`; no schema, rows, passwords, or login code changed.')
