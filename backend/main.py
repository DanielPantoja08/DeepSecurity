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

# Ensure the project root is on sys.path so db/ relative paths resolve correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.core.detector import FaceDetector
from backend.core.recognizer import FaceRecognizer
from backend.routers import recognition, faces


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[DeepSecurity] Loading AI models…")
    db_path = os.path.join(ROOT_DIR, "db", "faces")
    app.state.detector = FaceDetector()
    app.state.recognizer = FaceRecognizer(db_path=db_path)
    app.state.db_path = db_path
    print("[DeepSecurity] Models ready.")
    yield
    print("[DeepSecurity] Shutting down.")


app = FastAPI(
    title="DeepSecurity API",
    description="Face detection & recognition REST API powered by MTCNN + VGG-Face.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recognition.router)
app.include_router(faces.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "DeepSecurity API v2"}
