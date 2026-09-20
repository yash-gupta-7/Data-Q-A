"""Data profiling — computes statistics for the data catalog."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.ingestion.normalize import infer_duckdb_type
from app.models.dataset import ColumnInfo, ColumnQuality, SemanticType
from app.security.pii import is_pii_column, redact_pii_samples


_MAX_SAMPLE_VALUES = 5


def _infer_semantic_type(
    col_name: str,
    duckdb_type: str,
    unique_ratio: float,
    null_pct: float,
    series: pd.Series,
) -> SemanticType:
    """
    Deterministic semantic type inference.
    LLM fallback is handled at the catalog/schema level for genuinely ambiguous cases.
    """
    lower_name = col_name.lower().replace(" ", "_").replace("-", "_")

    # Boolean
    if duckdb_type == "BOOLEAN":
        return SemanticType.BOOLEAN

    # Date / Timestamp
    if duckdb_type in ("TIMESTAMP", "DATE"):
        return SemanticType.DATE

    # Identifier signals: high uniqueness, name contains id/key/code/no
    identifier_hints = {"_id", "id_", "_key", "_code", "_no", "_num", "_ref", "_uuid"}
    if any(h in lower_name for h in identifier_hints) or lower_name in {"id", "key", "uuid"}:
        if unique_ratio > 0.8:
            return SemanticType.IDENTIFIER

    # Metric signals: numeric + name contains metric-like words
    metric_hints = {
        "revenue", "sales", "amount", "price", "cost", "profit", "margin", "value",
        "quantity", "qty", "count", "total", "sum", "avg", "rate", "score",
        "salary", "income", "expense", "budget", "fee", "tax",
    }
    if duckdb_type in ("BIGINT", "DOUBLE"):
        if any(h in lower_name for h in metric_hints):
            return SemanticType.METRIC
        # Numeric columns with low unique ratio tend to be metrics
        if unique_ratio > 0.5:
            return SemanticType.METRIC

    # Dimension: low-cardinality string columns
    if duckdb_type == "VARCHAR":
        dimension_hints = {
            "region", "country", "city", "state", "category", "type", "status",
            "gender", "department", "team", "segment", "tier", "channel",
            "product", "brand", "platform", "source",
        }
        if any(h in lower_name for h in dimension_hints):
            return SemanticType.DIMENSION
        if unique_ratio < 0.3:
            return SemanticType.DIMENSION
        return SemanticType.TEXT

    # Default
    if duckdb_type in ("BIGINT", "DOUBLE"):
        return SemanticType.METRIC

    return SemanticType.TEXT


def profile_dataframe(df: pd.DataFrame) -> list[ColumnInfo]:
    """
    Profile a normalized DataFrame and return ColumnInfo list.
    """
    columns: list[ColumnInfo] = []
    total_rows = max(len(df), 1)

    for col in df.columns:
        series = df[col]
        dtype = infer_duckdb_type(series)

        null_count = int(series.isna().sum())
        null_pct = round(null_count / total_rows * 100, 2)
        non_null = series.dropna()
        unique_count = int(non_null.nunique())
        unique_ratio = round(unique_count / max(len(non_null), 1), 4)

        # Sample values (non-null, deduplicated, limited)
        raw_samples: list[Any] = non_null.dropna().unique()[:_MAX_SAMPLE_VALUES].tolist()

        # PII check
        pii_types = is_pii_column(col, raw_samples)
        sample_values = redact_pii_samples(raw_samples, pii_types) if pii_types else raw_samples

        # Min / max for numeric and date
        min_value: Any = None
        max_value: Any = None
        if dtype in ("BIGINT", "DOUBLE") and len(non_null) > 0:
            try:
                numeric_series = pd.to_numeric(non_null, errors="coerce").dropna()
                if len(numeric_series) > 0:
                    min_value = float(numeric_series.min())
                    max_value = float(numeric_series.max())
            except Exception:
                pass
        elif dtype in ("TIMESTAMP", "DATE") and len(non_null) > 0:
            try:
                min_value = str(non_null.min())
                max_value = str(non_null.max())
            except Exception:
                pass

        semantic_type = _infer_semantic_type(col, dtype, unique_ratio, null_pct, series)

        quality = ColumnQuality(
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique_count,
            unique_ratio=unique_ratio,
            pii_detected=pii_types,
        )

        columns.append(
            ColumnInfo(
                name=col,
                physical_type=dtype,
                semantic_type=semantic_type,
                nullable=null_count > 0,
                unique_ratio=unique_ratio,
                sample_values=sample_values,
                min_value=min_value,
                max_value=max_value,
                quality=quality,
            )
        )

    return columns
