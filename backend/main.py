"""
DeepSecurity — FastAPI Backend
Exposes REST endpoints for face detection, recognition, and identity management.

Run from the project root (DeepSecurity/):
    uvicorn backend.main:app --reload --port 8000
"""
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Ensure the project root is on sys.path so db/ relative paths resolve correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.core.detector import FaceDetector
from backend.core.recognizer import FaceRecognizer
from backend.core.recorder import VideoRecorder
from backend.routers import recognition, faces, settings, history
from backend.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[DeepSecurity] Loading AI models…")
    
    # Initialize DB
    create_db_and_tables()
    
    db_path = os.getenv("DB_PATH", os.path.join(ROOT_DIR, "db", "faces"))
    os.makedirs(db_path, exist_ok=True)
    
    app.state.detector = FaceDetector()
    app.state.recognizer = FaceRecognizer(db_path=db_path)
    app.state.recorder = VideoRecorder(output_dir=os.path.join(ROOT_DIR, "recordings"))
    app.state.db_path = db_path
    
    print(f"[DeepSecurity] Models ready (DB loaded from {db_path}).")
    yield
    print("[DeepSecurity] Shutting down.")


app = FastAPI(
    title="DeepSecurity API",
    description="Face detection & recognition REST API powered by MTCNN + VGG-Face.",
    version="2.1.0",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recognition.router)
app.include_router(faces.router)
app.include_router(settings.router)
app.include_router(history.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "DeepSecurity API v2"}
