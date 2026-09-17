# Production Rollback Strategy & Emergency Recovery

## Overview
This document describes the rollback procedures in the event of a failed deployment, critical regression, or corrupted state.

---

## 1. Application Container Rollback

To roll back to a previously tagged Docker image build:

```bash
# 1. Inspect running container images
docker compose ps

# 2. Re-tag or pull previous stable Docker image
docker tag meeting_backend:previous meeting_backend:latest
docker tag meeting_frontend:previous meeting_frontend:latest

# 3. Restart container stack with previous image
docker compose up -d --no-build
```

---

## 2. Database Migration Rollback (Alembic)

If a migration introduced a breaking schema change:

```bash
# Inspect migration history
docker compose run --rm backend alembic history

# Downgrade 1 revision back
docker compose run --rm backend alembic downgrade -1

# Downgrade to base initial schema
docker compose run --rm backend alembic downgrade base
```

---

## 3. Disaster Recovery (Database & File Restoration)

If database records or files became corrupted during deployment:

1. Stop active traffic at proxy level.
2. Restore database from latest clean backup via `docs/BACKUP_AND_RESTORE.md`.
3. Restore media files from latest clean backup archive.
4. Run health & readiness probes (`/health`, `/ready`).
5. Run smoke test suite (`python scripts/production_smoke_test.py`).
