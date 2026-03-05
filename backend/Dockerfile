FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies required by OpenCV and MTCNN
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy the uv config and requirements logic (pyproject.toml/requirements.txt/uv.lock)
# The backend is one level deeper in some structures, but uv sync can work if we copy the project
COPY pyproject.toml uv.lock ./

# Install python dependencies from the lock file
RUN uv sync --no-dev

# Create the db directory for volumes
RUN mkdir -p /app/db/faces

# Copy application source code
COPY backend/ ./backend/
# The main app also needs some files from root if relative paths are used
# We'll just copy the whole backend folder, which requires running from root

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/db/faces
ENV DISABLE_NATIVE_FILE_PICKER=true

# Start API
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
