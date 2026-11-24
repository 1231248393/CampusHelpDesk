# CampusHelpDesk Phase 6 analytics recovery

The uploaded project contains `backend/migrations/003_phase6_upgrade.sql` and the Phase 6 backend routes, but it does **not** contain the migration runner or the read-only database checker referenced by `DATABASE_UPGRADE.md`.

This patch adds those two missing scripts. It does not replace `app.py`, alter frontend code, reset accounts, or drop complaint data.

## Apply safely

1. Extract/merge this patch into the existing `~/CampusHelpDesk` folder.
2. In Terminal:

```bash
cd ~/CampusHelpDesk
./stop.sh

cd backend
source venv/bin/activate
python apply_migrations.py
python check_database.py
```

3. If both commands complete successfully, restart:

```bash
cd ~/CampusHelpDesk
./start.sh
```

4. Open the admin portal and refresh the dashboard.

The migration runner applies numbered SQL migrations 001, 002, and 003 in order. It first checks that the existing `complaints` table is present and refuses to proceed if it is absent. It uses the existing `backend/.env` settings. It does not run `DROP`, `TRUNCATE`, or recreate the database.

## If analytics still says "Unable to load analytics"

Run:

```bash
cd ~/CampusHelpDesk
tail -n 100 .campus-run/backend.log
```

The backend log contains the real MySQL error. Share the error lines only; redact passwords, tokens, and secret values. The dashboard's generic message alone cannot identify a specific SQL failure.
