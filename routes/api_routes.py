import os
import time
import base64
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, session
from database.database import db
from database.models import Session, Event, SuspiciousEvent, Evidence, Alert, Setting
from monitoring.face_detector import detector
from monitoring.browser_monitor import BrowserMonitor
from scoring.suspicious_detector import SuspiciousDetector
from scoring.integrity_score import IntegrityScorer
from ai.report_agent import AIReportAgent
from data.synthetic_generator import generate_synthetic_dataset
from analytics.analytics import AnalyticsEngine
from analytics.clustering import SessionClusterer
from evidence.evidence_manager import EvidenceManager

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/monitoring/face-frame", methods=["POST"])
def process_face_frame():
    """Real-time OpenCV Haar Cascade Face Detection endpoint for candidate webcam feed."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    frame_data = data.get("frame", "")
    mode = data.get("mode", "live")  # 'live' or 'simulated'

    if not session_id:
        return jsonify({"success": False, "error": "session_id is required"}), 400

    session_obj = db.session.get(Session, session_id)
    if not session_obj or session_obj.status != "in_progress":
        return jsonify({"success": False, "error": "Active session not found"}), 404

    # Process frame with OpenCV
    if mode == "simulated" or not frame_data:
        # Simulated mode payload
        sim_present = data.get("simulated_face_detected", True)
        face_count = 1 if sim_present else 0
        face_detected = sim_present
        status = "FACE_PRESENT" if sim_present else "FACE_ABSENT"
        boxes = [{"x": 140, "y": 80, "w": 180, "h": 220}] if sim_present else []
    else:
        result = detector.process_frame(frame_data)
        face_detected = result["face_detected"]
        face_count = result["face_count"]
        boxes = result["boxes"]
        status = result["status"]

    # Log Event in database
    event_severity = "INFO" if status == "FACE_PRESENT" else ("CRITICAL" if status == "MULTIPLE_FACES_DETECTED" else "WARNING")
    event_desc = f"Face presence check: {status} (Face count: {face_count})"

    event = Event(
        session_id=session_id,
        event_type=status,
        timestamp=datetime.now(timezone.utc),
        duration=1.5 if status == "FACE_ABSENT" else 0.0,
        severity=event_severity,
        description=event_desc
    )
    db.session.add(event)
    db.session.flush()

    # If multiple faces detected or critical absence, save evidence screenshot
    if status == "MULTIPLE_FACES_DETECTED" and frame_data:
        EvidenceManager.save_evidence_frame(
            session_id=session_id,
            base64_image=frame_data,
            event_id=event.id,
            evidence_type="face_frame",
            description=f"Multiple faces detected ({face_count} persons in frame)",
            upload_folder=current_app.config["EVIDENCE_FOLDER"]
        )

    # Re-calculate live Face Presence Ratio
    events = Event.query.filter_by(session_id=session_id).all()
    face_events = [e for e in events if e.event_type in ["FACE_PRESENT", "FACE_ABSENT", "MULTIPLE_FACES_DETECTED"]]
    if face_events:
        present_count = sum(1 for e in face_events if e.event_type in ["FACE_PRESENT", "MULTIPLE_FACES_DETECTED"])
        session_obj.face_presence_ratio = round(present_count / len(face_events), 3)

    # Check suspicious rules
    SuspiciousDetector.evaluate_session_events(session_id)
    db.session.commit()

    return jsonify({
        "success": True,
        "face_detected": face_detected,
        "face_count": face_count,
        "boxes": boxes,
        "status": status,
        "face_presence_ratio": session_obj.face_presence_ratio
    })


@api_bp.route("/monitoring/event", methods=["POST"])
def log_telemetry_event():
    """Log browser telemetry events (tab switch, window blur/focus, mouse/key activity)."""
    data = request.get_json() or {}
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"success": False, "error": "session_id is required"}), 400

    session_obj = db.session.get(Session, session_id)
    if not session_obj or session_obj.status != "in_progress":
        return jsonify({"success": False, "error": "Session is not active"}), 404

    processed = BrowserMonitor.process_telemetry_event(data)
    
    event = Event(
        session_id=session_id,
        event_type=processed["event_type"],
        timestamp=processed["timestamp"],
        duration=processed["duration"],
        severity=processed["severity"],
        description=processed["description"]
    )
    db.session.add(event)
    db.session.flush()

    # If screenshot payload attached to suspicious event, save it as evidence
    frame_data = data.get("screenshot", "")
    if frame_data and processed["event_type"] in ["TAB_SWITCH", "WINDOW_BLUR", "DEVTOOLS_OPENED"]:
        EvidenceManager.save_evidence_frame(
            session_id=session_id,
            base64_image=frame_data,
            event_id=event.id,
            evidence_type="screenshot",
            description=f"Snapshot during {processed['event_type']}",
            upload_folder=current_app.config["EVIDENCE_FOLDER"]
        )

    # Trigger rule evaluations
    SuspiciousDetector.evaluate_session_events(session_id)
    db.session.commit()

    return jsonify({"success": True, "event_id": event.id})


@api_bp.route("/monitoring/simulated-event", methods=["POST"])
def trigger_simulated_event():
    """Trigger a simulated anomaly event for live testing."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    event_type = data.get("event_type", "TAB_SWITCH")

    session_obj = Session.query.get_or_404(session_id)
    processed = BrowserMonitor.process_telemetry_event({
        "event_type": event_type,
        "description": f"Simulated test event: {event_type}",
        "duration": 5.0
    })

    event = Event(
        session_id=session_id,
        event_type=processed["event_type"],
        timestamp=processed["timestamp"],
        duration=processed["duration"],
        severity=processed["severity"],
        description=processed["description"]
    )
    db.session.add(event)
    db.session.flush()

    SuspiciousDetector.evaluate_session_events(session_id)
    db.session.commit()

    return jsonify({"success": True, "event_type": event_type, "message": f"Simulated {event_type} registered."})


