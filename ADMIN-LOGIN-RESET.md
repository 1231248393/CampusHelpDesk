# Administrator password recovery

Run this only on your local development machine after confirming that `backend/.env` points to the intended `campus_helpdesk` database.

```bash
cd ~/CampusHelpDesk/backend
source venv/bin/activate
python reset_admin_password.py
```

The script prompts for the administrator username and a new password, stores only a bcrypt hash, and never prints the password. Choose at least 12 characters. It updates the existing account or creates it if the username does not exist.
