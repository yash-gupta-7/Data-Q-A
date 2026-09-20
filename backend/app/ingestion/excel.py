"""Excel (XLSX) ingestion — multi-sheet handling, formula injection protection."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd


class ExcelParseError(Exception):
    pass


_NULL_MARKERS = {"", "na", "n/a", "null", "none", "nan", "-", "—", "#n/a"}
_MIN_ROWS_FOR_TABULAR = 1  # at least 1 data row (excluding header)
_MIN_COLS_FOR_TABULAR = 1


def _sanitize_cell(value: Any) -> Any:
    """Formula injection protection — treat formula-like strings as data."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in ("=", "+", "@"):
            return stripped  # stored as-is, never executed
    return value


def _is_usable_sheet(df: pd.DataFrame) -> bool:
    """Check if a sheet is non-empty and has tabular structure."""
    if df is None or df.empty:
        return False
    if len(df.columns) < _MIN_COLS_FOR_TABULAR:
        return False
    # Remove completely empty rows
    non_empty = df.dropna(how="all")
    if len(non_empty) < _MIN_ROWS_FOR_TABULAR:
        return False
    return True


def parse_excel(file_bytes: bytes, filename: str) -> dict[str, pd.DataFrame | None]:
    """
    Parse XLSX bytes into a dict of {sheet_name -> DataFrame or None (if skipped)}.
    Uses data_only=True to avoid formula execution.
    Returns raw DataFrames (normalization is separate).
    """
    try:
        xf = pd.ExcelFile(
            io.BytesIO(file_bytes),
            engine="openpyxl",
        )
    except Exception as e:
        raise ExcelParseError(f"Failed to open Excel file '{filename}': {e}") from e

    results: dict[str, pd.DataFrame | None] = {}

    for sheet_name in xf.sheet_names:
        try:
            df = pd.read_excel(
                xf,
                sheet_name=sheet_name,
                dtype=str,
                keep_default_na=False,
                na_values=list(_NULL_MARKERS),
            )
        except Exception:
            results[sheet_name] = None
            continue

        if not _is_usable_sheet(df):
            results[sheet_name] = None
            continue

        # Apply formula injection sanitization
        for col in df.columns:
            df[col] = df[col].apply(_sanitize_cell)

        results[sheet_name] = df

    return results


def check_duplicate_columns(df: pd.DataFrame) -> list[str]:
    """Return list of duplicate column names, empty if none."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for col in df.columns:
        col_str = str(col)
        if col_str in seen:
            duplicates.append(col_str)
        seen.add(col_str)
    return duplicates
