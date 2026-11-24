"""End-to-end smoke test for the CampusHelpDesk stack.

Run from backend/: ./venv/bin/python smoke_test.py
Creates two temporary student accounts and one complaint, then removes only
those test records. Existing student accounts and complaints are untouched.
"""
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv
import mysql.connector

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
BASE = os.getenv("CAMPUS_API_BASE", "http://127.0.0.1:5000").rstrip("/")
STAMP = f"{int(time.time())}-{os.getpid()}"
TEST_TITLE = f"CampusHelpDesk automated smoke test {STAMP}"
TEST_EMAIL_A = f"campus-test-a-{STAMP}@example.invalid"
TEST_EMAIL_B = f"campus-test-b-{STAMP}@example.invalid"
TEST_ROLL_A = f"TESTA-{STAMP}"
TEST_ROLL_B = f"TESTB-{STAMP}"
created_id = None
created_student_ids = []


def request(method, path, payload=None, token=None, expected=None, origin=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status, raw, response_headers = response.status, response.read().decode("utf-8"), response.headers
    except urllib.error.HTTPError as exc:
        status, raw, response_headers = exc.code, exc.read().decode("utf-8"), exc.headers
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw}
    if expected is not None and status != expected:
        raise AssertionError(f"{method} {path}: expected HTTP {expected}, got {status}: {data}")
    if origin:
        allowed = response_headers.get("Access-Control-Allow-Origin")
        if allowed != origin:
            raise AssertionError(f"CORS failed for {origin}: got {allowed!r}")
    return status, data


def db_connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME", "campus_helpdesk")
    )


def cleanup():
    db = cursor = None
    try:
        db = db_connect()
        cursor = db.cursor()
        if created_id is not None:
            cursor.execute("DELETE FROM complaints WHERE complaint_id = %s AND title = %s", (created_id, TEST_TITLE))
        if created_student_ids:
            placeholders = ",".join(["%s"] * len(created_student_ids))
            cursor.execute(f"DELETE FROM complaints WHERE student_id IN ({placeholders})", tuple(created_student_ids))
            cursor.execute(f"DELETE FROM students WHERE student_id IN ({placeholders})", tuple(created_student_ids))
        db.commit()
        if created_id is not None:
            print(f"CLEANUP: removed only smoke-test complaint #{created_id}")
        if created_student_ids:
            print(f"CLEANUP: removed {len(created_student_ids)} temporary student account(s)")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


def main():
    global created_id
    admin_username = input("Admin username: ").strip()
    admin_password = getpass.getpass("Admin password: ")
    student_a_token = student_b_token = admin_token = None
    try:
        _, health = request("GET", "/api/health", expected=200)
        assert health.get("database") == "connected", health
        print("PASS: API and MySQL health")

        request("GET", "/api/complaints", expected=401, origin="http://localhost:5173")
        request("POST", "/api/complaints", {"title": "anonymous"}, expected=401)
        print("PASS: student complaint APIs reject anonymous access and allow CORS")

        _, reg_a = request("POST", "/api/student/register", {
            "full_name": "Campus Test Student A", "email": TEST_EMAIL_A,
            "roll_number": TEST_ROLL_A, "password": "CampusTest!123"
        }, expected=201, origin="http://localhost:5173")
        student_a_token = reg_a["access_token"]
        created_student_ids.append(reg_a["student"]["student_id"])
        print("PASS: student registration and JWT issuance")

        request("POST", "/api/student/register", {
            "full_name": "Duplicate Test", "email": TEST_EMAIL_A,
            "roll_number": "DUPLICATE-ROLL", "password": "CampusTest!123"
        }, expected=409)
        request("POST", "/api/student/register", {
            "full_name": "Weak Password", "email": f"weak-{STAMP}@example.invalid",
            "roll_number": f"WEAK-{STAMP}", "password": "123"
        }, expected=400)
        print("PASS: duplicate account and weak-password validation")

        _, reg_b = request("POST", "/api/student/register", {
            "full_name": "Campus Test Student B", "email": TEST_EMAIL_B,
            "roll_number": TEST_ROLL_B, "password": "CampusTest!123"
        }, expected=201)
        student_b_token = reg_b["access_token"]
        created_student_ids.append(reg_b["student"]["student_id"])
        request("POST", "/api/student/login", {"roll_number": TEST_ROLL_A, "password": "wrong"}, expected=401)
        _, login_a = request("POST", "/api/student/login", {
            "roll_number": TEST_ROLL_A, "password": "CampusTest!123"
        }, expected=200)
        student_a_token = login_a["access_token"]
        request("GET", "/api/student/me", token=student_a_token, expected=200)
        print("PASS: student login and authenticated profile")

        request("GET", "/api/complaints", token=student_a_token, expected=200,
                origin="http://localhost:5173")
        _, created = request("POST", "/api/complaints", {
            "title": TEST_TITLE, "category": "Other", "location": "Automated test",
            "description": "Temporary smoke-test record; removed automatically.", "priority": "Low"
        }, token=student_a_token, expected=201, origin="http://localhost:5173")
        created_id = created["complaint_id"]
        print(f"PASS: authenticated student complaint submission (#{created_id})")

        _, b_rows = request("GET", "/api/complaints", token=student_b_token, expected=200)
        assert not any(row["complaint_id"] == created_id for row in b_rows), "Student B can see Student A's complaint"
        _, a_rows = request("GET", "/api/complaints", token=student_a_token, expected=200)
        assert any(row["complaint_id"] == created_id for row in a_rows), "Student A cannot see own complaint"
        print("PASS: students can only see their own complaints")

        request("GET", "/api/admin/complaints", expected=401)
        _, admin_login = request("POST", "/api/admin/login", {
            "username": admin_username, "password": admin_password
        }, expected=200)
        admin_token = admin_login["access_token"]
        request("GET", "/api/admin/me", token=admin_token, expected=200)
        _, admin_rows = request("GET", "/api/admin/complaints", token=admin_token,
                                expected=200, origin="http://localhost:5174")
        admin_row = next((row for row in admin_rows if row["complaint_id"] == created_id), None)
        assert admin_row and admin_row.get("student_roll_number") == TEST_ROLL_A, "Admin cannot see complaint owner"
        print("PASS: admin login, protected list and student ownership details")

        request("PATCH", f"/api/admin/complaints/{created_id}/status",
                {"status": "In Progress"}, token=admin_token, expected=200)
        request("PATCH", f"/api/admin/complaints/{created_id}/status",
                {"status": ["invalid"]}, token=admin_token, expected=400)
        _, a_rows = request("GET", "/api/complaints", token=student_a_token, expected=200)
        own_row = next((row for row in a_rows if row["complaint_id"] == created_id), None)
        assert own_row and own_row["status"] == "In Progress", "Student status did not synchronize"
        print("PASS: admin status updates synchronize to the complaint owner")

        request("POST", "/api/admin/logout", {}, token=admin_token, expected=200)
        request("GET", "/api/admin/me", token=admin_token, expected=401)
        request("POST", "/api/student/logout", {}, token=student_a_token, expected=200)
        request("GET", "/api/student/me", token=student_a_token, expected=401)
        print("PASS: admin and student logout revoke their JWTs")
        print("\nALL SMOKE TESTS PASSED")
    finally:
        admin_password = None
        cleanup()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nSMOKE TEST FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
