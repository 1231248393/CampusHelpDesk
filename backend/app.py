import os
import re
import uuid
import hashlib
from pathlib import Path
from datetime import timedelta

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from complaint_ai import analyze_complaint, find_similar_complaints

# --------------------------------------------------
# ENVIRONMENT CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(
    dotenv_path=os.path.join(BASE_DIR, ".env"),
    override=True
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB per request

jwt_secret = os.getenv("JWT_SECRET_KEY")

if not jwt_secret:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from backend/.env"
    )

app.config["JWT_SECRET_KEY"] = jwt_secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5175",
                "http://127.0.0.1:5175",
                "http://localhost:5176",
                "http://127.0.0.1:5176",
            ]
        }
    }
)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "campus_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campus_helpdesk"),
        connection_timeout=8,
    )


# --------------------------------------------------
# JWT TOKEN REVOCATION
# --------------------------------------------------

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id FROM revoked_tokens WHERE jti = %s",
            (jwt_payload["jti"],)
        )

        revoked = cursor.fetchone() is not None

        cursor.close()
        db.close()

        return revoked

    except mysql.connector.Error:
        app.logger.exception("JWT revocation database check failed")
        return True


@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    return jsonify({
        "error": "Access token has expired. Please log in again."
    }), 401


@jwt.invalid_token_loader
def invalid_token(error):
    return jsonify({
        "error": "Invalid authentication token."
    }), 401


@jwt.unauthorized_loader
def missing_token(error):
    return jsonify({
        "error": "Authentication token is required."
    }), 401


# --------------------------------------------------
# ADMIN ACCOUNT VERIFICATION
# --------------------------------------------------

def get_current_admin():
    if get_jwt().get("role") != "admin":
        return None
    admin_id = get_jwt_identity()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT admin_id, username, is_active
            FROM admins
            WHERE admin_id = %s
            """,
            (int(admin_id),)
        )

        admin = cursor.fetchone()

        if not admin or not admin["is_active"]:
            return None

        return admin

    finally:
        cursor.close()
        db.close()


def get_current_student():
    """Return the active student attached to the current student JWT."""
    if get_jwt().get("role") != "student":
        return None
    try:
        student_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT student_id, full_name, email, roll_number, is_active
               FROM students WHERE student_id = %s""",
            (student_id,)
        )
        student = cursor.fetchone()
        return student if student and student["is_active"] else None
    finally:
        cursor.close()
        db.close()


