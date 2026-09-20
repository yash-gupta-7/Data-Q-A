"""File security validation — extension, MIME, size, path traversal, filename safety."""

from __future__ import annotations

import os
import re
import uuid

import magic

from app.config import get_settings

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # some systems send this for xlsx
}

# Dangerous filename patterns
_DANGEROUS_PATTERN = re.compile(r"[/\\:.~*?<>|\"'\x00-\x1f]")


class FileSecurityError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_filename(filename: str) -> str:
    """Return safe display name, raise FileSecurityError on dangerous patterns."""
    if not filename:
        raise FileSecurityError("INVALID_FILENAME", "Filename is empty.")

    # Path traversal check
    basename = os.path.basename(filename)
    if basename != filename.replace("\\", "/").split("/")[-1]:
        raise FileSecurityError("PATH_TRAVERSAL", f"Filename '{filename}' contains path components.")

    # Null bytes and control characters
    if "\x00" in filename or any(ord(c) < 32 for c in filename):
        raise FileSecurityError("INVALID_FILENAME", "Filename contains invalid characters.")

    # Extremely long filenames
    if len(filename) > 255:
        raise FileSecurityError("INVALID_FILENAME", "Filename too long (max 255 chars).")

    return basename


def validate_extension(filename: str) -> str:
    """Return lowercase extension or raise."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise FileSecurityError(
            "UNSUPPORTED_FORMAT",
            f"File type '{ext}' is not supported. Please upload .csv or .xlsx files.",
        )
    return ext


def validate_mime_type(file_bytes: bytes, filename: str) -> str:
    """Validate MIME type from actual file content."""
    try:
        mime = magic.from_buffer(file_bytes[:2048], mime=True)
    except Exception:
        mime = "application/octet-stream"

    # Be lenient — mime detection varies, but still sanity-check
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".csv" and mime not in {"text/csv", "text/plain", "application/csv", "application/octet-stream"}:
        raise FileSecurityError(
            "MIME_MISMATCH",
            f"File '{filename}' has extension .csv but content type '{mime}' is unexpected.",
        )
    if ext == ".xlsx" and mime not in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",  # xlsx is a zip
        "application/octet-stream",
    }:
        raise FileSecurityError(
            "MIME_MISMATCH",
            f"File '{filename}' has extension .xlsx but content type '{mime}' is unexpected.",
        )
    return mime


def validate_file_size(size_bytes: int, filename: str) -> None:
    settings = get_settings()
    if size_bytes > settings.max_file_size_bytes:
        raise FileSecurityError(
            "FILE_TOO_LARGE",
            f"File '{filename}' is {size_bytes / 1_048_576:.1f} MB, "
            f"which exceeds the {settings.max_file_size_mb} MB limit.",
        )


def validate_session_capacity(
    session_file_count: int,
    session_total_bytes: int,
    new_file_size: int,
) -> None:
    settings = get_settings()
    if session_file_count >= settings.max_files_per_session:
        raise FileSecurityError(
            "SESSION_FILE_LIMIT",
            f"Session already has {session_file_count} files (max {settings.max_files_per_session}).",
        )
    if session_total_bytes + new_file_size > settings.max_session_size_bytes:
        raise FileSecurityError(
            "SESSION_SIZE_LIMIT",
            f"Adding this file would exceed the session size limit of {settings.max_session_size_mb} MB.",
        )


def generate_internal_filename(original_filename: str) -> str:
    """Generate a UUID-based safe internal filename preserving extension."""
    _, ext = os.path.splitext(original_filename.lower())
    return f"{uuid.uuid4().hex}{ext}"
