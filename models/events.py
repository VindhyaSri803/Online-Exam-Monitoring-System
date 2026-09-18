from datetime import datetime, timezone
from database.database import db

class Event(db.Model):
    __tablename__ = "events"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    # Types: FACE_PRESENT, FACE_ABSENT, TAB_SWITCH, WINDOW_BLUR, WINDOW_FOCUS,
    #        FULLSCREEN_EXIT, MOUSE_ACTIVITY, KEYBOARD_ACTIVITY, SESSION_STARTED,
    #        SESSION_SUBMITTED, MULTIPLE_FACES_DETECTED
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    duration = db.Column(db.Float, default=0.0)  # in seconds
    severity = db.Column(db.String(20), default="INFO")  # 'INFO', 'WARNING', 'SUSPICIOUS', 'CRITICAL'
    description = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, default="{}")
    
    # Relationship
    session = db.relationship("Session", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration": round(self.duration, 2) if self.duration else 0.0,
            "severity": self.severity,
            "description": self.description
        }


class SuspiciousEvent(db.Model):
    __tablename__ = "suspicious_events"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)
    rule_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), default="MEDIUM")  # 'LOW', 'MEDIUM', 'HIGH'
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    session = db.relationship("Session", back_populates="suspicious_events")
    event = db.relationship("Event")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class Evidence(db.Model):
    __tablename__ = "evidence"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)
    file_path = db.Column(db.String(256), nullable=False)
    screenshot_path = db.Column(db.String(256), nullable=True)  # alias for prompt spec
    evidence_type = db.Column(db.String(50), default="screenshot")  # 'screenshot', 'face_frame', 'telemetry_log'
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    session = db.relationship("Session", back_populates="evidence")
    event = db.relationship("Event")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "file_path": self.file_path,
            "screenshot_path": self.screenshot_path or self.file_path,
            "evidence_type": self.evidence_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "description": self.description
        }


class Report(db.Model):
    __tablename__ = "reports"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    integrity_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    report_text = db.Column(db.Text, nullable=False)
    summary_json = db.Column(db.Text, default="{}")
    model_used = db.Column(db.String(50), default="rule_based_deterministic")
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    session = db.relationship("Session", back_populates="reports")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "integrity_score": self.integrity_score,
            "risk_level": self.risk_level,
            "report_text": self.report_text,
            "model_used": self.model_used,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }


class Alert(db.Model):
    __tablename__ = "alerts"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=True)
    severity = db.Column(db.String(20), default="MEDIUM", index=True)  # 'LOW', 'MEDIUM', 'HIGH'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="New", index=True)  # 'New', 'Under Review', 'Reviewed', 'Resolved'
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    session = db.relationship("Session", back_populates="alerts")
    candidate = db.relationship("Candidate", back_populates="alerts")
    exam = db.relationship("Exam")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate.name if self.candidate else None,
            "exam_id": self.exam_id,
            "exam_title": self.exam.title if self.exam else None,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class Setting(db.Model):
    __tablename__ = "settings"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(256), nullable=True)

    @classmethod
    def get_val(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        if item:
            try:
                import json
                return json.loads(item.value)
            except Exception:
                return item.value
        return default

    @classmethod
    def set_val(cls, key, value, description=None):
        import json
        item = cls.query.filter_by(key=key).first()
        val_str = json.dumps(value) if not isinstance(value, str) else value
        if not item:
            item = cls(key=key, value=val_str, description=description)
            db.session.add(item)
        else:
            item.value = val_str
            if description:
                item.description = description
        db.session.commit()
