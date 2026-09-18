from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

db = SQLAlchemy()

# Required columns for the core ExamGuard schema.
REQUIRED = {
    "users": {"id","name","email","password_hash","role","created_at"},
    "candidates": {"id","user_id","registration_photo","created_at"},
    "exams": {"id","title","duration_minutes","description","total_marks","passing_marks","status"},
    "sessions": {"id","candidate_id","exam_id","start_time","end_time","status","face_presence_ratio","integrity_score","risk_level","answers_json","total_score","cluster_label"},
    "events": {"id","session_id","event_type","timestamp","severity","description","duration"},
    "evidence": {"id","session_id","event_id","file_path","timestamp","description"},
}

def _schema_matches():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if not set(REQUIRED).issubset(tables):
        return False
    for table, columns in REQUIRED.items():
        if not columns.issubset({c["name"] for c in inspector.get_columns(table)}):
            return False
    return True

def init_db(app):
    db.init_app(app)
    with app.app_context():
        # Academic/demo project migration strategy: if the existing SQLite schema
        # is from an incompatible version, rebuild it before seeding.
        if not app.config.get("TESTING") and not _schema_matches():
            db.drop_all()
        db.create_all()
