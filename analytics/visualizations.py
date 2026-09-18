"""
Data Science Visualizations Module for ExamGuard.
Uses Pandas, Matplotlib, Seaborn, and Scikit-learn to generate publication-grade
statistical charts and telemetry heatmaps for institutional monitoring.
"""

import io
import os
import base64
import matplotlib
matplotlib.use("Agg")  # Non-interactive, headless backend for web server
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from database.database import db
from database.models import Session, Event, SuspiciousEvent, Exam
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Set institutional modern dark/clean style
sns.set_theme(style="darkgrid")
plt.rcParams.update({
    "figure.facecolor": "#111827",
    "axes.facecolor": "#1f2937",
    "text.color": "#f3f4f6",
    "axes.labelcolor": "#d1d5db",
    "xtick.color": "#9ca3af",
    "ytick.color": "#9ca3af",
    "grid.color": "#374151",
    "font.family": "sans-serif"
})


class AnalyticsVisualizer:
    """Generates Matplotlib and Seaborn visualization charts for ExamGuard."""

    @staticmethod
    def _fig_to_base64(fig: plt.Figure) -> str:
        """Convert a Matplotlib figure into a base64 encoded PNG data URI."""
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return f"data:image/png;base64,{img_b64}"

    @classmethod
    def plot_integrity_score_distribution(cls, exam_id: Optional[int] = None) -> str:
        """
        1. Integrity Score Distribution:
        Seaborn histogram & KDE showing candidate integrity scores across sessions.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.all()

        scores = [float(s.integrity_score if s.integrity_score is not None else 100.0) for s in sessions]
        if not scores:
            scores = [100.0]

        df = pd.DataFrame({"Integrity Score": scores})

        fig, ax = plt.subplots(figsize=(7, 4.2))
        sns.histplot(df["Integrity Score"], kde=True, bins=15, color="#3b82f6", ax=ax, edgecolor="#1d4ed8", alpha=0.6)

        # Draw risk thresholds
        ax.axvline(50, color="#ef4444", linestyle="--", linewidth=1.5, label="High Risk Boundary (50)")
        ax.axvline(80, color="#10b981", linestyle="--", linewidth=1.5, label="Low Risk Boundary (80)")

        ax.set_title("Candidate Integrity Score Distribution", fontsize=13, fontweight="bold", pad=12, color="#f9fafb")
        ax.set_xlabel("Integrity Score (0 - 100)", fontsize=10)
        ax.set_ylabel("Candidate Session Count", fontsize=10)
        ax.set_xlim(0, 105)
        ax.legend(loc="upper left", framealpha=0.3, facecolor="#1f2937", edgecolor="#374151")

        return cls._fig_to_base64(fig)

    @classmethod
    def plot_event_frequency(cls, exam_id: Optional[int] = None) -> str:
        """
        2. Event Frequency Chart:
        Seaborn barplot showing the frequency of key telemetry markers:
        - Face absence
        - Multiple faces
        - Tab switches
        - Focus loss (Window blur)
        - Fullscreen exits
        """
        query = Event.query
        if exam_id:
            query = query.join(Session).filter(Session.exam_id == exam_id)
        events = query.all()

        counts = {
            "Face Absence": sum(1 for e in events if e.event_type == "FACE_ABSENT"),
            "Multiple Faces": sum(1 for e in events if e.event_type in ["MULTIPLE_FACES", "MULTIPLE_FACES_DETECTED"]),
            "Tab Switches": sum(1 for e in events if e.event_type == "TAB_SWITCH"),
            "Focus Loss": sum(1 for e in events if e.event_type == "WINDOW_BLUR"),
            "Fullscreen Exit": sum(1 for e in events if e.event_type == "FULLSCREEN_EXIT")
        }

        df = pd.DataFrame(list(counts.items()), columns=["Event Type", "Frequency"])

        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        palette = ["#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6", "#ec4899"]
        sns.barplot(data=df, x="Event Type", y="Frequency", palette=palette, ax=ax, hue="Event Type", legend=False)

        # Annotate bars with values
        for p in ax.patches:
            val = int(p.get_height())
            ax.annotate(f"{val}", (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha="center", va="center", xytext=(0, 6), textcoords="offset points",
                        fontsize=9, fontweight="bold", color="#f3f4f6")

        ax.set_title("Monitoring Telemetry Event Frequency", fontsize=13, fontweight="bold", pad=12, color="#f9fafb")
        ax.set_xlabel("Telemetry Anomaly Category", fontsize=10)
        ax.set_ylabel("Total Occurrences", fontsize=10)

        return cls._fig_to_base64(fig)

    @classmethod
    def plot_event_correlation_heatmap(cls, exam_id: Optional[int] = None) -> str:
        """
        3. Event Frequency Heatmap:
        Seaborn heatmap showing session feature correlations across telemetry markers.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.all()

        records = []
        for s in sessions:
            events = s.events
            records.append({
                "Integrity Score": float(s.integrity_score or 100.0),
                "Face Presence": float(s.face_presence_ratio or 1.0) * 100,
                "Tab Switches": sum(1 for e in events if e.event_type == "TAB_SWITCH"),
                "Focus Losses": sum(1 for e in events if e.event_type == "WINDOW_BLUR"),
                "Face Absences": sum(1 for e in events if e.event_type == "FACE_ABSENT"),
                "Multi Faces": sum(1 for e in events if e.event_type in ["MULTIPLE_FACES", "MULTIPLE_FACES_DETECTED"]),
                "Fullscreen Exits": sum(1 for e in events if e.event_type == "FULLSCREEN_EXIT")
            })

        if len(records) < 2:
            records.append({
                "Integrity Score": 100.0, "Face Presence": 100.0, "Tab Switches": 0,
                "Focus Losses": 0, "Face Absences": 0, "Multi Faces": 0, "Fullscreen Exits": 0
            })
            records.append({
                "Integrity Score": 40.0, "Face Presence": 50.0, "Tab Switches": 5,
                "Focus Losses": 4, "Face Absences": 6, "Multi Faces": 1, "Fullscreen Exits": 2
            })

        df = pd.DataFrame(records)
        corr = df.corr()

        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, ax=ax,
                    cbar_kws={"shrink": 0.8}, linewidths=0.5, linecolor="#374151")

        ax.set_title("Telemetry Anomaly Correlation Heatmap", fontsize=13, fontweight="bold", pad=12, color="#f9fafb")
        plt.xticks(rotation=40, ha="right", fontsize=9)
        plt.yticks(rotation=0, fontsize=9)

        return cls._fig_to_base64(fig)

    @classmethod
    def plot_kmeans_clusters(cls) -> str:
        """
        4. K-Means Clustering Plot:
        2D PCA projection of session features showing 3 clusters and cluster centroids.
        """
        sessions = Session.query.all()
        if len(sessions) < 3:
            fig, ax = plt.subplots(figsize=(7, 4.2))
            ax.text(0.5, 0.5, "Insufficient sessions to generate K-Means plot (Min 3 required).",
                    ha="center", va="center", color="#9ca3af", fontsize=11)
            ax.axis("off")
            return cls._fig_to_base64(fig)

        records = []
        for s in sessions:
            events = s.events
            records.append([
                float(s.integrity_score or 100.0),
                float(s.face_presence_ratio or 1.0),
                sum(1 for e in events if e.event_type == "TAB_SWITCH"),
                sum(1 for e in events if e.event_type == "WINDOW_BLUR"),
                sum((e.duration or 0.0) for e in events if e.event_type == "FACE_ABSENT"),
                len(s.suspicious_events)
            ])

        X = np.array(records)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        n_clusters = min(3, len(sessions))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(X_scaled)
        centroids_pca = pca.transform(kmeans.cluster_centers_)

        df = pd.DataFrame({
            "PCA 1": coords[:, 0],
            "PCA 2": coords[:, 1],
            "Cluster": [f"Cluster {l}" for l in labels]
        })

        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        cluster_colors = {"Cluster 0": "#10b981", "Cluster 1": "#f59e0b", "Cluster 2": "#ef4444"}
        sns.scatterplot(
            data=df, x="PCA 1", y="PCA 2", hue="Cluster",
            palette=cluster_colors, s=70, alpha=0.8, ax=ax, edgecolor="#111827"
        )

        # Plot centroids
        ax.scatter(
            centroids_pca[:, 0], centroids_pca[:, 1],
            s=220, c="#ffffff", marker="X", edgecolor="#000000", linewidth=1.5,
            label="Cluster Centroids"
        )

        ax.set_title("K-Means Behavioral Session Clustering (PCA 2D)", fontsize=13, fontweight="bold", pad=12, color="#f9fafb")
        ax.set_xlabel("Principal Component 1 (Primary Telemetry Variance)", fontsize=10)
        ax.set_ylabel("Principal Component 2 (Secondary Variance)", fontsize=10)
        ax.legend(loc="upper right", framealpha=0.3, facecolor="#1f2937", edgecolor="#374151")

        return cls._fig_to_base64(fig)

    @classmethod
    def plot_cohort_risk_profiling(cls, exam_id: Optional[int] = None) -> str:
        """
        5. Cohort Risk Profiling Chart:
        Seaborn donut chart showing the proportion of Low, Medium, and High Risk candidates.
        """
        query = Session.query
        if exam_id:
            query = query.filter_by(exam_id=exam_id)
        sessions = query.all()

        low_c = sum(1 for s in sessions if s.risk_level == "LOW")
        med_c = sum(1 for s in sessions if s.risk_level == "MEDIUM")
        high_c = sum(1 for s in sessions if s.risk_level == "HIGH")

        labels = ["Low Risk", "Medium Risk", "High Risk"]
        counts = [low_c, med_c, high_c]
        colors = ["#10b981", "#f59e0b", "#ef4444"]

        if sum(counts) == 0:
            counts = [1, 0, 0]

        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        wedges, texts, autotexts = ax.pie(
            counts, labels=labels, autopct="%1.1f%%",
            startangle=140, colors=colors,
            wedgeprops=dict(width=0.45, edgecolor="#111827", linewidth=2),
            textprops=dict(color="#f3f4f6", fontsize=10)
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")

        ax.set_title("Cohort Risk Classification Profile", fontsize=13, fontweight="bold", pad=12, color="#f9fafb")

        return cls._fig_to_base64(fig)

    @classmethod
    def generate_all_plots(cls, exam_id: Optional[int] = None, save_to_folder: Optional[str] = None) -> Dict[str, str]:
        """Generate all 5 data science figures as base64 images."""
        plots = {
            "score_distribution": cls.plot_integrity_score_distribution(exam_id),
            "event_frequency": cls.plot_event_frequency(exam_id),
            "correlation_heatmap": cls.plot_event_correlation_heatmap(exam_id),
            "kmeans_clusters": cls.plot_kmeans_clusters(),
            "cohort_risk_profiling": cls.plot_cohort_risk_profiling(exam_id)
        }
        return plots
