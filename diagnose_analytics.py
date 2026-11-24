#!/usr/bin/env python3
"""Read-only CampusHelpDesk analytics SQL diagnostic."""
import os
import sys
from pathlib import Path

try:
    import mysql.connector
    from dotenv import load_dotenv
except Exception as exc:
    print("DEPENDENCY ERROR:", exc)
    print("Run with backend/venv/bin/python diagnose_analytics.py")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
load_dotenv(BACKEND / ".env", override=True)

cfg = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "campus_app"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "campus_helpdesk"),
    "connection_timeout": 8,
}
print("CampusHelpDesk analytics diagnostic (READ ONLY)")
print("Database target:", cfg["database"], "@", cfg["host"], "port", cfg["port"])
print("Password: [not displayed]")

try:
    db = mysql.connector.connect(**cfg)
except Exception as exc:
    print("\nDATABASE CONNECTION: FAIL")
    print(type(exc).__name__ + ":", exc)
    sys.exit(1)

cur = db.cursor(dictionary=True)
failed = False

def check(label, sql):
    global failed
    print(f"\n[{label}]")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        print("PASS -", len(rows), "row(s)")
        for row in rows[:12]:
            print(" ", row)
    except Exception as exc:
        failed = True
        print("FAIL -", type(exc).__name__ + ":", exc)

try:
    check("complaints table columns", "SHOW COLUMNS FROM complaints")
    check("analytics totals query",
          "SELECT COUNT(*) AS total, SUM(status='Pending') AS pending, "
          "SUM(status IN ('Under Review','Assigned','In Progress')) AS active, "
          "SUM(status='Resolved') AS resolved, SUM(priority='High') AS high_priority "
          "FROM complaints")
    check("category aggregation",
          "SELECT category AS label, COUNT(*) AS count FROM complaints "
          "GROUP BY category ORDER BY count DESC")
    check("status aggregation",
          "SELECT status AS label, COUNT(*) AS count FROM complaints "
          "GROUP BY status ORDER BY count DESC")
    check("priority aggregation",
          "SELECT priority AS label, COUNT(*) AS count FROM complaints "
          "GROUP BY priority ORDER BY FIELD(priority,'High','Medium','Low')")
    check("monthly aggregation",
          "SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS count "
          "FROM complaints WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) "
          "GROUP BY DATE_FORMAT(created_at, '%Y-%m') ORDER BY month")
    print("\n[Phase 6 auxiliary tables]")
    cur.execute("SHOW TABLES")
    tables = {next(iter(row.values())) for row in cur.fetchall()}
    for table in ("complaint_ai_reviews", "notifications", "complaint_status_history"):
        print(("PRESENT" if table in tables else "MISSING"), table,
              "(not required by /api/admin/analytics itself)")
finally:
    cur.close()
    db.close()

print("\nRESULT:", "ONE OR MORE ANALYTICS SQL CHECKS FAILED" if failed else "ALL ANALYTICS SQL QUERIES PASSED")
sys.exit(1 if failed else 0)
