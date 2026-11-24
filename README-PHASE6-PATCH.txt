CampusHelpDesk Phase 6 - first authentication/data-seeding fix

This patch corrects backend/seed_students.py. The uploaded version imports the
third-party `bcrypt` module but calls Flask-Bcrypt methods (`generate_password_hash`),
which causes: module 'bcrypt' has no attribute 'generate_password_hash'.

Apply:
  cd ~/CampusHelpDesk
  cp /path/to/patch/backend/seed_students.py backend/seed_students.py

Then create demo student accounts:
  cd ~/CampusHelpDesk/backend
  source venv/bin/activate
  python seed_students.py

Or create a different number (1-500):
  python seed_students.py 5

The script uses the same `bcrypt` object configured by backend/app.py, so the
password hashes are compatible with /api/student/login. It creates real rows
in the existing students table; it does not bypass authentication.

Important:
- Unknown/random roll numbers and passwords should NOT be accepted by a real
  student portal. Login must match an active database account and password hash.
- Use the generated roll number/password pairs to sign in. Registration remains
  separate and is not required for these pre-created demo accounts.
- Do not commit or share generated credentials or backend/.env.
