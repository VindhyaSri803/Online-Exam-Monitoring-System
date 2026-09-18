from datetime import datetime, timezone
from database.database import db

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="candidate", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    candidate = db.relationship("Candidate", back_populates="user", uselist=False,
                                cascade="all, delete-orphan")

class Candidate(db.Model):
    __tablename__ = "candidates"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    registration_photo = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="candidate")
    sessions = db.relationship("Session", back_populates="candidate", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="candidate", cascade="all, delete-orphan")

    # Backward-compatible property proxies used by legacy templates/routes.
    @property
    def name(self): return self.user.name if self.user else None
    @name.setter
    def name(self, value):
        if self.user: self.user.name = value

    @property
    def email(self): return self.user.email if self.user else None
    @email.setter
    def email(self, value):
        if self.user: self.user.email = value

    @property
    def password_hash(self): return self.user.password_hash if self.user else None
    @password_hash.setter
    def password_hash(self, value):
        if self.user: self.user.password_hash = value

    @property
    def role(self): return self.user.role if self.user else "candidate"
    @role.setter
    def role(self, value):
        if self.user: self.user.role = value

    def __init__(self, user_id=None, registration_photo=None, **legacy):
        # Compatibility with the old model's Candidate(name=..., email=..., password_hash=...).
        user = legacy.pop("user", None)
        if user is None and any(k in legacy for k in ("name", "email", "password_hash", "role")):
            user = User(
                name=legacy.pop("name", ""),
                email=legacy.pop("email", ""),
                password_hash=legacy.pop("password_hash", ""),
                role=legacy.pop("role", "candidate"),
            )
        super().__init__(user_id=user_id, registration_photo=registration_photo, **legacy)
        if user is not None:
            self.user = user

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "name": self.name, "email": self.email,
                "registration_photo": self.registration_photo, "role": self.role,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "total_sessions": len(self.sessions)}

class Exam(db.Model):
    __tablename__ = "exams"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    total_marks = db.Column(db.Integer, default=100, nullable=False)
    passing_marks = db.Column(db.Integer, default=50, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    questions = db.relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    sessions = db.relationship("Session", back_populates="exam", cascade="all, delete-orphan")
    @property
    def duration(self): return self.duration_minutes
    @duration.setter
    def duration(self, value): self.duration_minutes = int(value)
    def to_dict(self):
        return {"id": self.id, "title": self.title, "description": self.description,
                "duration_minutes": self.duration_minutes, "total_marks": self.total_marks,
                "passing_marks": self.passing_marks, "status": self.status,
                "questions_count": len(self.questions), "sessions_count": len(self.sessions)}

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(256), nullable=False)
    option_b = db.Column(db.String(256), nullable=False)
    option_c = db.Column(db.String(256), nullable=False)
    option_d = db.Column(db.String(256), nullable=False)
    correct_option = db.Column(db.String(5), nullable=False)
    marks = db.Column(db.Integer, default=10, nullable=False)
    exam = db.relationship("Exam", back_populates="questions")
    def to_dict(self, include_correct=False):
        d = {"id": self.id, "exam_id": self.exam_id, "question_text": self.question_text,
             "option_a": self.option_a, "option_b": self.option_b, "option_c": self.option_c,
             "option_d": self.option_d, "marks": self.marks}
        if include_correct: d["correct_option"] = self.correct_option
        return d

class Session(db.Model):
    __tablename__ = "sessions"
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, default=utcnow, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="in_progress", nullable=False, index=True)
    face_presence_ratio = db.Column(db.Float, default=1.0)
    integrity_score = db.Column(db.Float, default=100.0)
    risk_level = db.Column(db.String(20), default="LOW", index=True)
    answers_json = db.Column(db.Text, default="{}")
    total_score = db.Column(db.Float, default=0.0)
    cluster_label = db.Column(db.String(50))
    mode = db.Column(db.String(20), default="live")
    incident_status = db.Column(db.String(20), default="New")
    cluster_id = db.Column(db.Integer)
    candidate = db.relationship("Candidate", back_populates="sessions")
    exam = db.relationship("Exam", back_populates="sessions")
    events = db.relationship("Event", back_populates="session", cascade="all, delete-orphan", order_by="Event.timestamp")
    suspicious_events = db.relationship("SuspiciousEvent", back_populates="session", cascade="all, delete-orphan", order_by="SuspiciousEvent.timestamp")
    evidence = db.relationship("Evidence", back_populates="session", cascade="all, delete-orphan", order_by="Evidence.timestamp")
    reports = db.relationship("Report", back_populates="session", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="session", cascade="all, delete-orphan")

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    severity = db.Column(db.String(20), default="INFO", nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Float, default=0.0)
    metadata_json = db.Column(db.Text, default="{}")
    session = db.relationship("Session", back_populates="events")
    def to_dict(self):
        return {"id": self.id, "session_id": self.session_id, "event_type": self.event_type,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "severity": self.severity, "description": self.description,
                "duration": self.duration or 0.0}

class SuspiciousEvent(db.Model):
    __tablename__ = "suspicious_events"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    rule_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), default="MEDIUM", nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    session = db.relationship("Session", back_populates="suspicious_events")
    event = db.relationship("Event")

class Evidence(db.Model):
    __tablename__ = "evidence"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    file_path = db.Column(db.String(256), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    description = db.Column(db.Text)
    evidence_type = db.Column(db.String(50), default="screenshot")
    session = db.relationship("Session", back_populates="evidence")
    event = db.relationship("Event")
    @property
    def screenshot_path(self): return self.file_path
    @screenshot_path.setter
    def screenshot_path(self, v): self.file_path = v

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    integrity_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    report_text = db.Column(db.Text, nullable=False)
    summary_json = db.Column(db.Text, default="{}")
    model_used = db.Column(db.String(100), default="rule_based_deterministic")
    generated_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    session = db.relationship("Session", back_populates="reports")

class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"))
    severity = db.Column(db.String(20), default="MEDIUM", nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="New", nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    session = db.relationship("Session", back_populates="alerts")
    candidate = db.relationship("Candidate", back_populates="alerts")
    exam = db.relationship("Exam")

class Setting(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(256))
    @classmethod
    def get_val(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        if not item: return default
        try:
            import json; return json.loads(item.value)
        except Exception: return item.value
    @classmethod
    def set_val(cls, key, value, description=None):
        import json
        item = cls.query.filter_by(key=key).first()
        val = json.dumps(value) if not isinstance(value, str) else value
        if not item: db.session.add(cls(key=key, value=val, description=description))
        else:
            item.value = val
            if description: item.description = description
        db.session.commit()
