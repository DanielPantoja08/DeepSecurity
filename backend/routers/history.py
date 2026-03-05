from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from typing import List
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
