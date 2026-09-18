import json
from datetime import datetime, timezone
from database.database import db
from database.models import Event, SuspiciousEvent, Alert, Session
from config import FACE_ABSENT_THRESHOLD, TAB_SWITCH_THRESHOLD, FOCUS_LOSS_THRESHOLD, MULTIPLE_FACES_THRESHOLD

class SuspiciousDetector:
    """Configurable Rule-Based Suspicious Event & Anomaly Detection Engine."""
    
    @staticmethod
    def get_settings():
        return {
            "face_absence_threshold_sec": float(FACE_ABSENT_THRESHOLD),
            "tab_switch_threshold": int(TAB_SWITCH_THRESHOLD),
            "high_risk_tab_switch_threshold": int(TAB_SWITCH_THRESHOLD * 2),
            "window_blur_threshold": int(FOCUS_LOSS_THRESHOLD),
            "multiple_faces_threshold": int(MULTIPLE_FACES_THRESHOLD),
        }

    @classmethod
    def evaluate_session_events(cls, session_id: int):
        """
        Evaluate full session event log and detect any triggered suspicious rules.
        Creates SuspiciousEvent and Alert rows in database if not already created.
        """
        session_obj = db.session.get(Session, session_id)
        if not session_obj:
            return []

        settings = cls.get_settings()
        events = Event.query.filter_by(session_id=session_id).order_by(Event.timestamp.asc()).all()
        
        # Existing rule names already flagged for this session
        existing_rules = {se.rule_name for se in session_obj.suspicious_events}
        
        detected_suspicious = []
        
        # 1. Evaluate Tab Switches
        tab_switches = [e for e in events if e.event_type == "TAB_SWITCH"]
        tab_count = len(tab_switches)
        
        if tab_count >= settings["high_risk_tab_switch_threshold"]:
            rule_name = "Excessive Tab Switching (High Risk)"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=tab_switches[-1].id if tab_switches else None,
                    rule_name=rule_name,
                    severity="HIGH",
                    description=f"Exam session recorded tab switches {tab_count} times, exceeding high-risk threshold ({settings['high_risk_tab_switch_threshold']}).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "HIGH", "High Risk: Excessive Tab Switching", se.description)
                existing_rules.add(rule_name)
        elif tab_count >= settings["tab_switch_threshold"]:
            rule_name = "Frequent Tab Switching"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=tab_switches[-1].id if tab_switches else None,
                    rule_name=rule_name,
                    severity="MEDIUM",
                    description=f"Exam session recorded tab switches {tab_count} times, exceeding threshold ({settings['tab_switch_threshold']}).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "MEDIUM", "Warning: Frequent Tab Switching", se.description)
                existing_rules.add(rule_name)

        # 2. Evaluate Window Focus Loss (Blurs)
        window_blurs = [e for e in events if e.event_type == "WINDOW_BLUR"]
        blur_count = len(window_blurs)
        if blur_count >= settings["window_blur_threshold"]:
            rule_name = "Repeated Window Focus Loss"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=window_blurs[-1].id if window_blurs else None,
                    rule_name=rule_name,
                    severity="MEDIUM",
                    description=f"Exam window lost focus {blur_count} times (Threshold: {settings['window_blur_threshold']}).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "MEDIUM", "Warning: Repeated Focus Loss", se.description)
                existing_rules.add(rule_name)

        # 3. Evaluate Prolonged Face Absence
        face_absent_events = [e for e in events if e.event_type == "FACE_ABSENT"]
        total_absence_duration = sum(e.duration for e in face_absent_events if e.duration)
        
        # Check if any single absence or total absence exceeded threshold
        max_single_absence = max([e.duration for e in face_absent_events], default=0.0)
        
        if max_single_absence >= settings["face_absence_threshold_sec"] or total_absence_duration >= (settings["face_absence_threshold_sec"] * 1.5):
            rule_name = "Prolonged Face Absence"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=face_absent_events[-1].id if face_absent_events else None,
                    rule_name=rule_name,
                    severity="MEDIUM",
                    description=f"Face absence was recorded for prolonged duration (Max single: {max_single_absence:.1f}s, Total: {total_absence_duration:.1f}s; Threshold: {settings['face_absence_threshold_sec']}s).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "MEDIUM", "Warning: Prolonged Face Absence", se.description)
                existing_rules.add(rule_name)

        # 4. Evaluate Multiple Persons Detected
        multi_face_events = [e for e in events if e.event_type == "MULTIPLE_FACES_DETECTED"]
        if len(multi_face_events) >= settings["multiple_faces_threshold"]:
            rule_name = "Multiple Persons Detected"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=multi_face_events[-1].id,
                    rule_name=rule_name,
                    severity="HIGH",
                    description=f"Multiple faces were detected in the exam environment ({len(multi_face_events)} occurrences).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "HIGH", "High Risk: Multiple Persons Detected", se.description)
                existing_rules.add(rule_name)

        # 5. Fullscreen Exit Detection
        fullscreen_exits = [e for e in events if e.event_type == "FULLSCREEN_EXIT"]
        if fullscreen_exits:
            rule_name = "Fullscreen Exit Violation"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=fullscreen_exits[-1].id,
                    rule_name=rule_name,
                    severity="MEDIUM",
                    description=f"The exam window exited full-screen exam mode ({len(fullscreen_exits)} occurrences).",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "MEDIUM", "Attention Required: Fullscreen Exit", se.description)
                existing_rules.add(rule_name)

        # 6. Developer Tools or Unauthorized System Actions
        devtools_events = [e for e in events if e.event_type == "DEVTOOLS_OPENED"]
        if devtools_events:
            rule_name = "Developer Tools / Inspection Detected"
            if rule_name not in existing_rules:
                se = SuspiciousEvent(
                    session_id=session_id,
                    event_id=devtools_events[-1].id,
                    rule_name=rule_name,
                    severity="HIGH",
                    description="A browser inspection event was recorded to inspect browser DOM or open debugging console.",
                    timestamp=datetime.now(timezone.utc)
                )
                db.session.add(se)
                detected_suspicious.append(se)
                cls._create_alert_if_not_exists(session_obj, "HIGH", "High Risk: Developer Tools Opened", se.description)
                existing_rules.add(rule_name)

        db.session.commit()
        return detected_suspicious

    @staticmethod
    def _create_alert_if_not_exists(session_obj, severity, title, description):
        """Helper to create an Alert item if one with the same title does not already exist for the session."""
        existing_alert = Alert.query.filter_by(session_id=session_obj.id, title=title).first()
        if not existing_alert:
            alert = Alert(
                session_id=session_obj.id,
                candidate_id=session_obj.candidate_id,
                exam_id=session_obj.exam_id,
                severity=severity,
                title=title,
                description=description,
                status="New",
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(alert)
