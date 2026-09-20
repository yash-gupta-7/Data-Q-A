"""FastAPI main application."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import datasets, files, queries, sessions
from app.config import get_settings

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.session_base_dir, exist_ok=True)
    logger.info("AI Analyst backend starting. Session dir: %s", settings.session_base_dir)
    yield
    logger.info("AI Analyst backend shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Data Analyst API",
        version="1.0.0",
        description="AI-powered data Q&A — structured analytical engine with LLM planning.",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    # Routers
    prefix = "/api/v1"
    app.include_router(sessions.router, prefix=prefix, tags=["Sessions"])
    app.include_router(files.router, prefix=prefix, tags=["Files"])
    app.include_router(datasets.router, prefix=prefix, tags=["Datasets"])
    app.include_router(queries.router, prefix=prefix, tags=["Queries"])

    return app


app = create_app()
