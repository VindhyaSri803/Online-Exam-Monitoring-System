from datetime import datetime, timezone
from database.database import db

class Session(db.Model):
    __tablename__ = "sessions"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="in_progress", index=True)  # 'in_progress', 'completed', 'terminated'
    face_presence_ratio = db.Column(db.Float, default=1.0)
    integrity_score = db.Column(db.Float, default=100.0)
    risk_level = db.Column(db.String(20), default="LOW", index=True)  # 'LOW', 'MEDIUM', 'HIGH'
    answers_json = db.Column(db.Text, default="{}")
    total_score = db.Column(db.Float, default=0.0)
    incident_status = db.Column(db.String(20), default="New", index=True)  # 'New', 'Under Review', 'Reviewed', 'Resolved'
    mode = db.Column(db.String(20), default="live")  # 'live', 'simulated'
    cluster_id = db.Column(db.Integer, nullable=True)
    cluster_label = db.Column(db.String(50), nullable=True)
    
    # Relationships
    candidate = db.relationship("Candidate", back_populates="sessions")
    exam = db.relationship("Exam", back_populates="sessions")
    events = db.relationship("Event", back_populates="session", cascade="all, delete-orphan", order_by="Event.timestamp")
    suspicious_events = db.relationship("SuspiciousEvent", back_populates="session", cascade="all, delete-orphan", order_by="SuspiciousEvent.timestamp")
    evidence = db.relationship("Evidence", back_populates="session", cascade="all, delete-orphan", order_by="Evidence.timestamp")
    reports = db.relationship("Report", back_populates="session", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate.name if self.candidate else None,
            "candidate_email": self.candidate.email if self.candidate else None,
            "exam_id": self.exam_id,
            "exam_title": self.exam.title if self.exam else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "face_presence_ratio": round(self.face_presence_ratio, 3) if self.face_presence_ratio is not None else 1.0,
            "integrity_score": round(self.integrity_score, 1) if self.integrity_score is not None else 100.0,
            "risk_level": self.risk_level,
            "total_score": self.total_score,
            "incident_status": self.incident_status,
            "mode": self.mode,
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "suspicious_events_count": len(self.suspicious_events) if self.suspicious_events else 0,
            "evidence_count": len(self.evidence) if self.evidence else 0
        }
