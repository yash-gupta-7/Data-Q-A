"""Global exception handlers for the FastAPI application."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.ingestion.csv import CSVParseError

logger = logging.getLogger(__name__)


async def csv_parse_error_handler(request: Request, exc: CSVParseError) -> JSONResponse:
    """Handle CSV parsing errors with a user-friendly 422 response."""
    logger.warning("CSV parse error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": "csv_parse_error",
            "message": str(exc),
            "filename": exc.filename,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors."""
    logger.exception("Unexpected error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )
