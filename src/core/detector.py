from deepface import DeepFace
from mtcnn import MTCNN
import cv2

class FaceDetector:
    def __init__(self, detector_backend="mtcnn"):
        self.detector_backend = detector_backend

    def detect_faces(self, frame):
        """Detects faces in a frame and returns bounding boxes and aligned faces."""
        try:


            detector = MTCNN(device="GPU:0")

            detections = detector.detect_faces(frame)

            # DeepFace.extract_faces 
            #face_objs = DeepFace.extract_faces(
            #    img_path=frame,
            #    detector_backend=self.detector_backend,
            #    enforce_detection=False
            #)
            
            #results = []
            #for obj in face_objs:
            #    if obj["confidence"] > 0.9:  # Confidence threshold
            #        results.append({
            #            "face": obj["face"],
            #            "box": obj["facial_area"],
            #            "confidence": obj["confidence"]
            #        })
            #return results


            return detections
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
