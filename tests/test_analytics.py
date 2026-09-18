import unittest
from app import create_app
from database.database import db
from database.models import Candidate, Exam, Session, Event
from analytics.analytics import AnalyticsEngine
from analytics.clustering import SessionClusterer

class TestAnalytics(unittest.TestCase):
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

        # Seed candidate, exam, and multiple sessions with varied behaviors
        self.cand = Candidate(name="Analytics Student", email="analytics@student.edu", password_hash="hash")
        self.exam = Exam(title="Operating Systems", duration_minutes=30, total_marks=100)
        db.session.add_all([self.cand, self.exam])
        db.session.commit()

        # 3 distinct test sessions
        s1 = Session(candidate_id=self.cand.id, exam_id=self.exam.id, integrity_score=95.0, face_presence_ratio=0.98, risk_level="LOW")
        s2 = Session(candidate_id=self.cand.id, exam_id=self.exam.id, integrity_score=68.0, face_presence_ratio=0.82, risk_level="MEDIUM")
        s3 = Session(candidate_id=self.cand.id, exam_id=self.exam.id, integrity_score=35.0, face_presence_ratio=0.45, risk_level="HIGH")
        db.session.add_all([s1, s2, s3])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_dashboard_kpis_calculation(self):
        kpis = AnalyticsEngine.get_dashboard_kpis()
        self.assertEqual(kpis["total_sessions"], 3)
        self.assertEqual(kpis["low_risk_count"], 1)
        self.assertEqual(kpis["medium_risk_count"], 1)
        self.assertEqual(kpis["high_risk_count"], 1)
        self.assertAlmostEqual(kpis["average_integrity_score"], 66.0, delta=1.0)

    def test_chart_data_generation(self):
        chart_data = AnalyticsEngine.get_chart_data()
        self.assertIn("chart1_score_dist", chart_data)
        self.assertIn("chart2_risk_dist", chart_data)
        self.assertIn("chart3_event_freq", chart_data)
        self.assertIn("chart4_face_presence", chart_data)
        self.assertEqual(len(chart_data["chart6_scatter"]), 3)

    def test_kmeans_clustering_execution(self):
        clustering_result = SessionClusterer.run_clustering(save_to_db=True)
        self.assertTrue(clustering_result["success"])
        self.assertEqual(clustering_result["total_sessions"], 3)
        self.assertEqual(len(clustering_result["points"]), 3)
        self.assertTrue(any(c["label"] == "Normal Behaviour" for c in clustering_result["clusters"]))

if __name__ == "__main__":
    unittest.main()
