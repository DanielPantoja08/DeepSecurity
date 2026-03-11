import tensorflow as tf
from mtcnn import MTCNN


def _configure_gpu() -> str:
    """
    Configure TensorFlow GPU memory growth and return a human-readable
    device summary for startup logging.

    Memory growth must be set *before* any GPU operation is triggered.
    Without it TF allocates the entire GPU VRAM upfront, which causes
    OOM errors on shared or low-VRAM cards.
    """
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            names = [gpu.name for gpu in gpus]
            return f"GPU ✔  ({', '.join(names)})"
        except RuntimeError as e:
            # Memory growth must be set before GPUs have been initialized.
            return f"GPU config error (falling back to CPU): {e}"
    return "CPU (no GPU detected)"


class FaceDetector:
    """
    Wraps MTCNN face detection.

    MTCNN is TensorFlow-backed, so GPU acceleration is transparent once the
    TF runtime is configured correctly. The `_configure_gpu()` call in
    `_get_detector()` ensures memory growth is set before the first
    TF operation.
    """

    def __init__(self):
        self._detector = None
        self._device_info: str | None = None

    def _get_detector(self) -> MTCNN:
        if self._detector is None:
            self._device_info = _configure_gpu()
            print(f"[FaceDetector] Initializing MTCNN on {self._device_info}")
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
