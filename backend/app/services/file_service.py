import os
import uuid
from pathlib import Path
import aiofiles
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

def get_max_file_size_bytes() -> int:
    return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

def get_file_category(extension: str) -> str:
    ext = extension.lower()
    if ext in {"txt", "pdf", "docx"}:
        return "document"
    elif ext in {"mp3", "wav", "m4a", "flac", "ogg"}:
        return "audio"
    elif ext in {"mp4", "mov", "mkv", "avi", "webm"}:
        return "video"
    return "unknown"

def validate_file_extension(filename: str) -> str:
    # Path traversal protection: extract base filename only
    safe_basename = Path(filename).name
    if not safe_basename or "." not in safe_basename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename '{filename}' is invalid or lacks an extension."
        )

    # Check for path traversal characters
    if ".." in filename or "/" in filename or "\\" in filename:
        safe_basename = os.path.basename(filename)

    ext = safe_basename.rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not supported. Allowed extensions: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )
    return ext

async def save_uploaded_file(upload_file: UploadFile) -> tuple[str, str, int]:
    raw_name = upload_file.filename or "uploaded_file.txt"
    ext = validate_file_extension(raw_name)

    # Sanitize basename to prevent directory traversal
    clean_filename = os.path.basename(raw_name)
    unique_filename = f"{uuid.uuid4().hex}_{clean_filename}"
    full_path = (settings.UPLOAD_DIR / unique_filename).resolve()

    # Verify target path is strictly within UPLOAD_DIR
    if not str(full_path).startswith(str(settings.UPLOAD_DIR.resolve())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal attempted."
        )

    size_bytes = 0
    async with aiofiles.open(full_path, "wb") as out_file:
        max_limit = get_max_file_size_bytes()
        while chunk := await upload_file.read(1024 * 1024):  # 1MB chunk size
            size_bytes += len(chunk)
            if size_bytes > max_limit:
                out_file.close()
                if full_path.exists():
                    full_path.unlink()
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds maximum limit of {max_limit // (1024*1024)} MB."
                )
            await out_file.write(chunk)

    return full_path.as_posix(), ext, size_bytes
