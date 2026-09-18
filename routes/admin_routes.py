import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from database.database import db
from database.models import Candidate, Exam, Question, Session, Event, SuspiciousEvent, Evidence, Report, Alert, Setting
from auth.security import admin_required, get_current_user
from analytics.analytics import AnalyticsEngine
from analytics.clustering import SessionClusterer
from analytics.visualizations import AnalyticsVisualizer
from scoring.integrity_score import IntegrityScorer
from scoring.suspicious_detector import SuspiciousDetector
from ai.report_agent import AIReportAgent
from utils.export import DataExporter
from utils.faker_generator import generate_synthetic_dataset

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@admin_bp.route("")
def admin_index():
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    user = get_current_user()
    exam_id = request.args.get("exam_id", type=int)
    
    kpis = AnalyticsEngine.get_dashboard_kpis(exam_id)
    chart_data = AnalyticsEngine.get_chart_data(exam_id)
    
    # Recent sessions
    recent_sessions = Session.query.order_by(Session.start_time.desc()).limit(8).all()
    # Recent monitoring telemetry events
    recent_events = Event.query.order_by(Event.timestamp.desc()).limit(8).all()
    # Recent alerts
    recent_alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(6).all()
    # Available exams for dropdown filter
    exams = Exam.query.all()

    return render_template(
        "admin/dashboard.html",
        user=user,
        kpis=kpis,
        chart_data=chart_data,
        recent_sessions=recent_sessions,
        recent_events=recent_events,
        recent_alerts=recent_alerts,
        exams=exams,
        selected_exam_id=exam_id
    )


@admin_bp.route("/candidates")
@admin_required
def candidates():
    user = get_current_user()
    search = request.args.get("search", "").strip()
    
    candidate_list = Candidate.query.order_by(Candidate.created_at.desc()).all()
    if search:
        term = search.lower()
        candidate_list = [c for c in candidate_list
                          if term in (c.name or "").lower() or term in (c.email or "").lower()]

    # Calculate stats per candidate
    candidate_data = []
    for c in candidate_list:
        sessions = c.sessions
        avg_score = round(sum((s.integrity_score or 100.0) for s in sessions) / len(sessions), 1) if sessions else 100.0
        high_risk_count = sum(1 for s in sessions if s.risk_level == "HIGH")
        candidate_data.append({
            "candidate": c,
            "session_count": len(sessions),
            "avg_score": avg_score,
            "high_risk_count": high_risk_count,
            "last_active": max([s.start_time for s in sessions], default=c.created_at)
        })

    return render_template(
        "admin/candidates.html",
        user=user,
        candidate_data=candidate_data,
        search=search
    )


@admin_bp.route("/candidate/<int:candidate_id>")
@admin_required
def candidate_detail(candidate_id):
    user = get_current_user()
    candidate = Candidate.query.get_or_404(candidate_id)
    
    sessions = Session.query.filter_by(candidate_id=candidate.id).order_by(Session.start_time.desc()).all()
    avg_score = round(sum((s.integrity_score or 100.0) for s in sessions) / len(sessions), 1) if sessions else 100.0
    avg_presence = round(sum((s.face_presence_ratio or 1.0) for s in sessions) / len(sessions) * 100, 1) if sessions else 100.0
    
    # Collect all suspicious events and evidence for this candidate
    session_ids = [s.id for s in sessions]
    suspicious_events = SuspiciousEvent.query.filter(SuspiciousEvent.session_id.in_(session_ids)).order_by(SuspiciousEvent.timestamp.desc()).all() if session_ids else []
    evidence_items = Evidence.query.filter(Evidence.session_id.in_(session_ids)).order_by(Evidence.timestamp.desc()).all() if session_ids else []
    reports = Report.query.filter(Report.session_id.in_(session_ids)).order_by(Report.generated_at.desc()).all() if session_ids else []

    return render_template(
        "admin/candidate_detail.html",
        user=user,
        candidate=candidate,
        sessions=sessions,
        avg_score=avg_score,
        avg_presence=avg_presence,
        suspicious_events=suspicious_events,
        evidence_items=evidence_items,
        reports=reports
    )


