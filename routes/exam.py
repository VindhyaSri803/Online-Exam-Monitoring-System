"""
Exam Routes for ExamGuard.
Handles examination listings and examination status.
"""

from flask import Blueprint, jsonify, render_template, request
from database.models import Exam, Question

exam_bp = Blueprint("exam_routes", __name__, url_prefix="/api/exams")

@exam_bp.route("/", methods=["GET"])
def get_exams():
    exams = Exam.query.all()
    return jsonify([e.to_dict() for e in exams])

@exam_bp.route("/<int:exam_id>", methods=["GET"])
def get_exam_detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    return jsonify(exam.to_dict())

__all__ = ["exam_bp"]
