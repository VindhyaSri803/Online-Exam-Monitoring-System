from datetime import datetime, timezone
from database.database import db

class Exam(db.Model):
    __tablename__ = "exams"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    total_marks = db.Column(db.Integer, default=100)
    passing_marks = db.Column(db.Integer, default=50)
    status = db.Column(db.String(20), default="active")  # 'active', 'draft', 'archived'
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    questions = db.relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    sessions = db.relationship("Session", back_populates="exam", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "total_marks": self.total_marks,
            "passing_marks": self.passing_marks,
            "status": self.status,
            "questions_count": len(self.questions) if self.questions else 0,
            "sessions_count": len(self.sessions) if self.sessions else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Question(db.Model):
    __tablename__ = "questions"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(256), nullable=False)
    option_b = db.Column(db.String(256), nullable=False)
    option_c = db.Column(db.String(256), nullable=False)
    option_d = db.Column(db.String(256), nullable=False)
    correct_option = db.Column(db.String(5), nullable=False)  # 'A', 'B', 'C', 'D'
    marks = db.Column(db.Integer, default=10)
    
    # Relationship
    exam = db.relationship("Exam", back_populates="questions")

    def to_dict(self, include_correct=False):
        data = {
            "id": self.id,
            "exam_id": self.exam_id,
            "question_text": self.question_text,
            "option_a": self.option_a,
            "option_b": self.option_b,
            "option_c": self.option_c,
            "option_d": self.option_d,
            "marks": self.marks
        }
        if include_correct:
            data["correct_option"] = self.correct_option
        return data
