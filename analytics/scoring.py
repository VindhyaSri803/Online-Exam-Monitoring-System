"""
Pandas-based Integrity Scoring and Risk Classification Module for ExamGuard.
Calculates weighted event scoring, normalized integrity score (0-100),
and risk levels (Low, Medium, High).
"""

from scoring.integrity_score import IntegrityScorer

__all__ = ["IntegrityScorer"]
