"""API response envelope helpers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool
    data: Any = None
    error: dict | None = None
    request_id: str


def ok(data: Any, request_id: str | None = None) -> dict:
    return {
        "success": True,
        "data": data,
        "error": None,
        "request_id": request_id or str(uuid.uuid4()),
    }


def err(code: str, message: str, details: dict | None = None, request_id: str | None = None) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": request_id or str(uuid.uuid4()),
    }
