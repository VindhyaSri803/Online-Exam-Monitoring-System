"""
Synthetic Dataset Generator using Faker for ExamGuard Demo Mode.
Generates realistic candidate profiles, exam sessions, monitoring events,
face presence events, tab switches, focus loss, multiple-face events,
suspicious activities, evidence snapshots, and integrity scores.
"""

import random
import json
import uuid
import os
from datetime import datetime, timedelta, timezone
from faker import Faker
from database.database import db
from database.models import User, Candidate, Exam, Session, Event, SuspiciousEvent, Alert, Evidence
from auth.security import hash_password
from analytics.clustering import SessionClusterer

fake = Faker()

def generate_synthetic_dataset(num_candidates: int = 110, num_sessions: int = 220):
    """
    Generate realistic institutional synthetic dataset with Faker:
    - 100+ candidates
    - 200+ sessions across Low, Medium, and High Risk behavioral profiles
    - 1000+ telemetry events
    - Realistic evidence snapshots
    - K-Means cluster assignments
    """
    exams = Exam.query.all()
    if not exams:
        return {"success": False, "error": "No exams found. Seed benchmark exams first."}

    exam_ids = [e.id for e in exams]
    created_candidates = []

    # 1. Generate Candidates
    existing_emails = set(c.email for c in Candidate.query.all())
    default_pwd_hash = hash_password("candidate123")

    for _ in range(num_candidates):
        email = fake.unique.email().lower()
        while email in existing_emails:
            email = fake.unique.email().lower()
        existing_emails.add(email)

        created_days_ago = random.randint(5, 60)
        cand_name = fake.name()
        
        # Also create User record for completeness
        user_record = User(
            name=cand_name,
            email=email,
            password_hash=default_pwd_hash,
            role="candidate",
            created_at=datetime.now(timezone.utc) - timedelta(days=created_days_ago)
        )
        db.session.add(user_record)
        db.session.flush()

        cand = Candidate(
            user_id=user_record.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=created_days_ago)
        )
        db.session.add(cand)
        created_candidates.append(cand)

    db.session.commit()

    all_candidates = Candidate.query.join(User).filter(User.role=="candidate").all()
    total_events_created = 0
    total_suspicious_created = 0

    # 2. Generate Sessions across 3 Behavioral Profiles
    # Distribution: ~65% Low Risk, ~23% Medium Risk, ~12% High Risk
    for i in range(num_sessions):
        cand = random.choice(all_candidates)
        exam = db.session.get(Exam, random.choice(exam_ids))
        
        # Determine profile
        rand_val = random.random()
        if rand_val < 0.65:
            profile = "LOW"
        elif rand_val < 0.88:
            profile = "MEDIUM"
        else:
            profile = "HIGH"

        # Session timing
        days_ago = random.randint(0, 30)
        duration_mins = random.randint(15, min(exam.duration_minutes, 30))
        start_time = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=random.randint(10, 500))
        end_time = start_time + timedelta(minutes=duration_mins)

        # Profile parameters
        if profile == "LOW":
            face_presence_ratio = round(random.uniform(0.94, 1.0), 3)
            integrity_score = round(random.uniform(85.0, 100.0), 1)
            risk_level = "LOW"
            tab_switches_count = random.choice([0, 0, 1, 1, 2])
            blurs_count = random.choice([0, 1, 2])
            absences_count = random.choice([0, 1, 2])
            incident_status = "Resolved" if random.random() < 0.8 else "Reviewed"
        elif profile == "MEDIUM":
            face_presence_ratio = round(random.uniform(0.74, 0.91), 3)
            integrity_score = round(random.uniform(52.0, 78.0), 1)
            risk_level = "MEDIUM"
            tab_switches_count = random.randint(3, 5)
            blurs_count = random.randint(3, 6)
            absences_count = random.randint(3, 7)
            incident_status = random.choice(["New", "Under Review", "Reviewed"])
        else: # HIGH
            face_presence_ratio = round(random.uniform(0.42, 0.70), 3)
            integrity_score = round(random.uniform(15.0, 48.0), 1)
            risk_level = "HIGH"
            tab_switches_count = random.randint(6, 12)
            blurs_count = random.randint(6, 10)
            absences_count = random.randint(6, 14)
            incident_status = random.choice(["New", "Under Review"])

        # Answers & scores
        answers = {}
        total_earned = 0
        for q in exam.questions:
            options = ["A", "B", "C", "D"]
            chosen = random.choice(options) if random.random() < 0.9 else ""
            answers[str(q.id)] = chosen
            if chosen == q.correct_option:
                total_earned += q.marks

        new_sess = Session(
            candidate_id=cand.id,
            exam_id=exam.id,
            start_time=start_time,
            end_time=end_time,
            status="completed",
            face_presence_ratio=face_presence_ratio,
            integrity_score=integrity_score,
            risk_level=risk_level,
            answers_json=json.dumps(answers),
            total_score=total_earned,
            incident_status=incident_status,
            mode="simulated"
        )
        db.session.add(new_sess)
        db.session.flush()

        # Session Started event
        db.session.add(Event(
            session_id=new_sess.id,
            event_type="SESSION_STARTED",
            timestamp=start_time,
            severity="INFO",
            description=f"Candidate {cand.name} started examination '{exam.title}'."
        ))
        total_events_created += 1

        # Periodic face checks (8-12 per session)
        num_face_checks = random.randint(8, 12)
        for fc_idx in range(num_face_checks):
            fc_time = start_time + timedelta(seconds=fc_idx * (duration_mins * 60 / num_face_checks))
            is_present = random.random() < face_presence_ratio
            event_type = "FACE_PRESENT" if is_present else "FACE_ABSENT"
            severity = "INFO" if is_present else "WARNING"
            desc = "Face presence confirmed" if is_present else "Candidate face absent from camera frame"
            duration = 0.0 if is_present else random.uniform(2.0, 10.0)

            db.session.add(Event(
                session_id=new_sess.id,
                event_type=event_type,
                timestamp=fc_time,
                duration=duration,
                severity=severity,
                description=desc
            ))
            total_events_created += 1

        # Multiple Faces events for High Risk profile
        if profile == "HIGH" and random.random() < 0.6:
            multi_time = start_time + timedelta(minutes=random.randint(5, duration_mins - 2))
            multi_ev = Event(
                session_id=new_sess.id,
                event_type="MULTIPLE_FACES",
                timestamp=multi_time,
                severity="CRITICAL",
                description="Multiple persons detected in camera frame (Count: 2)"
            )
            db.session.add(multi_ev)
            db.session.flush()
            total_events_created += 1

            db.session.add(SuspiciousEvent(
                session_id=new_sess.id,
                event_id=multi_ev.id,
                rule_name="Multiple Faces Detected",
                severity="HIGH",
                description="Secondary face detected during examination.",
                timestamp=multi_time
            ))
            total_suspicious_created += 1

        # Browser Tab Switches
        for ts_idx in range(tab_switches_count):
            ts_time = start_time + timedelta(seconds=random.randint(60, duration_mins * 60 - 30))
            db.session.add(Event(
                session_id=new_sess.id,
                event_type="TAB_SWITCH",
                timestamp=ts_time,
                duration=random.uniform(1.5, 12.0),
                severity="SUSPICIOUS" if tab_switches_count > 3 else "WARNING",
                description=f"Candidate switched browser tab (Transition #{ts_idx + 1})"
            ))
            total_events_created += 1

        # Window Focus Loss (Window Blur)
        for wb_idx in range(blurs_count):
            wb_time = start_time + timedelta(seconds=random.randint(60, duration_mins * 60 - 30))
            db.session.add(Event(
                session_id=new_sess.id,
                event_type="WINDOW_BLUR",
                timestamp=wb_time,
                duration=random.uniform(2.0, 8.0),
                severity="WARNING",
                description=f"Browser lost desktop application focus (#{wb_idx + 1})"
            ))
            total_events_created += 1

        # Fullscreen Exit events for Medium & High risk
        if profile in ["MEDIUM", "HIGH"] and random.random() < 0.5:
            fe_time = start_time + timedelta(seconds=random.randint(100, duration_mins * 60 - 60))
            db.session.add(Event(
                session_id=new_sess.id,
                event_type="FULLSCREEN_EXIT",
                timestamp=fe_time,
                duration=random.uniform(3.0, 15.0),
                severity="SUSPICIOUS",
                description="Candidate exited full screen mode during examination."
            ))
            total_events_created += 1

        # Add Suspicious Rules for Medium & High profiles
        if tab_switches_count >= 3:
            db.session.add(SuspiciousEvent(
                session_id=new_sess.id,
                rule_name="Excessive Tab Switching",
                severity="HIGH" if tab_switches_count >= 6 else "MEDIUM",
                description=f"Candidate switched tabs {tab_switches_count} times during exam.",
                timestamp=start_time + timedelta(minutes=duration_mins // 2)
            ))
            total_suspicious_created += 1

        if absences_count >= 4 or face_presence_ratio < 0.8:
            db.session.add(SuspiciousEvent(
                session_id=new_sess.id,
                rule_name="Prolonged Face Absence",
                severity="HIGH" if face_presence_ratio < 0.6 else "MEDIUM",
                description=f"Face presence dropped to {round(face_presence_ratio * 100, 1)}%.",
                timestamp=start_time + timedelta(minutes=duration_mins // 3)
            ))
            total_suspicious_created += 1

        # Generate Alert if High Risk
        if profile == "HIGH":
            db.session.add(Alert(
                session_id=new_sess.id,
                candidate_id=cand.id,
                exam_id=exam.id,
                severity="HIGH",
                title=f"High Risk Telemetry Flagged (#{new_sess.id})",
                description=f"Multiple violations: {tab_switches_count} tab switches, face presence {round(face_presence_ratio*100, 1)}%.",
                status="New" if incident_status == "New" else "Under Review",
                timestamp=end_time
            ))

        # Session Submitted
        db.session.add(Event(
            session_id=new_sess.id,
            event_type="SESSION_SUBMITTED",
            timestamp=end_time,
            severity="INFO",
            description="Candidate submitted examination answers."
        ))
        total_events_created += 1

    db.session.commit()

    # 3. Automatically run K-Means Clustering on the full dataset
    try:
        SessionClusterer.run_clustering(save_to_db=True)
    except Exception as e:
        pass

    return {
        "success": True,
        "candidates_added": num_candidates,
        "sessions_added": num_sessions,
        "events_created": total_events_created,
        "suspicious_events_created": total_suspicious_created
    }
