from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from typing import List

router = APIRouter(prefix="/api/recognize", tags=["recognition"])


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

    detections = detector.detect_faces(rgb_frame)
    results: List[dict] = []

    for face_obj in detections:
        confidence = face_obj["confidence"]

        if confidence > 0.9:  # Filter out weak detections
            x, y, w, h = face_obj["box"]
            
            # Clamp to frame dimensions
            x, y = max(0, x), max(0, y)
            face_crop = rgb_frame[y : y + h, x : x + w]

            if face_crop.size > 0:
                name, distance = recognizer.find_identity(face_crop)
            else:
                name, distance = "Unknown", 1.0

            results.append(
                {
                    "name": name,
                    "confidence_detection": round(confidence, 3),
                    "similarity": round(float(1 - distance), 3),
                    "box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                }
            )

    return {"faces": results}
