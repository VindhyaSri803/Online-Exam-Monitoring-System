"""
Manager / Invigilator Portal Routes for ExamGuard.
Handles Manager Dashboard, Sessions, Candidates, Monitoring Events,
Integrity Scores, Risk Classifications, Suspicious Activities, Evidence,
AI Integrity Reports, Settings, Demo Data Generation, and Exports.
"""

from flask import Blueprint, redirect, url_for
from routes.admin_routes import admin_bp

# manager_bp alias redirecting to admin_bp endpoints or serving manager prefix
manager_bp = Blueprint("manager", __name__, url_prefix="/manager")

@manager_bp.route("/")
@manager_bp.route("")
@manager_bp.route("/dashboard")
def manager_dashboard():
    return redirect(url_for("admin.dashboard"))

@manager_bp.route("/sessions")
def manager_sessions():
    return redirect(url_for("admin.sessions"))

@manager_bp.route("/session/<int:session_id>")
def manager_session_detail(session_id):
    return redirect(url_for("admin.session_detail", session_id=session_id))

@manager_bp.route("/candidates")
def manager_candidates():
    return redirect(url_for("admin.candidates"))

@manager_bp.route("/candidate/<int:candidate_id>")
def manager_candidate_detail(candidate_id):
    return redirect(url_for("admin.candidate_detail", candidate_id=candidate_id))

@manager_bp.route("/events")
def manager_events():
    return redirect(url_for("admin.events_log"))

@manager_bp.route("/scores")
def manager_scores():
    return redirect(url_for("admin.integrity_scores"))

@manager_bp.route("/analytics")
def manager_analytics():
    return redirect(url_for("admin.analytics"))

@manager_bp.route("/clustering")
def manager_clustering():
    return redirect(url_for("admin.clustering"))

@manager_bp.route("/reports")
def manager_reports():
    return redirect(url_for("admin.reports"))

@manager_bp.route("/evidence")
def manager_evidence():
    return redirect(url_for("admin.evidence"))

@manager_bp.route("/export")
def manager_export():
    return redirect(url_for("admin.export_hub"))

@manager_bp.route("/export/csv")
def manager_export_csv():
    return redirect(url_for("admin.export_csv"))

@manager_bp.route("/export/json")
def manager_export_json():
    return redirect(url_for("admin.export_json"))

__all__ = ["manager_bp", "admin_bp"]
