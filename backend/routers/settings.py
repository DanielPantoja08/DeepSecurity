import os
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth.users import current_active_user
from ..messages import (
    EMPTY_PATH,
    INVALID_PATH,
    NATIVE_PICKER_DISABLED,
    PATH_NOT_A_DIRECTORY,
)

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(current_active_user)],
)


class Settings(BaseModel):
    db_path: str
    antispoof_enabled: bool | None = None
    antispoof_threshold: float | None = None


@router.get("")
def get_settings(request: Request) -> dict:
    antispoof = getattr(request.app.state, "antispoof", None)
    return {
        "db_path": request.app.state.db_path or "",
        "antispoof_enabled": getattr(request.app.state, "antispoof_enabled", False),
        "antispoof_threshold": getattr(request.app.state, "antispoof_threshold", 0.5),
        "antispoof_available": antispoof.available if antispoof is not None else False,
    }


@router.post("")
async def update_settings(settings: Settings, request: Request) -> dict:
    new_path = settings.db_path

    if not new_path or not new_path.strip():
        raise HTTPException(status_code=400, detail=EMPTY_PATH)

    new_path = new_path.strip()

    if not os.path.exists(new_path):
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=INVALID_PATH.format(error=e))

    if not os.path.isdir(new_path):
        raise HTTPException(status_code=400, detail=PATH_NOT_A_DIRECTORY)

    # Serialize concurrent settings mutations so only one reload runs at a time.
    # Update every per-user recognizer that is currently cached.
    async with request.app.state.settings_lock:
        request.app.state.db_path = new_path
        for recognizer in request.app.state.recognizer_cache.values():
            recognizer.db_path = new_path
            recognizer.load_cache()

    if settings.antispoof_enabled is not None:
        request.app.state.antispoof_enabled = settings.antispoof_enabled

    if settings.antispoof_threshold is not None:
        request.app.state.antispoof_threshold = max(
            0.0, min(1.0, settings.antispoof_threshold)
        )

    return {
        "message": "Settings updated",
        "db_path": new_path,
        "antispoof_enabled": getattr(request.app.state, "antispoof_enabled", False),
        "antispoof_threshold": getattr(request.app.state, "antispoof_threshold", 0.5),
    }


@router.post("/browse")
def browse_folder() -> dict[str, Any]:
    """
    Opens a native OS folder picker dialog (tkinter) and returns the selected path.
    Runs on a separate thread because tkinter needs its own main-loop context.
    """
    if os.getenv("DISABLE_NATIVE_FILE_PICKER", "false").lower() == "true":
        raise HTTPException(status_code=501, detail=NATIVE_PICKER_DISABLED)

    result = {"path": None, "error": None}

    def _pick():
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="Seleccionar carpeta de base de datos")
            root.destroy()
            result["path"] = folder if folder else None
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=_pick)
    t.start()
    t.join(timeout=120)

    if result["error"]:
        raise HTTPException(status_code=500, detail=result["error"])

    if not result["path"]:
        return {"path": None, "cancelled": True}

    return {"path": result["path"], "cancelled": False}
