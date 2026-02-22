from mtcnn import MTCNN
import cv2


class FaceDetector:
    def __init__(self):
        self._detector = None

    def _get_detector(self):
        if self._detector is None:
            self._detector = MTCNN()
        return self._detector

    def detect_faces(self, frame):
        """
        Detects faces in an RGB frame.
        Returns list of dicts: [{box: [x,y,w,h], confidence: float, keypoints: {...}}]
        """
        try:
            detector = self._get_detector()
            detections = detector.detect_faces(frame)
            return detections
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
