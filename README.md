# DeepSecurity AI — Enterprise-grade Biometric Identification
> Robust biometric security system featuring real-time multi-camera face detection, recognition, anti-spoofing, and automated video audit trailing.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Deep_Learning-Python_3.11-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Build_Tool-Vite_7-646CFF?style=flat-square&logo=vite)](https://vitejs.dev/)

DeepSecurity AI is a robust solution for real-time person identification across multiple simultaneous camera feeds. It integrates state-of-the-art computer vision models into a scalable web architecture, providing seamless identity management, security auditing, and full video history management.

## Core Features

- **Multi-Camera Grid**: Register multiple webcams and process all of them simultaneously. Each camera runs its own independent response-gated recognition loop and can record concurrently.
- **Real-time Face Detection**: Implements **MTCNN** (Multi-task Cascaded CNN) for high-performance face localization and alignment.
- **Biometric Recognition**: Powered by **VGG-Face** (via DeepFace), achieving high precision in identity verification and matching.
- **Anti-Spoofing**: Optional PyTorch-based module that scores each detection for liveness, storing `is_spoof` and `antispoof_score` per log entry.
- **Concurrent Video Auditing**: Each camera maintains its own `VideoRecorder` instance — multiple recordings can run at the same time, each producing an independent H.264 + faststart MP4 file.
- **Video History & Playback**: Paginated recordings browser with camera name column, in-app streaming (HTTP 206 range support), and secure short-lived download tokens.
- **Recognition Log History**: Expandable per-recording logs showing detected identities, confidence, anti-spoofing scores, and source camera, with JSON export and per-camera filtering.
- **Identity Management**: Comprehensive CRUD operations for facial identity registration and biometric metadata management.
- **Soft-Delete Recordings**: Recordings are soft-deleted (flag + file cleanup) to preserve audit trail integrity.
- **Rate Limiting**: SlowAPI middleware on recognition endpoints prevents abuse.
- **Modular Architecture**: Hot-swappable face databases with native OS folder picker integration for enterprise flexibility.

## Technical Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy async ORM (asyncpg), FastAPI-Users 15.x (JWT auth).
- **Computer Vision**: MTCNN (Detection), DeepFace/VGG-Face (Recognition), optional PyTorch anti-spoofing, `ThreadPoolExecutor` (up to 8 workers, configurable via `MAX_WORKER_THREADS`) for CPU-bound concurrency.
- **Frontend**: React 19 (Modern Hooks/Context API), Vite 7.
- **Infrastructure**: Docker & Docker Compose, PostgreSQL 16, environment-based configuration.

## Architecture

The system uses a modular, high-performance pipeline:

1. **Ingestion**: The React frontend renders a grid of `CameraTile` components, one per registered active camera. Each tile runs its own `getUserMedia` stream and response-gated loop that POSTs frames (tagged with `camera_id`) to the REST API.
2. **Detection Layer**: MTCNN extracts face crops and bounding box coordinates per frame.
3. **Anti-Spoofing** *(optional)*: PyTorch model scores each crop for liveness before recognition.
4. **Recognition Engine**: A `ThreadPoolExecutor` handles DeepFace embedding comparisons against the registered biometric database (vectorized cosine distance against a precomputed cache).
5. **Audit & Logging**: Identity matches are persisted in PostgreSQL (`RecognitionLog` with `camera_id`). If recording is active for that camera, the `RecorderManager` routes the annotated frame to the correct `VideoRecorder` instance.
6. **History Access**: Users browse recordings and logs through paginated, cursor-based APIs, filterable by `camera_id`. MP4s stream securely via short-lived one-time tokens (5-minute TTL).
7. **Live Feedback**: Each tile displays real-time bounding boxes, identity labels, confidence metrics, spoof indicators, and a per-tile FPS counter.

## API Overview

| Router | Prefix | Highlights |
|---|---|---|
| Auth | `/api/auth` | JWT login, register (first user → superuser) |
| Recognition | `/api/recognize` | Frame analysis (with `camera_id`), per-camera start/stop recording, multi-camera status |
| Cameras | `/api/cameras` | Register, list, update, delete camera sources |
| Faces | `/api/faces` | List, register, delete identities |
| Settings | `/api/settings` | Read/write config, OS folder picker |
| History | `/api/history` | Logs + recordings (cursor paginated, filterable by `camera_id`), secure video streaming, soft-delete |

## Getting Started

### Prerequisites
- Python 3.11 (managed via `uv` or `pip`)
- Node.js 20+
- Docker & Docker Compose (recommended)

### Quickstart (Docker)
```bash
# 1. Copy and fill environment variables
cp .env.example backend/.env   # set JWT_SECRET at minimum

# 2. Start the full stack
docker compose up --build -d

# 3. Open http://localhost and register the first account
#    (automatically promoted to superuser)

# 4. Go to Cámaras → Detectar dispositivos → register your webcams
# 5. Go to Reconocimiento → all active cameras appear in a grid
```

### Local Development

**Backend:**
```bash
# Windows — use venv directly (uv sync fails due to tensorflow-io wheel)
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000

# Linux
uv sync && uv run uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Project Structure

```text
DeepSecurity/
├── backend/
│   ├── auth/           # FastAPI-Users JWT setup, token helpers
│   ├── core/           # CV engines: detector, recognizer, antispoof, recorder + RecorderManager
│   ├── db/             # SQLAlchemy models (Camera, VideoRecording, RecognitionLog, User)
│   ├── routers/        # RESTful controllers: recognition, faces, settings, history, cameras
│   ├── limiter.py      # SlowAPI rate limiting
│   ├── messages.py     # Error message constants
│   └── main.py         # App entry point, lifespan, CORS, router registration
├── frontend/
│   └── src/
│       ├── api/        # apiFetch client, cameras.js, and all API call functions
│       ├── components/ # CameraTile — self-contained per-camera recognition widget
│       ├── context/    # AuthContext (JWT, user state)
│       ├── pages/      # Recognition (grid), Cameras, Identities, Recordings, Historial, Logs, SystemInfo, Login
│       └── App.jsx     # Global routing, AuthProvider, navigation
├── db/                 # Biometric data (faces/ + embeddings_cache.npz)
├── recordings/         # Generated MP4 audit trails (persists across rebuilds)
└── docker-compose.yml
```

---
Developed with focus on **Scalability**, **Performance**, and **Professional Security Standards**.