# --------------------------------------------------
# HOME / API HEALTH
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "CampusHelpDesk API is running",
        "status": "success"
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Check both the Flask process and its configured MySQL connection."""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return jsonify({
            "status": "healthy",
            "api": "ok",
            "database": "connected"
        }), 200
    except mysql.connector.Error:
        app.logger.exception("Health check database connection failed")
        return jsonify({
            "status": "unhealthy",
            "api": "ok",
            "database": "disconnected"
        }), 503
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# --------------------------------------------------
# EXISTING STUDENT COMPLAINT API - GET
# --------------------------------------------------

@app.route("/api/complaints", methods=["GET"])
@jwt_required()
def get_complaints():
    db = None
    cursor = None
    try:
        student = get_current_student()
        if not student:
            return jsonify({"error": "Student authentication required"}), 403
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT complaint_id, title, category, location, priority, status, created_at
            FROM complaints
            WHERE student_id = %s
            ORDER BY created_at DESC, complaint_id DESC
        """, (student["student_id"],))
        data = cursor.fetchall()
        for item in data:
            if item["created_at"]:
                item["created_at"] = item["created_at"].isoformat()
        return jsonify(data), 200
    except mysql.connector.Error:
        app.logger.exception("Student complaint retrieval failed")
        return jsonify({"error": "Unable to retrieve complaints"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# --------------------------------------------------
# EXISTING STUDENT COMPLAINT API - POST
# --------------------------------------------------

@app.route("/api/complaints", methods=["POST"])
@jwt_required()
def create_complaint():
    try:
        student = get_current_student()
    except mysql.connector.Error:
        app.logger.exception("Student account lookup failed during complaint submission")
        return jsonify({"error": "Unable to verify student account"}), 500
    if not student:
        return jsonify({"error": "Student authentication required"}), 403

    data = request.get_json(silent=True) or {}
    required = ("title", "category", "location", "description")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(field), str) or not data[field].strip()
        for field in required
    ):
        return jsonify({
            "error": "Title, category, location and description are required text fields"
        }), 400

    max_lengths = {"title": 200, "category": 100, "location": 200}
    if any(len(data[field].strip()) > limit for field, limit in max_lengths.items()):
        return jsonify({"error": "One or more fields exceed the maximum allowed length"}), 400
    if len(data["description"].strip()) > 5000:
        return jsonify({"error": "Description must be 5000 characters or fewer"}), 400

    priority = data.get("priority", "Medium")
    if not isinstance(priority, str) or priority not in {"Low", "Medium", "High"}:
        return jsonify({"error": "Priority must be Low, Medium or High"}), 400

    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO complaints
            (student_id, title, category, location, description, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
        """, (
            student["student_id"], data["title"].strip(), data["category"].strip(),
            data["location"].strip(), data["description"].strip(), priority
        ))
        complaint_id = cursor.lastrowid
        # Persist advisory triage metadata for the admin's later review.
        ai_review = analyze_complaint(data["title"].strip(), data["description"].strip(), data["category"].strip())
        cursor.execute(
            "INSERT INTO complaint_ai_reviews "
            "(complaint_id, suggested_category, suggested_department, suggested_priority, sentiment, model_type, confidence) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (complaint_id, ai_review.get("category"), ai_review.get("suggested_department"),
             ai_review.get("priority"), ai_review.get("sentiment"), ai_review.get("model_type"),
             ai_review.get("confidence"))
        )
        db.commit()
        return jsonify({
            "message": "Complaint submitted successfully",
            "complaint_id": complaint_id
        }), 201
    except mysql.connector.Error:
        if db:
            db.rollback()
        app.logger.exception("Complaint submission failed")
        return jsonify({"error": "Unable to submit complaint"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()



# --------------------------------------------------
# PHASE 6.2 - AI-ASSISTED COMPLAINT ANALYSIS
# --------------------------------------------------

@app.route("/api/complaints/analyze", methods=["POST"])
@jwt_required()
def analyze_student_complaint():
    """Analyze a draft complaint without saving it or changing its priority."""
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Analysis data must be a JSON object"}), 400
    title = data.get("title", "")
    description = data.get("description", "")
    selected_category = data.get("category")
    if not isinstance(title, str) or not isinstance(description, str):
        return jsonify({"error": "Title and description must be text"}), 400
    title, description = title.strip(), description.strip()
    if not title or not description:
        return jsonify({"error": "Enter a title and description before AI analysis"}), 400
    if len(title) > 200 or len(description) > 5000:
        return jsonify({"error": "Title or description exceeds the allowed length"}), 400

    result = analyze_complaint(title, description, selected_category)
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT complaint_id, title, description, status FROM complaints "
            "WHERE student_id = %s ORDER BY created_at DESC LIMIT 100",
            (student["student_id"],),
        )
        result["possible_duplicates"] = find_similar_complaints(
            title, description, cursor.fetchall()
        )
        return jsonify({"analysis": result}), 200
    except mysql.connector.Error:
        app.logger.exception("AI complaint analysis duplicate lookup failed")
        return jsonify({"error": "Unable to complete complaint analysis"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

# --------------------------------------------------
# STUDENT REGISTRATION / LOGIN / SESSION
# --------------------------------------------------

@app.route("/api/student/register", methods=["POST"])
def student_register():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Registration data must be a JSON object"}), 400
    full_name = data.get("full_name", "")
    email = data.get("email", "")
    roll_number = data.get("roll_number", "")
    password = data.get("password", "")

    if not all(isinstance(value, str) for value in (full_name, email, roll_number, password)):
        return jsonify({"error": "All registration fields must be text"}), 400
    full_name, email, roll_number = full_name.strip(), email.strip().lower(), roll_number.strip().upper()
    if not full_name or len(full_name) > 120:
        return jsonify({"error": "Enter your name (maximum 120 characters)"}), 400
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 190:
        return jsonify({"error": "Enter a valid email address"}), 400
    if not roll_number or len(roll_number) > 50:
        return jsonify({"error": "Enter your college roll number"}), 400
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        return jsonify({"error": "Password must contain at least 8 characters and no more than 72 UTF-8 bytes"}), 400

    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""INSERT INTO students
            (full_name, email, roll_number, password_hash)
            VALUES (%s, %s, %s, %s)""",
            (full_name, email, roll_number, bcrypt.generate_password_hash(password).decode("utf-8")))
        student_id = cursor.lastrowid
        db.commit()
        token = create_access_token(
            identity=str(student_id),
            additional_claims={"role": "student", "email": email}
        )
        return jsonify({
            "message": "Student account created successfully",
            "access_token": token,
            "student": {"student_id": student_id, "full_name": full_name,
                        "email": email, "roll_number": roll_number, "role": "student"}
        }), 201
    except mysql.connector.Error as exc:
        if db:
            db.rollback()
        if getattr(exc, "errno", None) == 1062:
            return jsonify({"error": "This email address or roll number is already registered"}), 409
        app.logger.exception("Student registration failed")
        return jsonify({"error": "Registration service temporarily unavailable"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route("/api/student/login", methods=["POST"])
def student_login():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Login data must be a JSON object"}), 400
    roll_number = data.get("roll_number", "")
    password = data.get("password", "")
    if (not isinstance(roll_number, str) or not isinstance(password, str) or
            not roll_number.strip() or not password or len(password.encode("utf-8")) > 72):
        return jsonify({"error": "College roll number and password are required"}), 400

    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""SELECT student_id, full_name, email, roll_number,
                          password_hash, is_active FROM students WHERE roll_number = %s""",
                       (roll_number.strip().upper(),))
        student = cursor.fetchone()
        if (not student or not student["is_active"] or
                not bcrypt.check_password_hash(student["password_hash"], password)):
            return jsonify({"error": "Invalid college roll number or password"}), 401
        cursor.execute("UPDATE students SET last_login = CURRENT_TIMESTAMP WHERE student_id = %s",
                       (student["student_id"],))
        db.commit()
        token = create_access_token(
            identity=str(student["student_id"]),
            additional_claims={"role": "student", "email": student["email"]}
        )
        return jsonify({
            "message": "Student login successful", "access_token": token,
            "student": {"student_id": student["student_id"], "full_name": student["full_name"],
                        "email": student["email"], "roll_number": student["roll_number"], "role": "student"}
        }), 200
    except mysql.connector.Error:
        if db:
            db.rollback()
        app.logger.exception("Student login failed")
        return jsonify({"error": "Login service temporarily unavailable"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route("/api/student/me", methods=["GET"])
@jwt_required()
def student_profile():
    try:
        student = get_current_student()
        if not student:
            return jsonify({"error": "Student account is inactive or unavailable"}), 403
        return jsonify({"student": {**student, "role": "student"}}), 200
    except mysql.connector.Error:
        app.logger.exception("Student profile verification failed")
        return jsonify({"error": "Unable to verify student account"}), 500


@app.route("/api/student/logout", methods=["POST"])
@jwt_required()
def student_logout():
    if get_jwt().get("role") != "student":
        return jsonify({"error": "Student access required"}), 403
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT IGNORE INTO revoked_tokens (jti) VALUES (%s)", (get_jwt()["jti"],))
        db.commit()
        return jsonify({"message": "Student logged out successfully"}), 200
    except mysql.connector.Error:
        if db:
            db.rollback()
        app.logger.exception("Student logout failed")
        return jsonify({"error": "Unable to complete logout"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if (
        not username
        or not isinstance(password, str)
        or not password
    ):
        return jsonify({
            "error": "Username and password are required"
        }), 400

    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT admin_id, username, password_hash, is_active
            FROM admins
            WHERE username = %s
        """, (username,))

        admin = cursor.fetchone()

        if (
            not admin
            or not admin["is_active"]
            or not bcrypt.check_password_hash(
                admin["password_hash"],
                password
            )
        ):
            return jsonify({
                "error": "Invalid username or password"
            }), 401

        access_token = create_access_token(
            identity=str(admin["admin_id"]),
            additional_claims={
                "username": admin["username"],
                "role": "admin"
            }
        )

        cursor.execute("""
            UPDATE admins
            SET last_login = CURRENT_TIMESTAMP
            WHERE admin_id = %s
        """, (admin["admin_id"],))

        db.commit()

        return jsonify({
            "message": "Admin login successful",
            "access_token": access_token,
            "admin": {
                "admin_id": admin["admin_id"],
                "username": admin["username"],
                "role": "admin"
            }
        }), 200

    except mysql.connector.Error:
        if db:
            db.rollback()

        app.logger.exception("Admin login database error")

        return jsonify({
            "error": "Login service temporarily unavailable"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# --------------------------------------------------
# PROTECTED ADMIN PROFILE
# --------------------------------------------------

@app.route("/api/admin/me", methods=["GET"])
@jwt_required()
def admin_profile():
    try:
        admin = get_current_admin()

        if not admin:
            return jsonify({
                "error": "Admin account is inactive or unavailable"
            }), 403

        return jsonify({
            "message": "Admin authenticated successfully",
            "admin": {
                "admin_id": admin["admin_id"],
                "username": admin["username"],
                "role": "admin"
            }
        }), 200

    except (mysql.connector.Error, ValueError, TypeError):
        app.logger.exception("Admin profile verification failed")
        return jsonify({
            "error": "Unable to verify administrator"
        }), 500


# --------------------------------------------------
# ADMIN LOGOUT - REVOKE CURRENT TOKEN
# --------------------------------------------------

@app.route("/api/admin/logout", methods=["POST"])
@jwt_required()
def admin_logout():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Administrator access required"}), 403
    db = None
    cursor = None

    try:
        token_id = get_jwt()["jti"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT IGNORE INTO revoked_tokens (jti)
            VALUES (%s)
        """, (token_id,))

        db.commit()

        return jsonify({
            "message": "Admin logged out successfully"
        }), 200

    except mysql.connector.Error:
        if db:
            db.rollback()

        app.logger.exception("Admin logout failed")

        return jsonify({
            "error": "Unable to complete logout"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# --------------------------------------------------
# ADMIN COMPLAINT MANAGEMENT
# --------------------------------------------------

ADMIN_STATUSES = {
    "Pending", "Under Review", "Assigned",
    "In Progress", "Resolved", "Rejected"
}


def require_active_admin():
    """Return an active admin row or None for a valid JWT without an active account."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return None
    return get_current_admin()


@app.route("/api/admin/complaints", methods=["GET"])
@jwt_required()
def admin_get_complaints():
    db = None
    cursor = None
    try:
        admin = require_active_admin()
        if not admin:
            return jsonify({"error": "Administrator access required"}), 403

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.complaint_id, c.title, c.category, c.location, c.description,
                   c.priority, c.status, c.created_at,
                   s.full_name AS student_name, s.email AS student_email,
                   s.roll_number AS student_roll_number,
                   ai.suggested_department AS ai_suggested_department,
                   ai.suggested_category AS ai_suggested_category,
                   ai.suggested_priority AS ai_suggested_priority,
                   ai.confidence AS ai_confidence
            FROM complaints c
            LEFT JOIN students s ON s.student_id = c.student_id
            LEFT JOIN complaint_ai_reviews ai ON ai.review_id = (
                SELECT MAX(ai2.review_id) FROM complaint_ai_reviews ai2
                WHERE ai2.complaint_id = c.complaint_id
            )
            ORDER BY c.created_at DESC, c.complaint_id DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        return jsonify(rows), 200
    except mysql.connector.Error:
        app.logger.exception("Admin complaint retrieval failed")
        return jsonify({"error": "Unable to retrieve complaints"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route("/api/admin/complaints/<int:complaint_id>/status", methods=["PATCH"])
@jwt_required()
def admin_update_complaint_status(complaint_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not isinstance(status, str) or status not in ADMIN_STATUSES:
        return jsonify({
            "error": "Status must be one of: " + ", ".join(sorted(ADMIN_STATUSES))
        }), 400

    db = None
    cursor = None
    try:
        admin = require_active_admin()
        if not admin:
            return jsonify({"error": "Administrator access required"}), 403

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT status FROM complaints WHERE complaint_id = %s FOR UPDATE", (complaint_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"error": "Complaint not found"}), 404
        old_status = existing["status"]
        cursor.execute(
            "UPDATE complaints SET status = %s WHERE complaint_id = %s",
            (status, complaint_id)
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT complaint_id FROM complaints WHERE complaint_id = %s",
                (complaint_id,)
            )
            if not cursor.fetchone():
                return jsonify({"error": "Complaint not found"}), 404
        # Notify only the student who owns this complaint. Legacy unowned records are skipped.
        notify_cursor = db.cursor(dictionary=True)
        notify_cursor.execute("SELECT student_id, title FROM complaints WHERE complaint_id=%s", (complaint_id,))
        owner = notify_cursor.fetchone()
        notify_cursor.close()
        if owner and owner.get("student_id"):
            notify_cursor = db.cursor()
            notify_cursor.execute(
                "INSERT INTO notifications (student_id, complaint_id, title, message) VALUES (%s,%s,%s,%s)",
                (owner["student_id"], complaint_id, "Complaint status updated",
                 f'Your complaint "{owner["title"]}" is now {status}.')
            )
            notify_cursor.close()
        history_cursor = db.cursor()
        history_cursor.execute(
            "INSERT INTO complaint_status_history "
            "(complaint_id, admin_id, change_type, old_value, new_value) "
            "VALUES (%s, %s, 'status', %s, %s)",
            (complaint_id, admin["admin_id"], old_status, status)
        )
        history_cursor.close()
        db.commit()
        return jsonify({
            "message": "Complaint status updated successfully",
            "complaint_id": complaint_id,
            "status": status
        }), 200
    except mysql.connector.Error:
        if db:
            db.rollback()
        app.logger.exception("Admin complaint status update failed")
        return jsonify({"error": "Unable to update complaint status"}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route("/api/admin/complaints/<int:complaint_id>/priority", methods=["PATCH"])
@jwt_required()
def admin_update_complaint_priority(complaint_id):
    data = request.get_json(silent=True) or {}
    priority = data.get("priority")
    if priority not in {"Low", "Medium", "High"}:
        return jsonify({"error": "Priority must be Low, Medium or High"}), 400
    db = cursor = None
    try:
        admin = require_active_admin()
        if not admin:
            return jsonify({"error": "Administrator access required"}), 403
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT priority FROM complaints WHERE complaint_id=%s FOR UPDATE", (complaint_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Complaint not found"}), 404
        old_priority = row["priority"]
        cursor.execute("UPDATE complaints SET priority=%s WHERE complaint_id=%s", (priority, complaint_id))
        cursor.execute(
            "INSERT INTO complaint_status_history "
            "(complaint_id, admin_id, change_type, old_value, new_value) "
            "VALUES (%s, %s, 'priority', %s, %s)",
            (complaint_id, admin["admin_id"], old_priority, priority)
        )
        db.commit()
        return jsonify({"message": "Complaint priority updated", "complaint_id": complaint_id, "priority": priority}), 200
    except mysql.connector.Error:
        if db: db.rollback()
        app.logger.exception("Admin complaint priority update failed")
        return jsonify({"error": "Unable to update complaint priority"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/admin/complaints/<int:complaint_id>/history", methods=["GET"])
@jwt_required()
def admin_complaint_history(complaint_id):
    db = cursor = None
    try:
        admin = require_active_admin()
        if not admin:
            return jsonify({"error": "Administrator access required"}), 403
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT h.history_id, h.change_type, h.old_value, h.new_value, h.changed_at, "
            "a.username AS changed_by FROM complaint_status_history h "
            "LEFT JOIN admins a ON a.admin_id=h.admin_id "
            "WHERE h.complaint_id=%s ORDER BY h.changed_at DESC, h.history_id DESC",
            (complaint_id,)
        )
        rows = cursor.fetchall()
        for row in rows:
            if row.get("changed_at"): row["changed_at"] = row["changed_at"].isoformat()
        return jsonify(rows), 200
    except mysql.connector.Error:
        app.logger.exception("Complaint history retrieval failed")
        return jsonify({"error": "Unable to retrieve complaint history"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


# --------------------------------------------------
# PHASE 6.3-6.9 - ADMIN ANALYTICS & NOTIFICATIONS
# Requires migration 003_phase6_upgrade.sql.
# --------------------------------------------------

@app.route("/api/admin/analytics", methods=["GET"])
@jwt_required()
def admin_analytics():
    """Aggregated operational metrics; never returns student passwords/tokens."""
    admin = require_active_admin()
    if not admin:
        return jsonify({"error": "Administrator access required"}), 403
    db = cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total, SUM(status='Pending') AS pending, "
                       "SUM(status IN ('Under Review','Assigned','In Progress')) AS active, "
                       "SUM(status='Resolved') AS resolved, SUM(priority='High') AS `high_priority` "
                       "FROM complaints")
        totals = cursor.fetchone() or {}
        cursor.execute("SELECT category AS label, COUNT(*) AS count FROM complaints "
                       "GROUP BY category ORDER BY count DESC")
        categories = cursor.fetchall()
        cursor.execute("SELECT status AS label, COUNT(*) AS count FROM complaints "
                       "GROUP BY status ORDER BY count DESC")
        statuses = cursor.fetchall()
        cursor.execute("SELECT priority AS label, COUNT(*) AS count FROM complaints "
                       "GROUP BY priority ORDER BY FIELD(priority,'High','Medium','Low')")
        priorities = cursor.fetchall()
        cursor.execute("SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS count "
                       "FROM complaints WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) "
                       "GROUP BY DATE_FORMAT(created_at, '%Y-%m') ORDER BY month")
        monthly = cursor.fetchall()
        for group in (categories, statuses, priorities, monthly):
            for row in group:
                row['count'] = int(row.get('count') or 0)
        totals = {key: int(value or 0) for key, value in totals.items()}
        return jsonify({"totals": totals, "categories": categories,
                        "statuses": statuses, "priorities": priorities,
                        "monthly": monthly}), 200
    except mysql.connector.Error:
        app.logger.exception("Admin analytics query failed")
        return jsonify({"error": "Unable to load analytics"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/student/notifications", methods=["GET"])
@jwt_required()
def student_notifications():
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT notification_id, complaint_id, title, message, is_read, created_at "
                       "FROM notifications WHERE student_id=%s ORDER BY created_at DESC LIMIT 50",
                       (student['student_id'],))
        rows = cursor.fetchall()
        for row in rows:
            row['is_read'] = bool(row['is_read'])
            if row.get('created_at'): row['created_at'] = row['created_at'].isoformat()
        return jsonify(rows), 200
    except mysql.connector.Error:
        app.logger.exception("Student notifications retrieval failed")
        return jsonify({"error": "Unable to load notifications"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/student/notifications/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_student_notification_read(notification_id):
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db(); cursor = db.cursor()
        cursor.execute("UPDATE notifications SET is_read=1 WHERE notification_id=%s AND student_id=%s",
                       (notification_id, student['student_id']))
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT notification_id FROM notifications WHERE notification_id=%s AND student_id=%s",
                (notification_id, student["student_id"])
            )
            if not cursor.fetchone():
                return jsonify({"error": "Notification not found"}), 404
        db.commit()
        return jsonify({"message": "Notification marked as read"}), 200
    except mysql.connector.Error:
        if db: db.rollback()
        app.logger.exception("Notification update failed")
        return jsonify({"error": "Unable to update notification"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


# --------------------------------------------------
# PHASE 7.4 - STUDENT COMPLAINT TIMELINE / FEEDBACK / FILES
# All routes enforce ownership through the authenticated student identity.
# --------------------------------------------------

@app.route("/api/student/complaints/<int:complaint_id>/history", methods=["GET"])
@jwt_required()
def student_complaint_history(complaint_id):
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT complaint_id FROM complaints WHERE complaint_id=%s AND student_id=%s",
            (complaint_id, student["student_id"]),
        )
        if not cursor.fetchone():
            return jsonify({"error": "Complaint not found"}), 404
        cursor.execute(
            "SELECT h.history_id, h.change_type, h.old_value, h.new_value, h.changed_at, "
            "COALESCE(a.username, 'Campus administration') AS changed_by "
            "FROM complaint_status_history h LEFT JOIN admins a ON a.admin_id=h.admin_id "
            "WHERE h.complaint_id=%s ORDER BY h.changed_at ASC, h.history_id ASC",
            (complaint_id,),
        )
        rows = cursor.fetchall()
        for row in rows:
            if row.get("changed_at"):
                row["changed_at"] = row["changed_at"].isoformat()
        return jsonify(rows), 200
    except mysql.connector.Error:
        app.logger.exception("Student complaint history retrieval failed")
        return jsonify({"error": "Unable to retrieve complaint history. Verify Phase 6 migrations."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/student/complaints/<int:complaint_id>/feedback", methods=["GET", "POST"])
@jwt_required()
def student_complaint_feedback(complaint_id):
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT complaint_id, status FROM complaints WHERE complaint_id=%s AND student_id=%s",
            (complaint_id, student["student_id"]),
        )
        complaint = cursor.fetchone()
        if not complaint:
            return jsonify({"error": "Complaint not found"}), 404
        if request.method == "GET":
            cursor.execute(
                "SELECT rating, comment, created_at FROM complaint_feedback "
                "WHERE complaint_id=%s AND student_id=%s",
                (complaint_id, student["student_id"]),
            )
            row = cursor.fetchone()
            if row and row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
            return jsonify(row or {}), 200
        if complaint["status"] != "Resolved":
            return jsonify({"error": "Feedback is available after a complaint is resolved."}), 409
        data = request.get_json(silent=True) or {}
        try:
            rating = int(data.get("rating"))
        except (TypeError, ValueError):
            return jsonify({"error": "Rating must be a number from 1 to 5."}), 400
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5."}), 400
        comment = str(data.get("comment") or "").strip()
        if len(comment) > 1000:
            return jsonify({"error": "Feedback must be 1000 characters or fewer."}), 400
        cursor.execute(
            "INSERT INTO complaint_feedback (complaint_id, student_id, rating, comment) "
            "VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
            "rating=VALUES(rating), comment=VALUES(comment), created_at=CURRENT_TIMESTAMP",
            (complaint_id, student["student_id"], rating, comment or None),
        )
        db.commit()
        return jsonify({"message": "Thank you for your feedback.", "rating": rating, "comment": comment}), 200
    except mysql.connector.Error:
        if db: db.rollback()
        app.logger.exception("Student complaint feedback failed")
        return jsonify({"error": "Unable to save feedback. Apply Phase 7 migration 004 first."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


_ALLOWED_UPLOADS = {".pdf", ".png", ".jpg", ".jpeg"}
_UPLOAD_DIR = Path(BASE_DIR) / "uploads" / "complaints"


def _valid_upload_signature(extension, content):
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    return False


@app.route("/api/student/complaints/<int:complaint_id>/attachments", methods=["GET", "POST"])
@jwt_required()
def student_complaint_attachments(complaint_id):
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT complaint_id FROM complaints WHERE complaint_id=%s AND student_id=%s",
            (complaint_id, student["student_id"]),
        )
        if not cursor.fetchone():
            return jsonify({"error": "Complaint not found"}), 404
        if request.method == "GET":
            cursor.execute(
                "SELECT attachment_id, original_name, mime_type, file_size, created_at "
                "FROM complaint_attachments WHERE complaint_id=%s AND student_id=%s "
                "ORDER BY created_at DESC",
                (complaint_id, student["student_id"]),
            )
            rows = cursor.fetchall()
            for row in rows:
                if row.get("created_at"):
                    row["created_at"] = row["created_at"].isoformat()
            return jsonify(rows), 200
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "Choose a PDF, PNG or JPEG file."}), 400
        original_name = secure_filename(uploaded.filename)[:255]
        extension = Path(original_name).suffix.lower()
        if extension not in _ALLOWED_UPLOADS:
            return jsonify({"error": "Only PDF, PNG and JPEG attachments are allowed."}), 415
        content = uploaded.read(5 * 1024 * 1024 + 1)
        if not content or len(content) > 5 * 1024 * 1024:
            return jsonify({"error": "Attachment must be between 1 byte and 5 MB."}), 413
        if not _valid_upload_signature(extension, content):
            return jsonify({"error": "File content does not match its allowed file type."}), 415
        mime_type = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}[extension]
        storage_name = f"{uuid.uuid4().hex}{extension}"
        _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path = _UPLOAD_DIR / storage_name
        stored_path.write_bytes(content)
        try:
            cursor.execute(
                "INSERT INTO complaint_attachments "
                "(complaint_id, student_id, original_name, storage_name, mime_type, file_size, sha256) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (complaint_id, student["student_id"], original_name, storage_name,
                 mime_type, len(content), hashlib.sha256(content).hexdigest()),
            )
            attachment_id = cursor.lastrowid
            db.commit()
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise
        return jsonify({"message": "Attachment uploaded securely.", "attachment_id": attachment_id,
                        "original_name": original_name, "file_size": len(content)}), 201
    except mysql.connector.Error:
        if db: db.rollback()
        app.logger.exception("Student complaint attachment operation failed")
        return jsonify({"error": "Attachment storage is unavailable. Apply Phase 7 migration 004 first."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/student/attachments/<int:attachment_id>/download", methods=["GET"])
@jwt_required()
def student_download_attachment(attachment_id):
    student = get_current_student()
    if not student:
        return jsonify({"error": "Student authentication required"}), 403
    db = cursor = None
    try:
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT a.storage_name, a.original_name FROM complaint_attachments a "
            "JOIN complaints c ON c.complaint_id=a.complaint_id "
            "WHERE a.attachment_id=%s AND c.student_id=%s AND a.student_id=%s",
            (attachment_id, student["student_id"], student["student_id"]),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Attachment not found"}), 404
        path = _UPLOAD_DIR / row["storage_name"]
        if not path.is_file():
            return jsonify({"error": "Attachment file is missing from storage"}), 404
        return send_file(path, as_attachment=True, download_name=row["original_name"])
    except mysql.connector.Error:
        app.logger.exception("Student attachment download failed")
        return jsonify({"error": "Unable to download attachment"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/admin/complaints/<int:complaint_id>/attachments", methods=["GET"])
@jwt_required()
def admin_complaint_attachments(complaint_id):
    admin = get_current_admin()
    if not admin:
        return jsonify({"error": "Administrator access required"}), 403
    db = cursor = None
    try:
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints WHERE complaint_id=%s", (complaint_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Complaint not found"}), 404
        cursor.execute(
            "SELECT attachment_id, original_name, mime_type, file_size, created_at "
            "FROM complaint_attachments WHERE complaint_id=%s ORDER BY created_at DESC",
            (complaint_id,),
        )
        rows = cursor.fetchall()
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        return jsonify(rows), 200
    except mysql.connector.Error:
        app.logger.exception("Admin attachment listing failed")
        return jsonify({"error": "Unable to list complaint attachments. Apply Phase 7 migration 004."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route("/api/admin/attachments/<int:attachment_id>/download", methods=["GET"])
@jwt_required()
def admin_download_attachment(attachment_id):
    admin = get_current_admin()
    if not admin:
        return jsonify({"error": "Administrator access required"}), 403
    db = cursor = None
    try:
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT storage_name, original_name FROM complaint_attachments WHERE attachment_id=%s",
            (attachment_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Attachment not found"}), 404
        path = _UPLOAD_DIR / row["storage_name"]
        if not path.is_file():
            return jsonify({"error": "Attachment file is missing from storage"}), 404
        return send_file(path, as_attachment=True, download_name=row["original_name"])
    except mysql.connector.Error:
        app.logger.exception("Admin attachment download failed")
        return jsonify({"error": "Unable to download attachment"}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Upload exceeds the 5 MB limit."}), 413


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
