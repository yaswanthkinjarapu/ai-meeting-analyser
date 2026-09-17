# Database & File Backup and Restore Procedures

## Overview
This document outlines production backup, retention, and disaster recovery procedures for PostgreSQL databases, uploaded media files, and application state.

---

## 1. Automated PostgreSQL Database Backups

### Daily Database Backup Script
Create `/usr/local/bin/backup_meeting_db.sh`:
```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/meeting_db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/meeting_db_${TIMESTAMP}.sql.gz"

mkdir -p ${BACKUP_DIR}

# Execute pg_dump from PostgreSQL container
docker exec -t meeting_postgres pg_dump -U meeting_user -d meeting_db | gzip > ${BACKUP_FILE}

# Retain backups for 30 days
find ${BACKUP_DIR} -type f -name "*.sql.gz" -mtime +30 -delete

echo "✅ Backup created successfully at ${BACKUP_FILE}"
```

Make script executable and add to crontab:
```bash
chmod +x /usr/local/bin/backup_meeting_db.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_meeting_db.sh") | crontab -
```

---

## 2. PostgreSQL Restore Procedure

To restore PostgreSQL database from a `.sql.gz` backup file:
```bash
# 1. Stop backend service to prevent write conflicts
docker compose stop backend

# 2. Restore PostgreSQL database
gunzip -c /var/backups/meeting_db/meeting_db_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i meeting_postgres psql -U meeting_user -d meeting_db

# 3. Restart backend service
docker compose start backend
```

---

## 3. Uploaded File Storage Backup

Media files (`backend/uploads`) live outside PostgreSQL.

### Backup Upload Directory
```bash
tar -czf /var/backups/meeting_uploads_$(date +"%Y%m%d").tar.gz /opt/meeting-ai/backend/uploads
```

### Restore Upload Directory
```bash
tar -xzf /var/backups/meeting_uploads_YYYYMMDD.tar.gz -C /
```
