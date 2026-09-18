"""
Configurable Rule-Based Suspicious Event & Anomaly Detection Engine.
Monitors face absence, multiple faces, tab switching, focus loss, and fullscreen exit.
Categorizes using neutral, objective indicators: Normal, Attention Required, High Risk.
"""

from scoring.suspicious_detector import SuspiciousDetector

__all__ = ["SuspiciousDetector"]
