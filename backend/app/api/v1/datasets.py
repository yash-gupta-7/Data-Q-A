"""Dataset endpoints — list and delete datasets."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.response import err, ok
from app.catalog.registry import remove_dataset
from app.session.manager import get_session_and_connection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sessions/{session_id}/datasets")
async def list_datasets(session_id: str):
    """List all active datasets in a session."""
    session, _ = get_session_and_connection(session_id)
    if session is None:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    active = session.get_active_datasets()
    return ok({
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
                        "unique_ratio": round(c.unique_ratio, 3),
                        "sample_values": c.sample_values[:3],
                        "quality": {
                            "null_count": c.quality.null_count,
                            "null_pct": c.quality.null_pct,
                            "pii_detected": c.quality.pii_detected,
                        },
                    }
                    for c in d.columns
                ],
            }
            for d in active
        ],
        "count": len(active),
    })


@router.delete("/sessions/{session_id}/datasets/{dataset_id}")
async def delete_dataset(session_id: str, dataset_id: str):
    """
    Remove a dataset from the session.
    Drops DuckDB table, invalidates relationships, marks past answers as stale.
    """
    session, conn = get_session_and_connection(session_id)
    if session is None:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    removed = remove_dataset(session, dataset_id, conn)
    if not removed:
        return err("DATASET_NOT_FOUND", f"Dataset '{dataset_id}' not found.")

    # Update readiness
    active = session.get_active_datasets()
    from app.models.session import DataReadinessSummary
    session.readiness = DataReadinessSummary(
        files_processed=session.readiness.files_processed,
        datasets_detected=len(active),
        total_rows=sum(d.row_count for d in active),
        total_columns=sum(d.column_count for d in active),
        relationships=[
            {
                "left": f"{r.left_dataset}.{r.left_column}",
                "right": f"{r.right_dataset}.{r.right_column}",
                "status": r.status.value,
                "score": r.evidence.evidence_score,
            }
            for r in session.relationships
        ],
        warnings=session.readiness.warnings,
    )

    return ok({"message": f"Dataset '{dataset_id}' removed successfully."})
