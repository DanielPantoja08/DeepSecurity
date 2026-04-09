from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.users import current_active_user, get_user_from_query_token
from ..db import get_async_session, RecognitionLog, VideoRecording

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
)


# ── Response schemas ────────────────────────────────────────────────────────

class RecognitionLogOut(BaseModel):
    id: int
    person_name: str
    confidence: float
    timestamp: datetime
    video_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/logs", response_model=List[RecognitionLogOut])
async def get_logs(
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    _user=Depends(current_active_user),
):
    result = await session.execute(
        select(RecognitionLog)
        .order_by(RecognitionLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/recordings")
async def get_recordings(
    session: AsyncSession = Depends(get_async_session),
    limit: int = 50,
    _user=Depends(current_active_user),
):
    result = await session.execute(
        select(VideoRecording).order_by(VideoRecording.start_time.desc()).limit(limit)
    )
    recordings = result.scalars().all()

    enriched = []
    for rec in recordings:
        people_result = await session.execute(
            select(RecognitionLog.person_name)
            .where(RecognitionLog.video_id == rec.id)
            .distinct()
        )
        unique_people = people_result.scalars().all()
        enriched.append(
            {
                "id": rec.id,
                "file_path": rec.file_path,
                "start_time": rec.start_time,
                "end_time": rec.end_time,
                "detected_people": unique_people,
            }
        )

    return enriched


@router.get("/recordings/{recording_id}/file")
async def get_recording_file(
    recording_id: int,
    request: Request,
    download: bool = False,
    session: AsyncSession = Depends(get_async_session),
    _user=Depends(get_user_from_query_token),
):
    import os

    recording = await session.get(VideoRecording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail="Video file not found on server")

    if download:
        return FileResponse(
            path=recording.file_path,
            filename=os.path.basename(recording.file_path),
            media_type="video/mp4",
        )

    file_size = os.path.getsize(recording.file_path)
    range_header = request.headers.get("range")

    if range_header:
        try:
            range_type, range_val = range_header.split("=")
            if range_type != "bytes":
                raise ValueError()
            start_str, end_str = range_val.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1

            if start >= file_size:
                raise HTTPException(
                    status_code=416, detail="Requested Range Not Satisfiable"
                )

            chunk_size = (end - start) + 1

            def file_iterator():
                with open(recording.file_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        to_read = min(remaining, 1024 * 1024)
                        data = f.read(to_read)
                        if not data:
                            break
                        yield data
                        remaining -= len(data)

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Type": "video/mp4",
            }
            return StreamingResponse(file_iterator(), status_code=206, headers=headers)
        except Exception:
            pass

    return FileResponse(
        path=recording.file_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
