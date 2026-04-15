import secrets
from datetime import datetime, timedelta
from typing import Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.users import current_active_user
from ..db import get_async_session, RecognitionLog, VideoRecording
from ..messages import INVALID_DOWNLOAD_TOKEN, RECORDING_NOT_FOUND, VIDEO_FILE_NOT_FOUND

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
)

# ── One-time download tokens ─────────────────────────────────────────────────
# Maps token -> {recording_id, expires_at}
_download_tokens: dict[str, dict] = {}
_TOKEN_TTL_SECONDS = 300  # 5 minutes — long enough for range-request video streaming


def _cleanup_tokens() -> None:
    """Remove all expired tokens from the in-memory store."""
    now = datetime.utcnow()
    expired = [t for t, v in _download_tokens.items() if v["expires_at"] < now]
    for t in expired:
        del _download_tokens[t]


def _validate_download_token(token: str, recording_id: int) -> bool:  # noqa: D103
    _cleanup_tokens()
    data = _download_tokens.get(token)
    if not data:
        return False
    if data["recording_id"] != recording_id:
        return False
    return True


# ── Response schemas ────────────────────────────────────────────────────────

class RecognitionLogOut(BaseModel):
    id: int
    person_name: str
    confidence: float
    timestamp: datetime
    video_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    cursor: Optional[int] = None,
    _user=Depends(current_active_user),
) -> dict[str, Any]:
    """
    Returns up to ``limit`` recognition log entries ordered by id DESC.
    Pass ``cursor=<last_id>`` from the previous page to get the next page.
    Response: ``{ items: [...], next_cursor: int | null }``
    """
    query = (
        select(RecognitionLog)
        .order_by(RecognitionLog.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(RecognitionLog.id < cursor)

    result = await session.execute(query)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor: Optional[int] = items[-1].id if has_more and items else None

    return {
        "items": [RecognitionLogOut.model_validate(r) for r in items],
        "next_cursor": next_cursor,
    }


@router.get("/recordings")
async def get_recordings(
    session: AsyncSession = Depends(get_async_session),
    limit: int = 50,
    cursor: Optional[int] = None,
    _user=Depends(current_active_user),
) -> dict[str, Any]:
    """
    Returns up to ``limit`` recordings ordered by id DESC.
    Pass ``cursor=<last_id>`` from the previous page to get the next page.
    Response: ``{ items: [...], next_cursor: int | null }``
    """
    query = (
        select(VideoRecording)
        .order_by(VideoRecording.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(VideoRecording.id < cursor)

    result = await session.execute(query)
    recordings = result.scalars().all()

    has_more = len(recordings) > limit
    page = recordings[:limit]

    enriched: list[dict[str, Any]] = []
    for rec in page:
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

    next_cursor: Optional[int] = page[-1].id if has_more and page else None
    return {"items": enriched, "next_cursor": next_cursor}


@router.post("/recordings/{recording_id}/download-token")
async def create_download_token(
    recording_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user=Depends(current_active_user),
):
    """
    Issues a short-lived download token for a specific recording.
    The token must be passed as ?download_token= when fetching the video file,
    replacing the insecure practice of passing the user JWT in the URL.
    """
    recording = await session.get(VideoRecording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail=RECORDING_NOT_FOUND)

    _cleanup_tokens()
    token = secrets.token_urlsafe(32)
    _download_tokens[token] = {
        "recording_id": recording_id,
        "expires_at": datetime.utcnow() + timedelta(seconds=_TOKEN_TTL_SECONDS),
    }
    return {"token": token, "expires_in": _TOKEN_TTL_SECONDS}


@router.get("/recordings/{recording_id}/file")
async def get_recording_file(
    recording_id: int,
    request: Request,
    download: bool = False,
    download_token: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Streams or downloads a recording file.
    Requires a short-lived download token obtained from POST /recordings/{id}/download-token.
    """
    import os

    if not download_token or not _validate_download_token(download_token, recording_id):
        raise HTTPException(status_code=401, detail=INVALID_DOWNLOAD_TOKEN)

    recording = await session.get(VideoRecording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail=RECORDING_NOT_FOUND)

    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail=VIDEO_FILE_NOT_FOUND)

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
