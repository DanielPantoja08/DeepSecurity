"""
Test configuration and shared fixtures.

Uses a file-based SQLite database (temp file) instead of in-memory to avoid
event-loop / connection-lifetime issues across session-scoped setup and
per-function async test loops.

ML singletons (FaceDetector, FaceRecognizer, VideoRecorder) are replaced with
MagicMocks so TensorFlow is never loaded during the test suite.
"""
import asyncio
import os
import pathlib
import tempfile
from unittest.mock import MagicMock

# ── Env vars MUST be set before any backend module is imported ────────────────
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-for-production-32ch")
_DB_FILE = os.path.join(tempfile.mkdtemp(), "test_deepsecurity.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_DB_FILE}")

import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.db.database import Base, get_async_session
from backend.main import app

# ── File-based SQLite test engine ─────────────────────────────────────────────
_TEST_ENGINE = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_FILE}",
    connect_args={"check_same_thread": False},
)
_TestSession = async_sessionmaker(_TEST_ENGINE, expire_on_commit=False)


async def _override_session():
    async with _TestSession() as session:
        yield session


app.dependency_overrides[get_async_session] = _override_session

# ── Mock ML singletons ────────────────────────────────────────────────────────
FACES_DIR = pathlib.Path(tempfile.mkdtemp())

mock_recognizer = MagicMock()
mock_recognizer.db_path = str(FACES_DIR)
mock_recognizer.find_identity.return_value = ("Unknown", 1.0)
mock_recognizer.reload_db.return_value = None
mock_recognizer.load_cache.return_value = None

mock_detector = MagicMock()
mock_detector.detect_faces.return_value = []

mock_recorder = MagicMock()
mock_recorder.is_recording = False
mock_recorder.current_file = None
mock_recorder.start_time = None

app.state.detector = mock_detector
app.state.recognizer = mock_recognizer
app.state.recorder = mock_recorder
app.state.db_path = str(FACES_DIR)


# ── DB table lifecycle (sync fixture calls asyncio.run for isolation) ─────────
async def _create_tables() -> None:
    async with _TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Dispose pool so tests start with a fresh connection in their own event loop
    await _TEST_ENGINE.dispose()


async def _drop_tables() -> None:
    async with _TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _TEST_ENGINE.dispose()


@pytest.fixture(scope="session", autouse=True)
def db_tables():
    asyncio.run(_create_tables())
    yield
    asyncio.run(_drop_tables())


# ── HTTP client fixtures ──────────────────────────────────────────────────────
def _make_transport():
    return httpx.ASGITransport(app=app)


@pytest_asyncio.fixture
async def client():
    """Unauthenticated async HTTP client."""
    app.state.settings_lock = asyncio.Lock()
    async with httpx.AsyncClient(
        transport=_make_transport(), base_url="http://test"
    ) as ac:
        yield ac


async def _register_and_login(email: str, password: str) -> str:
    """Register (idempotent) and return a valid JWT."""
    async with httpx.AsyncClient(
        transport=_make_transport(), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        resp = await ac.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_client():
    """Authenticated async HTTP client (admin@test.com)."""
    app.state.settings_lock = asyncio.Lock()
    token = await _register_and_login("admin@test.com", "AdminPass123!")
    async with httpx.AsyncClient(
        transport=_make_transport(),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


# ── Shared test helpers ───────────────────────────────────────────────────────
def make_jpeg(width: int = 10, height: int = 10) -> bytes:
    """Return a minimal valid JPEG as bytes (using cv2)."""
    import cv2
    import numpy as np

    img = np.zeros((height, width, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()
