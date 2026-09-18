import os
import cv2
import numpy as np
import base64
import time
from typing import Dict, Any, Tuple, Optional


class FaceDetector:
    """OpenCV Haar Cascade Face Detector for Real-Time Exam Monitoring."""

    def __init__(self):
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        cascade_path = os.path.join(
            project_root,
            "assets",
            "haarcascades",
            "haarcascade_frontalface_default.xml"
        )

        if not os.path.exists(cascade_path):
            raise FileNotFoundError(
                f"Haar cascade XML not found at: {cascade_path}"
            )

        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            raise RuntimeError(
                f"Failed to load Haar cascade: {cascade_path}"
            )

    def decode_base64_frame(
        self, base64_data: str
    ) -> Optional[np.ndarray]:
        """Convert a base64 image data URL/string into an OpenCV BGR numpy array."""
        try:
            if not base64_data:
                return None

            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            img_bytes = base64.b64decode(base64_data)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            return img

        except Exception:
            return None

    def detect_faces(
        self, frame: np.ndarray
    ) -> Tuple[int, list]:
        """Detect faces in an OpenCV BGR frame and return (count, bounding_boxes)."""

        if frame is None or frame.size == 0:
            return 0, []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Equalize histogram for contrast enhancement
        gray = cv2.equalizeHist(gray)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(40, 40),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        boxes = []

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                boxes.append({
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h)
                })

        return len(boxes), boxes

    def process_frame(self, base64_data: str) -> Dict[str, Any]:
        """
        Process incoming webcam frame.

        Returns:
            {
                "success": bool,
                "face_detected": bool,
                "face_count": int,
                "boxes": list,
                "status": "FACE_PRESENT" |
                          "FACE_ABSENT" |
                          "MULTIPLE_FACES_DETECTED",
                "timestamp": float
            }
        """

        frame = self.decode_base64_frame(base64_data)

        if frame is None:
            return {
                "success": False,
                "face_detected": False,
                "face_count": 0,
                "boxes": [],
                "status": "FACE_ABSENT",
                "error": "Failed to decode frame",
                "timestamp": time.time()
            }

        face_count, boxes = self.detect_faces(frame)

        if face_count == 1:
            status = "FACE_PRESENT"
            face_detected = True

        elif face_count == 0:
            status = "FACE_ABSENT"
            face_detected = False

        else:
            status = "MULTIPLE_FACES_DETECTED"
            face_detected = True

        return {
            "success": True,
            "face_detected": face_detected,
            "face_count": face_count,
            "boxes": boxes,
            "status": status,
            "timestamp": time.time()
        }

    def save_annotated_frame(
        self,
        frame: np.ndarray,
        boxes: list,
        output_path: str,
        caption: str = ""
    ) -> bool:
        """Draw bounding boxes and caption on frame and save to output_path."""

        try:
            annotated = frame.copy()

            for b in boxes:
                x, y, w, h = (
                    b["x"],
                    b["y"],
                    b["w"],
                    b["h"]
                )

                cv2.rectangle(
                    annotated,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    annotated,
                    "Candidate Face",
                    (x, max(y - 10, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )

            if caption:
                cv2.putText(
                    annotated,
                    caption,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            output_dir = os.path.dirname(output_path)

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            cv2.imwrite(output_path, annotated)

            return True

        except Exception:
            return False


# Global Singleton Instance
detector = FaceDetector()