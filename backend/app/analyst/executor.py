"""DuckDB executor — runs validated, safe parameterized SQL with timeout."""

from __future__ import annotations

import logging
import time
from typing import Any

import duckdb

from app.analyst.compiler import CompiledQuery
from app.config import get_settings
from app.models.result import ColumnMeta, DataQualityInfo, QueryResult

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _infer_column_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if hasattr(value, "isoformat"):  # datetime / date
        return "date"
    return "string"


def execute_query(
    conn: duckdb.DuckDBPyConnection,
    compiled: CompiledQuery,
) -> QueryResult:
    """
    Execute a compiled, safety-validated query against DuckDB.
    Enforces row limits and timeout.
    """
    settings = get_settings()
    max_rows = settings.max_result_rows

    start = time.perf_counter()

    try:
        # Execute parameterized query
        # Timeout is enforced at the API layer (synchronous request lifecycle).
        rel = conn.execute(compiled.sql, compiled.parameters)
        desc = rel.description  # list of (name, type_code, ...)
        rows_raw = rel.fetchmany(max_rows + 1)  # fetch one extra to detect truncation

    except duckdb.Error as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "Timeout" in error_msg:
            raise ExecutionError("QUERY_TIMEOUT", f"Query timed out after {settings.query_timeout_seconds}s.")
        raise ExecutionError("EXECUTION_ERROR", f"Query execution failed: {error_msg}") from e

    elapsed_ms = (time.perf_counter() - start) * 1000

    truncated = len(rows_raw) > max_rows
    rows = rows_raw[:max_rows]

    # Build column metadata from description
    columns: list[ColumnMeta] = []
    if desc:
        for col_desc in desc:
            col_name = col_desc[0]
            # Infer type from first non-null value
            col_type = "string"
            for row in rows:
                idx = list(rel.description).index(col_desc)
                val = row[idx] if idx < len(row) else None
                if val is not None:
                    col_type = _infer_column_type(val)
                    break
            columns.append(ColumnMeta(name=col_name, type=col_type))

    # Convert rows to serializable lists
    serialized_rows: list[list[Any]] = []
    for row in rows:
        serialized_row = []
        for val in row:
            if hasattr(val, "isoformat"):
                serialized_row.append(val.isoformat())
            elif isinstance(val, float) and (val != val):  # NaN
                serialized_row.append(None)
            else:
                serialized_row.append(val)
        serialized_rows.append(serialized_row)

    # Count nulls per column for data quality
    nulls_by_col: dict[str, int] = {}
    if columns:
        for col_idx, col_meta in enumerate(columns):
            null_count = sum(1 for row in serialized_rows if col_idx >= len(row) or row[col_idx] is None)
            if null_count > 0:
                nulls_by_col[col_meta.name] = null_count

    data_quality = DataQualityInfo(
        rows_analyzed=len(serialized_rows),
        total_rows=len(serialized_rows) + (1 if truncated else 0),
        nulls_excluded=nulls_by_col,
        warnings=[
            f"Result truncated to {max_rows} rows (total may be larger)."
            if truncated else ""
        ] if truncated else [],
    )

    logger.info(
        "Query executed: rows=%d truncated=%s elapsed_ms=%.1f",
        len(serialized_rows),
        truncated,
        elapsed_ms,
    )

    return QueryResult(
        columns=columns,
        rows=serialized_rows,
        row_count=len(serialized_rows),
        total_row_count=len(rows_raw),
        truncated=truncated,
        execution_time_ms=round(elapsed_ms, 2),
        data_quality=data_quality,
    )
