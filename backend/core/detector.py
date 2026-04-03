from mtcnn import MTCNN


class FaceDetector:
    """
    Wraps MTCNN face detection running on CPU.

    MTCNN uses TensorFlow under the hood. Since CUDA_VISIBLE_DEVICES is set to
    an empty string in the container environment, TF automatically falls back to
    CPU — no GPU configuration needed.
    """

    def __init__(self):
        self._detector: MTCNN | None = None

    def _get_detector(self) -> MTCNN:
        if self._detector is None:
            print("[FaceDetector] Initializing MTCNN on CPU…")
            self._detector = MTCNN()
            print("[FaceDetector] MTCNN ready.")
        return self._detector

    def detect_faces(self, frame):
        """
        Detects faces in an RGB numpy frame.
        Returns list of dicts: [{ box: [x,y,w,h], confidence: float, keypoints: {...} }]
        """
        try:
            detector = self._get_detector()
            return detector.detect_faces(frame)
        except Exception as e:
            print(f"[FaceDetector] Error during detection: {e}")
            return []
