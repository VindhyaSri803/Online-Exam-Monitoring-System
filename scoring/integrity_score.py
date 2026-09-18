from typing import List, Dict, Any
import pandas as pd
from database.database import db
from database.models import Event, SuspiciousEvent
from config import (
    WEIGHT_FACE_ABSENCE, WEIGHT_MULTIPLE_FACES, WEIGHT_TAB_SWITCH,
    WEIGHT_FOCUS_LOSS, WEIGHT_FULLSCREEN_EXIT, LOW_RISK_MIN, MEDIUM_RISK_MIN
)

class IntegrityScorer:
    @staticmethod
    def get_scoring_weights():
        return {
            "weight_face_absence": float(WEIGHT_FACE_ABSENCE),
            "weight_multiple_faces": float(WEIGHT_MULTIPLE_FACES),
            "weight_tab_switch": float(WEIGHT_TAB_SWITCH),
            "weight_focus_loss": float(WEIGHT_FOCUS_LOSS),
            "weight_fullscreen_exit": float(WEIGHT_FULLSCREEN_EXIT),
            "low_risk_min_score": float(LOW_RISK_MIN),
            "medium_risk_min_score": float(MEDIUM_RISK_MIN),
        }

    @classmethod
    def calculate_session_integrity(cls, session_id: int, events: List[Event] = None,
                                    face_presence_ratio: float = None) -> Dict[str, Any]:
        weights = cls.get_scoring_weights()
        events = events if events is not None else Event.query.filter_by(session_id=session_id).all()
        df = pd.DataFrame([{
            "event_type": e.event_type, "severity": e.severity, "duration": e.duration or 0.0
        } for e in events])

        if face_presence_ratio is None:
            frames = df[df.event_type.isin(["FACE_PRESENT", "FACE_ABSENT", "MULTIPLE_FACES_DETECTED"])] if not df.empty else df
            calculated_ratio = (len(frames[frames.event_type == "FACE_PRESENT"]) / len(frames)) if len(frames) else 1.0
        else:
            calculated_ratio = float(face_presence_ratio)
        calculated_ratio = max(0.0, min(1.0, calculated_ratio))

        count = lambda t: int((df.event_type == t).sum()) if not df.empty else 0
        face_absent = count("FACE_ABSENT")
        multi = count("MULTIPLE_FACES_DETECTED")
        tabs = count("TAB_SWITCH")
        blur = count("WINDOW_BLUR")
        fullscreen = count("FULLSCREEN_EXIT")

        # Each configured weight is expressed in risk points. Face absence is
        # proportional to the fraction of monitored time without a face.
        penalty_face = round((1.0 - calculated_ratio) * weights["weight_face_absence"], 2)
        penalty_multi = round(multi * weights["weight_multiple_faces"], 2)
        penalty_tab = round(tabs * weights["weight_tab_switch"], 2)
        penalty_blur = round(blur * weights["weight_focus_loss"], 2)
        penalty_fs = round(fullscreen * weights["weight_fullscreen_exit"], 2)

        suspicious = SuspiciousEvent.query.filter_by(session_id=session_id).all()
        # Suspicious rule rows are informational flags; do not double-charge
        # events already represented by the explicit configurable weights.
        other = [s for s in suspicious if s.rule_name not in {
            "Frequent Tab Switching", "Excessive Tab Switching (High Risk)",
            "Repeated Window Focus Loss", "Prolonged Face Absence",
            "Multiple Persons Detected", "Fullscreen Exit Violation"
        }]
        penalty_other = min(100.0, sum({"HIGH": 20.0, "MEDIUM": 10.0, "LOW": 5.0}.get(s.severity, 0.0) for s in other))

        total = penalty_face + penalty_multi + penalty_tab + penalty_blur + penalty_fs + penalty_other
        normalized = max(0.0, min(100.0, total))
        score = round(max(0.0, min(100.0, 100.0 - normalized)), 1)
        risk = "LOW" if score >= weights["low_risk_min_score"] else ("MEDIUM" if score >= weights["medium_risk_min_score"] else "HIGH")

        penalties = {
            "face_absence": penalty_face, "multiple_faces": penalty_multi,
            "tab_switch": penalty_tab, "window_blur": penalty_blur,
            "fullscreen_exit": penalty_fs, "suspicious_events": penalty_other,
            "total_penalty": round(normalized, 2)
        }
        deductions = []
        labels = [
            ("face_absence", "Face absence"),
            ("multiple_faces", "Multiple faces"),
            ("tab_switch", "Tab switching"),
            ("window_blur", "Focus loss"),
            ("fullscreen_exit", "Fullscreen exit"),
            ("suspicious_events", "Other rule indicators"),
        ]
        for key, label in labels:
            if penalties[key] > 0:
                deductions.append(f"-{penalties[key]} pts: {label}")
        if not deductions:
            deductions.append("No configured risk indicators were recorded.")

        return {
            "integrity_score": score, "risk_level": risk,
            "face_presence_ratio": round(calculated_ratio, 3),
            "total_risk_points": round(total, 2),
            "normalized_risk_points": round(normalized, 2),
            "penalties": penalties,
            "event_counts": {
                "tab_switches": tabs, "window_blurs": blur,
                "multiple_faces": multi, "fullscreen_exits": fullscreen,
                "suspicious_events": len(suspicious),
                "face_absent_count": face_absent, "total_events": len(events)
            },
            "deductions_explanation": deductions
        }
