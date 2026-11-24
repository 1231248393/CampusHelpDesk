"""Create demo student accounts using the same password hasher as app.py.

Run from backend/: python seed_students.py [count]
The generated credentials are printed once to the terminal. Store them securely.
"""

import secrets
import string
import sys

from app import bcrypt, get_db

STUDENT_NAMES = [
    "Rahul Sharma",
    "Aman Kumar",
    "Simran Kaur",
    "Arjun Singh",
    "Priya Sharma",
    "Karan Verma",
    "Neha Kumari",
    "Rohit Singh",
    "Anjali Gupta",
    "Harpreet Singh",
]


def generate_password(length=14):
    alphabet = string.ascii_letters + string.digits + "@#$!"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "@#$!" for c in password)
        ):
            return password


def generate_unique_roll(cursor):
    while True:
        roll = f"STU{secrets.randbelow(900000) + 100000}"
        email = f"{roll.lower()}@campus.test"
        cursor.execute(
            "SELECT student_id FROM students WHERE roll_number = %s OR email = %s",
            (roll, email),
        )
        if cursor.fetchone() is None:
            return roll, email


def create_students(count=10):
    if count < 1 or count > 500:
        raise ValueError("count must be between 1 and 500")

    db = None
    cursor = None
    created = []
    try:
        db = get_db()
        cursor = db.cursor()

        for index in range(count):
            name = STUDENT_NAMES[index % len(STUDENT_NAMES)]
            roll, email = generate_unique_roll(cursor)
            password = generate_password()
            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            cursor.execute(
                """INSERT INTO students
                   (full_name, email, roll_number, password_hash, is_active)
                   VALUES (%s, %s, %s, %s, TRUE)""",
                (name, email, roll, password_hash),
            )
            created.append((name, roll, password))

        db.commit()
        print("\nDEMO STUDENT ACCOUNTS CREATED")
        print("=" * 72)
        for name, roll, password in created:
            print(f"Name: {name}\nRoll number: {roll}\nPassword: {password}")
            print("-" * 72)
        print(f"Total created: {len(created)}")
        print("Use these credentials on the existing Student Portal login page.")
    except Exception:
        if db and db.is_connected():
            db.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


if __name__ == "__main__":
    amount = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    create_students(amount)
