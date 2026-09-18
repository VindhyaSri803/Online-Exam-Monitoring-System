import random
import json
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
    - 200+ sessions
    - 1000+ events across Low, Medium, and High Risk behavioral profiles.
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
        user_record = User(name=fake.name(), email=email, password_hash=default_pwd_hash, role="candidate",
                           created_at=datetime.now(timezone.utc) - timedelta(days=created_days_ago))
        db.session.add(user_record)
        db.session.flush()
        cand = Candidate(user_id=user_record.id,
                         created_at=datetime.now(timezone.utc) - timedelta(days=created_days_ago))
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

        # Test answers & test score
        questions = exam.questions
        answers_dict = {}
        earned_score = 0
        for q in questions:
            chosen = random.choice(["A", "B", "C", "D"])
            answers_dict[str(q.id)] = chosen
            if chosen == q.correct_option:
                earned_score += q.marks

        # Create Session record
        sess = Session(
            candidate_id=cand.id,
            exam_id=exam.id,
            start_time=start_time,
            end_time=end_time,
            status="completed",
            face_presence_ratio=face_presence_ratio,
            integrity_score=integrity_score,
            risk_level=risk_level,
            answers_json=json.dumps(answers_dict),
            total_score=earned_score,
            incident_status=incident_status,
            mode="simulated"
        )
        db.session.add(sess)
        db.session.flush()

        # 3. Generate Fine-Grained Chronological Events for this Session
        curr_t = start_time
        # Session Started
        db.session.add(Event(
            session_id=sess.id,
            event_type="SESSION_STARTED",
            timestamp=curr_t,
            severity="INFO",
            description=f"Candidate began examination session for '{exam.title}'."
        ))
        total_events_created += 1

        # Periodic Face telemetry markers
        num_frame_checks = random.randint(8, 16)
        interval_secs = (duration_mins * 60) / num_frame_checks

        for frame_idx in range(num_frame_checks):
            curr_t = start_time + timedelta(seconds=interval_secs * (frame_idx + 1))
            is_present = random.random() < face_presence_ratio
            if is_present:
                db.session.add(Event(
                    session_id=sess.id,
                    event_type="FACE_PRESENT",
                    timestamp=curr_t,
                    severity="INFO",
                    description="Candidate face present and verified."
                ))
            else:
                db.session.add(Event(
                    session_id=sess.id,
                    event_type="FACE_ABSENT",
                    timestamp=curr_t,
                    duration=random.uniform(4.0, 14.0) if profile != "LOW" else random.uniform(1.0, 3.0),
                    severity="WARNING",
                    description="Face absent from webcam field of view."
                ))
            total_events_created += 1

        # Browser Tab Switches
        for ts_idx in range(tab_switches_count):
            t_offset = random.randint(60, max(120, duration_mins * 60 - 60))
            ts_time = start_time + timedelta(seconds=t_offset)
            e_tab = Event(
                session_id=sess.id,
                event_type="TAB_SWITCH",
                timestamp=ts_time,
                duration=random.uniform(3.0, 25.0),
                severity="SUSPICIOUS",
                description="Candidate switched browser tabs."
            )
            db.session.add(e_tab)
            total_events_created += 1

        # Window Blurs & Focus
        for wb_idx in range(blurs_count):
            t_offset = random.randint(60, max(120, duration_mins * 60 - 60))
            wb_time = start_time + timedelta(seconds=t_offset)
            e_blur = Event(
                session_id=sess.id,
                event_type="WINDOW_BLUR",
                timestamp=wb_time,
                duration=random.uniform(2.0, 15.0),
                severity="WARNING",
                description="Exam window lost operating system focus."
            )
            db.session.add(e_blur)
            total_events_created += 1

        # Session Submitted Event
        db.session.add(Event(
            session_id=sess.id,
            event_type="SESSION_SUBMITTED",
            timestamp=end_time,
            severity="INFO",
            description="Candidate submitted examination answers."
        ))
        total_events_created += 1

        # 4. Generate Suspicious Events & Alerts according to profile
        if profile == "HIGH":
            se1 = SuspiciousEvent(
                session_id=sess.id,
                rule_name="Excessive Tab Switching (High Risk)",
                severity="HIGH",
                description=f"Candidate switched tabs {tab_switches_count} times, exceeding high-risk threshold (6).",
                timestamp=start_time + timedelta(minutes=random.randint(5, 12))
            )
            db.session.add(se1)
            total_suspicious_created += 1

            if absences_count >= 5:
                se2 = SuspiciousEvent(
                    session_id=sess.id,
                    rule_name="Prolonged Face Absence",
                    severity="MEDIUM",
                    description=f"Candidate face was absent for prolonged periods (Face presence ratio: {face_presence_ratio*100:.1f}%).",
                    timestamp=start_time + timedelta(minutes=random.randint(8, 14))
                )
                db.session.add(se2)
                total_suspicious_created += 1

            # High Risk Alert
            db.session.add(Alert(
                session_id=sess.id,
                candidate_id=cand.id,
                exam_id=exam.id,
                severity="HIGH",
                title=f"High Risk Alert: Multiple Telemetry Violations (#{sess.id})",
                description=f"Candidate {cand.name} incurred {tab_switches_count} tab switches and {absences_count} face absent events.",
                status=incident_status,
                timestamp=start_time + timedelta(minutes=random.randint(10, 15))
            ))

        elif profile == "MEDIUM":
            if tab_switches_count >= 3:
                se = SuspiciousEvent(
                    session_id=sess.id,
                    rule_name="Frequent Tab Switching",
                    severity="MEDIUM",
                    description=f"Candidate switched tabs {tab_switches_count} times during exam.",
                    timestamp=start_time + timedelta(minutes=random.randint(5, 12))
                )
                db.session.add(se)
                total_suspicious_created += 1

                db.session.add(Alert(
                    session_id=sess.id,
                    candidate_id=cand.id,
                    exam_id=exam.id,
                    severity="MEDIUM",
                    title=f"Warning: Frequent Tab Switching (#{sess.id})",
                    description=f"Candidate {cand.name} switched browser tabs {tab_switches_count} times.",
                    status=incident_status,
                    timestamp=start_time + timedelta(minutes=10)
                ))

    db.session.commit()

    # 5. Run KMeans clustering to categorize all sessions
    try:
        SessionClusterer.run_clustering(save_to_db=True)
    except Exception as e:
        print(f"Error updating KMeans clusters: {e}")

    return {
        "success": True,
        "candidates_added": num_candidates,
        "total_candidates": Candidate.query.join(User).filter(User.role=="candidate").count(),
        "sessions_added": num_sessions,
        "total_sessions": Session.query.count(),
        "events_created": total_events_created,
        "suspicious_events_created": total_suspicious_created
    }
