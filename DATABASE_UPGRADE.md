# CampusHelpDesk Phase 6 integrated upgrade

This upgrade restores the two frontends and connects complaint management, student self-service, advisory AI triage, MySQL analytics, notifications and audit history.

## Before applying

1. Stop the running app with `cd ~/CampusHelpDesk && ./stop.sh` if your local project has that script. Otherwise leave the database running and stop only the Flask process before replacing backend files.
2. Keep a copy of your current project folder.
3. Back up MySQL: `cd ~/CampusHelpDesk/backend && ./backup_database.sh`.
4. Copy your real `backend/.env` into the upgraded project. The ZIP intentionally does not contain private `.env` credentials.

## Apply database migrations

The migration runner applies migrations 001, 002 and 003 in order. They use `CREATE TABLE IF NOT EXISTS`; migration 002 adds `complaints.student_id` only if absent. Existing complaint records are not dropped or recreated.

```bash
cd ~/CampusHelpDesk/backend
source venv/bin/activate
python apply_migrations.py
python check_database.py
```

If your MySQL user cannot run migrations, ask the database administrator to run the SQL files in `backend/migrations/` in numeric order. Do not drop the `campus_helpdesk` database or the `complaints` table.

## Install frontend dependencies

```bash
cd ~/CampusHelpDesk/frontend && pnpm install
cd ~/CampusHelpDesk/admin-frontend && pnpm install
```

If you use npm instead, run `npm install` in each frontend directory.

## Build and run

```bash
cd ~/CampusHelpDesk/frontend && pnpm run build
cd ~/CampusHelpDesk/admin-frontend && pnpm run build
cd ~/CampusHelpDesk && ./start.sh
```

- Student: http://localhost:5174
- Admin: http://localhost:5175
- API health: http://127.0.0.1:5000/api/health

## Features in this upgrade

- Student registration and login with roll number, private complaint list, submission, AI draft analysis and status notifications.
- Admin complaint list with text search, status and priority filters, details modal, status/priority changes and change history.
- Overview analytics are calculated from live complaint records in MySQL.
- AI triage is transparent keyword/rule-based advisory logic, not a trained ML model. It never makes final decisions or changes a saved complaint without the student's/admin's explicit action.
- `python check_database.py` provides a read-only schema and referential-integrity report.

## Security

- Keep `.env` private and never commit it.
- Use a long random `JWT_SECRET_KEY` and a non-default database password.
- Change any local development admin password before exposing the service to a network.
- Student complaint reads are scoped to the authenticated student; admin endpoints require an active admin JWT.

## Automated logic tests

```bash
cd ~/CampusHelpDesk/backend
source venv/bin/activate
python -m unittest test_complaint_ai -v
```
