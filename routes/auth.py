"""
Authentication Routes for ExamGuard.
Handles Candidate and Manager Registration, Login, Logout, and Demo Logins.
"""

from auth.routes import auth_bp

__all__ = ["auth_bp"]
