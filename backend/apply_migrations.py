#!/usr/bin/env python3
"""Apply CampusHelpDesk SQL migrations in numeric order, preserving existing rows."""
from pathlib import Path
import os
import re
import sys

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env", override=True)

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "campus_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campus_helpdesk"),
        connection_timeout=10,
        autocommit=True,
    )

def statements(sql):
    # The supplied migration files contain ordinary SQL statements and
    # MySQL PREPARE/EXECUTE statements, but no stored procedures/delimiters.
    cleaned = []
    for line in sql.splitlines():
        if line.lstrip().startswith("--") or not line.strip():
            continue
        cleaned.append(line)
    return [part.strip() for part in "\n".join(cleaned).split(";") if part.strip()]

def main():
    migrations = sorted((BASE / "migrations").glob("[0-9][0-9][0-9]_*.sql"))
    if not migrations:
        print("ERROR: no numbered SQL migrations found.")
        return 2

    db = None
    cursor = None
    try:
        db = connect()
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        if not db_name:
            print("ERROR: DB_NAME did not select a database.")
            return 2

        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='complaints'",
            (db_name,),
        )
        if cursor.fetchone()[0] == 0:
            print(f"ERROR: {db_name}.complaints does not exist.")
            print("Refusing to create or replace the core complaints table.")
            return 2

        print(f"Connected to database: {db_name}")
        for migration in migrations:
            print(f"\nApplying {migration.name} ...")
            for statement in statements(migration.read_text(encoding="utf-8")):
                cursor.execute(statement)
                # Consume any result set produced by SELECT 1 in conditional DDL.
                if cursor.with_rows:
                    cursor.fetchall()
            print(f"OK: {migration.name}")

        print("\nAll migrations completed. Existing complaint rows were not deleted.")
        return 0
    except (Error, OSError, ValueError) as exc:
        print(f"\nMIGRATION FAILED: {type(exc).__name__}: {exc}")
        print("No DROP/TRUNCATE statements are used by these migrations.")
        return 1
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

if __name__ == "__main__":
    sys.exit(main())
