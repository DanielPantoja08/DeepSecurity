import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.users import current_active_user
from ..db import get_async_session
from ..db.models import Camera

router = APIRouter(
    prefix="/api/cameras",
    tags=["cameras"],
    dependencies=[Depends(current_active_user)],
)


class CameraCreate(BaseModel):
    name: str
    device_label: Optional[str] = None
    device_id_hash: Optional[str] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    device_label: Optional[str] = None
    device_id_hash: Optional[str] = None
    is_active: Optional[bool] = None


class CameraOut(BaseModel):
    id: str
    name: str
    device_label: Optional[str] = None
    device_id_hash: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=List[CameraOut])
async def list_cameras(
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    result = await session.execute(
        select(Camera)
        .where(Camera.user_id == str(user.id))
        .order_by(Camera.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(
    body: CameraCreate,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    cam = Camera(
        id=str(uuid.uuid4()),
        name=body.name,
        device_label=body.device_label,
        device_id_hash=body.device_id_hash,
        user_id=str(user.id),
    )
    session.add(cam)
    await session.commit()
    await session.refresh(cam)
    return cam


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: str,
    body: CameraUpdate,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    cam = await session.get(Camera, camera_id)
    if not cam or cam.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    if body.name is not None:
        cam.name = body.name
    if body.device_label is not None:
        cam.device_label = body.device_label
    if body.device_id_hash is not None:
        cam.device_id_hash = body.device_id_hash
    if body.is_active is not None:
        cam.is_active = body.is_active
    await session.commit()
    await session.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_active_user),
):
    cam = await session.get(Camera, camera_id)
    if not cam or cam.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    await session.delete(cam)
    await session.commit()
