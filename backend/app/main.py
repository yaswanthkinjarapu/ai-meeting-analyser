from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.database.session import Base, engine
from app.api.meetings import router as meetings_router
from app.api.auth import router as auth_router
from app.api.live_meetings import router as live_meetings_router
from app.api.followups import router as followups_router

# Create database tables if not existing
Base.metadata.create_all(bind=engine)

# Ensure new columns exist on pre-existing SQLite database tables
if engine.dialect.name == "sqlite":
    with engine.connect() as conn:
        # 1. media_files migration
        res_mf = conn.execute(text("PRAGMA table_info(media_files);")).fetchall()
        mf_cols = [r[1] for r in res_mf]
        if "duration_seconds" not in mf_cols:
            conn.execute(text("ALTER TABLE media_files ADD COLUMN duration_seconds FLOAT;"))
        if "language" not in mf_cols:
            conn.execute(text("ALTER TABLE media_files ADD COLUMN language VARCHAR(10);"))

        # 2. transcript_segments migration
        res_ts = conn.execute(text("PRAGMA table_info(transcript_segments);")).fetchall()
        ts_cols = [r[1] for r in res_ts]
        if "speaker_id" not in ts_cols:
            conn.execute(text("ALTER TABLE transcript_segments ADD COLUMN speaker_id VARCHAR(36);"))
        if "speaker_name" not in ts_cols:
            conn.execute(text("ALTER TABLE transcript_segments ADD COLUMN speaker_name VARCHAR(100);"))

        # 3. meetings migration (user_id and error_message)
        res_m = conn.execute(text("PRAGMA table_info(meetings);")).fetchall()
        m_cols = [r[1] for r in res_m]
        if "user_id" not in m_cols:
            conn.execute(text("ALTER TABLE meetings ADD COLUMN user_id VARCHAR(36);"))
        if "error_message" not in m_cols:
            conn.execute(text("ALTER TABLE meetings ADD COLUMN error_message TEXT;"))

        # 4. decisions migration (review_status, updated_at)
        res_d = conn.execute(text("PRAGMA table_info(decisions);")).fetchall()
        d_cols = [r[1] for r in res_d]
        if "review_status" not in d_cols:
            conn.execute(text("ALTER TABLE decisions ADD COLUMN review_status VARCHAR(50) DEFAULT 'confirmed';"))
        if "updated_at" not in d_cols:
            conn.execute(text("ALTER TABLE decisions ADD COLUMN updated_at DATETIME;"))

        # 5. action_items migration (notes, updated_at, follow_up_status, normalized_deadline)
        res_ai = conn.execute(text("PRAGMA table_info(action_items);")).fetchall()
        ai_cols = [r[1] for r in res_ai]
        if "notes" not in ai_cols:
            conn.execute(text("ALTER TABLE action_items ADD COLUMN notes TEXT;"))
        if "updated_at" not in ai_cols:
            conn.execute(text("ALTER TABLE action_items ADD COLUMN updated_at DATETIME;"))
        if "follow_up_status" not in ai_cols:
            conn.execute(text("ALTER TABLE action_items ADD COLUMN follow_up_status VARCHAR(50) DEFAULT 'NOT_SCHEDULED';"))
        if "normalized_deadline" not in ai_cols:
            conn.execute(text("ALTER TABLE action_items ADD COLUMN normalized_deadline DATETIME;"))

        # 6. unresolved_questions migration (status, updated_at)
        res_uq = conn.execute(text("PRAGMA table_info(unresolved_questions);")).fetchall()
        uq_cols = [r[1] for r in res_uq]
        if "status" not in uq_cols:
            conn.execute(text("ALTER TABLE unresolved_questions ADD COLUMN status VARCHAR(50) DEFAULT 'open';"))
        if "updated_at" not in uq_cols:
            conn.execute(text("ALTER TABLE unresolved_questions ADD COLUMN updated_at DATETIME;"))

        # 7. meeting_summaries migration (executive_summary, detailed_summary_json, conversational_tone, tone_explanation, meeting_outcome)
        res_ms = conn.execute(text("PRAGMA table_info(meeting_summaries);")).fetchall()
        ms_cols = [r[1] for r in res_ms]
        if "executive_summary" not in ms_cols:
            conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN executive_summary TEXT;"))
        if "detailed_summary_json" not in ms_cols:
            conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN detailed_summary_json TEXT;"))
        if "conversational_tone" not in ms_cols:
            conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN conversational_tone VARCHAR(50) DEFAULT 'neutral';"))
        if "tone_explanation" not in ms_cols:
            conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN tone_explanation TEXT;"))
        if "meeting_outcome" not in ms_cols:
            conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN meeting_outcome VARCHAR(50) DEFAULT 'not_determined';"))

        conn.commit()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Backend API for AI Meeting Intelligence & Follow-up Agent"
)

# Production CORS Configuration
cors_origins = settings.cors_origins
allow_credentials = True if "*" not in cors_origins else False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(meetings_router, prefix=settings.API_V1_STR)
app.include_router(live_meetings_router, prefix=settings.API_V1_STR)
app.include_router(followups_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "environment": settings.APP_ENV,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Liveness probe for infrastructure health check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.APP_ENV
    }

@app.get("/ready")
def readiness_check():
    """Readiness probe verifying database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return {
            "status": "ready",
            "database": "connected",
            "environment": settings.APP_ENV
        }
    except Exception as e:
        from fastapi import Response
        return Response(
            content=f'{{"status": "not_ready", "error": "{str(e)}"}}',
            status_code=503,
            media_type="application/json"
        )
