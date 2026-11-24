# CampusHelpDesk — Installation Guide

This guide covers local development on **Windows 10/11** and **Ubuntu/Linux**.

CampusHelpDesk contains three separate services:

| Service | Technology | Local URL |
|---|---|---|
| Student portal | React + Vite | http://localhost:5174 |
| Administrator portal | React + Vite | http://localhost:5175 |
| REST API | Python + Flask | http://127.0.0.1:5000 |
| Database | MySQL | `campus_helpdesk` |

> This repository contains the application source and migration files. It does not include a configured database, private environment file, student records, or database backup.

## 1. Requirements

- **Git**
- **Python 3.11 or later** (use a version supported by the Python packages installed in your environment)
- **Node.js 20.19+ or 22.12+** for the Vite 8 frontend toolchain
- **MySQL 8.x**
- **pnpm** package manager

Vite 8's documented Node.js requirement is 20.19+ or 22.12+. See the [Vite guide](https://vite.dev/guide/).

## 2. Get the source

### Windows PowerShell

```powershell
git clone https://github.com/1231248393/CampusHelpDesk.git
Set-Location CampusHelpDesk
```

### Ubuntu / Linux terminal

```bash
git clone https://github.com/1231248393/CampusHelpDesk.git
cd CampusHelpDesk
```

## 3. Install system dependencies

### Windows 10/11

