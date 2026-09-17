# Meeting AI Intelligence & Follow-up Agent

A full-stack, local-first AI system for processing meeting transcripts, audio, and video files. Automatically performs speech-to-text transcription, speaker diarization, grounded AI intelligence extraction (decisions, action items, ownership, deadlines, unresolved questions), and status tracking with full multi-user authentication and data isolation.

---

## 🏗️ Architecture Overview

```
                          ┌──────────────────────────┐
                          │   React Frontend (Vite)  │
                          │   (Tailwind CSS, React)  │
                          └─────────────┬────────────┘
                                        │ HTTP / Bearer JWT
                                        ▼
                          ┌──────────────────────────┐
                          │     FastAPI Backend      │
                          └──────┬────────────┬──────┘
                                 │            │
            ┌────────────────────┴──┐      ┌──┴─────────────────────┐
            │   Security & Auth     │      │   Pipeline Engines     │
            │ (Bcrypt, JWT, Auth)   │      │ (Whisper, FFmpeg, AI)  │
            └───────────────────────┘      └────────────────────────┘
                                 │            │
                                 ▼            ▼
                          ┌──────────────────────────┐
                          │ SQLite / PostgreSQL DB   │
                          └──────────────────────────┘
```

---

## 🚀 Key Features

- **Authentication & Security**:
  - User registration & login using bcrypt password hashing.
  - Signed JWT bearer authentication tokens (`PyJWT`).
  - Strict user data isolation: Authenticated users can only view and modify their own meeting assets.
  - Hardened file uploads: Path traversal protection, safe UUID filename generation, 500 MB max size limit.

- **Multi-Format Meeting Processing**:
  - **Documents**: `.txt`, `.pdf`, `.docx`
  - **Audio**: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`
  - **Video**: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`

- **AI Intelligence & Diarization**:
  - Speech-to-text transcription via Whisper.
  - FFmpeg-based video audio extraction.
  - Speaker diarization & custom speaker label mapping.
  - Grounded AI intelligence extraction: Distinguishes confirmed decisions from suggestions, extracts action items with ownership and explicit deadlines, tracks unresolved questions, and records verbatim `context_quote` evidence.

- **Database & Architecture**:
  - Zero-config SQLite local development (`data/meeting.db`).
  - Environment-driven `DATABASE_URL` for instant PostgreSQL migration readiness.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` to configure your environment:

```bash
# Project Settings
PROJECT_NAME="Meeting AI Intelligence API"

# Database Configuration (SQLite default, PostgreSQL ready)
DATABASE_URL="sqlite:///./data/meeting.db"

# Security & Authentication Secrets
SECRET_KEY="your-production-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Speech-to-Text Model Size
WHISPER_MODEL_SIZE="tiny"

# Upload Limits
MAX_FILE_SIZE_BYTES=524288000
```

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python**: Version 3.9+
- **Node.js**: Version 18+
- **FFmpeg**: Required for video processing (`.mp4`, `.mov`, `.mkv`).
  - Windows: `winget install ffmpeg` or `choco install ffmpeg`

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Launch FastAPI Backend Server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend Swagger API documentation is available at: `http://127.0.0.1:8000/docs`

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite Development Server
npm run dev -- --port 5173
```

Frontend Application UI is accessible at: `http://localhost:5173`

---

## 🧪 Testing

Run the full automated test suite for all phases:

```bash
# Phase 1: Upload API Test
python test_upload.py

# Phase 2: Transcript Processing Test
python test_phase2_transcript.py

# Phase 3: Audio Processing Test
python test_phase3_audio.py

# Phase 4: Video Processing Test
python test_phase4_video.py

# Phase 5: Speaker Diarization Test
python test_phase5_diarization.py

# Phase 7: Reliability & Grounded Intelligence Test
python test_phase7_reliability.py

# Phase 8: Production Security & Auth Test Suite
python test_phase8_production.py

# Frontend Build Test
cd frontend
npm run build
```

---

## 📚 API Endpoints Summary

### Authentication

- `POST /api/v1/auth/register`: Register user account
- `POST /api/v1/auth/login`: Authenticate and receive JWT token
- `GET /api/v1/auth/me`: Get current user profile

### Meetings & Processing

- `POST /api/v1/meetings/upload`: Upload meeting file (TXT, Audio, Video)
- `GET /api/v1/meetings`: List meetings (filtered by owner when logged in)
- `GET /api/v1/meetings/{id}`: Get meeting details
- `GET /api/v1/meetings/{id}/transcript`: Get meeting transcript segments
- `POST /api/v1/meetings/{id}/diarize`: Execute speaker diarization
- `GET /api/v1/meetings/{id}/speakers`: Get detected meeting speakers
- `PUT /api/v1/meetings/{id}/speakers/{speaker_id}`: Map speaker label to name
- `POST /api/v1/meetings/{id}/analyze`: Execute grounded AI intelligence analysis
- `GET /api/v1/meetings/{id}/analysis`: Get stored AI analysis

---

## ⚠️ Limitations & Future Production Steps

1. **FFmpeg Dependency**: Video processing requires FFmpeg binary on the host system `PATH`.
2. **Celery / Redis Distributed Task Queue**: For large-scale production enterprise deployments handling thousands of concurrent video files, worker queues using Redis/Celery can be attached via `DATABASE_URL` and `BackgroundTasks`.
