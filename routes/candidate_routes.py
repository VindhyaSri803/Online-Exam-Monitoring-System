import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from database.database import db
from database.models import Candidate, Exam, Question, Session, Event, SuspiciousEvent, Evidence
from auth.security import candidate_required, get_current_user
from scoring.suspicious_detector import SuspiciousDetector
from scoring.integrity_score import IntegrityScorer
from monitoring.browser_monitor import BrowserMonitor

candidate_bp = Blueprint("candidate", __name__, url_prefix="/candidate")

@candidate_bp.route("/")
@candidate_bp.route("")
def candidate_index():
    return redirect(url_for("candidate.dashboard"))

@candidate_bp.route("/dashboard")
@candidate_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    # Fetch available exams
    exams = Exam.query.filter_by(status="active").all()
    
    # Fetch candidate's past & in-progress sessions
    past_sessions = Session.query.filter_by(candidate_id=user.id).order_by(Session.start_time.desc()).all()
    
    # Active in-progress session if any
    active_session = Session.query.filter_by(candidate_id=user.id, status="in_progress").first()

    return render_template(
        "candidate/dashboard.html",
        user=user,
        exams=exams,
        past_sessions=past_sessions,
        active_session=active_session
    )


@candidate_bp.route("/exam/<int:exam_id>/instructions")
@candidate_required
def instructions(exam_id):
    user = get_current_user()
    exam = Exam.query.get_or_404(exam_id)
    return render_template("instructions.html", user=user, exam=exam)


@candidate_bp.route("/exam/<int:exam_id>/start", methods=["GET", "POST"])
@candidate_required
def start_exam(exam_id):
    user = get_current_user()
    exam = Exam.query.get_or_404(exam_id)

    # Check if there is already an active session for this exam
    existing = Session.query.filter_by(candidate_id=user.id, exam_id=exam.id, status="in_progress").first()
    if existing:
        return redirect(url_for("candidate.exam_room", session_id=existing.id))

    # Create a new session
    mode = request.args.get("mode", "live")  # 'live' or 'simulated'
    new_session = Session(
        candidate_id=user.id,
        exam_id=exam.id,
        start_time=datetime.now(timezone.utc),
        status="in_progress",
        face_presence_ratio=1.0,
        integrity_score=100.0,
        risk_level="LOW",
        answers_json="{}",
        total_score=0.0,
        mode=mode
    )
    db.session.add(new_session)
    db.session.commit()

    # Log initial SESSION_STARTED event
    start_event = Event(
        session_id=new_session.id,
        event_type="SESSION_STARTED",
        timestamp=datetime.now(timezone.utc),
        severity="INFO",
        description=f"Candidate {user.name} initiated examination session for '{exam.title}'."
    )
    db.session.add(start_event)
    db.session.commit()

    return redirect(url_for("candidate.exam_room", session_id=new_session.id))


@candidate_bp.route("/exam/<int:session_id>")
@candidate_required
def exam_room(session_id):
    user = get_current_user()
    session_obj = Session.query.get_or_404(session_id)

    if session_obj.candidate_id != user.id:
        flash("Unauthorized access to examination session.", "danger")
        return redirect(url_for("candidate.dashboard"))

    if session_obj.status == "completed":
        return redirect(url_for("candidate.completed", session_id=session_id))

    exam = session_obj.exam
    questions = exam.questions

    # Parse saved answers if any
    try:
        saved_answers = json.loads(session_obj.answers_json or "{}")
    except Exception:
        saved_answers = {}

    return render_template(
        "candidate/exam.html",
        user=user,
        exam=exam,
        session_obj=session_obj,
        questions=questions,
        saved_answers=saved_answers
    )


@candidate_bp.route("/exam/<int:session_id>/submit", methods=["POST"])
@candidate_required
def submit_exam(session_id):
    user = get_current_user()
    session_obj = Session.query.get_or_404(session_id)

    if session_obj.candidate_id != user.id:
        flash("Unauthorized access to session.", "danger")
        return redirect(url_for("candidate.dashboard"))

    if session_obj.status == "completed":
        return redirect(url_for("candidate.completed", session_id=session_id))

    exam = session_obj.exam
    questions = exam.questions

    # Collect answers from submitted form
    answers = {}
    total_earned = 0
    for q in questions:
        field_name = f"question_{q.id}"
        chosen_option = request.form.get(field_name, "")
        answers[str(q.id)] = chosen_option
        if chosen_option == q.correct_option:
            total_earned += q.marks

    # Update session status
    session_obj.answers_json = json.dumps(answers)
    session_obj.total_score = total_earned
    session_obj.end_time = datetime.now(timezone.utc)
    session_obj.status = "completed"

    # Log SESSION_SUBMITTED event
    submit_event = Event(
        session_id=session_obj.id,
        event_type="SESSION_SUBMITTED",
        timestamp=datetime.now(timezone.utc),
        severity="INFO",
        description="Candidate finished and submitted the examination answers."
    )
    db.session.add(submit_event)
    db.session.commit()

    # Run Suspicious Event Detection Rules
    SuspiciousDetector.evaluate_session_events(session_obj.id)

    # Compute final integrity score & risk level
    scoring_result = IntegrityScorer.calculate_session_integrity(session_obj.id)
    session_obj.integrity_score = scoring_result["integrity_score"]
    session_obj.risk_level = scoring_result["risk_level"]
    session_obj.face_presence_ratio = scoring_result["face_presence_ratio"]
    db.session.commit()

    flash("Examination successfully submitted. Thank you for completing your test.", "success")
    return redirect(url_for("candidate.completed", session_id=session_id))


@candidate_bp.route("/exam/<int:session_id>/completed")
@candidate_required
def completed(session_id):
    user = get_current_user()
    session_obj = Session.query.get_or_404(session_id)

    if session_obj.candidate_id != user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("candidate.dashboard"))

    return render_template(
        "candidate/completed.html",
        user=user,
        session_obj=session_obj,
        exam=session_obj.exam
    )