@admin_bp.route("/exams", methods=["GET", "POST"])
@admin_required
def exams():
    user = get_current_user()
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        duration_minutes = int(request.form.get("duration_minutes", 30))
        total_marks = int(request.form.get("total_marks", 100))
        passing_marks = int(request.form.get("passing_marks", 50))
        
        if not title:
            flash("Exam title is required.", "danger")
        else:
            new_exam = Exam(
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                total_marks=total_marks,
                passing_marks=passing_marks,
                status="active"
            )
            db.session.add(new_exam)
            db.session.commit()
            flash(f"Exam '{title}' created successfully.", "success")
            return redirect(url_for("admin.exams"))

    exam_list = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template("admin/exams.html", user=user, exams=exam_list)


@admin_bp.route("/sessions")
@admin_required
def sessions():
    user = get_current_user()
    exam_id = request.args.get("exam_id", type=int)
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    query = Session.query.join(Candidate)
    if exam_id:
        query = query.filter(Session.exam_id == exam_id)
    if risk_level:
        query = query.filter(Session.risk_level == risk_level)
    if status:
        query = query.filter(Session.status == status)
    if search:
        query = query.filter(
            (Candidate.name.ilike(f"%{search}%")) | (Candidate.email.ilike(f"%{search}%"))
        )

    session_list = query.order_by(Session.start_time.desc()).all()
    exams = Exam.query.all()

    return render_template(
        "admin/sessions.html",
        user=user,
        sessions=session_list,
        exams=exams,
        selected_exam_id=exam_id,
        selected_risk=risk_level,
        selected_status=status,
        search=search
    )


@admin_bp.route("/session/<int:session_id>")
@admin_required
def session_detail(session_id):
    user = get_current_user()
    session_obj = Session.query.get_or_404(session_id)
    
    # Recalculate scoring details for transparency breakdown
    scoring_info = IntegrityScorer.calculate_session_integrity(session_obj.id, session_obj.events, session_obj.face_presence_ratio)
    
    # Fetch chronological timeline events
    events = Event.query.filter_by(session_id=session_id).order_by(Event.timestamp.asc()).all()
    suspicious_events = SuspiciousEvent.query.filter_by(session_id=session_id).order_by(SuspiciousEvent.timestamp.asc()).all()
    evidence_items = Evidence.query.filter_by(session_id=session_id).order_by(Evidence.timestamp.desc()).all()
    reports = Report.query.filter_by(session_id=session_id).order_by(Report.generated_at.desc()).all()
    
    # Answer summary
    try:
        answers = json.loads(session_obj.answers_json or "{}")
    except Exception:
        answers = {}

    return render_template(
        "admin/session_detail.html",
        user=user,
        session_obj=session_obj,
        scoring_info=scoring_info,
        events=events,
        suspicious_events=suspicious_events,
        evidence_items=evidence_items,
        reports=reports,
        answers=answers
    )


@admin_bp.route("/analytics")
@admin_required
def analytics():
    user = get_current_user()
    exam_id = request.args.get("exam_id", type=int)
    
    kpis = AnalyticsEngine.get_dashboard_kpis(exam_id)
    chart_data = AnalyticsEngine.get_chart_data(exam_id)
    exams = Exam.query.all()

    # Most frequent suspicious rules
    suspicious_summary = db.session.query(
        SuspiciousEvent.rule_name,
        SuspiciousEvent.severity,
        db.func.count(SuspiciousEvent.id).label("count")
    ).group_by(SuspiciousEvent.rule_name, SuspiciousEvent.severity).order_by(db.desc("count")).limit(5).all()

    return render_template(
        "admin/analytics.html",
        user=user,
        kpis=kpis,
        chart_data=chart_data,
        exams=exams,
        selected_exam_id=exam_id,
        suspicious_summary=suspicious_summary
    )


@admin_bp.route("/clustering")
@admin_required
def clustering():
    user = get_current_user()
    clustering_results = SessionClusterer.run_clustering(save_to_db=False)
    
    return render_template(
        "admin/clustering.html",
        user=user,
        clustering=clustering_results
    )


@admin_bp.route("/alerts")
@admin_required
def alerts():
    user = get_current_user()
    severity = request.args.get("severity", "").strip()
    status = request.args.get("status", "").strip()

    query = Alert.query
    if severity:
        query = query.filter_by(severity=severity)
    if status:
        query = query.filter_by(status=status)

    alert_list = query.order_by(Alert.timestamp.desc()).all()

    return render_template(
        "admin/alerts.html",
        user=user,
        alerts=alert_list,
        selected_severity=severity,
        selected_status=status
    )


