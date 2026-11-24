#!/usr/bin/env python3
"""Read-only CampusHelpDesk database and analytics diagnostic."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env", override=True)

EXPECTED = {
    "admins": {"admin_id", "username", "password_hash", "is_active"},
    "students": {"student_id", "roll_number", "password_hash", "is_active"},
    "complaints": {"complaint_id", "title", "category", "priority", "status", "created_at"},
    "revoked_tokens": {"id", "jti"},
    "complaint_ai_reviews": {"review_id", "complaint_id"},
    "notifications": {"notification_id", "student_id", "complaint_id"},
    "complaint_status_history": {"history_id", "complaint_id", "admin_id"},
}

def main():
    db = None
    cursor = None
    try:
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "campus_app"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "campus_helpdesk"),
            connection_timeout=10,
        )
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]
        print(f"DATABASE: {database}")
        missing = []
        for table, required_columns in EXPECTED.items():
            cursor.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                (database, table),
            )
            found = {row[0] for row in cursor.fetchall()}
            if not found:
                print(f"MISSING TABLE: {table}")
                missing.append(table)
            else:
                absent = required_columns - found
                if absent:
                    print(f"MISSING COLUMNS in {table}: {', '.join(sorted(absent))}")
                    missing.append(table)
                else:
                    print(f"OK TABLE: {table}")

        # This is the same family of queries used by /api/admin/analytics.
        try:
            cursor.execute(
                "SELECT COUNT(*) AS total, "
                "COALESCE(SUM(status='Pending'),0) AS pending, "
                "COALESCE(SUM(status IN ('Under Review','Assigned','In Progress')),0) AS active, "
                "COALESCE(SUM(status='Resolved'),0) AS resolved, "
                "COALESCE(SUM(priority='High'),0) AS high_priority "
                "FROM complaints"
            )
            print("ANALYTICS TOTALS QUERY: OK", cursor.fetchone())
            cursor.execute(
                "SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) "
                "FROM complaints "
                "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) "
                "GROUP BY DATE_FORMAT(created_at, '%Y-%m') ORDER BY month"
            )
            print("ANALYTICS MONTHLY QUERY: OK")
        except Error as exc:
            print(f"ANALYTICS QUERY FAILED: {exc}")
            return 1

        if missing:
            print("\nPhase 6 schema is incomplete. Run: python apply_migrations.py")
            return 2
        print("\nDATABASE CHECK: all expected tables and analytics queries are present.")
        return 0
    except Error as exc:
        print(f"DATABASE CONNECTION FAILED: {exc}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

if __name__ == "__main__":
    sys.exit(main())
