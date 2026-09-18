from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256")

def verify_password(password: str, password_hash: str) -> bool:
    return bool(password and password_hash and check_password_hash(password_hash, password))

def get_current_user():
    from database.database import db
    from database.models import User, Candidate
    user_id = session.get("user_id")
    if not user_id:
        return None
    role = session.get("user_role")
    if role in ("admin", "manager"):
        return db.session.get(User, user_id)
    cand = db.session.get(Candidate, user_id)
    return cand or db.session.get(User, user_id)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            flash("Please log in as a manager or admin.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") not in ["manager", "admin"]:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Manager/admin privilege required"}), 403
            flash("Access denied: manager/admin privileges required.", "danger")
            return redirect(url_for("candidate.dashboard"))
        return f(*args, **kwargs)
    return decorated_function

manager_required = admin_required

def candidate_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            flash("Please log in to access candidate portal.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") != "candidate":
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Candidate privilege required"}), 403
            flash("Candidate portal access is restricted to candidate accounts.", "danger")
            return redirect(url_for("admin.dashboard"))
        return f(*args, **kwargs)
    return decorated_function
