# Phase 15 — Production Deployment & Hardening Audit

## A. Existing Architecture
- **Frontend**: React 18 + Vite + Tailwind CSS. Multi-page app supporting Dashboard, Meeting Details, Live Meeting, Upload, Follow-Up Center, Settings, Login, and Register.
- **Backend**: Python 3.14 + FastAPI + Uvicorn. Structured cleanly into `backend/app/core`, `api`, `database`, `schemas`, `services`.
- **Database**: SQLite (`data/meeting.db`) accessed via SQLAlchemy 2.0 ORM models (`backend/app/database/models.py`).
- **Processing Pipelines**:
  - Transcripts (`.txt`, `.pdf`, `.docx`): Segmented by `transcript_service.py`.
  - Audio (`.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`): Transcribed via `transcription.py` (Whisper API / fallback).
  - Video (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`): Audio extracted via FFmpeg (`video_processor.py`), then transcribed.
  - Speaker Diarization: Handled by `diarization.py`.
  - AI Intelligence: Structured grounding, summaries, topics, timeline, risks, and evidence extraction via `ai_intelligence.py`.
  - Live Meetings: Real-time WebSockets streaming audio and transcript/intelligence JSON updates via `live_meetings.py` & `live_session_service.py`.
  - Follow-up Automation: `followup_service.py`, `deadline_service.py`, calendar and email provider abstractions.

## B. Existing Security Controls
- **Authentication**: JWT tokens (HS256) with 24-hour expiration, password hashing via `passlib` / `bcrypt` (`backend/app/core/security.py`).
- **User Data Isolation**: Mandatory ownership checks on all authenticated endpoints (`verify_meeting_access` in `meetings.py`, user scoping in queries).
- **File Upload Protection**: UUID-based random filenames, path traversal sanitization, extension validation against whitelist.
- **Phase 4 Synthetic Video Safety**: Strict check for `FTYP_MP4_DUMMY_HEADER` test fixture preventing fake video processing for corrupted real MP4 files.
- **External Action Confirmation**: Calendar events and email sending strictly require explicit user confirmation via UI/API modals.

## C. Existing Deployment Blockers
1. **Database Hardcoding**: Development defaults to SQLite (`sqlite:///data/meeting.db`). Missing PostgreSQL configuration and migration tool (Alembic).
2. **Wildcard CORS**: `allow_origins=["*"]` configured in `backend/app/main.py`.
3. **Hardcoded Secrets & Local URLs**: Hardcoded default `SECRET_KEY` in `core/config.py` and local backend base URLs in `frontend/src/services/api.js`.
4. **Local File Storage**: Direct local disk writes (`backend/uploads`) without storage provider abstraction for cloud/S3 storage.
5. **Lack of Containerization & Reverse Proxy**: No Dockerfile, docker-compose setup, or Nginx/reverse-proxy configuration for production deployment, WSS, or HTTPS.
6. **Missing Health & Readiness Probes**: No `/health` or `/ready` status endpoints.
7. **Missing Rate Limiting**: Critical endpoints (Auth, Uploads, AI triggers) lack rate-limiting protection.
8. **Lack of Automated DB Migration Scripts**: Direct `PRAGMA` table alterations instead of structured migration tool.

## D. Existing Environment Variables
Currently recognized by `backend/app/core/config.py`:
- `SECRET_KEY`
- `WHISPER_MODEL_SIZE`

## E. Existing External Integrations
- **FFmpeg**: System command-line binary (`C:\ffmpeg\bin\ffmpeg.exe`).
- **Whisper / Speech-to-Text**: Local or API transcription service.
- **Google Calendar Provider**: Foundation class `GoogleCalendarProvider` alongside `MockCalendarProvider`.
- **Gmail Email Provider**: Foundation class `GmailEmailProvider` alongside `MockEmailProvider`.
- **Google Gemini / AI Models**: `ai_intelligence.py` for structured grounded extraction.

## F. Existing Test Coverage
20 dedicated Python test scripts in workspace root:
- `test_upload.py` (Phase 1)
- `test_phase2_transcript.py` (Phase 2)
- `test_phase3_audio.py` (Phase 3)
- `test_phase4_video.py` (Phase 4)
- `test_phase5_diarization.py` (Phase 5)
- `test_phase7_reliability.py` (Phase 7)
- `test_phase8_production.py` (Phase 8)
- 10 `test_phase9_*.py` scripts (Phase 9 - Action Items, Decisions, Export, Grounding, History, Details, Status, Questions, Search, Security)
- `test_phase10_intelligence.py` (Phase 10)
- `test_phase11_live_meeting.py` (Phase 11)
- `test_phase12_followup.py` (Phase 12)

All 20 test scripts pass 100% cleanly.

## G. Required Phase 15 Changes
1. **Production Configuration**: Environment-based config with fail-fast validation (`APP_ENV`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `MAX_UPLOAD_SIZE_MB`, `STORAGE_PROVIDER`).
2. **PostgreSQL & Alembic**: Support `postgresql+psycopg://`, initialize Alembic migrations (`alembic/`, `alembic.ini`).
3. **SQLite to PostgreSQL Migration Utility**: `scripts/migrate_sqlite_to_postgres.py`.
4. **Storage Abstraction**: `StorageProvider` base class with `LocalStorageProvider` and `S3StorageProvider`.
5. **Background Worker / Task Queue Architecture**: Safe background processing setup for media and AI workloads.
6. **Health & Readiness Endpoints**: Add `GET /health` and `GET /ready`.
7. **Rate Limiting & Security Hardening**: Add middleware for rate-limiting, CORS restriction, and security response headers.
8. **Containerization & Deployment**: `Dockerfile`, `Dockerfile.frontend`, `docker-compose.yml`, `nginx.conf`.
9. **Smoke Test Script**: `scripts/production_smoke_test.py`.
10. **Documentation**: `PRODUCTION_DEPLOYMENT.md`, `BACKUP_AND_RESTORE.md`, `ROLLBACK.md`, `PHASE15_PRODUCTION_CHECKLIST.md`, `PHASE15_FINAL_REPORT.md`.

## H. Files That Will Be Modified / Created
- `backend/app/core/config.py` (Add production config validation, storage & database options)
- `backend/app/database/session.py` (Add PostgreSQL engine pooling & dialect configuration)
- `backend/app/main.py` (Register CORS from env, rate limiting, health/ready routes, security headers)
- `backend/requirements.txt` (Add `psycopg`, `alembic`, `slowapi`)
- `frontend/src/services/api.js` (Support environment-driven base URLs for REST & WS)
- `.env.example`
- `Dockerfile`, `Dockerfile.frontend`, `docker-compose.yml`, `nginx.conf`
- `alembic.ini`, `alembic/`
- `scripts/migrate_sqlite_to_postgres.py`, `scripts/production_smoke_test.py`
- `docs/PRODUCTION_DEPLOYMENT.md`, `docs/BACKUP_AND_RESTORE.md`, `docs/ROLLBACK.md`

## I. Files That Must NOT Be Modified Unnecessarily
- `backend/app/database/models.py` (Preserve all existing schema tables & relationships)
- `backend/app/services/ai_intelligence.py` (Preserve all grounding & evidence extraction rules)
- `backend/app/services/video_processor.py` (Preserve Phase 4 synthetic video safety rule)
- `backend/app/services/followup_service.py` (Preserve Phase 12 confirmation rules)
- Existing 20 `test_*.py` test scripts (Must not weaken or delete any tests)
