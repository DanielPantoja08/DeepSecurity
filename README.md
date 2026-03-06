# DeepSecurity AI — Enterprise-grade Biometric Identification
> Robust biometric security system featuring real-time face detection, recognition, and automated video audit trailing.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Deep_Learning-Python_3.12-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Build_Tool-Vite_7-646CFF?style=flat-square&logo=vite)](https://vitejs.dev/)

DeepSecurity AI is a robust solution for real-time person identification. It integrates state-of-the-art computer vision models into a scalable web architecture, providing seamless identity management and security auditing.

## Core Features

- **Real-time Face Detection**: Implements **MTCNN** (Multi-task Cascaded CNN) for high-performance face localization and alignment.
- **Biometric Recognition**: Powered by **VGG-Face** (via DeepFace), achieving high precision in identity verification and matching.
- **Automated Video Auditing**: Integrated recording system that generates high-quality security footage with real-time recognition overlays.
- **Identity Management**: Comprehensive CRUD operations for facial identity registration and biometric metadata management.
- **Historical Analysis**: Advanced log system for biometric detections stored in SQLite, featuring instant video audit playback.
- **Modular Architecture**: Hot-swappable face databases with native OS folder picker integration for enterprise flexibility.

## Technical Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy/SQLModel (ORM), OpenCV (Imaging).
- **Computer Vision**: MTCNN (Detection), DeepFace/VGG-Face (Recognition), ThreadPoolExecutor for optimized CPU-bound concurrency.
- **Frontend**: React 19 (Modern Hooks/Context API), Vite 7 (Ultra-fast build tool), DaisyUI/Tailwind CSS.
- **Infrastructure**: Docker & Docker Compose integration, Environment-based configuration management.

## Architecture

The system utilizes a modular, high-performance pipeline:

1. **Ingestion**: The React frontend captures high-frequency frames and transmits them to the REST API via optimized Multipart requests.
2. **Detection Layer**: MTCNN extracts face crops and precise bounding box coordinates.
3. **Recognition Engine**: A specialized `ThreadPoolExecutor` handles DeepFace embedding comparisons against the registered biometric database to prevent event-loop blocking.
4. **Audit & Logging**: Identity matches are persisted in SQLite. Simultaneously, if auditing is active, the `VideoRecorder` encodes frames into a security-grade MP4 stream.
5. **Live Feedback**: Real-time response cycle with visual bounding boxes, identity labels, and confidence metrics.

## Getting Started

### Prerequisites
- Python 3.12+ (managed via `uv` or `pip`)
- Node.js 20+

### Backend Setup
```bash
# In the project root
uv sync          # Install Python dependencies (FastAPI, DeepFace, etc.)
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Abre: http://localhost:5173

## Project Structure

```text
DeepSecurity/
├── backend/
│   ├── core/           # Computer Vision Engines (Detector, Recognizer, Recorder)
│   ├── db/             # Data Persistence (SQLModel schemas & sessions)
│   ├── routers/        # RESTful API Controllers
│   └── main.py         # Application Entry Point & Lifespan Management
├── frontend/
│   └── src/
│       ├── api/        # Axios Client Configuration
│       ├── pages/      # Reactive UI Components & Dashboards
│       └── App.jsx     # Global Routing & State
└── db/                 # Default Biometric Data Storage
```

---
Developed with focus on **Scalability**, **Performance**, and **Professional Security Standards**.