@admin_bp.route("/reports")
@admin_required
def reports():
    user = get_current_user()
    reports_list = Report.query.order_by(Report.generated_at.desc()).all()
    sessions = Session.query.order_by(Session.start_time.desc()).limit(50).all()

    return render_template(
        "admin/reports.html",
        user=user,
        reports=reports_list,
        sessions=sessions
    )


@admin_bp.route("/evidence")
@admin_required
def evidence():
    user = get_current_user()
    session_id = request.args.get("session_id", type=int)
    
    query = Evidence.query
    if session_id:
        query = query.filter_by(session_id=session_id)
        
    evidence_list = query.order_by(Evidence.timestamp.desc()).all()
    sessions = Session.query.order_by(Session.start_time.desc()).all()

    return render_template(
        "admin/evidence.html",
        user=user,
        evidence_list=evidence_list,
        sessions=sessions,
        selected_session_id=session_id
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    user = get_current_user()

    if request.method == "POST":
        try:
            Setting.set_val("face_absence_threshold_sec", float(request.form.get("face_absence_threshold_sec", 8.0)))
            Setting.set_val("tab_switch_threshold", int(request.form.get("tab_switch_threshold", 3)))
            Setting.set_val("high_risk_tab_switch_threshold", int(request.form.get("high_risk_tab_switch_threshold", 6)))
            Setting.set_val("window_blur_threshold", int(request.form.get("window_blur_threshold", 4)))
            Setting.set_val("monitoring_interval_ms", int(request.form.get("monitoring_interval_ms", 1500)))
            Setting.set_val("multiple_faces_threshold", int(request.form.get("multiple_faces_threshold", 1)))
            
            Setting.set_val("weight_face_absence", float(request.form.get("weight_face_absence", 0.30)))
            Setting.set_val("weight_tab_switch", float(request.form.get("weight_tab_switch", 0.25)))
            Setting.set_val("weight_window_blur", float(request.form.get("weight_window_blur", 0.20)))
            Setting.set_val("weight_other_suspicious", float(request.form.get("weight_other_suspicious", 0.25)))
            
            Setting.set_val("low_risk_min_score", float(request.form.get("low_risk_min_score", 80.0)))
            Setting.set_val("medium_risk_min_score", float(request.form.get("medium_risk_min_score", 50.0)))

            flash("Platform monitoring settings and scoring weights updated successfully.", "success")
        except Exception as e:
            flash(f"Error saving settings: {e}", "danger")

        return redirect(url_for("admin.settings"))

    current_settings = {
        "face_absence_threshold_sec": Setting.get_val("face_absence_threshold_sec", 8.0),
        "tab_switch_threshold": Setting.get_val("tab_switch_threshold", 3),
        "high_risk_tab_switch_threshold": Setting.get_val("high_risk_tab_switch_threshold", 6),
        "window_blur_threshold": Setting.get_val("window_blur_threshold", 4),
        "monitoring_interval_ms": Setting.get_val("monitoring_interval_ms", 1500),
        "multiple_faces_threshold": Setting.get_val("multiple_faces_threshold", 1),
        "weight_face_absence": Setting.get_val("weight_face_absence", 0.30),
        "weight_tab_switch": Setting.get_val("weight_tab_switch", 0.25),
        "weight_window_blur": Setting.get_val("weight_window_blur", 0.20),
        "weight_other_suspicious": Setting.get_val("weight_other_suspicious", 0.25),
        "low_risk_min_score": Setting.get_val("low_risk_min_score", 80.0),
        "medium_risk_min_score": Setting.get_val("medium_risk_min_score", 50.0),
    }

    return render_template("admin/settings.html", user=user, settings=current_settings)


@admin_bp.route("/events")
@admin_required
def events_log():
    """Monitoring Events Log page displaying all raw and flagged telemetry events."""
    user = get_current_user()
    session_id = request.args.get("session_id", type=int)
    event_type = request.args.get("event_type", "").strip()
    severity = request.args.get("severity", "").strip()

    query = Event.query.join(Session).join(Candidate)
    if session_id:
        query = query.filter(Event.session_id == session_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if severity:
        query = query.filter(Event.severity == severity)

    event_list = query.order_by(Event.timestamp.desc()).limit(150).all()
    sessions = Session.query.order_by(Session.start_time.desc()).all()

    # Get distinct event types
    event_types = [r[0] for r in db.session.query(Event.event_type).distinct().all()]

    return render_template(
        "admin/monitoring_events.html",
        user=user,
        events=event_list,
        sessions=sessions,
        event_types=event_types,
        selected_session_id=session_id,
        selected_event_type=event_type,
        selected_severity=severity
    )


@admin_bp.route("/scores")
@admin_required
def integrity_scores():
    """Integrity Scores ranking and risk classification table."""
    user = get_current_user()
    exam_id = request.args.get("exam_id", type=int)
    risk_level = request.args.get("risk_level", "").strip()
    sort_by = request.args.get("sort_by", "score_asc")

    query = Session.query.join(Candidate)
    if exam_id:
        query = query.filter(Session.exam_id == exam_id)
    if risk_level:
        query = query.filter(Session.risk_level == risk_level)

    if sort_by == "score_asc":
        query = query.order_by(Session.integrity_score.asc())
    elif sort_by == "score_desc":
        query = query.order_by(Session.integrity_score.desc())
    else:
        query = query.order_by(Session.start_time.desc())

    sessions = query.all()
    exams = Exam.query.all()
    kpis = AnalyticsEngine.get_dashboard_kpis(exam_id)

    return render_template(
        "admin/integrity_scores.html",
        user=user,
        sessions=sessions,
        exams=exams,
        kpis=kpis,
        selected_exam_id=exam_id,
        selected_risk=risk_level,
        sort_by=sort_by
    )


@admin_bp.route("/export")
@admin_required
def export_hub():
    """Institutional Data Export Hub."""
    user = get_current_user()
    exams = Exam.query.all()
    total_sessions = Session.query.count()
    total_events = Event.query.count()

    return render_template(
        "admin/export.html",
        user=user,
        exams=exams,
        total_sessions=total_sessions,
        total_events=total_events
    )


@admin_bp.route("/export/csv")
@admin_required
def export_csv():
    """Export session data, scores, risk, and clusters as CSV."""
    exam_id = request.args.get("exam_id", type=int)
    csv_stream = DataExporter.export_sessions_csv(exam_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"examguard_sessions_{timestamp}.csv"

    return Response(
        csv_stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@admin_bp.route("/export/events-csv")
@admin_required
def export_events_csv():
    """Export raw monitoring telemetry events as CSV."""
    session_id = request.args.get("session_id", type=int)
    csv_stream = DataExporter.export_events_csv(session_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"examguard_events_{timestamp}.csv"

    return Response(
        csv_stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@admin_bp.route("/export/json")
@admin_required
def export_json():
    """Export complete structured dataset as JSON."""
    exam_id = request.args.get("exam_id", type=int)
    json_data = DataExporter.export_dataset_json(exam_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"examguard_telemetry_{timestamp}.json"

    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@admin_bp.route("/export/session/<int:session_id>")
@admin_required
def export_single_session(session_id):
    """Export single session audit package as JSON."""
    try:
        report_data = DataExporter.export_session_report(session_id)
        filename = f"examguard_session_{session_id}_report.json"
        return Response(
            json.dumps(report_data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        flash(f"Error exporting session report: {e}", "danger")
        return redirect(url_for("admin.session_detail", session_id=session_id))


@admin_bp.route("/generate-demo-data", methods=["POST", "GET"])
@admin_required
def generate_demo_data():
    """Manager button action to generate synthetic demo dataset with Faker."""
    try:
        result = generate_synthetic_dataset(num_candidates=110, num_sessions=220)
        flash(f"Demo Mode: Generated {result['candidates_added']} candidates, {result['sessions_added']} sessions, and {result['events_created']} events.", "success")
    except Exception as e:
        flash(f"Error generating synthetic demo data: {e}", "danger")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/visualizations")
@admin_required
def visualizations():
    """Render publication-grade Matplotlib & Seaborn data science visualizations."""
    user = get_current_user()
    exam_id = request.args.get("exam_id", type=int)
    exams = Exam.query.all()

    # Generate figures on the fly
    plots = AnalyticsVisualizer.generate_all_plots(exam_id)

    return render_template(
        "admin/visualizations.html",
        user=user,
        exams=exams,
        selected_exam_id=exam_id,
        plots=plots
    )

