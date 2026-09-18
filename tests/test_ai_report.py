import unittest
from app import create_app
from database.database import db
from database.models import Candidate, Exam, Session, Event, SuspiciousEvent
from ai.report_agent import AIReportAgent, ETHICAL_DISCLAIMER

class TestAIReport(unittest.TestCase):
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

        self.cand = Candidate(name="Samantha Reed", email="samantha@university.edu", password_hash="hash")
        self.exam = Exam(title="CYBER205: Network Security", duration_minutes=25, total_marks=50)
        db.session.add_all([self.cand, self.exam])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_low_risk_ai_report_generation(self):
        sess = Session(candidate_id=self.cand.id, exam_id=self.exam.id, integrity_score=94.0, face_presence_ratio=0.97, risk_level="LOW")
        db.session.add(sess)
        db.session.commit()

        report = AIReportAgent.generate_report(sess.id)
        self.assertIsNotNone(report["report_text"])
        self.assertIn("1. SESSION SUMMARY", report["report_text"])
        self.assertIn("2. MONITORING OBSERVATIONS", report["report_text"])
        self.assertIn("3. INTEGRITY ANALYSIS", report["report_text"])
        self.assertIn("4. RISK INDICATORS", report["report_text"])
        self.assertIn("5. INVIGILATOR REVIEW NOTES", report["report_text"])
        self.assertIn("EXAMGUARD CANDIDATE INTEGRITY & TELEMETRY AUDIT REPORT", report["report_text"])
        self.assertIn("Samantha Reed", report["report_text"])
        self.assertIn(ETHICAL_DISCLAIMER, report["report_text"])
        self.assertIn("LOW", report["report_text"])

    def test_high_risk_ai_report_generation(self):
        sess = Session(candidate_id=self.cand.id, exam_id=self.exam.id, integrity_score=38.0, face_presence_ratio=0.55, risk_level="HIGH")
        db.session.add(sess)
        db.session.commit()

        # Add suspicious event
        db.session.add(SuspiciousEvent(
            session_id=sess.id,
            rule_name="Excessive Tab Switching (High Risk)",
            severity="HIGH",
            description="Candidate switched tabs 7 times."
        ))
        db.session.commit()

        report = AIReportAgent.generate_report(sess.id)
        self.assertIsNotNone(report["report_text"])
        self.assertIn("HIGH", report["report_text"])
        self.assertIn("Excessive Tab Switching", report["report_text"])
        self.assertIn("Conduct a comprehensive human invigilation audit", report["report_text"])
        self.assertIn(ETHICAL_DISCLAIMER, report["report_text"])

if __name__ == "__main__":
    unittest.main()
