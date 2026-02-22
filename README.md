# DeepSecurity AI — v2.0

Sistema de identificación de personas mediante reconocimiento facial en tiempo real.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19 + Vite 7 |
| Backend | FastAPI + Uvicorn |
| Detector | MTCNN |
| Reconocimiento | VGG-Face (DeepFace) |

## Inicio rápido

### 1 — Backend (FastAPI)

```bash
# En la raíz del proyecto
uv sync          # instala dependencias Python (incluye fastapi, uvicorn)
uvicorn backend.main:app --reload --port 8000
```

Swagger UI disponible en: http://localhost:8000/docs

### 2 — Frontend (React + Vite)

```bash
cd frontend
npm install      # solo la primera vez
npm run dev
```

Abre: http://localhost:5173

## Estructura

```
DeepSecurity/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── core/
│   │   ├── detector.py      # MTCNN
│   │   └── recognizer.py    # VGG-Face (DeepFace)
│   └── routers/
│       ├── recognition.py   # POST /api/recognize
│       └── faces.py         # CRUD /api/faces
├── frontend/
│   └── src/
│       ├── api/client.js
│       ├── pages/
│       │   ├── Recognition.jsx
│       │   ├── Identities.jsx
│       │   └── SystemInfo.jsx
│       └── App.jsx
└── db/faces/                # imágenes de identidades registradas
```