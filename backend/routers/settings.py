import os
import threading
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/settings", tags=["settings"])


class Settings(BaseModel):
    db_path: str


@router.get("")
def get_settings(request: Request):
    return {"db_path": request.app.state.db_path or ""}


@router.post("")
def update_settings(settings: Settings, request: Request):
    new_path = settings.db_path

    if not new_path or not new_path.strip():
        raise HTTPException(status_code=400, detail="La ruta no puede estar vacía.")

    new_path = new_path.strip()

    if not os.path.exists(new_path):
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ruta inválida: {str(e)}")

    if not os.path.isdir(new_path):
        raise HTTPException(status_code=400, detail="La ruta debe ser un directorio.")

    request.app.state.db_path = new_path
    request.app.state.recognizer.db_path = new_path
    request.app.state.recognizer.reload_db()

    return {"message": "Settings updated", "db_path": new_path}


@router.post("/browse")
def browse_folder():
    """
    Opens a native OS folder picker dialog (tkinter) and returns
    the selected path.  Runs on a separate thread because tkinter
    needs its own main-loop context.
    """
    result = {"path": None, "error": None}

    def _pick():
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()          # hide the tiny root window
            root.attributes("-topmost", True)  # bring dialog to front
            folder = filedialog.askdirectory(title="Seleccionar carpeta de base de datos")
            root.destroy()
            result["path"] = folder if folder else None
        except Exception as e:
            result["error"] = str(e)

    # tkinter must run on its own thread in an async server context
    t = threading.Thread(target=_pick)
    t.start()
    t.join(timeout=120)  # wait up to 2 minutes for user selection

    if result["error"]:
        raise HTTPException(status_code=500, detail=result["error"])

    if not result["path"]:
        return {"path": None, "cancelled": True}

    return {"path": result["path"], "cancelled": False}