1. Install Git from [git-scm.com](https://git-scm.com/download/win).
2. Install a supported Python 3 release from [python.org](https://www.python.org/downloads/windows/). Enable **Add Python to PATH** in the installer.
3. Install Node.js from [nodejs.org](https://nodejs.org/en/download/). Choose Node.js 20.19+ or 22.12+.
4. Install MySQL Server 8.x using the [MySQL Installer](https://dev.mysql.com/downloads/installer/).
5. Open PowerShell and install pnpm:

   ```powershell
   npm install --global pnpm
   ```

6. Verify tools:

   ```powershell
   git --version
   py --version
   node --version
   npm --version
   pnpm --version
   ```

### Ubuntu / Debian-based Linux

Update package indexes and install common tools:

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv python3-pip mysql-server
```

Install a supported Node.js release using the instructions at [Node.js Downloads](https://nodejs.org/en/download/package-manager/), then install pnpm:

```bash
npm install --global pnpm
```

Verify:

```bash
git --version
python3 --version
node --version
npm --version
pnpm --version
```

## 4. Configure MySQL

Start the MySQL service.

### Ubuntu / Linux

```bash
sudo systemctl enable --now mysql
sudo systemctl status mysql
```

### Windows

Start the MySQL80 service from **Services** or from the MySQL Installer. The service name can differ if a custom instance name was chosen.

Create the application database and a dedicated database user. Open the MySQL client as an administrator and run the following SQL after replacing the example password with a strong, unique password:

```sql
CREATE DATABASE campus_helpdesk
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'campus_app'@'localhost'
  IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';

GRANT ALL PRIVILEGES ON campus_helpdesk.*
  TO 'campus_app'@'localhost';

FLUSH PRIVILEGES;
```

Do not reuse the example password. Never commit database credentials.

### Important schema note for a fresh database

The repository currently contains migrations `001_admin_auth.sql` through `004_phase7_foundation.sql`. These migrations extend the existing CampusHelpDesk schema; they are **not a complete initial schema installer for an empty database**. The original core `complaints` table/base-schema SQL is not included in this repository.

- **Existing installation:** Back up your database, then review `DATABASE_UPGRADE.md` and apply migrations as described there.
- **Fresh installation:** Do not run the upgrade migrations against an empty database and assume they create the entire application schema. Obtain and review the project's approved base-schema SQL first, create the core schema, and only then apply the numbered migrations.

Do not drop or truncate an existing database to resolve migration errors.

## 5. Configure the Flask backend

Create the private environment file from the example.

### Windows PowerShell

```powershell
Copy-Item backend/.env.example backend/.env
notepad backend/.env
```

### Ubuntu / Linux

```bash
cp backend/.env.example backend/.env
chmod 600 backend/.env
nano backend/.env
```

Set values for your local MySQL installation:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=campus_app
DB_PASSWORD=YOUR_STRONG_DATABASE_PASSWORD
DB_NAME=campus_helpdesk
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
```

Generate a random JWT secret on Linux:

```bash
openssl rand -hex 32
```

On Windows PowerShell, generate one with Python:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `JWT_SECRET_KEY`. Keep `backend/.env` private. The backend loads this file when `backend/app.py` starts.

## 6. Set up the Python environment

### Windows PowerShell

```powershell
Set-Location backend
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use the current PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

After installation, keep the virtual environment activated while running backend commands.

### Ubuntu / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Apply database migrations and check the database

Only do this after the correct base schema exists and the database credentials in `backend/.env` have been checked. For an existing project database, make a verified backup first.

### Windows PowerShell (from the repository root)

```powershell
Set-Location backend
.\venv\Scripts\python.exe apply_migrations.py
.\venv\Scripts\python.exe check_database.py
```

### Ubuntu / Linux (from the repository root)

```bash
cd backend
source venv/bin/activate
python apply_migrations.py
python check_database.py
deactivate
cd ..
```

Read `DATABASE_UPGRADE.md` and the SQL files under `backend/migrations/` before applying changes to an existing database. If a migration fails, stop and inspect the error; do not delete application tables or records.

## 8. Install frontend dependencies

Run the commands from the repository root.

### Windows PowerShell

```powershell
Set-Location frontend
pnpm install
Set-Location ../admin-frontend
pnpm install
Set-Location ..
```

### Ubuntu / Linux

```bash
cd frontend
pnpm install
cd ../admin-frontend
pnpm install
cd ..
```

Optional production-build checks:

```bash
cd frontend
pnpm run build
cd ../admin-frontend
pnpm run build
cd ..
```

## 9. Start the application

The root `start.sh` is a Bash script intended for Linux environments. It checks the backend health endpoint and starts the two Vite frontends on their designated ports. It is not a PowerShell script.

### Ubuntu / Linux — recommended startup

From the repository root:

```bash
chmod +x start.sh stop.sh
./start.sh
```

Open:

- Student portal: http://localhost:5174
- Admin portal: http://localhost:5175
- Backend health: http://127.0.0.1:5000/api/health

Stop the services with:

```bash
./stop.sh
```

### Windows 10/11 — run each service in a separate PowerShell window

**Window 1 — Flask backend**

```powershell
Set-Location path\to\CampusHelpDesk\backend
.\venv\Scripts\Activate.ps1
python app.py
```

**Window 2 — Student portal**

```powershell
Set-Location path\to\CampusHelpDesk\frontend
pnpm dev -- --host 127.0.0.1 --port 5174 --strictPort
```

**Window 3 — Administrator portal**

```powershell
Set-Location path\to\CampusHelpDesk\admin-frontend
pnpm dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Replace `path\to\CampusHelpDesk` with the folder where you cloned the repository. Keep all three windows open while using the application.

## 10. Health checks and troubleshooting

Check the backend:

```bash
curl -i http://127.0.0.1:5000/api/health
```

Check that the frontend development servers answer:

- http://localhost:5174
- http://localhost:5175

Common problems:

| Symptom | Check |
|---|---|
| Backend exits on startup | Confirm `backend/.env` exists and `JWT_SECRET_KEY` is set. |
| MySQL connection failure | Confirm MySQL is running and DB host, port, user, password and database name are correct. |
| Migration reports missing table | Verify the approved base schema is installed before upgrade migrations. |
| Port 5000, 5174 or 5175 is busy | Stop the duplicate process or configure a free port and matching frontend API/CORS settings. |
| Vite reports unsupported Node.js | Install Node.js 20.19+ or 22.12+. |
| Frontend dependencies missing | Run `pnpm install` in both `frontend` and `admin-frontend`. |

## 11. Security checklist

- Never commit `backend/.env`, real database passwords, JWT secrets, local database dumps, student records, runtime logs, or private uploads.
- Use a dedicated MySQL application account rather than the MySQL root account.
- Use unique, strong secrets for every installation.
- Do not use shared demo passwords for real student accounts.
- Restrict database network access and review Flask CORS settings before exposing the application beyond localhost.
- Use HTTPS and a production-grade deployment configuration before internet-facing deployment.
- Keep a verified database backup before upgrades.

## 12. Project documentation

- [Project README](../README.md)
- [Database upgrade notes](../DATABASE_UPGRADE.md)
- [Phase 7 implementation status](../PHASE7-IMPLEMENTATION-STATUS.md)
- [Security policy](../SECURITY.md)

## 13. Official dependency documentation

- [Python downloads](https://www.python.org/downloads/)
- [Node.js downloads](https://nodejs.org/en/download/)
- [Vite guide and Node.js requirements](https://vite.dev/guide/)
- [pnpm installation](https://pnpm.io/installation)
- [MySQL installation documentation](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/)
- [Git installation](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
