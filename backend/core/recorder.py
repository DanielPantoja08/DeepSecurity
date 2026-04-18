import logging
import os
import subprocess
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoRecorder:
    def __init__(self, output_dir: str = "recordings") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.is_recording: bool = False
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_file: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None

    def start(self) -> None:
        """Prepares the recorder, but waits for the first frame to init VideoWriter."""
        if self.is_recording:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = os.path.join(self.output_dir, f"rec_{timestamp}.mp4")
        self.is_recording = True
        self.start_time = datetime.utcnow()
        self.writer = None  # Lazy-initialised on first frame
        logger.info("Recording session enabled: %s", self.current_file)

    def add_frame(self, frame_bgr: np.ndarray) -> None:
        if not self.is_recording:
            return

        h, w = frame_bgr.shape[:2]

        # Lazy init writer with actual frame dimensions
        if self.writer is None:
            # Try AVC1 (H.264) for browser compatibility, fallback to MP4V
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            self.writer = cv2.VideoWriter(self.current_file, fourcc, 10.0, (w, h))

            if not self.writer.isOpened():
                logger.warning("avc1 codec failed, falling back to mp4v")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self.writer = cv2.VideoWriter(self.current_file, fourcc, 10.0, (w, h))

            self.width, self.height = w, h
            logger.info("VideoWriter initialised: %dx%d", w, h)

        # Ensure frame matches initialized dimensions (OpenCV requirement)
        if w != self.width or h != self.height:
            frame_bgr = cv2.resize(frame_bgr, (self.width, self.height))

        self.writer.write(frame_bgr)

    def stop(self) -> tuple[Optional[str], Optional[datetime], Optional[datetime]]:
        """
        Stops recording, releases the VideoWriter, and post-processes the file
        with FFmpeg for web compatibility (H.264 + faststart).

        This method is synchronous and may take several seconds due to FFmpeg.
        Call it via ``asyncio.to_thread(recorder.stop)`` from async contexts.
        """
        if not self.is_recording:
            return None, None, None

        file_path = self.current_file
        start_time = self.start_time

        self.is_recording = False
        if self.writer:
            self.writer.release()
            self.writer = None

        end_time = datetime.utcnow()

        # Post-process with FFmpeg to ensure web compatibility and add faststart
        if file_path and os.path.exists(file_path):
            temp_file = file_path.replace(".mp4", "_temp.mp4")
            try:
                os.rename(file_path, temp_file)
                cmd = [
                    "ffmpeg", "-y", "-i", temp_file,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    file_path,
                ]
                logger.info("Post-processing: %s", " ".join(cmd))
                subprocess.run(cmd, check=True, capture_output=True)
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                logger.info("Web-optimized file created: %s", file_path)
            except Exception as e:
                logger.error("Post-processing failed: %s", e)
                # Restore original file if FFmpeg didn't produce output
                if os.path.exists(temp_file) and not os.path.exists(file_path):
                    os.rename(temp_file, file_path)

        logger.info("Stopped recording: %s", file_path)

        self.current_file = None
        self.start_time = None
        self.width = None
        self.height = None

        return file_path, start_time, end_time
