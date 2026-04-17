import asyncio
import os
import re
import shutil
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..auth.users import current_active_user
from ..core.recognizer import FaceRecognizer
from ..messages import INVALID_IDENTITY_NAME, IDENTITY_NOT_FOUND

_NAME_RE = re.compile(r'^[a-zA-Z0-9_\- ]{1,64}$')


def _validate_name(name: str) -> None:
    """Reject names that could cause path traversal or shell injection."""
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=400, detail=INVALID_IDENTITY_NAME)

router = APIRouter(
    prefix="/api/faces",
    tags=["faces"],
    dependencies=[Depends(current_active_user)],
)


def _user_db_path(request: Request, user_id: str) -> str:
    return os.path.join(request.app.state.db_path, user_id)


def _get_user_recognizer(request: Request, user_id: str) -> FaceRecognizer:
    cache: dict = request.app.state.recognizer_cache
    if user_id not in cache:
        user_path = _user_db_path(request, user_id)
        cache[user_id] = FaceRecognizer(db_path=user_path)
    return cache[user_id]


def _rebuild_cache(recognizer: object) -> None:
    recognizer.reload_db()  # type: ignore[attr-defined]


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


@router.get("")
async def faces(
    request: Request,
    user=Depends(current_active_user),
) -> dict[str, list[str]]:
    """Returns the list of registered identity names for the current user."""
    db = _user_db_path(request, str(user.id))
    await asyncio.to_thread(os.makedirs, db, exist_ok=True)
    entries = await asyncio.to_thread(os.listdir, db)
    names = sorted(d for d in entries if os.path.isdir(os.path.join(db, d)))
    return {"faces": names}


@router.post("/{name}", status_code=201)
async def face(
    name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user=Depends(current_active_user),
) -> dict[str, object]:
    """Registers or extends an identity for the current user."""
    _validate_name(name)
    db = _user_db_path(request, str(user.id))
    await asyncio.to_thread(os.makedirs, db, exist_ok=True)
    person_dir = os.path.join(db, name)
    is_new = not os.path.exists(person_dir)
    await asyncio.to_thread(os.makedirs, person_dir, exist_ok=True)

    saved = 0
    for upload in files:
        content = await upload.read()
        timestamp = int(time.time() * 1000)
        ext = os.path.splitext(upload.filename)[1] if upload.filename else ".jpg"
        if not ext:
            ext = ".jpg"
        path = os.path.join(person_dir, f"face_{timestamp}_{saved}{ext}")
        await asyncio.to_thread(_write_bytes, path, content)
        saved += 1

    recognizer = _get_user_recognizer(request, str(user.id))
    background_tasks.add_task(_rebuild_cache, recognizer)

    return {
        "message": f"{'Created' if is_new else 'Updated'} identity '{name}'",
        "saved": saved,
    }


@router.delete("/{name}", status_code=204)
async def delete_face(
    name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user=Depends(current_active_user),
) -> JSONResponse:
    """Deletes all images for an identity belonging to the current user."""
    _validate_name(name)
    db = _user_db_path(request, str(user.id))
    person_dir = os.path.join(db, name)
    if not os.path.exists(person_dir):
        raise HTTPException(status_code=404, detail=IDENTITY_NOT_FOUND.format(name=name))
    await asyncio.to_thread(shutil.rmtree, person_dir)
    recognizer = _get_user_recognizer(request, str(user.id))
    background_tasks.add_task(_rebuild_cache, recognizer)
    return JSONResponse(status_code=204, content=None)
