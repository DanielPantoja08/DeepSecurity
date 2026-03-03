from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import JSONResponse
import asyncio
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List

router = APIRouter(prefix="/api/recognize", tags=["recognition"])

# Shared thread pool for CPU-bound recognition work.
# Using 4 workers lets us recognise up to 4 faces simultaneously.
_pool = ThreadPoolExecutor(max_workers=4)


def _downscale(frame: np.ndarray, max_width: int = 640) -> tuple[np.ndarray, float]:
    """
    Down-scale *frame* so the widest side is at most *max_width*.
    Returns (resized_frame, scale_factor).
    """
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame, 1.0
    scale = max_width / w
    new_size = (max_width, int(h * scale))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA), scale


@router.post("")
async def frame(request: Request, file: UploadFile = File(...)):
    """
    Receives a JPEG/PNG frame captured from the browser,
    runs MTCNN face detection + VGG-Face recognition,
    and returns bounding boxes with identity labels.
    """
    detector = request.app.state.detector
    recognizer = request.app.state.recognizer

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame_bgr is None:
        return JSONResponse(status_code=400, content={"detail": "Invalid image data"})

    # MTCNN expects RGB
    rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # ── 1. Down-scale for faster detection ────────────────────────
    small_frame, scale = _downscale(rgb_frame, max_width=640)

    # ── 2. Detect (single MTCNN pass on the small frame) ─────────
    detections = detector.detect_faces(small_frame)

    # Filter weak detections and scale boxes back to original size
    valid_faces: list[dict] = []
    for face_obj in detections:
        confidence = face_obj["confidence"]
        if confidence <= 0.9:
            continue
        x, y, w, h = face_obj["box"]
        # Scale to original resolution for cropping
        ox = max(0, int(x / scale))
        oy = max(0, int(y / scale))
        ow = int(w / scale)
        oh = int(h / scale)
        face_crop = rgb_frame[oy : oy + oh, ox : ox + ow]
        if face_crop.size == 0:
            continue
        valid_faces.append({
            "crop": face_crop,
            "confidence": confidence,
            "box": {"x": ox, "y": oy, "w": ow, "h": oh},
        })

    if not valid_faces:
        return {"faces": []}

    # ── 3. Recognise all faces in PARALLEL ────────────────────────
    loop = asyncio.get_running_loop()

    async def _recognise(crop: np.ndarray):
        return await loop.run_in_executor(_pool, recognizer.find_identity, crop)

    tasks = [_recognise(f["crop"]) for f in valid_faces]
    identities = await asyncio.gather(*tasks)

    # ── 4. Build response ─────────────────────────────────────────
    results: List[dict] = []
    for face_info, (name, distance) in zip(valid_faces, identities):
        results.append({
            "name": name,
            "confidence_detection": round(face_info["confidence"], 3),
            "similarity": round(float(1 - distance), 3),
            "box": face_info["box"],
        })

    return {"faces": results}
