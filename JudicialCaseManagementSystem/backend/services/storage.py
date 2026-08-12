"""
Object-storage abstraction for JCM.

Two implementations:
- LocalStorage (default, for development): stores files under MEDIA_ROOT.
- S3Storage: S3-compatible object storage (AWS S3, MinIO, ...) via boto3.

The rest of the application talks to the StorageService interface so the
provider can be swapped via the STORAGE_BACKEND env var.
"""
import logging
import os
import uuid
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    pass


class BaseStorage:
    backend = 'base'

    def save(self, file_obj, key_prefix='', filename='') -> str:
        raise NotImplementedError

    def open(self, key):
        raise NotImplementedError

    def delete(self, key) -> None:
        raise NotImplementedError

    def exists(self, key) -> bool:
        raise NotImplementedError

    def url(self, key, signed=False) -> str:
        raise NotImplementedError

    def signed_url(self, key, expires=300) -> str:
        raise NotImplementedError


class LocalStorage(BaseStorage):
    """Store files on the local filesystem under MEDIA_ROOT."""

    backend = 'local'

    def _absolute(self, key):
        return os.path.join(settings.MEDIA_ROOT, key)

    def save(self, file_obj, key_prefix='', filename=''):
        ext = os.path.splitext(filename or getattr(file_obj, 'name', ''))[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        key = os.path.join(key_prefix, safe_name).replace('\\', '/')
        abs_path = self._absolute(key)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'wb+') as dest:
            file_obj.seek(0)
            for chunk in file_obj.chunks():
                dest.write(chunk)
        return key

    def open(self, key):
        return open(self._absolute(key), 'rb')

    def delete(self, key):
        try:
            os.remove(self._absolute(key))
        except FileNotFoundError:
            pass

    def exists(self, key) -> bool:
        return os.path.exists(self._absolute(key))

    def url(self, key, signed=False) -> str:
        base = settings.MEDIA_URL or '/media/'
        return urljoin(base, key)

    def signed_url(self, key, expires=300) -> str:
        # Local dev: signed URL == plain URL (no auth on media in dev).
        return self.url(key, signed=True)


class S3Storage(BaseStorage):
    """S3-compatible object storage via boto3."""

    backend = 's3'

    def __init__(self):
        import boto3  # lazy import
        self.bucket = settings.S3_BUCKET
        kwargs = {}
        if settings.S3_ENDPOINT:
            kwargs['endpoint_url'] = settings.S3_ENDPOINT
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.S3_SECRET_KEY or None,
            region_name=settings.S3_REGION or None,
            **kwargs,
        )

    def save(self, file_obj, key_prefix='', filename=''):
        ext = os.path.splitext(filename or getattr(file_obj, 'name', ''))[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        key = f"{key_prefix}/{safe_name}".replace('//', '/').lstrip('/')
        try:
            self.client.upload_fileobj(file_obj, self.bucket, key)
        except Exception as exc:
            raise StorageError(f"S3 upload failed: {exc}") from exc
        return key

    def open(self, key):
        import io
        buf = io.BytesIO()
        try:
            self.client.download_fileobj(self.bucket, key, buf)
        except Exception as exc:
            raise StorageError(f"S3 download failed: {exc}") from exc
        buf.seek(0)
        return buf

    def delete(self, key):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            logger.warning(f"S3 delete failed for {key}: {exc}")

    def exists(self, key) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def url(self, key, signed=False) -> str:
        if signed:
            return self.signed_url(key)
        if settings.S3_PUBLIC_BASE_URL:
            return urljoin(settings.S3_PUBLIC_BASE_URL.rstrip('/') + '/', key)
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def signed_url(self, key, expires=300) -> str:
        try:
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=min(expires, 3600),
            )
        except Exception as exc:
            raise StorageError(f"S3 presign failed: {exc}") from exc


class StorageService:
    """Facade over the configured backend."""

    _instance = None

    def __init__(self):
        self.backend_name = settings.STORAGE_BACKEND
        if self.backend_name == 's3':
            self.impl = S3Storage()
        else:
            self.impl = LocalStorage()

    @classmethod
    def get(cls) -> 'StorageService':
        if cls._instance is None or cls._instance.backend_name != settings.STORAGE_BACKEND:
            cls._instance = cls()
        return cls._instance

    def save(self, file_obj, key_prefix='', filename='') -> str:
        return self.impl.save(file_obj, key_prefix=key_prefix, filename=filename)

    def open(self, key):
        return self.impl.open(key)

    def delete(self, key) -> None:
        self.impl.delete(key)

    def exists(self, key) -> bool:
        return self.impl.exists(key)

    def url(self, key, signed=False) -> str:
        return self.impl.url(key, signed=signed)

    def signed_url(self, key, expires=None) -> str:
        return self.impl.signed_url(key, expires=expires or settings.SIGNED_URL_TTL)


# Convenience
storage = StorageService.get
