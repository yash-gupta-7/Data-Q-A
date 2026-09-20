"""Session manager — ephemeral sessions with temp filesystem and DuckDB."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid

import duckdb

from app.config import get_settings
from app.models.session import Session

logger = logging.getLogger(__name__)

# In-memory session store: session_id -> (Session, DuckDB connection)
_sessions: dict[str, Session] = {}
_connections: dict[str, duckdb.DuckDBPyConnection] = {}


def create_session() -> tuple[Session, duckdb.DuckDBPyConnection]:
    """Create a new ephemeral session with temp directory and DuckDB database."""
    settings = get_settings()
    session_id = str(uuid.uuid4())

    # Create session temp directory
    temp_dir = tempfile.mkdtemp(
        prefix="session_",
        dir=settings.session_base_dir if os.path.exists(settings.session_base_dir) else None,
    )
    os.makedirs(os.path.join(temp_dir, "raw"), exist_ok=True)

    duckdb_path = os.path.join(temp_dir, "workspace.duckdb")

    # Create DuckDB connection
    conn = duckdb.connect(duckdb_path)

    session = Session(
        session_id=session_id,
        temp_dir=temp_dir,
        duckdb_path=duckdb_path,
    )

    _sessions[session_id] = session
    _connections[session_id] = conn

    logger.info("Created session %s at %s", session_id, temp_dir)
    return session, conn


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def get_connection(session_id: str) -> duckdb.DuckDBPyConnection | None:
    return _connections.get(session_id)


def get_session_and_connection(
    session_id: str,
) -> tuple[Session, duckdb.DuckDBPyConnection] | tuple[None, None]:
    session = _sessions.get(session_id)
    conn = _connections.get(session_id)
    if session is None or conn is None:
        return None, None
    return session, conn


def delete_session(session_id: str) -> bool:
    """Delete session: close DuckDB, remove temp directory, clear memory."""
    if session_id not in _sessions:
        return False

    # Close DuckDB connection
    conn = _connections.pop(session_id, None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass

    session = _sessions.pop(session_id, None)

    # Remove temp directory
    if session and os.path.exists(session.temp_dir):
        try:
            shutil.rmtree(session.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("Failed to remove session dir %s: %s", session.temp_dir, e)

    logger.info("Deleted session %s", session_id)
    return True


def get_all_session_ids() -> list[str]:
    return list(_sessions.keys())


def get_raw_dir(session: Session) -> str:
    """Return the path for raw uploaded files in a session."""
    raw_dir = os.path.join(session.temp_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    return raw_dir
