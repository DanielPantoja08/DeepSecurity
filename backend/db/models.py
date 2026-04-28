import uuid as _uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Boolean, Index, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Camera(Base):
    __tablename__ = "camera"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    device_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_id_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    recordings: Mapped[List["VideoRecording"]] = relationship(back_populates="camera", passive_deletes=True)
    logs: Mapped[List["RecognitionLog"]] = relationship(back_populates="camera", passive_deletes=True)


class VideoRecording(Base):
    __tablename__ = "videorecording"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    camera_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("camera.id", ondelete="SET NULL"), nullable=True, index=True
    )

    logs: Mapped[List["RecognitionLog"]] = relationship(back_populates="video")
    camera: Mapped[Optional["Camera"]] = relationship(back_populates="recordings")


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
    is_spoof: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    antispoof_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    camera_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("camera.id", ondelete="SET NULL"), nullable=True
    )

    video: Mapped[Optional["VideoRecording"]] = relationship(back_populates="logs")
    camera: Mapped[Optional["Camera"]] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_log_timestamp", "timestamp"),
        Index("ix_log_person", "person_name"),
        Index("ix_log_camera_timestamp", "camera_id", "timestamp"),
    )
