"""Interactively create or reset the local CampusHelpDesk admin password."""
import os
import getpass
import bcrypt
import mysql.connector
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


def main():
    username = input("Administrator username [admin]: ").strip() or "admin"
    if len(username) > 80:
        raise SystemExit("Username must be 80 characters or fewer.")
    password = getpass.getpass("New administrator password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Password must be at least 12 characters and no more than 72 UTF-8 bytes.")

    db = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "campus_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campus_helpdesk"),
        connection_timeout=8,
    )
    cursor = None
    try:
        cursor = db.cursor()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
        cursor.execute("SELECT admin_id FROM admins WHERE username=%s", (username,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE admins SET password_hash=%s, is_active=TRUE WHERE admin_id=%s", (password_hash, existing[0]))
            action = "updated"
        else:
            cursor.execute("INSERT INTO admins (username,password_hash,is_active) VALUES (%s,%s,TRUE)", (username, password_hash))
            action = "created"
        db.commit()
        print(f"Administrator {action}: {username}")
        print("Password saved as a bcrypt hash. It was not printed.")
    except Exception:
        db.rollback()
        raise
    finally:
        if cursor: cursor.close()
        db.close()


if __name__ == "__main__":
    main()
