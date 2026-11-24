# CampusHelpDesk database configuration fix

This source bundle fixes the migration credential mismatch:

- `campus.sh migrate` now reads `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` from `backend/.env`.
- It creates a temporary MySQL client option file with owner-only permissions, uses it for both migration files, and removes it afterward. It no longer prompts for the database password twice.
- Flask now honours `DB_PORT` as well.
- The ZIP intentionally excludes `backend/.env`, `node_modules`, Python virtual environments, backups, and runtime files. Your existing local `.env` and data are not included or overwritten.

## Apply

1. Back up your existing `CampusHelpDesk` folder.
2. Extract this ZIP. It contains a `CampusHelpDesk/` folder.
3. Copy the patched `campus.sh` and `backend/app.py` into your existing project, replacing those two files. You may also copy `backend/.env.example` if you need the updated example. Do not replace your real `backend/.env`.
4. Ensure `backend/.env` contains matching MySQL credentials, including `DB_PORT=3306`.
5. Run from the project directory:

   ```bash
   chmod +x campus.sh
   ./campus.sh migrate
   ./campus.sh restart
   ./campus.sh status
   ```

The migration command now uses the password stored in `backend/.env`; it does not reset or change the MySQL account password. Set/reset the MySQL account separately with an administrator account, then put that same password in `backend/.env`.
