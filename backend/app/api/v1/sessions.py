"""Session API endpoints — POST/GET/DELETE sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.response import err, ok
from app.session.manager import create_session, delete_session, get_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions")
async def create_new_session():
    """Create a new ephemeral session."""
    try:
        session, _ = create_session()
        return ok({
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
        })
    except Exception as e:
        logger.exception("Failed to create session")
        return err("SESSION_CREATE_FAILED", str(e))


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session state including datasets, relationships, and readiness summary."""
    session = get_session(session_id)
    if not session:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    active_datasets = session.get_active_datasets()
    return ok({
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "datasets": [
            {
                "dataset_id": d.dataset_id,
                "display_name": d.display_name,
                "source_file": d.source_file,
                "sheet_name": d.sheet_name,
                "row_count": d.row_count,
                "column_count": d.column_count,
                "status": d.status.value,
                "warnings": d.warnings,
                "columns": [
                    {
                        "name": c.name,
                        "physical_type": c.physical_type,
                        "semantic_type": c.semantic_type.value,
                        "nullable": c.nullable,
                        "unique_ratio": c.unique_ratio,
                        "sample_values": c.sample_values,
                        "quality": {
                            "null_count": c.quality.null_count,
                            "null_pct": c.quality.null_pct,
                            "pii_detected": c.quality.pii_detected,
                        },
                    }
                    for c in d.columns
                ],
            }
            for d in active_datasets
        ],
        "relationships": [
            {
                "relationship_id": r.relationship_id,
                "left_dataset": r.left_dataset,
                "left_column": r.left_column,
                "right_dataset": r.right_dataset,
                "right_column": r.right_column,
                "relationship_type": r.relationship_type.value,
                "status": r.status.value,
                "evidence_score": r.evidence.evidence_score,
                "overlap_ratio": r.evidence.overlap_ratio,
            }
            for r in session.relationships
        ],
        "readiness": {
            "files_processed": session.readiness.files_processed,
            "datasets_detected": session.readiness.datasets_detected,
            "total_rows": session.readiness.total_rows,
            "total_columns": session.readiness.total_columns,
            "relationships": session.readiness.relationships,
            "warnings": session.readiness.warnings,
            "skipped_sheets": session.readiness.skipped_sheets,
        },
        "message_count": len(session.conversation.messages),
    })


@router.delete("/sessions/{session_id}")
async def clear_workspace(session_id: str):
    """Delete session — clears all files, datasets, DuckDB, conversation."""
    deleted = delete_session(session_id)
    if not deleted:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")
    return ok({"message": "Workspace cleared successfully."})
