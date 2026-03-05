import os
from fastapi import APIRouter, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse
import asyncio
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List
from sqlmodel import Session, select
from ..db import get_session, RecognitionLog, VideoRecording
from datetime import datetime

router = APIRouter(prefix="/api/recognize", tags=["recognition"])

# Shared thread pool for CPU-bound recognition work.
_pool = ThreadPoolExecutor(max_workers=4)


def _downscale(frame: np.ndarray, max_width: int = 640) -> tuple[np.ndarray, float]:
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame, 1.0
    scale = max_width / w
    new_size = (max_width, int(h * scale))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA), scale


@router.post("")
async def frame(
    request: Request, 
    file: UploadFile = File(...), 
    session: Session = Depends(get_session)
):
    detector = request.app.state.detector
    recognizer = request.app.state.recognizer
    recorder = request.app.state.recorder

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame_bgr is None:
        return JSONResponse(status_code=400, content={"detail": "Invalid image data"})

    # Add frame to recorder if active
    if recorder.is_recording:
        recorder.add_frame(frame_bgr)

    # MTCNN expects RGB
    rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    small_frame, scale = _downscale(rgb_frame, max_width=640)

    detections = detector.detect_faces(small_frame)

    valid_faces: list[dict] = []
    for face_obj in detections:
        confidence = face_obj["confidence"]
        if confidence <= 0.9:
            continue
        x, y, w, h = face_obj["box"]
        ox, oy = max(0, int(x / scale)), max(0, int(y / scale))
        ow, oh = int(w / scale), int(h / scale)
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

    loop = asyncio.get_running_loop()
    async def _recognise(crop: np.ndarray):
        return await loop.run_in_executor(_pool, recognizer.find_identity, crop)

    tasks = [_recognise(f["crop"]) for f in valid_faces]
    identities = await asyncio.gather(*tasks)

    results: List[dict] = []
    for face_info, (name, distance) in zip(valid_faces, identities):
        similarity = round(float(1 - distance), 3)
        results.append({
            "name": name,
            "confidence_detection": round(face_info["confidence"], 3),
            "similarity": similarity,
            "box": face_info["box"],
        })
        
        # Log to DB
        recording_id = getattr(request.app.state, "current_recording_id", None)
        log = RecognitionLog(
            person_name=name,
            confidence=similarity,
            timestamp=datetime.utcnow(),
            video_id=recording_id
        )
        session.add(log)
    
    session.commit()
    return {"faces": results}


@router.post("/start_recording")
async def start_recording(request: Request, session: Session = Depends(get_session)):
    recorder = request.app.state.recorder
    recorder.start()
    
    # Create recording entry early to have an ID for logs
    recording = VideoRecording(
        file_path=recorder.current_file,
        start_time=recorder.start_time
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)
    
    request.app.state.current_recording_id = recording.id
    return {"status": "recording_started", "id": recording.id}


@router.get("/status")
async def get_status(request: Request):
    recorder = request.app.state.recorder
    return {
        "is_recording": recorder.is_recording,
        "current_file": os.path.basename(recorder.current_file) if recorder.current_file else None
    }


@router.post("/stop_recording")
async def stop_recording(request: Request, session: Session = Depends(get_session)):
    recorder = request.app.state.recorder
    recording_id = getattr(request.app.state, "current_recording_id", None)
    
    file_path, start_time, end_time = recorder.stop()
    
    if recording_id:
        statement = select(VideoRecording).where(VideoRecording.id == recording_id)
        recording = session.exec(statement).first()
        if recording:
            recording.end_time = end_time
            session.add(recording)
            session.commit()
            session.refresh(recording)
            request.app.state.current_recording_id = None
            return {"status": "recording_stopped", "id": recording.id, "path": file_path}
    
    request.app.state.current_recording_id = None
    return {"status": "no_active_recording"}
