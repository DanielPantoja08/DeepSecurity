from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

class VideoRecording(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Relationship to logs
    logs: List["RecognitionLog"] = Relationship(back_populates="video")

class RecognitionLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    person_name: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    video_id: Optional[int] = Field(default=None, foreign_key="videorecording.id")
    video: Optional[VideoRecording] = Relationship(back_populates="logs")
