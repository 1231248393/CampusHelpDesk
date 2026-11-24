# CampusHelpDesk account setup

## Separate account types
- Admin accounts are created only by `python create_admin.py` and sign in at the admin portal.
- Student accounts can be created by an administrator in **Student account management**, imported from CSV, or self-registered from the student portal.
- Student sign-in always uses the student's own college roll number and password.
- Admin and student JWTs use separate role claims and protected API routes.

## Database setup (run once)
1. Copy `backend/.env.example` to `backend/.env` and set the MySQL password and a long random JWT secret.
2. Ensure MySQL is running and the database and DB user exist. From a privileged MySQL session:

   ```sql
   CREATE DATABASE IF NOT EXISTS campus_helpdesk;
   CREATE USER IF NOT EXISTS 'campus_app'@'localhost' IDENTIFIED BY 'CHOOSE_A_STRONG_DB_PASSWORD';
   ALTER USER 'campus_app'@'localhost' IDENTIFIED BY 'CHOOSE_A_STRONG_DB_PASSWORD';
   GRANT ALL PRIVILEGES ON campus_helpdesk.* TO 'campus_app'@'localhost';
   FLUSH PRIVILEGES;
   ```

   Use the exact same DB password in `backend/.env` as in `IDENTIFIED BY`.
3. Run the migrations in order from `backend/`:

   ```bash
   mysql -u campus_app -p campus_helpdesk < migrations/001_admin_auth.sql
   mysql -u campus_app -p campus_helpdesk < migrations/002_student_accounts.sql
   ```

4. Create the first administrator:

   ```bash
   python create_admin.py
   ```

   This utility refuses to create a second admin if one already exists.
5. Install backend dependencies and start Flask:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```

6. In two other terminals, start the Vite apps using their existing package scripts:
   - `frontend`: `npm install && npm run dev -- --host 0.0.0.0 --port 5174`
   - `admin-frontend`: `npm install && npm run dev -- --host 0.0.0.0 --port 5175`

## Student CSV format
Save as UTF-8 CSV with this exact header:

```csv
full_name,email,roll_number,password
A Student,a.student@example.edu,2514516,UseAUniqueStrongPassword
B Student,b.student@example.edu,2514517,UseAnotherStrongPassword
```

Passwords are hashed before storage. Do not send CSV files containing passwords over public or untrusted channels.

## Health checks
- API: `http://127.0.0.1:5000/api/health` should report `database: connected`.
- Student portal: `http://localhost:5174`
- Admin portal: `http://localhost:5175`

If the browser shows **Failed to fetch**, open the health-check URL first. If it reports the database disconnected, compare `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, and `DB_PORT` in `backend/.env` with the MySQL account. If health is healthy, inspect the browser Network tab and Flask terminal for CORS or route errors.
