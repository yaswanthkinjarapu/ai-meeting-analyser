import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of backend (c:\Users\yaswa\OneDrive\Desktop\meeting\backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Root directory of the repository (c:\Users\yaswa\OneDrive\Desktop\meeting)
REPO_DIR = BASE_DIR.parent

DEFAULT_DEV_SECRET = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Meeting AI Intelligence API"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Path settings
    DATA_DIR: Path = REPO_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(REPO_DIR / 'data' / 'meeting.db').as_posix()}"
    )

    # File upload limits & storage settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")

    # CORS Settings
    CORS_ORIGINS_STR: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def cors_origins(self) -> List[str]:
        if not self.CORS_ORIGINS_STR or self.CORS_ORIGINS_STR.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",") if origin.strip()]

    # Supported extensions
    ALLOWED_EXTENSIONS: set[str] = {
        "txt", "pdf", "docx",
        "mp3", "wav", "m4a", "flac", "ogg",
        "mp4", "mov", "mkv", "avi", "webm"
    }

    # Security & Auth settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Whisper settings
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "tiny")
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "")

    # AI & Integrations
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")

    # Task Queue / Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    def validate_production_config(self):
        """
        Production Startup Guard:
        Validates required security controls in production mode.
        Fails fast if critical secrets or production database configurations are missing.
        """
        if self.APP_ENV.lower() == "production":
            errors = []
            if self.SECRET_KEY == DEFAULT_DEV_SECRET or len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be configured with a secure random string (minimum 32 characters) in production.")
            
            if "sqlite" in self.DATABASE_URL.lower():
                errors.append("DATABASE_URL cannot use SQLite in production. Configure a production PostgreSQL database URL.")

            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS cannot use wildcard '*' when running in production environment.")

            if errors:
                error_msg = "\n[CRITICAL PRODUCTION DEPLOYMENT BLOCKER]:\n" + "\n".join(f"  - {e}" for e in errors)
                raise ValueError(error_msg)

settings = Settings()
settings.validate_production_config()

# Ensure directories exist upon config load
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
