"""Unit tests for CSV ingestion module."""

from __future__ import annotations

import pytest

from app.ingestion.csv import (
    CSVParseError,
    check_duplicate_columns,
    detect_delimiter,
    parse_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\n"

SEMICOLON_CSV = b"name;age;city\nAlice;30;NYC\nBob;25;LA\n"

TAB_CSV = b"name\tage\tcity\nAlice\t30\tNYC\n"

FORMULA_CSV = b"name,formula\nAlice,=SUM(A1:B2)\nBob,+dangerous\n"

EMPTY_CSV = b""

DUPLICATE_COL_CSV = b"a,b,a\n1,2,3\n"

LARGE_ROW_COUNT_CSV = (b"x,y\n" + b"1,2\n" * 1_000_001)


# ---------------------------------------------------------------------------
# parse_csv tests
# ---------------------------------------------------------------------------


class TestParseCsv:
    def test_parse_simple_csv(self):
        df = parse_csv(SIMPLE_CSV, "test.csv")
        assert list(df.columns) == ["name", "age", "city"]
        assert len(df) == 2
        assert df["name"].iloc[0] == "Alice"

    def test_formula_injection_sanitized(self):
        df = parse_csv(FORMULA_CSV, "formulas.csv")
        # Formulas starting with = or + should be prefixed with apostrophe
        assert df["formula"].iloc[0].startswith("'")
        assert df["formula"].iloc[1].startswith("'")

    def test_empty_csv_raises(self):
        with pytest.raises(CSVParseError, match="empty"):
            parse_csv(EMPTY_CSV, "empty.csv")

    def test_bad_encoding_raises(self):
        # Completely invalid bytes that can't be decoded
        bad_bytes = bytes([0x80, 0x81, 0x82, 0x83] * 10)
        with pytest.raises(CSVParseError, match="encoding"):
            parse_csv(bad_bytes, "broken.csv")

    def test_exceeds_row_limit_raises(self):
        with pytest.raises(CSVParseError, match="rows"):
            parse_csv(LARGE_ROW_COUNT_CSV, "huge.csv")

    def test_latin1_encoding(self):
        latin1_csv = "name,city\nMüller,Köln\n".encode("latin-1")
        df = parse_csv(latin1_csv, "latin1.csv")
        assert len(df) == 1

    def test_utf8_bom_stripped(self):
        bom_csv = b"\xef\xbb\xbf" + b"col1,col2\n1,2\n"
        df = parse_csv(bom_csv, "bom.csv")
        assert "col1" in df.columns  # BOM should be stripped from header

    def test_csv_parse_error_has_filename(self):
        with pytest.raises(CSVParseError) as exc_info:
            parse_csv(EMPTY_CSV, "my_file.csv")
        assert exc_info.value.filename == "my_file.csv"


# ---------------------------------------------------------------------------
# detect_delimiter tests
# ---------------------------------------------------------------------------


class TestDetectDelimiter:
    def test_detects_comma(self):
        assert detect_delimiter(SIMPLE_CSV, "test.csv") == ","

    def test_detects_semicolon(self):
        assert detect_delimiter(SEMICOLON_CSV, "test.csv") == ";"

    def test_detects_tab(self):
        assert detect_delimiter(TAB_CSV, "test.csv") == "\t"

    def test_empty_defaults_to_comma(self):
        assert detect_delimiter(b"", "empty.csv") == ","


# ---------------------------------------------------------------------------
# check_duplicate_columns tests
# ---------------------------------------------------------------------------


class TestCheckDuplicateColumns:
    def test_no_duplicates(self):
        df = parse_csv(SIMPLE_CSV, "test.csv")
        assert check_duplicate_columns(df, "test.csv") == []

    def test_detects_duplicates(self):
        df = parse_csv(DUPLICATE_COL_CSV, "dup.csv")
        # pandas renames duplicates, so we test the function directly
        import pandas as pd

        df_manual = pd.DataFrame(columns=["a", "b", "a"])
        dupes = check_duplicate_columns(df_manual, "manual")
        assert "a" in dupes
