import os
import re
import shutil
import time
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..auth.users import current_active_user

_NAME_RE = re.compile(r'^[a-zA-Z0-9_\- ]{1,64}$')


def _validate_name(name: str) -> None:
    """Reject names that could cause path traversal or shell injection."""
    if not _NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Nombre de identidad inválido. Use solo letras, números, espacios, guiones o guiones bajos (máx 64 caracteres).",
        )

router = APIRouter(
    prefix="/api/faces",
    tags=["faces"],
    dependencies=[Depends(current_active_user)],
)


def _db_path(request: Request) -> str:
    return request.app.state.db_path


def _reload_recognizer(request: Request):
    """Rebuild the in-memory embedding cache after DB changes."""
    recognizer = request.app.state.recognizer
    recognizer.reload_db()


@router.get("")
async def faces(request: Request):
    """Returns the list of registered identity names."""
    db = _db_path(request)
    os.makedirs(db, exist_ok=True)
    names = sorted(
        d for d in os.listdir(db) if os.path.isdir(os.path.join(db, d))
    )
    return {"faces": names}


@router.post("/{name}", status_code=201)
async def face(name: str, request: Request, files: List[UploadFile] = File(...)):
    """
    Registers or extends an identity by saving one or more face images.
    Invalidates the DeepFace representation cache after saving.
    """
    _validate_name(name)
    db = _db_path(request)
    os.makedirs(db, exist_ok=True)
    person_dir = os.path.join(db, name)
    is_new = not os.path.exists(person_dir)
    os.makedirs(person_dir, exist_ok=True)

    saved = 0
    for upload in files:
        content = await upload.read()
        timestamp = int(time.time() * 1000)
        ext = os.path.splitext(upload.filename)[1] if upload.filename else ".jpg"
        if not ext:
            ext = ".jpg"
        path = os.path.join(person_dir, f"face_{timestamp}_{saved}{ext}")
        with open(path, "wb") as f:
            f.write(content)
        saved += 1

    _reload_recognizer(request)

    return {
        "message": f"{'Created' if is_new else 'Updated'} identity '{name}'",
        "saved": saved,
    }


@router.delete("/{name}", status_code=204)
def delete_face(name: str, request: Request):
    """Deletes all images for an identity."""
    _validate_name(name)
    db = _db_path(request)
    person_dir = os.path.join(db, name)
    if not os.path.exists(person_dir):
        raise HTTPException(status_code=404, detail=f"Identity '{name}' not found")
    shutil.rmtree(person_dir)
    _reload_recognizer(request)
    return JSONResponse(status_code=204, content=None)
