import os
from flask import Flask, redirect, url_for, session, send_from_directory
from config import Config
from database.database import db, init_db
from database.models import User, Candidate
from data.seed_data import seed_default_data

# Import Blueprints
from auth.routes import auth_bp
from routes.candidate_routes import candidate_bp
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp

def create_app(config_class=Config):
    """ExamGuard Application Factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    init_db(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Static routes for user photos and incident evidence
    @app.route("/uploads/photos/<filename>")
    def uploaded_photo(filename):
        return send_from_directory(app.config["PHOTOS_FOLDER"], filename)

    @app.route("/uploads/evidence/<filename>")
    def uploaded_evidence(filename):
        return send_from_directory(app.config["EVIDENCE_FOLDER"], filename)

    # Root and alias redirects
    @app.route("/")
    def index():
        if "user_id" in session:
            if session.get("user_role") in ["admin", "manager"]:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("candidate.dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/login")
    def login_redirect():
        return redirect(url_for("auth.login"))

    @app.route("/register")
    def register_redirect():
        return redirect(url_for("auth.register"))

    @app.route("/admin")
    def admin_redirect():
        return redirect(url_for("admin.dashboard"))

    @app.route("/manager")
    def manager_redirect():
        return redirect(url_for("admin.dashboard"))

    @app.route("/candidate")
    def candidate_redirect():
        return redirect(url_for("candidate.dashboard"))

    # Global Template Context
    @app.context_processor
    def inject_global_context():
        current_user = None
        if "user_id" in session:
            current_user = db.session.get(Candidate, session["user_id"])
            if not current_user:
                current_user = db.session.get(User, session["user_id"])
        return {
            "current_user": current_user,
            "app_name": "ExamGuard",
            "app_version": "2.4.0-Enterprise",
            "ethical_disclaimer": (
                "ExamGuard provides monitoring indicators and analytical evidence to assist invigilators. "
                "Automated indicators do not constitute proof of academic misconduct. "
                "Final decisions must be made through appropriate human review."
            )
        }

    # Seed only after schema initialization, and never while unit tests run.
    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                seed_default_data()
            except Exception as e:
                app.logger.warning(f"Could not auto-seed database on startup: {e}")
    return app

if __name__ == "__main__":
    app = create_app()
    print("=========================================================")
    print("  EXAMGUARD — Online Exam Monitoring & Analytics Platform ")
    print("  Default Manager     : manager@examguard.com / manager123 ")
    print("  Default Invigilator : admin@examguard.com / admin123   ")
    print("  Default Candidate   : candidate@examguard.com / candidate123 ")
    print("  Server running at   : http://127.0.0.1:5000            ")
    print("=========================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
