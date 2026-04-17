from datetime import datetime
from typing import Optional, List
from sqlalchemy import Index, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base




class VideoRecording(Base):
    __tablename__ = "videorecording"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    logs: Mapped[List["RecognitionLog"]] = relationship(back_populates="video")


class RecognitionLog(Base):
    __tablename__ = "recognitionlog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_name: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("videorecording.id"), nullable=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    video: Mapped[Optional["VideoRecording"]] = relationship(back_populates="logs")

    # 4.3: indexes for history query performance
    __table_args__ = (
        Index("ix_log_timestamp", "timestamp"),
        Index("ix_log_person", "person_name"),
    )
