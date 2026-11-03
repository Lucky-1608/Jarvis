"""Workspace and sensitive-file policy for local file tools."""

from __future__ import annotations

import os
from pathlib import Path

from jarvis.config.settings import PROJECT_ROOT

MAX_READ_BYTES = 1_048_576
_SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "token.json",
}
_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def allowed_file_path(raw_path: str) -> Path:
    """Resolve a path below the configured workspace and reject secrets."""
    root = Path(os.getenv("JARVIS_FILE_ROOT", str(PROJECT_ROOT))).expanduser().resolve()
    path = Path(raw_path).expanduser().resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("File access is restricted to the Jarvis workspace") from exc

    parts = {part.lower() for part in path.relative_to(root).parts}
    name = path.name.lower()
    if (
        ".git" in parts
        or ".ssh" in parts
        or name in _SENSITIVE_NAMES
        or path.suffix.lower() in _SENSITIVE_SUFFIXES
    ):
        raise ValueError("Access to sensitive files is not allowed")
    return path
