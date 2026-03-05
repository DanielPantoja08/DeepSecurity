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

@router.get("/recordings", response_model=List[VideoRecording])
async def get_recordings(session: Session = Depends(get_session), limit: int = 50):
    statement = select(VideoRecording).order_by(VideoRecording.start_time.desc()).limit(limit)
    recordings = session.exec(statement).all()
    return recordings
