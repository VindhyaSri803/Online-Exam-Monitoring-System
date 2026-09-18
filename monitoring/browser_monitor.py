from datetime import datetime, timezone
from typing import Dict, Any, Tuple

EVENT_SEVERITY_MAP = {
    "SESSION_STARTED": "INFO",
    "SESSION_SUBMITTED": "INFO",
    "FACE_PRESENT": "INFO",
    "MOUSE_ACTIVITY": "INFO",
    "KEYBOARD_ACTIVITY": "INFO",
    "QUESTION_NAVIGATE": "INFO",
    "ANSWER_SELECTED": "INFO",
    "WINDOW_FOCUS": "INFO",
    "FACE_ABSENT": "WARNING",
    "WINDOW_BLUR": "WARNING",
    "TAB_SWITCH": "SUSPICIOUS",
    "MULTIPLE_FACES_DETECTED": "CRITICAL",
    "DEVTOOLS_OPENED": "CRITICAL",
    "FULLSCREEN_EXIT": "SUSPICIOUS",
    "COPY_PASTE_ATTEMPT": "SUSPICIOUS"
}

EVENT_DESCRIPTIONS = {
    "SESSION_STARTED": "Candidate started the examination session.",
    "SESSION_SUBMITTED": "Candidate completed and submitted the examination.",
    "FACE_PRESENT": "Candidate face detected in frame.",
    "FACE_ABSENT": "No face detected in webcam view.",
    "MULTIPLE_FACES_DETECTED": "Multiple faces detected simultaneously in the examination room view.",
    "TAB_SWITCH": "Candidate switched browser tabs away from exam interface.",
    "WINDOW_BLUR": "Candidate moved focus away from the exam window.",
    "WINDOW_FOCUS": "Candidate returned focus to the exam window.",
    "MOUSE_ACTIVITY": "Normal mouse cursor movement recorded.",
    "KEYBOARD_ACTIVITY": "Keyboard interaction recorded.",
    "QUESTION_NAVIGATE": "Candidate navigated to another question.",
    "ANSWER_SELECTED": "Candidate selected an answer choice.",
    "DEVTOOLS_OPENED": "Developer tools or inspector panel opened.",
    "FULLSCREEN_EXIT": "Candidate exited full screen mode.",
    "COPY_PASTE_ATTEMPT": "Candidate attempted clipboard copy/paste action."
}

class BrowserMonitor:
    """Helper to standardize, validate, and enrich browser telemetry events."""
    
    @staticmethod
    def process_telemetry_event(raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and format a raw telemetry payload from candidate client."""
        event_type = raw_event.get("event_type", "UNKNOWN").upper()
        severity = EVENT_SEVERITY_MAP.get(event_type, "INFO")
        description = raw_event.get("description") or EVENT_DESCRIPTIONS.get(event_type, f"Telemetry event: {event_type}")
        duration = float(raw_event.get("duration", 0.0))
        metadata = raw_event.get("metadata", {})
        
        return {
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "duration": duration,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc)
        }
