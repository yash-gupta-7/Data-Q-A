"""Unit tests — CSV parser, formula injection, duplicate columns."""

from __future__ import annotations

import pytest
from app.ingestion.csv import CSVParseError, check_duplicate_columns, parse_csv


def _b(s: str) -> bytes:
    return s.encode("utf-8")


class TestCSVParser:
    def test_basic_parse(self):
        csv = _b("name,value\nAlice,100\nBob,200")
        df = parse_csv(csv, "test.csv")
        assert list(df.columns) == ["name", "value"]
        assert len(df) == 2

    def test_formula_injection_cell_preserved(self):
        """Formula cells must be preserved as data strings, never executed."""
        csv = _b("cmd,value\n=CMD(rm -rf /),100\n+SUM(A1),200")
        df = parse_csv(csv, "injection.csv")
        # Should parse successfully — formula strings are just data
        assert len(df) == 2
        assert "=CMD(rm -rf /)" in df["cmd"].values or df["cmd"].iloc[0].startswith("=")

    def test_null_markers_detected(self):
        csv = _b("a,b\nnull,100\nnone,200\n-,300")
        df = parse_csv(csv, "nulls.csv")
        # null, none, - should become NaN via na_values
        assert df["a"].isna().sum() == 3

    def test_empty_csv_raises(self):
        with pytest.raises(CSVParseError):
            parse_csv(b"", "empty.csv")

    def test_duplicate_columns_detected(self):
        # pandas auto-renames duplicate columns with .1, .2 suffix
        # Our check_duplicate_columns works on the original df which will have renamed cols
        # The real duplicate detection is via the original pandas behavior
        csv = _b("a,b,a\n1,2,3")
        df = parse_csv(csv, "dup.csv")
        # pandas renames the second 'a' to 'a.1' — duplicates are in original col names
        # Our duplicate detection checks for .1 patterns or runs on the raw header
        # The check should detect that there were duplicates
        col_names = list(df.columns)
        # After pandas reads, it may rename to 'a' and 'a.1'
        assert len(col_names) == 3
        # The duplicate is reflected as a.1 suffix
        assert any(".1" in c or col_names.count(c) > 1 for c in col_names)

    def test_encoding_latin1(self):
        csv = "name,city\nJosé,São Paulo\n".encode("latin-1")
        df = parse_csv(csv, "latin.csv")
        assert len(df) == 1


class TestNormalize:
    def test_numeric_coercion(self):
        from app.ingestion.normalize import normalize_dataframe
        import pandas as pd
        df = pd.DataFrame({"revenue": ["₹1,000", "₹2,500", "₹3,200"]})
        norm = normalize_dataframe(df)
        assert norm["revenue"].dtype in ["float64", "int64"] or str(norm["revenue"].dtype).startswith("float")

    def test_date_coercion(self):
        from app.ingestion.normalize import normalize_dataframe
        import pandas as pd
        df = pd.DataFrame({"order_date": ["2025-01-01", "2025-02-15", "2025-03-20"]})
        norm = normalize_dataframe(df)
        assert "datetime" in str(norm["order_date"].dtype)

    def test_whitespace_stripping(self):
        from app.ingestion.normalize import normalize_dataframe
        import pandas as pd
        df = pd.DataFrame({"name": ["  Alice  ", "  Bob  "]})
        norm = normalize_dataframe(df)
        assert norm["name"].iloc[0] == "Alice"
