import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.users import current_active_user
from ..db import get_async_session, RecognitionLog, VideoRecording
from ..limiter import limiter
from ..messages import IMAGE_TOO_LARGE, UNSUPPORTED_IMAGE_FORMAT
from .faces import _get_user_recognizer

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_JPEG_SIG = b'\xff\xd8\xff'
_PNG_SIG = b'\x89PNG'
_WEBP_RIFF = b'RIFF'
_WEBP_MARKER = b'WEBP'


def _is_allowed_image(data: bytes) -> bool:  # noqa: D103
    if len(data) < 12:
        return False
    if data[:3] == _JPEG_SIG:
        return True
    if data[:4] == _PNG_SIG:
        return True
    if data[:4] == _WEBP_RIFF and data[8:12] == _WEBP_MARKER:
        return True
    return False

router = APIRouter(
    prefix="/api/recognize",
    tags=["recognition"],
    dependencies=[Depends(current_active_user)],
)

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
#@limiter.limit("30/minute")
async def frame(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    detector = request.app.state.detector
    recognizer = _get_user_recognizer(request, str(user.id))
    recorder = request.app.state.recorder

    contents = await file.read()

    if len(contents) > _MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=413, content={"detail": IMAGE_TOO_LARGE})

    if not _is_allowed_image(contents):
        return JSONResponse(status_code=415, content={"detail": UNSUPPORTED_IMAGE_FORMAT})

    nparr = np.frombuffer(contents, np.uint8)
    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame_bgr is None:
        return JSONResponse(status_code=400, content={"detail": "Invalid image data"})

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
        valid_faces.append(
            {
                "crop": face_crop,
                "confidence": confidence,
                "box": {"x": ox, "y": oy, "w": ow, "h": oh},
            }
        )

    if not valid_faces:
        if recorder.is_recording:
            recorder.add_frame(frame_bgr)
        return {"faces": []}

    loop = asyncio.get_running_loop()

    async def _recognise(crop: np.ndarray):
        return await loop.run_in_executor(_pool, recognizer.find_identity, crop)

    tasks = [_recognise(f["crop"]) for f in valid_faces]
    identities = await asyncio.gather(*tasks)

    # Anti-spoofing: run in parallel per-face if enabled and PyTorch is available.
    antispoof = request.app.state.antispoof
    antispoof_enabled = getattr(request.app.state, "antispoof_enabled", False)
    antispoof_threshold = getattr(request.app.state, "antispoof_threshold", 0.5)
    spoof_results = None

    if antispoof_enabled and antispoof.available:
        async def _check_spoof(bbox: dict):
            return await loop.run_in_executor(
                _pool,
                antispoof.check,
                rgb_frame,
                (bbox["x"], bbox["y"], bbox["w"], bbox["h"]),
            )
        spoof_tasks = [_check_spoof(f["box"]) for f in valid_faces]
        spoof_results = await asyncio.gather(*spoof_tasks)

    results: List[dict] = []
    recording_id = getattr(request.app.state, "current_recording_id", None)
    record_frame = frame_bgr.copy() if recorder.is_recording else None

    for i, (face_info, (name, distance)) in enumerate(zip(valid_faces, identities)):
        similarity = round(float(1 - distance), 3)
        entry: dict = {
            "name": name,
            "confidence_detection": round(face_info["confidence"], 3),
            "similarity": similarity,
            "box": face_info["box"],
        }

        is_spoof = False
        if spoof_results is not None:
            raw_is_real, score = spoof_results[i]            
            entry["is_real"] = raw_is_real
            entry["antispoof_score"] = round(score, 3)
            is_spoof = not raw_is_real

        results.append(entry)

        # Only persist logs while a recording is active
        if recorder.is_recording:
            two_secs_ago = datetime.utcnow() - timedelta(seconds=2)
            recent = await session.execute(
                select(RecognitionLog)
                .where(RecognitionLog.person_name == name)
                .where(RecognitionLog.timestamp >= two_secs_ago)
                .limit(1)
            )
            if recent.scalars().first() is None:
                log = RecognitionLog(
                    person_name=name,
                    confidence=similarity,
                    timestamp=datetime.utcnow(),
                    video_id=recording_id,
                    user_id=str(user.id),
                    is_spoof=is_spoof,
                    antispoof_score=entry.get("antispoof_score"),
                )
                session.add(log)

        if record_frame is not None:
            box = face_info["box"]
            if name == "Unknown":
                bgr_color = (68, 68, 239)   # red — unknown face (regardless of spoof)
            elif is_spoof:
                bgr_color = (0, 165, 245)   # amber — known face but spoofing detected
            else:
                bgr_color = (129, 185, 16)  # green — known face, real
            cv2.rectangle(
                record_frame,
                (box["x"], box["y"]),
                (box["x"] + box["w"], box["y"] + box["h"]),
                bgr_color,
                2,
            )
            if name == "Unknown":
                label = f"Unknown {int(similarity * 100)}%"
            
            else:
                label = f"{name} {int(similarity * 100)}%"
            cv2.putText(
                record_frame,
                label,
                (box["x"], box["y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                bgr_color,
                2,
            )

    if record_frame is not None:
        recorder.add_frame(record_frame)

    await session.commit()
    return {"faces": results}


@router.post("/start_recording")
async def start_recording(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    recorder = request.app.state.recorder
    recorder.start()

    recording = VideoRecording(
        file_path=recorder.current_file,
        start_time=recorder.start_time,
        user_id=str(user.id),
    )
    session.add(recording)
    await session.commit()
    await session.refresh(recording)

    request.app.state.current_recording_id = recording.id
    return {"status": "recording_started", "id": recording.id}


@router.get("/status")
async def get_status(request: Request) -> dict[str, object]:
    recorder = request.app.state.recorder
    return {
        "is_recording": recorder.is_recording,
        "current_file": (
            os.path.basename(recorder.current_file) if recorder.current_file else None
        ),
    }


@router.post("/stop_recording")
async def stop_recording(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    recorder = request.app.state.recorder
    recording_id = getattr(request.app.state, "current_recording_id", None)

    # recorder.stop() runs FFmpeg — offload to a thread to avoid blocking the event loop
    file_path, start_time, end_time = await asyncio.to_thread(recorder.stop)

    if recording_id:
        result = await session.execute(
            select(VideoRecording).where(VideoRecording.id == recording_id)
        )
        recording = result.scalars().first()
        if recording:
            recording.end_time = end_time
            if file_path:
                recording.file_path = file_path
            session.add(recording)
            await session.commit()
            await session.refresh(recording)
            request.app.state.current_recording_id = None
            return {
                "status": "recording_stopped",
                "id": recording.id,
                "path": file_path,
            }

    request.app.state.current_recording_id = None
    return {"status": "no_active_recording"}
