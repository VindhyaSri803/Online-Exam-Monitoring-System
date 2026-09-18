import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from typing import Dict, Any, List
from database.database import db
from database.models import Session, Event, SuspiciousEvent

class SessionClusterer:
    """Scikit-Learn K-Means Behavioral Session Clustering Engine (Invigilator Analytics Assistance)."""

    CLUSTER_NAMES = {
        0: "Normal Behaviour",
        1: "Moderate Suspicion",
        2: "High Suspicion"
    }

    CLUSTER_COLORS = {
        "Normal Behaviour": "#10b981",    # Emerald
        "Moderate Suspicion": "#f59e0b",  # Amber
        "High Suspicion": "#ef4444"       # Red
    }

    @classmethod
    def run_clustering(cls, save_to_db: bool = True) -> Dict[str, Any]:
        """
        Extract session features, run K-Means clustering, compute PCA 2D coordinates,
        and assign explainable cluster labels.
        """
        sessions = Session.query.all()
        if len(sessions) < 3:
            return {
                "success": False,
                "message": "At least 3 sessions required to perform K-Means clustering.",
                "clusters": [],
                "points": [],
                "features_summary": []
            }

        # Build feature dataset
        records = []
        for s in sessions:
            # Count events
            events = s.events
            tab_switches = sum(1 for e in events if e.event_type == "TAB_SWITCH")
            focus_losses = sum(1 for e in events if e.event_type == "WINDOW_BLUR")
            face_absence_sec = sum((e.duration or 0.0) for e in events if e.event_type == "FACE_ABSENT")
            suspicious_count = len(s.suspicious_events)
            
            records.append({
                "session_id": s.id,
                "candidate_id": s.candidate_id,
                "candidate_name": s.candidate.name if s.candidate else f"ID #{s.candidate_id}",
                "exam_title": s.exam.title if s.exam else "N/A",
                "integrity_score": float(s.integrity_score if s.integrity_score is not None else 100.0),
                "face_presence_ratio": float(s.face_presence_ratio if s.face_presence_ratio is not None else 1.0),
                "tab_switches": float(tab_switches),
                "focus_losses": float(focus_losses),
                "face_absence_sec": float(face_absence_sec),
                "suspicious_count": float(suspicious_count),
                "risk_level": s.risk_level
            })

        df = pd.DataFrame(records)
        feature_cols = [
            "integrity_score",
            "face_presence_ratio",
            "tab_switches",
            "focus_losses",
            "face_absence_sec",
            "suspicious_count"
        ]

        X = df[feature_cols].values

        # 1. Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 2. Run KMeans
        n_clusters = min(3, len(sessions))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        raw_cluster_labels = kmeans.fit_predict(X_scaled)

        df["raw_cluster"] = raw_cluster_labels

        # 3. Sort cluster labels by average integrity score to assign consistent semantic names:
        # Highest average integrity score -> Normal Behaviour
        # Medium -> Moderate Suspicion
        # Lowest -> High Suspicion
        cluster_integrity_means = df.groupby("raw_cluster")["integrity_score"].mean().to_dict()
        sorted_raw_clusters = sorted(cluster_integrity_means.keys(), key=lambda c: cluster_integrity_means[c], reverse=True)
        
        mapping = {}
        semantic_names = ["Normal Behaviour", "Moderate Suspicion", "High Suspicion"]
        for idx, raw_c in enumerate(sorted_raw_clusters):
            mapping[raw_c] = {
                "id": idx,
                "label": semantic_names[min(idx, len(semantic_names) - 1)]
            }

        df["cluster_id"] = df["raw_cluster"].apply(lambda c: mapping[c]["id"])
        df["cluster_label"] = df["raw_cluster"].apply(lambda c: mapping[c]["label"])

        # 4. Perform 2D PCA for visual projection on dashboard
        pca = PCA(n_components=2, random_state=42)
        pca_coords = pca.fit_transform(X_scaled)
        df["pca_x"] = np.round(pca_coords[:, 0], 3)
        df["pca_y"] = np.round(pca_coords[:, 1], 3)

        # 5. Optionally save cluster labels back to database
        if save_to_db:
            for _, row in df.iterrows():
                sess_obj = db.session.get(Session, int(row["session_id"]))
                if sess_obj:
                    sess_obj.cluster_id = int(row["cluster_id"])
                    sess_obj.cluster_label = str(row["cluster_label"])
            db.session.commit()

        # 6. Build cluster summary statistics
        cluster_summaries = []
        for label in ["Normal Behaviour", "Moderate Suspicion", "High Suspicion"]:
            cluster_df = df[df["cluster_label"] == label]
            if not cluster_df.empty:
                cluster_summaries.append({
                    "label": label,
                    "color": cls.CLUSTER_COLORS.get(label, "#3b82f6"),
                    "session_count": int(len(cluster_df)),
                    "avg_integrity": round(float(cluster_df["integrity_score"].mean()), 1),
                    "avg_face_presence": round(float(cluster_df["face_presence_ratio"].mean() * 100), 1),
                    "avg_tab_switches": round(float(cluster_df["tab_switches"].mean()), 1),
                    "avg_focus_losses": round(float(cluster_df["focus_losses"].mean()), 1),
                    "avg_suspicious_events": round(float(cluster_df["suspicious_count"].mean()), 1),
                    "description": cls._get_cluster_desc(label)
                })

        # 7. Prepare points for frontend 2D Chart
        points = []
        for _, row in df.iterrows():
            points.append({
                "x": float(row["pca_x"]),
                "y": float(row["pca_y"]),
                "session_id": int(row["session_id"]),
                "candidate_name": str(row["candidate_name"]),
                "exam_title": str(row["exam_title"]),
                "integrity_score": float(row["integrity_score"]),
                "cluster_label": str(row["cluster_label"]),
                "cluster_id": int(row["cluster_id"]),
                "color": cls.CLUSTER_COLORS.get(row["cluster_label"], "#3b82f6"),
                "risk_level": str(row["risk_level"])
            })

        return {
            "success": True,
            "total_sessions": len(df),
            "clusters": cluster_summaries,
            "points": points,
            "pca_variance_ratio": [round(float(v), 3) for v in pca.explained_variance_ratio_],
            "disclaimer": "ExamGuard clustering is an unsupervised analytical aid for invigilator triage. It does not constitute proof of academic dishonesty."
        }

    @staticmethod
    def _get_cluster_desc(label: str) -> str:
        if label == "Normal Behaviour":
            return "Standard examination pattern: High face presence, minimal browser focus shifts, zero to negligible telemetry infractions."
        elif label == "Moderate Suspicion":
            return "Irregular activity pattern: Occasional tab switches, minor face absence durations, moderate integrity deviations requiring standard review."
        else:
            return "Elevated anomaly pattern: Frequent browser defocusing, prolonged absence from camera view, or multiple suspicious flags requiring priority invigilator audit."
