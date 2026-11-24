# CampusHelpDesk login recovery patch

This patch restores the project's existing `app.py.backup-analytics` snapshot as
`backend/app.py`. It retains the student/admin login routes and the additional
Phase 6 API routes present in that snapshot.

## Apply

1. Extract this ZIP into the existing `~/CampusHelpDesk` folder, merging folders.
   Do not extract it into a new nested `CampusHelpDesk` directory.
2. Open a terminal:

   ```bash
   cd ~/CampusHelpDesk
   chmod +x apply_login_recovery.sh
   ./apply_login_recovery.sh
   ```

The script makes timestamped copies of the existing `backend/app.py` (if any)
and `start.sh` under `.recovery-backups/` before replacing them. It does not
modify `.env`, reset passwords, alter the database, or run SQL migrations.

The startup script waits for `/api/health` to report a healthy database before
starting the two Vite frontends on ports 5174 and 5175.

## If recovery stops at the database check

The login APIs require the MySQL database and the `admins` and `students`
tables. The project's migrations are in `backend/migrations/`:
- `001_admin_auth.sql`
- `002_student_accounts.sql`
- `003_phase6_upgrade.sql` (for Phase 6 features)

Do not run migrations blindly on a different database. First back up the
database and inspect which tables already exist. The recovery script reports
missing tables without changing the database.

## Verify routes without using real credentials

After startup, these requests should return HTTP 400 (missing fields), proving
the routes are present:
- `POST http://127.0.0.1:5000/api/student/login`
- `POST http://127.0.0.1:5000/api/admin/login`

A real login additionally requires a valid active account and matching
password in MySQL.

## Security

The uploaded project archive included `backend/.env`. Treat its database
password and JWT signing secret as exposed: rotate the MySQL password and
generate a new JWT secret after recovery, then update `backend/.env`.
