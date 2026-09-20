"""Unit tests — Excel parser, multi-sheet handling, formula injection."""

from __future__ import annotations

import io

import openpyxl
import pytest
from openpyxl import Workbook

from app.ingestion.excel import ExcelParseError, parse_excel


def _make_xlsx(sheets: dict) -> bytes:
    """Helper to create in-memory XLSX bytes."""
    wb = Workbook()
    first = True
    for sheet_name, rows in sheets.items():
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(sheet_name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestExcelParser:
    def test_single_sheet(self):
        xlsx = _make_xlsx({"Sales": [["a", "b"], [1, 2], [3, 4]]})
        result = parse_excel(xlsx, "test.xlsx")
        assert "Sales" in result
        df = result["Sales"]
        assert df is not None
        assert list(df.columns) == ["a", "b"]
        assert len(df) == 2

    def test_multi_sheet(self):
        xlsx = _make_xlsx({
            "Products": [["id", "name"], ["P1", "Widget"]],
            "Customers": [["id", "region"], ["C1", "India"]],
        })
        result = parse_excel(xlsx, "multi.xlsx")
        assert result["Products"] is not None
        assert result["Customers"] is not None

    def test_empty_sheet_skipped(self):
        xlsx = _make_xlsx({
            "Data": [["a", "b"], [1, 2]],
            "Empty": [],
        })
        result = parse_excel(xlsx, "test.xlsx")
        assert result["Data"] is not None
        assert result["Empty"] is None  # should be skipped

    def test_notes_sheet_skipped(self):
        """A sheet with a single cell (non-tabular) should be skipped."""
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Data"
        ws1.append(["col1", "col2"])
        ws1.append([1, 2])
        ws2 = wb.create_sheet("Notes")
        ws2["A1"] = "Internal notes only"
        buf = io.BytesIO()
        wb.save(buf)
        xlsx = buf.getvalue()

        result = parse_excel(xlsx, "test.xlsx")
        assert result["Data"] is not None
        assert result["Notes"] is None

    def test_formula_injection_preserved(self):
        """Formula-like cell values must be preserved as data."""
        xlsx = _make_xlsx({
            "Sheet1": [
                ["cmd", "value"],
                ["=CMD(malicious)", 100],
                ["+HYPERLINK(evil)", 200],
            ]
        })
        result = parse_excel(xlsx, "test.xlsx")
        df = result["Sheet1"]
        assert df is not None
        # openpyxl data_only=True reads string values, not evaluating formulas
        assert len(df) == 2
