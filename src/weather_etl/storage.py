"""Object storage for the local filesystem and S3."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from weather_etl.exceptions import StorageError


class Storage(Protocol):
    def write_bytes(self, key: str, data: bytes) -> str:
        """Write bytes and return a URI the caller can log."""

    def read_bytes(self, key: str) -> bytes:
        """Read the object at key."""

    def list_keys(self, prefix: str) -> list[str]:
        """List object keys that start with prefix."""


class LocalStorage:
    """Store objects under a directory, using the key as a relative path."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write_bytes(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path.as_posix()

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StorageError(f"object not found: {key}") from exc

    def list_keys(self, prefix: str) -> list[str]:
        base = self._resolve(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [base.relative_to(self.root).as_posix()]
        keys: list[str] = []
        for path in base.rglob("*"):
            if path.is_file():
                keys.append(path.relative_to(self.root).as_posix())
        return sorted(keys)

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith(("/", "\\")) or "\\" in key:
            raise StorageError(f"invalid object key: {key}")
        parts = Path(key).parts
        if any(part in {"", ".", ".."} for part in parts):
            raise StorageError(f"invalid object key: {key}")
        return self.root.joinpath(*parts)


class S3Storage:
    """Store objects in one bucket. The client is injected so tests can use moto."""

    def __init__(self, bucket: str, client: Any) -> None:
        self.bucket = bucket
        self.client = client

    def write_bytes(self, key: str, data: bytes) -> str:
        _reject_unsafe_key(key)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return f"s3://{self.bucket}/{key}"

    def read_bytes(self, key: str) -> bytes:
        _reject_unsafe_key(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise StorageError(f"failed to read s3://{self.bucket}/{key}: {exc}") from exc
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise StorageError(f"unexpected body type for {key}")
        return body

    def list_keys(self, prefix: str) -> list[str]:
        _reject_unsafe_key(prefix)
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                keys.append(item["Key"])
        return sorted(keys)


def build_storage(settings: Any, s3_client: Any | None = None) -> Storage:
    """Build the storage backend selected by settings."""
    if settings.storage_backend == "local":
        return LocalStorage(settings.local_data_dir)
    if s3_client is None:
        import boto3

        s3_client = boto3.client("s3", region_name=settings.aws_region)
    return S3Storage(settings.s3_bucket, s3_client)


def _reject_unsafe_key(key: str) -> None:
    if not key or key.startswith("/") or ".." in key.split("/"):
        raise StorageError(f"invalid object key: {key}")
