CampusHelpDesk - Analytics SQL alias fix

Root cause from the user's diagnostic output:
MySQL error 1064 occurs at `high_priority FROM complaints` in the totals query.
HIGH_PRIORITY is a MySQL SELECT modifier/keyword, so the unquoted alias high_priority
is ambiguous in this query. Quote the alias as `high_priority`.

Apply:
1. Extract this ZIP.
2. Open a terminal and cd to ~/CampusHelpDesk (the folder containing backend/).
3. Run:
   python3 /path/to/apply_analytics_sql_fix.py
4. Verify:
   grep -n -A5 'SELECT COUNT(\*) AS total' backend/app.py
   backend/venv/bin/python -m py_compile backend/app.py
5. Restart:
   ./stop.sh
   ./start.sh
6. Sign in to Admin Portal and press Refresh.

This patch changes exactly one SQL alias in backend/app.py. It does not run migrations,
modify database data, alter authentication, or change the frontend.
A timestamped backup of backend/app.py is created automatically.
