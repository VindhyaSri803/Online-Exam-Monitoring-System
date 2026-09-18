"""
Analytics Routes for ExamGuard.
Handles Institutional Analytics, Clustering API, Visualizations, and Data Export.
"""

from flask import Blueprint, jsonify, request, Response
from analytics.analytics import AnalyticsEngine
from analytics.clustering import SessionClusterer
from analytics.visualizations import AnalyticsVisualizer
from utils.export import DataExporter

analytics_bp = Blueprint("analytics_routes", __name__, url_prefix="/api/analytics")

@analytics_bp.route("/kpis", methods=["GET"])
def get_kpis():
    exam_id = request.args.get("exam_id", type=int)
    kpis = AnalyticsEngine.get_dashboard_kpis(exam_id)
    return jsonify({"success": True, "kpis": kpis})

@analytics_bp.route("/charts", methods=["GET"])
def get_charts():
    exam_id = request.args.get("exam_id", type=int)
    charts = AnalyticsEngine.get_chart_data(exam_id)
    return jsonify({"success": True, "charts": charts})

@analytics_bp.route("/visualizations", methods=["GET"])
def get_visualizations():
    exam_id = request.args.get("exam_id", type=int)
    plots = AnalyticsVisualizer.generate_all_plots(exam_id)
    return jsonify({"success": True, "plots": plots})

@analytics_bp.route("/clustering/run", methods=["POST"])
def run_clustering():
    results = SessionClusterer.run_clustering(save_to_db=True)
    return jsonify(results)

__all__ = ["analytics_bp"]
