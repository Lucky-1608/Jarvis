"""Request and upload limits for expensive media endpoints."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_TTS_CHARACTERS = 10_000


async def read_upload_limited(file: UploadFile, maximum: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read an upload only when it fits within the configured byte limit."""
    content = await file.read(maximum + 1)
    if len(content) > maximum:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit")
    return content
