"""Integration tests — full ingestion pipeline with real fixture files."""

from __future__ import annotations

import os

import duckdb
import pytest

from app.ingestion.csv import parse_csv
from app.ingestion.excel import parse_excel
from app.ingestion.normalize import normalize_dataframe
from app.ingestion.profiler import profile_dataframe
from app.catalog.registry import register_dataset
from app.catalog.relationships import detect_relationships
from app.models.session import Session
from app.models.dataset import DatasetStatus


FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


@pytest.fixture
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def empty_session():
    import tempfile
    tmp = tempfile.mkdtemp()
    return Session(
        session_id="test-session",
        temp_dir=tmp,
        duckdb_path=os.path.join(tmp, "test.duckdb"),
    )


class TestIngestionPipeline:
    def test_csv_full_pipeline(self, duckdb_conn, empty_session):
        """Ingest orders.csv and verify dataset registration."""
        with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
            raw_bytes = f.read()

        raw_df = parse_csv(raw_bytes, "orders.csv")
        assert len(raw_df) == 45
        assert "revenue" in raw_df.columns

        norm_df = normalize_dataframe(raw_df)
        # revenue should be numeric after normalization
        assert str(norm_df["revenue"].dtype).startswith("float") or "int" in str(norm_df["revenue"].dtype)

        cols = profile_dataframe(norm_df)
        assert len(cols) > 0
        col_names = [c.name for c in cols]
        assert "revenue" in col_names
        assert "order_date" in col_names

        dataset = register_dataset(
            session=empty_session,
            df=norm_df,
            conn=duckdb_conn,
            display_name="orders",
            source_file="orders.csv",
            source_file_id="file001",
            columns_info=cols,
        )
        assert dataset.status == DatasetStatus.READY
        assert dataset.row_count == 45

        # Verify DuckDB table exists and queryable
        result = duckdb_conn.execute(f'SELECT COUNT(*) FROM "{dataset.internal_table_name}"').fetchone()
        assert result[0] == 45

    def test_xlsx_multi_sheet_pipeline(self, duckdb_conn, empty_session):
        """Ingest products.xlsx and verify multi-sheet handling."""
        with open(os.path.join(FIXTURES, "products.xlsx"), "rb") as f:
            raw_bytes = f.read()

        sheets = parse_excel(raw_bytes, "products.xlsx")

        # Products sheet should be parsed
        assert "Products" in sheets
        assert sheets["Products"] is not None

        # Pricing Tiers should also be parsed
        assert "Pricing Tiers" in sheets
        assert sheets["Pricing Tiers"] is not None

        # Notes sheet may not be skipped if it has 2+ rows — this depends on content
        # Our fixture Notes sheet has 2 rows, so it may be parsed as tabular
        # The important thing is that Products sheet IS parsed correctly
        assert sheets["Products"] is not None

        products_df = normalize_dataframe(sheets["Products"])
        cols = profile_dataframe(products_df)
        dataset = register_dataset(
            session=empty_session,
            df=products_df,
            conn=duckdb_conn,
            display_name="Products",
            source_file="products.xlsx",
            source_file_id="file002",
            columns_info=cols,
            sheet_name="Products",
        )
        assert dataset.row_count == 6

    def test_relationship_detection(self, duckdb_conn, empty_session):
        """Detect customer_id relationship between customers and orders."""
        for fname in ["customers.csv", "orders.csv"]:
            with open(os.path.join(FIXTURES, fname), "rb") as f:
                raw = f.read()
            df = normalize_dataframe(parse_csv(raw, fname))
            cols = profile_dataframe(df)
            register_dataset(
                session=empty_session,
                df=df,
                conn=duckdb_conn,
                display_name=fname,
                source_file=fname,
                source_file_id=fname,
                columns_info=cols,
            )

        active = empty_session.get_active_datasets()
        assert len(active) == 2

        from app.catalog.registry import get_dataframes_from_duckdb
        dfs = get_dataframes_from_duckdb(empty_session, duckdb_conn)
        relationships = detect_relationships(active, dfs)

        # Should detect customer_id link
        rel_keys = [
            (r.left_column, r.right_column) for r in relationships
        ]
        assert any("customer_id" in k[0] or "customer_id" in k[1] for k in rel_keys), \
            f"Expected customer_id relationship, got: {rel_keys}"

    def test_query_after_ingestion(self, duckdb_conn, empty_session):
        """Full pipeline: ingest orders.csv → compile + execute a query."""
        from app.analyst.compiler import SQLCompiler
        from app.analyst.executor import execute_query
        from app.models.plan import (
            AggregateOperation, AggregationFunction, AnalyticalPlan,
            Intent, PlanStatus,
        )

        with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
            raw = f.read()
        df = normalize_dataframe(parse_csv(raw, "orders.csv"))
        cols = profile_dataframe(df)
        dataset = register_dataset(
            session=empty_session,
            df=df,
            conn=duckdb_conn,
            display_name="orders",
            source_file="orders.csv",
            source_file_id="x",
            columns_info=cols,
        )

        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.AGGREGATION,
            datasets=[dataset.dataset_id],
            operations=[
                AggregateOperation(
                    type="AGGREGATE",
                    column="revenue",
                    function=AggregationFunction.SUM,
                    alias="total_revenue",
                )
            ],
        )

        compiler = SQLCompiler([dataset])
        from app.security.sql import validate_sql_safety
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(duckdb_conn, compiled)

        assert result.row_count == 1
        total = result.rows[0][0]
        # Total revenue from orders (excluding 2 NULL rows) - should be > 0
        assert total is not None and float(total) > 0
        # Approximate expected total (sum of non-null revenues)
        import pandas as pd
        expected = df["revenue"].dropna().sum()
        assert abs(float(total) - float(expected)) < 1.0, f"Expected ~{expected}, got {total}"
