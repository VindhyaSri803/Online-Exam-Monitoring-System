import os
import re
import uuid
import base64
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from database.database import db
from database.models import User, Candidate
from auth.security import hash_password, verify_password, get_current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/")
@auth_bp.route("")
def auth_index():
    return redirect(url_for("auth.login"))

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

def save_base64_image(base64_str: str, folder: str) -> str:
    """Decode and save a base64 image data string into target folder."""
    if not base64_str:
        return ""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    
    img_data = base64.b64decode(base64_str)
    filename = f"user_{uuid.uuid4().hex[:12]}.jpg"
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(img_data)
    return filename


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("admin.dashboard") if session.get("user_role") in ["admin", "manager"] else url_for("candidate.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        photo_data = request.form.get("photo_data", "")

        # Validation
        errors = []
        if not name or len(name) < 2:
            errors.append("Full Name is required (at least 2 characters).")
        if not email or not re.match(EMAIL_REGEX, email):
            errors.append("A valid email address is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check duplicate email in both User and Candidate
        existing_u = User.query.filter_by(email=email).first()
        if existing_u:
            errors.append(f"An account with email '{email}' already exists. Please login instead.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html", name=name, email=email)

        # Handle photograph
        photo_filename = None
        if photo_data:
            try:
                photo_filename = save_base64_image(photo_data, current_app.config["PHOTOS_FOLDER"])
            except Exception as e:
                current_app.logger.error(f"Error saving registration photo: {e}")

        # Create user record
        pwd_hash = hash_password(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=pwd_hash,
            role="candidate"
        )
        db.session.add(new_user)
        db.session.flush()

        # Create linked candidate record (Candidate stores only candidate-specific data).
        new_candidate = Candidate(
            user_id=new_user.id,
            registration_photo=photo_filename
        )
        db.session.add(new_candidate)
        db.session.commit()

        # Automatically log in user
        session.clear()
        session["user_id"] = new_candidate.id
        session["user_name"] = new_candidate.name
        session["user_email"] = new_candidate.email
        session["user_role"] = new_candidate.role

        flash("Registration successful! Welcome to ExamGuard.", "success")
        return redirect(url_for("candidate.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("admin.dashboard") if session.get("user_role") in ["admin", "manager"] else url_for("candidate.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role_hint = request.form.get("role_hint", "candidate")

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template("auth/login.html", email=email, role_hint=role_hint)

        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("auth/login.html", email=email, role_hint=role_hint)

        # Login session
        session.clear()
        session["user_id"] = user.candidate.id if user.role == "candidate" and user.candidate else user.id
        session["user_name"] = user.name
        session["user_email"] = user.email
        session["user_role"] = user.role

        flash(f"Welcome back, {user.name}!", "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)

        if user.role in ["admin", "manager"]:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("candidate.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/demo-login/<role>")
def demo_login(role):
    """Convenience shortcut for demo Candidate, Manager, or Admin login."""
    email_map = {
        "candidate": "candidate@examguard.com",
        "manager": "manager@examguard.com",
        "admin": "admin@examguard.com",
    }
    email = email_map.get(role)
    user = User.query.filter_by(email=email).first() if email else None
    if user:
        session.clear()
        session["user_id"] = user.candidate.id if user.role == "candidate" and user.candidate else user.id
        session["user_name"] = user.name
        session["user_email"] = user.email
        session["user_role"] = user.role
        flash(f"Logged in via quick demo as {user.name} ({user.role.title()}).", "info")
        return redirect(url_for("admin.dashboard") if user.role in ("manager", "admin") else url_for("candidate.dashboard"))
    flash("Demo account not initialized.", "warning")
    return redirect(url_for("auth.login"))
