from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select
from typing import List
import os
from ..db import get_session, RecognitionLog, VideoRecording

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/logs", response_model=List[RecognitionLog])
async def get_logs(session: Session = Depends(get_session), limit: int = 100):
    statement = select(RecognitionLog).order_by(RecognitionLog.timestamp.desc()).limit(limit)
    logs = session.exec(statement).all()
    return logs

@router.get("/recordings")
async def get_recordings(session: Session = Depends(get_session), limit: int = 50):
    statement = select(VideoRecording).order_by(VideoRecording.start_time.desc()).limit(limit)
    recordings = session.exec(statement).all()
    
    # Enrich recordings with consolidated unique people
    enriched = []
    for rec in recordings:
        # Get unique person names for this recording
        unique_people = session.exec(
            select(RecognitionLog.person_name)
            .where(RecognitionLog.video_id == rec.id)
            .distinct()
        ).all()
        
        rec_data = rec.model_dump()
        rec_data["detected_people"] = unique_people
        enriched.append(rec_data)
        
    return enriched

@router.get("/recordings/{recording_id}/file")
async def get_recording_file(
    recording_id: int, 
    request: Request,
    download: bool = False, 
    session: Session = Depends(get_session)
):
    recording = session.get(VideoRecording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail="Video file not found on server")
    
    if download:
        return FileResponse(
            path=recording.file_path,
            filename=os.path.basename(recording.file_path),
            media_type="video/mp4"
        )

    # Range request handling for video playback
    file_size = os.path.getsize(recording.file_path)
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range: "bytes=start-end"
        try:
            range_type, range_val = range_header.split("=")
            if range_type != "bytes":
                raise ValueError()
            
            start_str, end_str = range_val.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
            
            # Constraints
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")
            
            chunk_size = (end - start) + 1
            
            def file_iterator():
                with open(recording.file_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        to_read = min(remaining, 1024 * 1024) # 1MB chunks
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
            # Fallback to full file if range parsing fails
            pass

    return FileResponse(
        path=recording.file_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )
