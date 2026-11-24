# CampusHelpDesk — repaired project

## Port layout
- Student portal: `http://localhost:5174`
- Administrator portal: `http://localhost:5175` (separate Vite app)
- Flask API: `http://127.0.0.1:5000`

## First-time setup
1. Keep your existing database credentials in `backend/.env`. If this is a fresh install, copy `backend/.env.example` to `backend/.env` and fill in the values.
2. Install Python 3, Node.js 20.19+ and pnpm.
3. From the project root run: `./campus.sh setup`
4. Ensure MySQL is running and the `campus_helpdesk` database and original `complaints` table exist.
5. Run `./campus.sh migrate`. This applies the admin and student-account migrations. It does not drop the complaints table.
6. Run `./campus.sh create-admin` to create the first administrator account (the password must be at least 12 characters). If an administrator already exists, this script will not replace it.
7. Run `./campus.sh start`.

## Everyday commands
- `./campus.sh status` — check all three services and database health.
- `./campus.sh start` — start backend, student and admin apps.
- `./campus.sh stop` — stop services started by the runner.
- `./campus.sh restart` — restart all services.

## Repairs included
- Corrected Flask CORS origin list (a missing comma previously concatenated two origins).
- Student app remains on port 5174; standalone admin app moved to port 5175.
- Added the missing `admin-frontend/package.json`.
- Updated admin Vite host/port and the admin login footer.
- Replaced the old port assumptions in `campus.sh` and added setup/migration/admin-creation commands.
- Removed unused zero-byte admin placeholders from the student app; the real administrator UI remains in `admin-frontend`.

## Important
A successful frontend page load does not prove login works. The backend must respond on port 5000, and `/api/health` must report a connected database. The original database backup in `backups/` contains legacy complaints but not student accounts; run the migrations before testing student login. Existing student accounts are not generated automatically: register them through the student registration API or your intended account-provisioning workflow.