@api_bp.route("/admin/generate-report/<int:session_id>", methods=["POST"])
def generate_ai_report(session_id):
    """Generate and return an AI integrity audit report for session."""
    try:
        report_data = AIReportAgent.generate_report(session_id)
        return jsonify({"success": True, "report": report_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/admin/generate-synthetic-data", methods=["POST"])
def generate_synthetic_data_endpoint():
    """API endpoint to trigger synthetic dataset generation with Faker."""
    try:
        data = request.get_json() or {}
        num_candidates = int(data.get("candidates", 110))
        num_sessions = int(data.get("sessions", 220))
        
        result = generate_synthetic_dataset(num_candidates=num_candidates, num_sessions=num_sessions)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/admin/update-incident-status", methods=["POST"])
def update_incident_status():
    """Update review status of a session or alert."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    alert_id = data.get("alert_id")
    new_status = data.get("status", "Reviewed")

    if session_id:
        session_obj = Session.query.get_or_404(session_id)
        session_obj.incident_status = new_status
        # Also update any associated alerts
        for a in session_obj.alerts:
            a.status = new_status
        db.session.commit()
        return jsonify({"success": True, "message": f"Session #{session_id} status updated to '{new_status}'."})

    if alert_id:
        alert_obj = Alert.query.get_or_404(alert_id)
        alert_obj.status = new_status
        db.session.commit()
        return jsonify({"success": True, "message": f"Alert #{alert_id} status updated to '{new_status}'."})

    return jsonify({"success": False, "error": "session_id or alert_id required"}), 400


@api_bp.route("/admin/clustering/run", methods=["POST"])
def run_clustering_api():
    """Trigger K-Means clustering algorithm on demand."""
    try:
        result = SessionClusterer.run_clustering(save_to_db=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/admin/analytics-data", methods=["GET"])
def get_analytics_data_api():
    """Fetch raw analytics and chart datasets."""
    exam_id = request.args.get("exam_id", type=int)
    kpis = AnalyticsEngine.get_dashboard_kpis(exam_id)
    chart_data = AnalyticsEngine.get_chart_data(exam_id)
    return jsonify({"success": True, "kpis": kpis, "charts": chart_data})
