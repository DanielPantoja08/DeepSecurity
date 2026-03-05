import cv2
import os
import numpy as np
from datetime import datetime

class VideoRecorder:
    def __init__(self, output_dir="recordings"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.is_recording = False
        self.writer = None
        self.current_file = None
        self.start_time = None
        self.width = None
        self.height = None

    def start(self):
        """Prepares the recorder, but waits for the first frame to init VideoWriter."""
        if self.is_recording:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = os.path.join(self.output_dir, f"rec_{timestamp}.mp4")
        self.is_recording = True
        self.start_time = datetime.utcnow()
        self.writer = None # Will be init on first frame
        print(f"[VideoRecorder] Recording session enabled: {self.current_file}")

    def add_frame(self, frame_bgr: np.ndarray):
        if not self.is_recording:
            return

        h, w = frame_bgr.shape[:2]
        
        # Lazy init writer with actual frame dimensions
        if self.writer is None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(self.current_file, fourcc, 10.0, (w, h))
            self.width, self.height = w, h
            print(f"[VideoRecorder] Initialized VideoWriter: {w}x{h}")

        # Ensure frame matches initialized dimensions (OpenCV requirement)
        if w != self.width or h != self.height:
            frame_bgr = cv2.resize(frame_bgr, (self.width, self.height))

        self.writer.write(frame_bgr)

    def stop(self):
        if not self.is_recording:
            return None, None, None
        
        file_path = self.current_file
        start_time = self.start_time
        
        self.is_recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
        
        end_time = datetime.utcnow()
        print(f"[VideoRecorder] Stopped recording: {file_path}")
        
        self.current_file = None
        self.start_time = None
        self.width = None
        self.height = None
        
        return file_path, start_time, end_time
