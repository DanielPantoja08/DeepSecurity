import os
import time
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import List

router = APIRouter(prefix="/api/faces", tags=["faces"])


def _db_path(request: Request) -> str:
    return request.app.state.db_path


def _invalidate_cache(db: str):
    pkl = os.path.join(db, "representations_vgg_face.pkl")
    if os.path.exists(pkl):
        os.remove(pkl)


@router.get("")
def list_faces(request: Request):
    """Returns the list of registered identity names."""
    db = _db_path(request)
    os.makedirs(db, exist_ok=True)
    names = sorted(
        d for d in os.listdir(db) if os.path.isdir(os.path.join(db, d))
    )
    return {"faces": names}


@router.post("/{name}", status_code=201)
async def register_face(name: str, request: Request, files: List[UploadFile] = File(...)):
    """
    Registers or extends an identity by saving one or more face images.
    Invalidates the DeepFace representation cache after saving.
    """
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

    _invalidate_cache(db)

    return {
        "message": f"{'Created' if is_new else 'Updated'} identity '{name}'",
        "saved": saved,
    }


@router.delete("/{name}", status_code=204)
def delete_face(name: str, request: Request):
    """Deletes all images for an identity."""
    db = _db_path(request)
    person_dir = os.path.join(db, name)
    if not os.path.exists(person_dir):
        raise HTTPException(status_code=404, detail=f"Identity '{name}' not found")
    shutil.rmtree(person_dir)
    _invalidate_cache(db)
    return JSONResponse(status_code=204, content=None)
