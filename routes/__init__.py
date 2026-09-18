from routes.auth import auth_bp
from routes.candidate import candidate_bp
from routes.manager import manager_bp, admin_bp
from routes.monitoring import monitoring_bp
from routes.exam import exam_bp
from routes.analytics import analytics_bp
from routes.api_routes import api_bp

__all__ = [
    "auth_bp",
    "candidate_bp",
    "manager_bp",
    "admin_bp",
    "monitoring_bp",
    "exam_bp",
    "analytics_bp",
    "api_bp"
]
