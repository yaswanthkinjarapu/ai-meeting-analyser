# Production Deployment Guide

## Overview
This document provides complete, step-by-step instructions for deploying the **AI Meeting Intelligence & Follow-up Agent** in a production environment using Docker, PostgreSQL, Redis, Nginx reverse proxy, and SSL/TLS.

---

## 1. Environment & Server Requirements
- **OS**: Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9 recommended) or Docker Host
- **Hardware**: Minimum 2 vCPU, 4 GB RAM, 20 GB Disk Space
- **Software Dependencies**:
  - Docker v24.0+ & Docker Compose v2.20+
  - FFmpeg (Installed automatically in backend container)

---

## 2. Production Environment Setup

### Step 1: Clone Repository & Create Configuration
```bash
git clone https://github.com/your-org/meeting-ai.git /opt/meeting-ai
cd /opt/meeting-ai
cp .env.example .env
```

### Step 2: Configure Environment Variables
Edit `.env` and configure production secrets:
```env
APP_ENV=production
SECRET_KEY=generate_a_secure_random_string_min_32_chars
DATABASE_URL=postgresql+psycopg://meeting_user:meeting_password@postgres:5432/meeting_db
CORS_ORIGINS=https://meeting.example.com
MAX_UPLOAD_SIZE_MB=500
STORAGE_PROVIDER=local
REDIS_URL=redis://redis:6379/0
```

---

## 3. Database Migrations (Alembic)
Run Alembic schema migrations on the target PostgreSQL instance:
```bash
# Execute Alembic migrations to create tables and indexes
docker compose run --rm backend alembic upgrade head
```

---

## 4. SQLite to PostgreSQL Data Migration (Optional)
If migrating from a local development SQLite database (`data/meeting.db`) to production PostgreSQL:
```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path data/meeting.db \
  --postgres-url postgresql+psycopg://meeting_user:meeting_password@localhost:5432/meeting_db
```

---

## 5. Build & Launch Container Stack
Start the full production deployment stack (PostgreSQL, Redis, Backend, Frontend/Nginx):
```bash
# Build production Docker images
docker compose build --no-cache

# Launch services in detached mode
docker compose up -d

# Verify container status
docker compose ps
```

---

## 6. Verification & Health Probes

### 1. Liveness & Readiness Check
```bash
curl -f http://localhost/health
# Expected Output: {"status":"healthy","service":"Meeting AI Intelligence API","environment":"production"}

curl -f http://localhost/ready
# Expected Output: {"status":"ready","database":"connected","environment":"production"}
```

### 2. Execute Production Smoke Test
```bash
python scripts/production_smoke_test.py --base-url http://localhost
```

---

## 7. Local Windows Development Workflow
To run local development on Windows without Docker:

**Backend**:
```powershell
cd C:\Users\yaswa\OneDrive\Desktop\meeting\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend**:
```powershell
cd C:\Users\yaswa\OneDrive\Desktop\meeting\frontend
npm run dev
```

**Verify FFmpeg**:
```powershell
ffmpeg -version
```
