# ── Stage 1: GPU-accelerated base ──────────────────────────────────────────────
# tensorflow/tensorflow:2.15.0-gpu ships CUDA 12.2 + cuDNN 8.9 pre-installed.
# The host only needs the NVIDIA driver (≥535) + nvidia-container-toolkit.
FROM tensorflow/tensorflow:2.15.0-gpu AS base

WORKDIR /app

# Install system dependencies required by OpenCV, MTCNN, and ffmpeg
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv 
RUN pip install uv

# Copy the uv lockfile & project descriptor
COPY pyproject.toml uv.lock ./

# Install python dependencies.
RUN uv sync --no-dev

# Create the identity DB directory 
RUN mkdir -p /app/db/faces

# Copy application source
COPY backend/ ./backend/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/db/faces
ENV DISABLE_NATIVE_FILE_PICKER=true


ENV TF_FORCE_GPU_ALLOW_GROWTH=true

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
