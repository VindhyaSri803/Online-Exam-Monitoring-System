import unittest
import numpy as np
import cv2
import base64
from monitoring.face_detector import FaceDetector, detector
from monitoring.browser_monitor import BrowserMonitor

class TestMonitoring(unittest.TestCase):

    def test_face_detector_initialization(self):
        self.assertIsNotNone(detector.face_cascade)

    def test_empty_frame_handling(self):
        result = detector.process_frame("")
        self.assertFalse(result["success"])
        self.assertFalse(result["face_detected"])
        self.assertEqual(result["status"], "FACE_ABSENT")

    def test_synthetic_image_detection(self):
        # Create a blank black frame
        blank_frame = np.zeros((300, 300, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', blank_frame)
        b64_str = base64.b64encode(buffer).decode('utf-8')

        result = detector.process_frame(b64_str)
        self.assertTrue(result["success"])
        self.assertEqual(result["face_count"], 0)
        self.assertEqual(result["status"], "FACE_ABSENT")

    def test_browser_monitor_event_classification(self):
        tab_event = BrowserMonitor.process_telemetry_event({
            "event_type": "TAB_SWITCH",
            "duration": 4.5
        })
        self.assertEqual(tab_event["event_type"], "TAB_SWITCH")
        self.assertEqual(tab_event["severity"], "SUSPICIOUS")
        self.assertEqual(tab_event["duration"], 4.5)

        focus_event = BrowserMonitor.process_telemetry_event({
            "event_type": "WINDOW_FOCUS"
        })
        self.assertEqual(focus_event["severity"], "INFO")

        blur_event = BrowserMonitor.process_telemetry_event({
            "event_type": "WINDOW_BLUR",
            "duration": 2.0
        })
        self.assertEqual(blur_event["severity"], "WARNING")

if __name__ == "__main__":
    unittest.main()
