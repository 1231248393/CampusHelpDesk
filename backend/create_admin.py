import os
import getpass
import mysql.connector
import bcrypt
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "campus_helpdesk")
    )

def main():
    print("\n================================")
    print(" CAMPUS HELPDESK ADMIN SETUP")
    print("================================\n")

    username = input("Enter admin username: ").strip()

    if not username or len(username) > 80:
        print("Invalid username.")
        return

    password = getpass.getpass("Enter admin password: ")
    confirm = getpass.getpass("Confirm admin password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if len(password) > 72:
        print("Password must not exceed 72 UTF-8 bytes.")
        return

    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) FROM admins")
        count = cursor.fetchone()[0]

        if count > 0:
            print("An administrator already exists.")
            print("No account was created.")
            return

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        cursor.execute("""
            INSERT INTO admins
            (username, password_hash, is_active)
            VALUES (%s, %s, TRUE)
        """, (username, password_hash))

        db.commit()

        print("\nADMIN ACCOUNT CREATED SUCCESSFULLY")
        print("Username:", username)
        print("Password: Hidden")
        print("Role: Administrator")

    except mysql.connector.Error:
        if db:
            db.rollback()
        print("Database error. Admin account was not created.")

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

if __name__ == "__main__":
    main()
