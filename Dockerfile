# ==============================================================================
# Backend Dockerfile — Production Python FastAPI + FFmpeg environment
# ==============================================================================
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install FFmpeg and system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg is installed and accessible on system PATH
RUN ffmpeg -version

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source code and Alembic migrations
COPY backend /app/backend
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts

WORKDIR /app/backend

# Create uploads and data directories and set permissions for non-root user
RUN mkdir -p /app/backend/uploads /app/data \
    && useradd -m appuser \
    && chown -R appuser:appuser /app \
    && chmod -R 777 /app/backend/uploads /app/data
USER appuser

EXPOSE 8000

# Production startup command using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
