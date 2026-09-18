"""
OpenCV Haar Cascade Face Presence Monitoring Module for ExamGuard.
Monitors webcam stream, detects face presence, tracks absences,
identifies multiple faces, and calculates face presence ratios.
"""

from monitoring.face_detector import FaceDetector, detector

__all__ = ["FaceDetector", "detector"]
