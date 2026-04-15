# syntax=docker/dockerfile:1
# ── Backend: CPU-only ────────────────────────────────────────────────────────
# Uses BuildKit cache mounts so that apt packages and uv/pip packages are
# cached on the Docker host between builds. This cuts rebuild time from
# ~20 min down to ~1-2 min after the first build.
FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies required by OpenCV, DeepFace/MTCNN, and ffmpeg.
# --mount=type=cache keeps downloaded .deb files on the host between builds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy the uv lockfile & project descriptor BEFORE syncing.
# Docker only re-runs the uv sync step when these two files change.
COPY pyproject.toml uv.lock ./

# Install python dependencies.
# --mount=type=cache keeps the uv download cache on the host between builds,
# so packages are NOT re-downloaded if the lockfile hasn't changed.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Create the identity DB directory
RUN mkdir -p /app/db/faces

# Copy application source LAST so above layers stay cached during code edits.
COPY backend/ ./backend/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
# Defaults for development/docker; can be overridden at runtime
ENV DB_PATH=/app/db/faces
ENV DISABLE_NATIVE_FILE_PICKER=true
ENV CUDA_VISIBLE_DEVICES=""

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
