import os
import uuid
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from database.database import db
from database.models import Evidence, Session, Event

class EvidenceManager:
    """Manager for Incident Snapshots, Frame Captures, and Evidence Linking."""

    @staticmethod
    def save_evidence_frame(session_id: int, base64_image: str, event_id: Optional[int] = None,
                            evidence_type: str = "screenshot", description: str = "",
                            upload_folder: str = "uploads/evidence") -> Optional[Evidence]:
        """Save a base64 encoded image as an evidence file and create Evidence DB record."""
        try:
            if not base64_image:
                return None
            
            if "," in base64_image:
                base64_image = base64_image.split(",")[1]

            os.makedirs(upload_folder, exist_ok=True)
            filename = f"ev_{session_id}_{uuid.uuid4().hex[:10]}.jpg"
            filepath = os.path.join(upload_folder, filename)

            img_bytes = base64.b64decode(base64_image)
            with open(filepath, "wb") as f:
                f.write(img_bytes)

            evidence_item = Evidence(
                session_id=session_id,
                event_id=event_id,
                file_path=filename,
                evidence_type=evidence_type,
                timestamp=datetime.now(timezone.utc),
                description=description or f"Captured {evidence_type} for session #{session_id}"
            )
            db.session.add(evidence_item)
            db.session.commit()
            return evidence_item
        except Exception as e:
            return None

    @staticmethod
    def get_session_evidence(session_id: int) -> List[Evidence]:
        """Retrieve all evidence records associated with a session."""
        return Evidence.query.filter_by(session_id=session_id).order_by(Evidence.timestamp.desc()).all()
