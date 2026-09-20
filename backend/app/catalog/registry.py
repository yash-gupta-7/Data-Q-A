"""Dataset registry — CRUD operations on the session catalog."""

from __future__ import annotations

import uuid
from typing import Any

import duckdb
import pandas as pd

from app.models.dataset import Dataset, DatasetStatus
from app.models.session import Session


def _next_dataset_id(session: Session) -> str:
    n = len(session.datasets) + 1
    return f"ds_{n:03d}"


def _safe_table_name(dataset_id: str) -> str:
    """Convert dataset_id to safe SQL table name."""
    return dataset_id.replace("-", "_").replace(".", "_")


def register_dataset(
    session: Session,
    df: pd.DataFrame,
    conn: duckdb.DuckDBPyConnection,
    display_name: str,
    source_file: str,
    source_file_id: str,
    columns_info: list,
    sheet_name: str | None = None,
    warnings: list[str] | None = None,
) -> Dataset:
    """
    Register a normalized DataFrame as a DuckDB table and add to session catalog.
    """
    dataset_id = _next_dataset_id(session)
    table_name = f"dataset_{len(session.datasets) + 1:03d}"

    # Register DataFrame as a DuckDB table (DuckDB can query Pandas DataFrames directly)
    conn.register(f"_temp_{table_name}", df)
    conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM "_temp_{table_name}"')
    conn.unregister(f"_temp_{table_name}")

    dataset = Dataset(
        dataset_id=dataset_id,
        internal_table_name=table_name,
        display_name=display_name,
        source_file=source_file,
        source_file_id=source_file_id,
        sheet_name=sheet_name,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns_info,
        status=DatasetStatus.READY,
        warnings=warnings or [],
    )

    session.datasets.append(dataset)
    return dataset


def remove_dataset(
    session: Session,
    dataset_id: str,
    conn: duckdb.DuckDBPyConnection,
) -> bool:
    """
    Remove a dataset: drop DuckDB table, remove from catalog, invalidate relationships.
    """
    dataset = session.get_dataset_by_id(dataset_id)
    if not dataset:
        return False

    # Drop DuckDB table
    try:
        conn.execute(f'DROP TABLE IF EXISTS "{dataset.internal_table_name}"')
    except Exception:
        pass

    # Mark dataset as removed
    dataset.status = DatasetStatus.REMOVED

    # Invalidate relationships involving this dataset
    session.relationships = [
        r for r in session.relationships
        if r.left_dataset != dataset_id and r.right_dataset != dataset_id
    ]

    return True


def get_dataframes_from_duckdb(
    session: Session,
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, pd.DataFrame]:
    """Load all active dataset tables from DuckDB into DataFrames (for relationship detection)."""
    dfs: dict[str, pd.DataFrame] = {}
    for ds in session.get_active_datasets():
        try:
            df = conn.execute(f'SELECT * FROM "{ds.internal_table_name}"').df()
            dfs[ds.dataset_id] = df
        except Exception:
            pass
    return dfs
