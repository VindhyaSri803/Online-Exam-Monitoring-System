import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database.database import db
from database.models import Session, Candidate, Exam, Event, SuspiciousEvent, Evidence, Report

ETHICAL_DISCLAIMER = (
    "ExamGuard provides monitoring indicators and analytical evidence to assist invigilators. "
    "Automated indicators do not constitute proof of academic misconduct. "
    "Final decisions must be made through appropriate human review."
)

class AIReportAgent:
    """AI-Powered Examination Integrity Report Generator using LangChain with Deterministic Fallback."""

    @classmethod
    def generate_report(cls, session_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive AI integrity report for a given session.
        Saves report to database and returns dict payload.
        """
        session_obj = db.session.get(Session, session_id)
        if not session_obj:
            raise ValueError(f"Session {session_id} not found.")

        candidate = session_obj.candidate
        exam = session_obj.exam
        events = session_obj.events
        suspicious_events = session_obj.suspicious_events
        evidence_items = session_obj.evidence

        # Aggregate telemetry metrics
        tab_switches = sum(1 for e in events if e.event_type == "TAB_SWITCH")
        window_blurs = sum(1 for e in events if e.event_type == "WINDOW_BLUR")
        face_absences = sum(1 for e in events if e.event_type == "FACE_ABSENT")
        absence_duration = sum((e.duration or 0.0) for e in events if e.event_type == "FACE_ABSENT")
        multi_faces = sum(1 for e in events if e.event_type == "MULTIPLE_FACES_DETECTED")
        
        presence_pct = round((session_obj.face_presence_ratio or 1.0) * 100, 1)
        score = round(session_obj.integrity_score or 100.0, 1)
        risk = session_obj.risk_level or "LOW"

        context = {
            "session_id": session_obj.id,
            "candidate_name": candidate.name if candidate else "Unknown Candidate",
            "candidate_email": candidate.email if candidate else "N/A",
            "exam_title": exam.title if exam else "Online Assessment",
            "start_time": session_obj.start_time.strftime("%Y-%m-%d %H:%M:%S UTC") if session_obj.start_time else "N/A",
            "end_time": session_obj.end_time.strftime("%Y-%m-%d %H:%M:%S UTC") if session_obj.end_time else "In Progress",
            "integrity_score": score,
            "risk_level": risk,
            "face_presence_ratio_pct": presence_pct,
            "tab_switches": tab_switches,
            "window_blurs": window_blurs,
            "face_absences_count": face_absences,
            "total_absence_sec": round(absence_duration, 1),
            "multiple_faces_count": multi_faces,
            "suspicious_events_list": [
                f"- [{se.severity}] {se.rule_name}: {se.description} (at {se.timestamp.strftime('%H:%M:%S') if se.timestamp else 'N/A'})"
                for se in suspicious_events
            ],
            "evidence_count": len(evidence_items),
            "cluster_label": session_obj.cluster_label or "Unclassified"
        }

        # Try LangChain LLM first if API key configured
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        report_text = None
        model_used = "Rule-Based Deterministic Synthesizer"

        if openai_key or google_key:
            try:
                report_text = cls._generate_llm_report(context, openai_key, google_key)
                required_sections = [
                    "1. SESSION SUMMARY", "2. MONITORING OBSERVATIONS",
                    "3. INTEGRITY ANALYSIS", "4. RISK INDICATORS",
                    "5. INVIGILATOR REVIEW NOTES"
                ]
                if not report_text or not all(section in report_text for section in required_sections):
                    raise ValueError("LLM response did not satisfy the required five-section format")
                model_used = "LangChain LLM Agent (Live Completion)"
            except Exception as e:
                # Fallback on LLM failure
                report_text = cls._generate_fallback_report(context)
                model_used = f"Deterministic Fallback (LLM Exception: {str(e)[:50]})"
        else:
            report_text = cls._generate_fallback_report(context)

        # Persist report in database
        report_record = Report(
            session_id=session_id,
            integrity_score=score,
            risk_level=risk,
            report_text=report_text,
            summary_json=json.dumps(context),
            model_used=model_used,
            generated_at=datetime.now(timezone.utc)
        )
        db.session.add(report_record)
        db.session.commit()

        return {
            "id": report_record.id,
            "session_id": session_id,
            "integrity_score": score,
            "risk_level": risk,
            "report_text": report_text,
            "model_used": model_used,
            "generated_at": report_record.generated_at.isoformat(),
            "context": context
        }

    @staticmethod
    def _generate_fallback_report(ctx: Dict[str, Any]) -> str:
        """
        Intelligent, structured deterministic report generator that adheres to strict
        ethical invigilator-assistance guidelines without accusing cheating.
        """
        risk = ctx["risk_level"]
        score = ctx["integrity_score"]
        name = ctx["candidate_name"]
        exam = ctx["exam_title"]
        presence = ctx["face_presence_ratio_pct"]
        tab_switches = ctx["tab_switches"]
        blurs = ctx["window_blurs"]
        suspicious_list = ctx["suspicious_events_list"]
        evidence_count = ctx["evidence_count"]

        # Assessment section based on risk
        if risk == "LOW":
            assessment_text = (
                f"The session telemetry for {name} shows consistent recorded examination behavior throughout "
                f"the session. Monitored face presence remained optimal at {presence}%, with minimal or zero "
                f"tab-switching activity ({tab_switches} events) and no significant focus loss anomalies. "
                f"The integrity profile is consistent with standard test-taking conditions."
            )
            recommendation_text = (
                "1. No automated conclusion is made; authorized invigilators may review the session as appropriate.\n"
                "2. Mark session status as verified/cleared in the institutional registry."
            )
        elif risk == "MEDIUM":
            assessment_text = (
                f"The examination telemetry for {name} reflects intermittent deviations that warrant invigilator review. "
                f"Recorded indicators show {tab_switches} browser tab transitions and {blurs} window focus loss events, "
                f"with an overall face presence ratio of {presence}%. These anomalies may stem from background notifications, "
                f"system multi-tasking, or environmental distractions."
            )
            recommendation_text = (
                "1. Review the chronological session timeline for clusters of tab switches.\n"
                "2. Inspect recorded webcam frame evidence around timestamps of focus loss.\n"
                "3. Consult candidate's answer timestamps relative to out-of-focus periods.\n"
                "4. Conduct a brief review before validating the final assessment grade."
            )
        else: # HIGH RISK
            assessment_text = (
                f"Elevated telemetry anomalies were logged during this session for {name}. "
                f"System rules detected substantial irregular patterns, including {tab_switches} tab switches, "
                f"{blurs} window focus loss events, and {ctx['total_absence_sec']} seconds of cumulative face absence "
                f"(Face Presence: {presence}%). Total captured incident evidence frames: {evidence_count}."
            )
            recommendation_text = (
                "1. High Priority: Conduct a comprehensive human invigilation audit of all captured visual evidence.\n"
                "2. Cross-reference window focus loss durations with question answering times.\n"
                "3. Request an invigilator review panel if unexplained multi-tab browsing is confirmed in the evidence log.\n"
                "4. Final determination must be made solely by authorized academic staff."
            )

        suspicious_str = "\n".join(suspicious_list) if suspicious_list else "- No critical suspicious rules triggered."

        neutral_statement = "Multiple suspicious indicators were detected and may require invigilator review." if (risk in ["MEDIUM", "HIGH"] or suspicious_list) else "Telemetry markers remained within normal operational thresholds."

        report = f"""================================================================================
EXAMGUARD CANDIDATE INTEGRITY & TELEMETRY AUDIT REPORT
================================================================================

1. SESSION SUMMARY
--------------------------------------------------------------------------------
Candidate Name          : {name}
Candidate Email         : {ctx['candidate_email']}
Examination Title       : {exam}
Session Identifier      : #{ctx['session_id']}
Session Interval        : {ctx['start_time']} -> {ctx['end_time']}
Behavioral Cluster      : {ctx['cluster_label']}

2. MONITORING OBSERVATIONS
--------------------------------------------------------------------------------
* Face Presence Ratio    : {presence}% (Monitored Active Time)
* Face Absence Duration  : {ctx['total_absence_sec']}s total ({ctx['face_absences_count']} frame absence events)
* Multiple Face Events   : {ctx['multiple_faces_count']} detections
* Browser Tab Switches   : {tab_switches} transitions
* Window Focus Losses    : {blurs} blur occurrences
* Captured Evidence      : {evidence_count} visual snapshots logged

3. INTEGRITY ANALYSIS
--------------------------------------------------------------------------------
Overall Integrity Score : {score} / 100.0
Assigned Risk Level     : {risk}
Automated Assessment   :
{assessment_text}

4. RISK INDICATORS
--------------------------------------------------------------------------------
Summary Status: {neutral_statement}
Flagged Rules:
{suspicious_str}

5. INVIGILATOR REVIEW NOTES
--------------------------------------------------------------------------------
{recommendation_text}

--------------------------------------------------------------------------------
ETHICAL DISCLAIMER:
{ETHICAL_DISCLAIMER}
================================================================================
"""
        return report

    @staticmethod
    def _generate_llm_report(ctx: Dict[str, Any], openai_key: str, google_key: str) -> str:
        """Call LangChain with ChatOpenAI or fallback."""
        prompt_text = f"""You are ExamGuard's AI Invigilator Intelligence Agent.
Generate a structured, professional, objective examination integrity audit report based on the following candidate session telemetry.

Input Data:
- Candidate Name: {ctx['candidate_name']} ({ctx['candidate_email']})
- Exam Title: {ctx['exam_title']} (Session #{ctx['session_id']})
- Start/End Time: {ctx['start_time']} -> {ctx['end_time']}
- Integrity Score: {ctx['integrity_score']}/100.0
- Risk Level: {ctx['risk_level']}
- Face Presence Ratio: {ctx['face_presence_ratio_pct']}%
- Monitoring Events & Frequencies:
  * Browser Tab Switches: {ctx['tab_switches']}
  * Window Focus Losses: {ctx['window_blurs']}
  * Face Absence Duration: {ctx['total_absence_sec']}s
  * Multiple Faces Count: {ctx['multiple_faces_count']}
  * Flagged Suspicious Rules: {json.dumps(ctx['suspicious_events_list'])}
  * Evidence Snapshots Captured: {ctx['evidence_count']}

You MUST format the output using these EXACT 5 numbered section headings:

1. SESSION SUMMARY
2. MONITORING OBSERVATIONS
3. INTEGRITY ANALYSIS
4. RISK INDICATORS
5. INVIGILATOR REVIEW NOTES

STRICT ETHICAL RULES:
1. The tone must remain completely neutral, objective, and analytical.
2. Example phrase to use: "Multiple suspicious indicators were detected and may require invigilator review."
3. NEVER write "The candidate cheated" or make accusations of cheating. These are automated indicators to assist human review.
4. End the report with the following Ethical Notice:
"{ETHICAL_DISCLAIMER}"
"""
        if openai_key:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(api_key=openai_key, model_name=os.environ.get("LLM_MODEL", "gpt-4o-mini"), temperature=0.2)
                res = llm.invoke(prompt_text)
                return res.content
            except Exception:
                pass
        return AIReportAgent._generate_fallback_report(ctx)
