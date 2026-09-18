import unittest
from datetime import datetime, timezone
from app import create_app
from database.database import db
from database.models import Candidate, Exam, Session, Event, SuspiciousEvent
from scoring.integrity_score import IntegrityScorer
from scoring.suspicious_detector import SuspiciousDetector

class TestScoring(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SECRET_KEY = "test-secret"
            UPLOAD_FOLDER = "uploads"
            PHOTOS_FOLDER = "uploads/photos"
            EVIDENCE_FOLDER = "uploads/evidence"
            DEFAULT_SETTINGS = {}

        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed test candidate and exam
        self.candidate = Candidate(name="Test Student", email="test@student.edu", password_hash="hash")
        self.exam = Exam(title="Test Exam", duration_minutes=30, total_marks=100)
        db.session.add_all([self.candidate, self.exam])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_low_risk_clean_session_scoring(self):
        sess = Session(candidate_id=self.candidate.id, exam_id=self.exam.id, face_presence_ratio=1.0)
        db.session.add(sess)
        db.session.commit()

        # Add 5 face present events
        for _ in range(5):
            db.session.add(Event(session_id=sess.id, event_type="FACE_PRESENT", severity="INFO"))
        db.session.commit()

        result = IntegrityScorer.calculate_session_integrity(sess.id, face_presence_ratio=1.0)
        self.assertEqual(result["integrity_score"], 100.0)
        self.assertEqual(result["risk_level"], "LOW")
        self.assertEqual(result["penalties"]["total_penalty"], 0.0)

    def test_medium_risk_session_scoring(self):
        sess = Session(candidate_id=self.candidate.id, exam_id=self.exam.id, face_presence_ratio=0.8)
        db.session.add(sess)
        db.session.commit()

        # Add 3 tab switches and 2 window blurs
        for _ in range(3):
            db.session.add(Event(session_id=sess.id, event_type="TAB_SWITCH", severity="SUSPICIOUS"))
        for _ in range(2):
            db.session.add(Event(session_id=sess.id, event_type="WINDOW_BLUR", severity="WARNING"))
        db.session.commit()

        result = IntegrityScorer.calculate_session_integrity(sess.id, face_presence_ratio=0.8)
        self.assertLess(result["integrity_score"], 80.0)
        self.assertGreaterEqual(result["integrity_score"], 50.0)
        self.assertEqual(result["risk_level"], "MEDIUM")

    def test_high_risk_session_scoring(self):
        sess = Session(candidate_id=self.candidate.id, exam_id=self.exam.id, face_presence_ratio=0.4)
        db.session.add(sess)
        db.session.commit()

        # 8 tab switches and multiple suspicious events
        for _ in range(8):
            db.session.add(Event(session_id=sess.id, event_type="TAB_SWITCH", severity="SUSPICIOUS"))
        for _ in range(6):
            db.session.add(Event(session_id=sess.id, event_type="WINDOW_BLUR", severity="WARNING"))
        
        # Add high severity suspicious event
        db.session.add(SuspiciousEvent(
            session_id=sess.id,
            rule_name="Excessive Tab Switching (High Risk)",
            severity="HIGH",
            description="Candidate switched tabs 8 times."
        ))
        db.session.commit()

        result = IntegrityScorer.calculate_session_integrity(sess.id, face_presence_ratio=0.4)
        self.assertLess(result["integrity_score"], 50.0)
        self.assertEqual(result["risk_level"], "HIGH")

    def test_suspicious_detector_rules(self):
        sess = Session(candidate_id=self.candidate.id, exam_id=self.exam.id)
        db.session.add(sess)
        db.session.commit()

        # 4 tab switches (threshold is 3)
        for _ in range(4):
            db.session.add(Event(session_id=sess.id, event_type="TAB_SWITCH", severity="SUSPICIOUS"))
        db.session.commit()

        detected = SuspiciousDetector.evaluate_session_events(sess.id)
        self.assertGreater(len(detected), 0)
        rule_names = [se.rule_name for se in sess.suspicious_events]
        self.assertTrue(any("Tab Switching" in name for name in rule_names))

if __name__ == "__main__":
    unittest.main()
