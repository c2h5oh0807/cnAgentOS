"""File storage service skeleton (Phase 7+).

Phase 5 establishes:
  - SHA-256 content hashing for deduplication.
  - File type and size validation rules.
  - Date-sharded storage path generation.

Full upload/download endpoints, permission checks, and reference-counted
blob management are implemented in Phase 7 / Phase 6.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "application/zip",
})


class FileStorageService:
    """Local filesystem storage with SHA-256 dedup and size/type validation.

    Production deployments should replace the local backend with an object
    storage adapter (S3 / MinIO).
    """

    def __init__(self, storage_path: str | Path = "storage") -> None:
        self.storage_base = Path(storage_path)

    # ------------------------------------------------------------------
    # Hashing & validation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def validate_file(data: bytes, content_type: str) -> None:
        """Raise ``ValueError`` if the file exceeds size limits or its
        content type is not in the allowlist."""
        if len(data) > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({len(data)} bytes; limit {MAX_FILE_SIZE})")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Content type '{content_type}' is not allowed")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _store_path(self, original_filename: str, file_id: str | None = None) -> Path:
        """Generate a date-sharded file path.

        Layout: ``storage/YYYY/MM/DD/<uuid>_<original_filename>``
        """
        now = datetime.utcnow()
        date_dir = self.storage_base / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        fid = file_id or str(uuid.uuid4())
        return date_dir / f"{fid}_{Path(original_filename).name}"
