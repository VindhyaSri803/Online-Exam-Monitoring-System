import unittest
from app import create_app
from database.database import db
from database.models import User, Candidate
from auth.security import verify_password, hash_password

class TestAuth(unittest.TestCase):
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
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        pwd = "SecurePassword2026!"
        h = hash_password(pwd)
        self.assertNotEqual(pwd, h)
        self.assertTrue(verify_password(pwd, h))
        self.assertFalse(verify_password("WrongPassword", h))

    def test_candidate_registration(self):
        res = self.client.post("/auth/register", data={
            "name": "Jane Doe",
            "email": "jane@university.edu",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        cand = Candidate.query.join(User).filter(User.email=="jane@university.edu").first()
        self.assertIsNotNone(cand)
        self.assertEqual(cand.name, "Jane Doe")
        self.assertTrue(verify_password("password123", cand.user.password_hash))

    def test_registration_creates_user_and_candidate_link(self):
        self.client.post("/auth/register", data={
            "name": "Linked User", "email": "linked@test.com",
            "password": "password123", "confirm_password": "password123"
        })
        user = User.query.filter_by(email="linked@test.com").first()
        cand = Candidate.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(cand)
        self.assertEqual(user.role, "candidate")

    def test_duplicate_registration_prevented(self):
        # Register first time
        self.client.post("/auth/register", data={
            "name": "Alex Mercer",
            "email": "alex@test.com",
            "password": "password123",
            "confirm_password": "password123"
        })
        # Log out before attempting to register second candidate with same email
        self.client.get("/auth/logout")

        # Register second time with duplicate email
        res = self.client.post("/auth/register", data={
            "name": "Alex Mercer 2",
            "email": "alex@test.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertIn(b"already exists", res.data)

    def test_login_success_and_logout(self):
        user = User(name="Bob Smith", email="bob@test.com", password_hash=hash_password("mypassword"), role="candidate")
        db.session.add(user)
        db.session.flush()
        cand = Candidate(user_id=user.id)
        db.session.add(cand)
        db.session.commit()

        # Valid login
        res = self.client.post("/auth/login", data={
            "email": "bob@test.com",
            "password": "mypassword"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), cand.id)

        # Logout
        res_logout = self.client.get("/auth/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_invalid_password_rejected(self):
        user = User(name="Bob Smith", email="bob@test.com", password_hash=hash_password("mypassword"), role="candidate")
        db.session.add(user)
        db.session.flush()
        cand = Candidate(user_id=user.id)
        db.session.add(cand)
        db.session.commit()

        res = self.client.post("/auth/login", data={
            "email": "bob@test.com",
            "password": "IncorrectPassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res.data)

if __name__ == "__main__":
    unittest.main()
