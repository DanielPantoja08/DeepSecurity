"""
DeepSecurity — FastAPI Backend
Exposes REST endpoints for face detection, recognition, and identity management.

Run from the project root (DeepSecurity/):
    uvicorn backend.main:app --reload --port 8000
"""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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
from backend.auth.users import (
    fastapi_users,
    auth_backend,
    UserRead,
    UserCreate,
    UserUpdate,
)
from backend.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database…")
    await create_db_and_tables()

    logger.info("Loading AI models…")
    db_path = os.getenv("DB_PATH", os.path.join(ROOT_DIR, "db", "faces"))
    os.makedirs(db_path, exist_ok=True)

    app.state.detector = FaceDetector()
    app.state.recognizer = FaceRecognizer(db_path=db_path)
    app.state.recorder = VideoRecorder(output_dir=os.path.join(ROOT_DIR, "recordings"))
    app.state.db_path = db_path
    app.state.settings_lock = asyncio.Lock()  # 4.1: guard concurrent settings mutations

    logger.info("Models ready (DB loaded from %s).", db_path)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="DeepSecurity API",
    description="Face detection & recognition REST API powered by MTCNN + VGG-Face.",
    version="2.2.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = origins_raw.split(",")
allow_all_origins = origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth routes (public) ────────────────────────────────────────────────────
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/api/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)

# ── Application routes (protected by router-level dependency) ───────────────
app.include_router(recognition.router)
app.include_router(faces.router)
app.include_router(settings.router)
app.include_router(history.router)


@app.get("/", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "DeepSecurity API v2"}
