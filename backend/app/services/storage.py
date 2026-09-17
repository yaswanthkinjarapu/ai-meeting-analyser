import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.config import settings

class BaseStorageProvider(ABC):
    @abstractmethod
    def save(self, file_path_or_bytes: str, relative_path: str) -> str:
        """Saves a file to storage and returns the stored file path / key."""
        pass

    @abstractmethod
    def delete(self, file_path_or_key: str) -> bool:
        """Deletes a file from storage."""
        pass

    @abstractmethod
    def exists(self, file_path_or_key: str) -> bool:
        """Checks if a file exists in storage."""
        pass

    @abstractmethod
    def get_url_or_path(self, file_path_or_key: str) -> str:
        """Returns the accessible file path or public/presigned URL."""
        pass

class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, base_dir: Path = settings.UPLOAD_DIR):
        self.base_dir = base_dir.resolve()
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, source_path: str, relative_path: str) -> str:
        target_path = (self.base_dir / os.path.basename(relative_path)).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attempt blocked in LocalStorageProvider.")
        if source_path != str(target_path):
            shutil.copyfile(source_path, target_path)
        return target_path.as_posix()

    def delete(self, file_path_or_key: str) -> bool:
        p = Path(file_path_or_key)
        if p.exists() and p.is_file():
            try:
                p.unlink()
                return True
            except OSError:
                return False
        return False

    def exists(self, file_path_or_key: str) -> bool:
        p = Path(file_path_or_key)
        return p.exists() and p.is_file()

    def get_url_or_path(self, file_path_or_key: str) -> str:
        return Path(file_path_or_key).as_posix()

class S3StorageProvider(BaseStorageProvider):
    def __init__(self):
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        except Exception:
            self.s3_client = None

    def save(self, source_path: str, relative_path: str) -> str:
        key = f"uploads/{os.path.basename(relative_path)}"
        if self.s3_client and self.bucket_name:
            self.s3_client.upload_file(source_path, self.bucket_name, key)
            return f"s3://{self.bucket_name}/{key}"
        # Fallback to local if S3 credentials not configured
        return LocalStorageProvider().save(source_path, relative_path)

    def delete(self, file_path_or_key: str) -> bool:
        if self.s3_client and self.bucket_name and file_path_or_key.startswith("s3://"):
            key = file_path_or_key.replace(f"s3://{self.bucket_name}/", "")
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception:
                return False
        return LocalStorageProvider().delete(file_path_or_key)

    def exists(self, file_path_or_key: str) -> bool:
        if self.s3_client and self.bucket_name and file_path_or_key.startswith("s3://"):
            key = file_path_or_key.replace(f"s3://{self.bucket_name}/", "")
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception:
                return False
        return LocalStorageProvider().exists(file_path_or_key)

    def get_url_or_path(self, file_path_or_key: str) -> str:
        if self.s3_client and self.bucket_name and file_path_or_key.startswith("s3://"):
            key = file_path_or_key.replace(f"s3://{self.bucket_name}/", "")
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=3600
            )
        return LocalStorageProvider().get_url_or_path(file_path_or_key)

def get_storage_provider() -> BaseStorageProvider:
    if settings.STORAGE_PROVIDER.lower() == "s3":
        return S3StorageProvider()
    return LocalStorageProvider()
