# syntax=docker/dockerfile:1
# ── Backend: CPU-only ────────────────────────────────────────────────────────
# Uses BuildKit cache mounts so that apt packages and uv/pip packages are
# cached on the Docker host between builds. This cuts rebuild time from
# ~20 min down to ~1-2 min after the first build.
#
# Build args:
#   INSTALL_ANTISPOOF=false  — set to "true" to install PyTorch CPU and enable
#                              the anti-spoofing module (+~160 MB image size).
FROM python:3.11-slim AS base

# Build-time switch: set to "true" to include PyTorch CPU for anti-spoofing.
ARG INSTALL_ANTISPOOF=false

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

# Install core python dependencies (no dev, no optional extras).
# --mount=type=cache keeps the uv download cache on the host between builds,
# so packages are NOT re-downloaded if the lockfile hasn't changed.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Conditionally install PyTorch CPU-only for anti-spoofing.
# Uses the official PyTorch CPU index to avoid pulling the full CUDA build.
# Skipped when INSTALL_ANTISPOOF != "true" so the base image stays lean.
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$INSTALL_ANTISPOOF" = "true" ]; then \
        uv pip install torch --index-url https://download.pytorch.org/whl/cpu; \
    fi

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
ENV ANTISPOOF_ENABLED=true
ENV ANTISPOOF_THRESHOLD=0.5

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
