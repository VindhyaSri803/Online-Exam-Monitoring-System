import pandas as pd
import numpy as np
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from database.database import db
from database.models import User, Candidate, Exam, Session, Event, SuspiciousEvent, Alert

class AnalyticsEngine:
    """Institutional Analytics Engine for ExamGuard."""

    @staticmethod
    def get_dashboard_kpis(exam_id: Optional[int] = None) -> Dict[str, Any]:
        """Compute high-level executive KPI cards."""
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)

        sessions = query.all()
        total_sessions = len(sessions)
        total_candidates = Candidate.query.join(User).filter(User.role=="candidate").count()
        active_sessions = sum(1 for s in sessions if s.status == "in_progress")
        completed_sessions = sum(1 for s in sessions if s.status == "completed")

        if total_sessions > 0:
            avg_score = round(sum((s.integrity_score or 100.0) for s in sessions) / total_sessions, 1)
            low_risk = sum(1 for s in sessions if s.risk_level == "LOW")
            med_risk = sum(1 for s in sessions if s.risk_level == "MEDIUM")
            high_risk = sum(1 for s in sessions if s.risk_level == "HIGH")
            avg_face_presence = round(sum((s.face_presence_ratio or 1.0) for s in sessions) / total_sessions * 100, 1)
        else:
            avg_score = 100.0
            low_risk = med_risk = high_risk = 0
            avg_face_presence = 100.0

        active_exams = Exam.query.filter_by(status="active").count()
        attention_required = med_risk + unresolved_alerts

        return {
            "total_candidates": total_candidates,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "active_exams": active_exams,
            "completed_sessions": completed_sessions,
            "average_integrity_score": avg_score,
            "average_face_presence_pct": avg_face_presence,
            "attention_required": attention_required,
            "low_risk_count": low_risk,
            "medium_risk_count": med_risk,
            "high_risk_count": high_risk,
            "high_risk_sessions": high_risk,
            "low_risk_pct": round(low_risk / max(1, total_sessions) * 100, 1),
            "med_risk_pct": round(med_risk / max(1, total_sessions) * 100, 1),
            "high_risk_pct": round(high_risk / max(1, total_sessions) * 100, 1),
            "total_suspicious_events": total_suspicious,
            "unresolved_alerts": unresolved_alerts,
        }

    @staticmethod
    def get_chart_data(exam_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate structured datasets for all 6 core dashboard visualizations.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.all()

        if not sessions:
            return {
                "chart1_score_dist": {"labels": ["0-20", "21-40", "41-60", "61-80", "81-100"], "data": [0, 0, 0, 0, 0]},
                "chart2_risk_dist": {"labels": ["Low Risk", "Medium Risk", "High Risk"], "data": [0, 0, 0]},
                "chart3_event_freq": {"labels": [], "data": []},
                "chart4_face_presence": {"labels": ["<50%", "50-70%", "70-85%", "85-95%", "95-100%"], "data": [0, 0, 0, 0, 0]},
                "chart5_suspicious_heatmap": {"rules": [], "exams": [], "matrix": []},
                "chart6_scatter": []
            }

        scores = [s.integrity_score or 100.0 for s in sessions]
        presence_ratios = [(s.face_presence_ratio or 1.0) * 100 for s in sessions]

        # Chart 1: Integrity Score Distribution
        score_bins = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
        for sc in scores:
            if sc <= 20: score_bins[0] += 1
            elif sc <= 40: score_bins[1] += 1
            elif sc <= 60: score_bins[2] += 1
            elif sc <= 80: score_bins[3] += 1
            else: score_bins[4] += 1

        chart1 = {
            "labels": ["0-20 (Critical)", "21-40 (High Risk)", "41-60 (Medium-High)", "61-80 (Medium)", "81-100 (Optimal)"],
            "data": score_bins
        }

        # Chart 2: Risk-level Distribution
        low_c = sum(1 for s in sessions if s.risk_level == "LOW")
        med_c = sum(1 for s in sessions if s.risk_level == "MEDIUM")
        high_c = sum(1 for s in sessions if s.risk_level == "HIGH")
        chart2 = {
            "labels": ["Low Risk", "Medium Risk", "High Risk"],
            "data": [low_c, med_c, high_c]
        }

        # Chart 3: Event Frequency Breakdown
        event_counts_query = db.session.query(
            Event.event_type, func.count(Event.id)
        ).group_by(Event.event_type).order_by(func.count(Event.id).desc()).all()
        
        chart3 = {
            "labels": [e[0].replace("_", " ").title() for e in event_counts_query],
            "data": [e[1] for e in event_counts_query]
        }

        # Chart 4: Face Presence Ratio Distribution
        presence_bins = [0, 0, 0, 0, 0]
        for p in presence_ratios:
            if p < 50: presence_bins[0] += 1
            elif p < 70: presence_bins[1] += 1
            elif p < 85: presence_bins[2] += 1
            elif p < 95: presence_bins[3] += 1
            else: presence_bins[4] += 1

        chart4 = {
            "labels": ["< 50%", "50% - 69%", "70% - 84%", "85% - 94%", "95% - 100%"],
            "data": presence_bins
        }

        # Chart 5: Suspicious Event Rule Breakdown / Heatmap
        suspicious_rules = db.session.query(
            SuspiciousEvent.rule_name, func.count(SuspiciousEvent.id)
        ).group_by(SuspiciousEvent.rule_name).order_by(func.count(SuspiciousEvent.id).desc()).all()

        chart5 = {
            "rules": [r[0] for r in suspicious_rules],
            "counts": [r[1] for r in suspicious_rules]
        }

        # Chart 6: Integrity Score vs Suspicious Events (Scatter)
        scatter_points = []
        for s in sessions:
            scatter_points.append({
                "x": len(s.suspicious_events),
                "y": round(s.integrity_score or 100.0, 1),
                "id": s.id,
                "candidate": s.candidate.name if s.candidate else f"ID #{s.candidate_id}",
                "risk": s.risk_level
            })

        return {
            "chart1_score_dist": chart1,
            "chart2_risk_dist": chart2,
            "chart3_event_freq": chart3,
            "chart4_face_presence": chart4,
            "chart5_suspicious_heatmap": chart5,
            "chart6_scatter": scatter_points
        }
