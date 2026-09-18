"""
Real-time Monitoring Routes for ExamGuard.
Handles OpenCV Haar Cascade Face Detection frame processing,
browser telemetry events (tab switch, window blur, fullscreen exit),
and simulated anomaly triggers.
"""

from flask import Blueprint, request, jsonify, current_app
from database.database import db
from database.models import Session, Event, SuspiciousEvent, Evidence
from monitoring.face_detector import detector
from monitoring.browser_monitor import BrowserMonitor
from scoring.suspicious_detector import SuspiciousDetector
from evidence.evidence_manager import EvidenceManager
from datetime import datetime, timezone

monitoring_bp = Blueprint("monitoring_routes", __name__, url_prefix="/api/monitoring")

@monitoring_bp.route("/face-frame", methods=["POST"])
def process_face_frame():
    """Real-time OpenCV Haar Cascade Face Detection endpoint for candidate webcam feed."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    frame_data = data.get("frame", "")
    mode = data.get("mode", "live")

    if not session_id:
        return jsonify({"success": False, "error": "session_id is required"}), 400

    session_obj = db.session.get(Session, session_id)
    if not session_obj or session_obj.status != "in_progress":
        return jsonify({"success": False, "error": "Active session not found"}), 404

    if mode == "simulated" or not frame_data:
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

    event_severity = "INFO" if status == "FACE_PRESENT" else ("CRITICAL" if status in ["MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"] else "WARNING")
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

    if status in ["MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"] and frame_data:
        EvidenceManager.save_evidence_frame(
            session_id=session_id,
            base64_image=frame_data,
            event_id=event.id,
            evidence_type="face_frame",
            description=f"Multiple faces detected ({face_count} persons in frame)",
            upload_folder=current_app.config["EVIDENCE_FOLDER"]
        )

    events = Event.query.filter_by(session_id=session_id).all()
    face_events = [e for e in events if e.event_type in ["FACE_PRESENT", "FACE_ABSENT", "MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"]]
    if face_events:
        present_count = sum(1 for e in face_events if e.event_type in ["FACE_PRESENT", "MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"])
        session_obj.face_presence_ratio = round(present_count / len(face_events), 3)

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


@monitoring_bp.route("/event", methods=["POST"])
def log_telemetry_event():
    """Log browser telemetry events (tab switch, window blur/focus, fullscreen exit, mouse/key activity)."""
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

    frame_data = data.get("screenshot", "")
    if frame_data and processed["event_type"] in ["TAB_SWITCH", "WINDOW_BLUR", "FULLSCREEN_EXIT", "DEVTOOLS_OPENED"]:
        EvidenceManager.save_evidence_frame(
            session_id=session_id,
            base64_image=frame_data,
            event_id=event.id,
            evidence_type="screenshot",
            description=f"Snapshot during {processed['event_type']}",
            upload_folder=current_app.config["EVIDENCE_FOLDER"]
        )

    SuspiciousDetector.evaluate_session_events(session_id)
    db.session.commit()

    return jsonify({"success": True, "event_id": event.id})


@monitoring_bp.route("/simulated-event", methods=["POST"])
def trigger_simulated_event():
    """Trigger a simulated anomaly event for testing and demonstrations."""
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
