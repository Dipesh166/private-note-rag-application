from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from app.config import Settings, get_settings

_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".md": (),
    ".txt": (),
}

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

class UploadValidationError(ValueError):
    pass

def validate_upload(filename: str, content: bytes, settings: Settings | None = None) -> str:
    settings = settings or get_settings()

    ext = Path(filename or "").suffix.lower()
    if ext not in settings.allowed_extensions:
        raise UploadValidationError(
            f"Unsupported file type {ext or '(no extension)'!r}. "
            f"Allowed: {', '.join(sorted(settings.allowed_extensions))}"
        )

    if len(content) > settings.max_upload_bytes:
        raise UploadValidationError(
            f"File exceeds the {settings.max_upload_mb} MB limit."
        )

    if not content:
        raise UploadValidationError("File is empty.")

    expected = _MAGIC_SIGNATURES.get(ext)
    if expected and not any(content.startswith(sig) for sig in expected):
        raise UploadValidationError(
            "File content does not match its extension (magic-byte check failed)."
        )

    return ext

def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def safe_storage_name(filename: str) -> str:
    path = Path(filename or "upload")
    stem = _FILENAME_SAFE.sub("_", path.stem).strip("._")[:60] or "upload"
    ext = path.suffix.lower()
    return f"{uuid.uuid4().hex[:12]}__{stem}{ext}"
