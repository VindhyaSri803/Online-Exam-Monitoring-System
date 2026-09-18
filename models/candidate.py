from datetime import datetime, timezone
from database.database import db

class Candidate(db.Model):
    __tablename__ = "candidates"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    registration_photo = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default="candidate", nullable=False)  # 'candidate', 'admin', 'manager'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    sessions = db.relationship("Session", back_populates="candidate", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="candidate", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "registration_photo": self.registration_photo,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_sessions": len(self.sessions) if self.sessions else 0
        }
