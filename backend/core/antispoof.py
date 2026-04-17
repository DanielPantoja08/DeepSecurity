"""
Anti-spoofing checker wrapping DeepFace's FasNet (MiniFASNet ensemble).

FasNet requires PyTorch. If torch is not installed, all checks return (True, 1.0)
so the rest of the pipeline is unaffected. Install with:

    pip install torch  (CPU-only: ~160 MB)
    # or for the full CUDA build: pip install torch --index-url https://download.pytorch.org/whl/cu121
"""

import numpy as np


class AntiSpoofChecker:
    """Singleton wrapper around DeepFace's FasNet anti-spoofing model.

    Thread-safe for concurrent read (inference) calls once the model is loaded.
    PyTorch models in eval mode with torch.no_grad() are safe to call from
    multiple threads simultaneously.
    """

    def __init__(self) -> None:
        self._model = None
        self._available: bool | None = None  # None = not yet probed

    @property
    def available(self) -> bool:
        """True if PyTorch is installed and FasNet can be loaded."""
        if self._available is None:
            try:
                import torch  # noqa: F401
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def _get_model(self):
        if self._model is None:
            from deepface.modules import modeling
            self._model = modeling.build_model(task="spoofing", model_name="Fasnet")
        return self._model

    def check(
        self,
        frame: np.ndarray,
        facial_area: tuple[int, int, int, int],
    ) -> tuple[bool, float]:
        """Run anti-spoofing on a detected face region.

        Args:
            frame: Full RGB image (H×W×3, uint8) — FasNet crops internally at
                   scales 2.7× and 4.0× of 80×80, so the full frame is needed.
            facial_area: Bounding box of the face as (x, y, w, h) in pixel coords
                         of ``frame``.

        Returns:
            (is_real, antispoof_score) where is_real=True means a live face was
            detected and score is in [0, 1] (higher = more real).
            Returns (True, 1.0) gracefully when PyTorch is not installed.
        """
        if not self.available:
            return True, 1.0
        try:
            model = self._get_model()
            is_real, score = model.analyze(img=frame, facial_area=facial_area)
            return bool(is_real), float(score)
        except Exception:
            # Never let an anti-spoofing failure break the recognition pipeline.
            return True, 1.0
