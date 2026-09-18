"""
Export Module for ExamGuard.
Generates CSV and JSON exports of session data, monitoring events,
integrity scores, risk classifications, and cluster assignments.
"""

import io
import csv
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from database.database import db
from database.models import Candidate, Exam, Session, Event, SuspiciousEvent, Report

class DataExporter:
    """Institutional Data Exporter for Compliance, Auditing, and Analysis."""

    @staticmethod
    def export_sessions_csv(exam_id: Optional[int] = None) -> io.StringIO:
        """
        Export all sessions data into CSV format:
        Session ID, Candidate Name, Candidate Email, Exam Title, Start Time, End Time,
        Face Presence Ratio, Integrity Score, Risk Level, Cluster Label, Suspicious Events Count, Status.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.order_by(Session.start_time.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Session ID",
            "Candidate ID",
            "Candidate Name",
            "Candidate Email",
            "Exam Title",
            "Start Time (UTC)",
            "End Time (UTC)",
            "Face Presence Ratio",
            "Integrity Score",
            "Risk Level",
            "Cluster Label",
            "Suspicious Events Count",
            "Evidence Count",
            "Incident Status",
            "Assessment Score",
            "Session Status"
        ])

        for s in sessions:
            writer.writerow([
                s.id,
                s.candidate_id,
                s.candidate.name if s.candidate else "N/A",
                s.candidate.email if s.candidate else "N/A",
                s.exam.title if s.exam else "N/A",
                s.start_time.strftime("%Y-%m-%d %H:%M:%S") if s.start_time else "",
                s.end_time.strftime("%Y-%m-%d %H:%M:%S") if s.end_time else "",
                round(s.face_presence_ratio or 1.0, 3),
                round(s.integrity_score or 100.0, 1),
                s.risk_level,
                s.cluster_label or "Unassigned",
                len(s.suspicious_events) if s.suspicious_events else 0,
                len(s.evidence) if s.evidence else 0,
                s.incident_status,
                s.total_score,
                s.status
            ])

        output.seek(0)
        return output

    @staticmethod
    def export_events_csv(session_id: Optional[int] = None) -> io.StringIO:
        """
        Export telemetry and monitoring events into CSV format.
        """
        query = Event.query
        if session_id:
            query = query.filter_by(session_id=session_id)
        events = query.order_by(Event.timestamp.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Event ID",
            "Session ID",
            "Candidate Name",
            "Event Type",
            "Timestamp (UTC)",
            "Duration (Seconds)",
            "Severity",
            "Description"
        ])

        for ev in events:
            cand_name = ev.session.candidate.name if ev.session and ev.session.candidate else "N/A"
            writer.writerow([
                ev.id,
                ev.session_id,
                cand_name,
                ev.event_type,
                ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp else "",
                round(ev.duration or 0.0, 2),
                ev.severity,
                ev.description
            ])

        output.seek(0)
        return output

    @staticmethod
    def export_dataset_json(exam_id: Optional[int] = None) -> str:
        """
        Export complete examination monitoring telemetry, integrity scores,
        and cluster assignments in structured JSON format.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.order_by(Session.start_time.desc()).all()

        data = {
            "platform": "ExamGuard",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_sessions": len(sessions),
            "sessions": []
        }

        for s in sessions:
            session_dict = {
                "session_id": s.id,
                "candidate": {
                    "id": s.candidate_id,
                    "name": s.candidate.name if s.candidate else None,
                    "email": s.candidate.email if s.candidate else None
                },
                "exam": {
                    "id": s.exam_id,
                    "title": s.exam.title if s.exam else None
                },
                "timeline": {
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None
                },
                "integrity_metrics": {
                    "integrity_score": round(s.integrity_score or 100.0, 1),
                    "risk_level": s.risk_level,
                    "face_presence_ratio": round(s.face_presence_ratio or 1.0, 3),
                    "cluster_label": s.cluster_label,
                    "incident_status": s.incident_status
                },
                "suspicious_events": [
                    {
                        "rule": se.rule_name,
                        "severity": se.severity,
                        "description": se.description,
                        "timestamp": se.timestamp.isoformat() if se.timestamp else None
                    } for se in (s.suspicious_events or [])
                ],
                "telemetry_events_count": len(s.events) if s.events else 0,
                "evidence_count": len(s.evidence) if s.evidence else 0
            }
            data["sessions"].append(session_dict)

        return json.dumps(data, indent=2)

    @staticmethod
    def export_session_report(session_id: int) -> Dict[str, Any]:
        """
        Export comprehensive single-session audit package.
        """
        s = db.session.get(Session, session_id)
        if not s:
            raise ValueError(f"Session {session_id} not found.")

        report = Report.query.filter_by(session_id=session_id).order_by(Report.generated_at.desc()).first()

        return {
            "session_id": s.id,
            "candidate": s.candidate.name if s.candidate else "N/A",
            "email": s.candidate.email if s.candidate else "N/A",
            "exam": s.exam.title if s.exam else "N/A",
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "integrity_score": round(s.integrity_score or 100.0, 1),
            "risk_level": s.risk_level,
            "face_presence_ratio": round(s.face_presence_ratio or 1.0, 3),
            "cluster_label": s.cluster_label,
            "incident_status": s.incident_status,
            "ai_report_text": report.report_text if report else "No AI report generated.",
            "suspicious_events": [se.to_dict() for se in (s.suspicious_events or [])],
            "events_count": len(s.events) if s.events else 0,
            "evidence_count": len(s.evidence) if s.evidence else 0
        }
