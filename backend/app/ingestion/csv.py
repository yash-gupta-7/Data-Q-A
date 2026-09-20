"""CSV ingestion — safe parsing with formula injection protection."""

from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Values treated as NULL during normalization
_NULL_MARKERS = {"", "na", "n/a", "null", "none", "nan", "-", "—", "#n/a", "#null!", "nil"}

# Formula injection prefixes (treated as data, never executed)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Maximum columns and rows allowed
MAX_COLUMNS = 500
MAX_ROWS = 1_000_000


class CSVParseError(Exception):
    """Raised when CSV parsing fails."""

    def __init__(self, message: str, filename: str | None = None):
        super().__init__(message)
        self.filename = filename


def _sanitize_cell(value: Any) -> Any:
    """Ensure formula-like string values are treated as data (not executed).

    Strips leading formula-injection characters used in spreadsheet attacks.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in ("=", "+", "@"):
            # Prefix with apostrophe to mark as plain text
            return "'" + stripped
    return value


def parse_csv(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Parse CSV bytes into a DataFrame.

    Steps:
    1. Auto-detect character encoding (utf-8-sig → utf-8 → latin-1 → cp1252)
    2. Parse with pandas (all columns as str to defer type coercion)
    3. Sanitize formula-injection patterns in string cells
    4. Validate shape constraints (rows/columns limits)

    Args:
        file_bytes: Raw bytes of the uploaded CSV file.
        filename: Original filename (used in error messages).

    Returns:
        DataFrame with string-typed columns (normalization is a separate step).

    Raises:
        CSVParseError: If decoding, parsing, or validation fails.
    """
    # 1. Encoding detection
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            logger.debug("Decoded '%s' using %s encoding", filename, encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise CSVParseError(
            f"Could not decode '{filename}' with any supported encoding (utf-8, cp1252).",
            filename=filename,
        )

    # 2. Parse CSV
    try:
        df = pd.read_csv(
            io.StringIO(text),
            dtype=str,  # read everything as string first; normalization handles types
            keep_default_na=False,
            na_values=list(_NULL_MARKERS),
            on_bad_lines="warn",
        )
    except Exception as e:
        raise CSVParseError(f"Failed to parse CSV '{filename}': {e}", filename=filename) from e

    # 3. Validate: not empty
    if df.empty and len(df.columns) == 0:
        raise CSVParseError(f"CSV '{filename}' appears to be empty or has no columns.", filename=filename)

    # 4. Validate: shape limits
    if len(df.columns) > MAX_COLUMNS:
        raise CSVParseError(
            f"CSV '{filename}' has {len(df.columns)} columns, exceeding limit of {MAX_COLUMNS}.",
            filename=filename,
        )

    if len(df) > MAX_ROWS:
        raise CSVParseError(
            f"CSV '{filename}' has {len(df):,} rows, exceeding limit of {MAX_ROWS:,}.",
            filename=filename,
        )

    # 5. Sanitize formula injection in all string columns
    for col in df.columns:
        df[col] = df[col].apply(_sanitize_cell)

    logger.info("Parsed CSV '%s': %d rows × %d columns", filename, len(df), len(df.columns))
    return df


def check_duplicate_columns(df: pd.DataFrame, source: str) -> list[str]:
    """Return list of duplicate column names, empty if none.

    Args:
        df: DataFrame to check.
        source: Source identifier for logging.

    Returns:
        List of column names that appear more than once.
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for col in df.columns:
        if col in seen:
            duplicates.append(col)
            logger.warning("Duplicate column '%s' found in %s", col, source)
        seen.add(col)
    return duplicates


def detect_delimiter(file_bytes: bytes, filename: str) -> str:
    """Heuristically detect CSV delimiter (comma, semicolon, tab, pipe).

    Args:
        file_bytes: Raw file bytes.
        filename: Used in logging.

    Returns:
        Detected delimiter character. Defaults to ',' if uncertain.
    """
    try:
        sample = file_bytes[:4096].decode("utf-8-sig", errors="replace")
    except Exception:
        return ","

    counts = {
        ",": sample.count(","),
        ";": sample.count(";"),
        "\t": sample.count("\t"),
        "|": sample.count("|"),
    }
    detected = max(counts, key=lambda k: counts[k])
    logger.debug("Detected delimiter '%s' for '%s' (counts: %s)", repr(detected), filename, counts)
    return detected
