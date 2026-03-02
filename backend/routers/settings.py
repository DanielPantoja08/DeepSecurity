import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/settings", tags=["settings"])

class Settings(BaseModel):
    db_path: str

@router.get("")
def get_settings(request: Request):
    return {"db_path": request.app.state.db_path}

@router.post("")
def update_settings(settings: Settings, request: Request):
    new_path = settings.db_path
    
    # Validation: check if path is absolute or exists
    # We allow relative paths if they are intended, but absolute is safer for external folders
    if not os.path.isabs(new_path):
        # Resolve relative to project root if needed
        pass
    
    if not os.path.exists(new_path):
        # Create it if it doesn't exist? Or error out? 
        # Better to error if the user is supposed to "select" an existing one, 
        # or maybe they want to create a new one. Let's allow creating it.
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

    request.app.state.db_path = new_path
    # We also need to update the recognizer's db_path
    request.app.state.recognizer.db_path = new_path
    
    return {"message": "Settings updated", "db_path": new_path}
