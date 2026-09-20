"""Data normalization — clean raw DataFrames while preserving originals."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


# Common date formats to try
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

# Strings that should be treated as NULL
_NULL_STRINGS = {"na", "n/a", "null", "none", "nan", "-", "—", "#n/a", "#null!", ""}

# Numeric cleaning regex (removes currency symbols, thousands separators)
_NUMERIC_CLEAN = re.compile(r"[₹$€£¥,\s]")


def _try_parse_numeric(series: pd.Series) -> pd.Series | None:
    """Attempt to parse a string series as numeric, return None if < 80% parseable."""
    cleaned = series.dropna().apply(
        lambda v: _NUMERIC_CLEAN.sub("", str(v)) if isinstance(v, str) else v
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")
    non_null_orig = series.dropna()
    if len(non_null_orig) == 0:
        return None
    success_rate = numeric.notna().sum() / len(non_null_orig)
    if success_rate >= 0.8:
        return pd.to_numeric(
            series.apply(lambda v: _NUMERIC_CLEAN.sub("", str(v)) if isinstance(v, str) else v),
            errors="coerce",
        )
    return None


def _try_parse_date(series: pd.Series) -> pd.Series | None:
    """Attempt to parse a string series as dates, return None if < 70% parseable."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return None

    for fmt in _DATE_FORMATS:
        try:
            parsed = pd.to_datetime(series, format=fmt, errors="coerce")
            success_rate = parsed.notna().sum() / max(len(non_null), 1)
            if success_rate >= 0.7:
                return parsed
        except Exception:
            continue

    # Last resort: infer (pandas >= 2.0 removed infer_datetime_format)
    try:
        parsed = pd.to_datetime(series, errors="coerce")
        success_rate = parsed.notna().sum() / max(len(non_null), 1)
        if success_rate >= 0.7:
            return parsed
    except Exception:
        pass

    return None


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a raw DataFrame for analytical use:
    1. Strip whitespace from string columns
    2. Standardize null markers
    3. Attempt numeric type coercion
    4. Attempt date type coercion
    Returns a new DataFrame (original is never mutated).
    """
    df = df.copy()

    # Normalize column names: strip whitespace
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        series = df[col]

        # Strip string whitespace and normalize nulls
        if series.dtype == object:
            series = series.apply(
                lambda v: None if (isinstance(v, str) and v.strip().lower() in _NULL_STRINGS)
                else (v.strip() if isinstance(v, str) else v)
            )

        # Try numeric coercion first
        if series.dtype == object:
            numeric = _try_parse_numeric(series)
            if numeric is not None:
                df[col] = numeric
                continue

        # Try date coercion
        if series.dtype == object:
            date_parsed = _try_parse_date(series)
            if date_parsed is not None:
                df[col] = date_parsed
                continue

        df[col] = series

    return df


def infer_duckdb_type(series: pd.Series) -> str:
    """Map pandas dtype to DuckDB SQL type name."""
    dtype = str(series.dtype)
    if "int" in dtype:
        return "BIGINT"
    if "float" in dtype:
        return "DOUBLE"
    if "datetime" in dtype:
        return "TIMESTAMP"
    if "bool" in dtype:
        return "BOOLEAN"
    return "VARCHAR"
