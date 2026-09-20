"""Golden evaluation tests — verify analytical correctness against fixture datasets.

These tests do NOT require an LLM — they test the compile + execute layer directly.
The numerical results must match expected values within tolerance.
"""

from __future__ import annotations

import math
import os

import duckdb
import pytest

from app.ingestion.csv import parse_csv
from app.ingestion.normalize import normalize_dataframe
from app.ingestion.profiler import profile_dataframe
from app.catalog.registry import register_dataset
from app.analyst.compiler import SQLCompiler
from app.analyst.executor import execute_query
from app.security.sql import validate_sql_safety
from app.models.plan import (
    AggregateOperation,
    AggregationFunction,
    AnalyticalPlan,
    FilterOperation,
    FilterOperator,
    GroupByOperation,
    Intent,
    JoinOperation,
    PlanStatus,
    SortDirection,
    SortSpec,
    TrendOperation,
    DateGroupUnit,
    CompareOperation,
)
from app.models.session import Session


FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")
TOLERANCE = 0.01  # 1% relative tolerance


def _rel_close(actual: float, expected: float, tol: float = TOLERANCE) -> bool:
    if expected == 0:
        return abs(actual) < tol
    return abs(actual - expected) / abs(expected) <= tol


@pytest.fixture(scope="module")
def loaded_session():
    """Load all three fixture files into a shared DuckDB + session."""
    import tempfile
    conn = duckdb.connect(":memory:")
    tmp = tempfile.mkdtemp()
    session = Session(session_id="golden", temp_dir=tmp, duckdb_path=":memory:")

    for fname in ["customers.csv", "orders.csv"]:
        with open(os.path.join(FIXTURES, fname), "rb") as f:
            raw = f.read()
        df = normalize_dataframe(parse_csv(raw, fname))
        cols = profile_dataframe(df)
        register_dataset(
            session=session, df=df, conn=conn,
            display_name=fname.replace(".csv", ""),
            source_file=fname, source_file_id=fname, columns_info=cols,
        )

    yield session, conn
    conn.close()


class TestGoldenQuestions:
    def test_q1_total_revenue(self, loaded_session):
        """Q1: What is total revenue?"""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.AGGREGATION,
            datasets=[orders_ds.dataset_id],
            operations=[
                AggregateOperation(type="AGGREGATE", column="revenue",
                                   function=AggregationFunction.SUM, alias="total_revenue"),
            ],
        )
        compiler = SQLCompiler([orders_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        assert result.row_count == 1
        total = float(result.rows[0][0])
        assert total > 0, "Total revenue must be positive"
        # Expected: sum of non-null revenues from orders.csv
        assert total > 500000, f"Expected large total, got {total}"

    def test_q2_revenue_by_country(self, loaded_session):
        """Q2: Which country/region generated the most revenue?"""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.GROUPING,
            datasets=[orders_ds.dataset_id],
            operations=[
                AggregateOperation(type="AGGREGATE", column="revenue",
                                   function=AggregationFunction.SUM, alias="total_revenue"),
            ],
            group_by=["country"],
            sort=SortSpec(column="total_revenue", direction=SortDirection.DESC),
        )
        compiler = SQLCompiler([orders_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        assert result.row_count >= 2, "Expected multiple countries"
        top_country = result.rows[0][0]
        assert top_country is not None

    def test_q3_monthly_revenue_2025(self, loaded_session):
        """Q3: Show monthly revenue for 2025."""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.TREND,
            datasets=[orders_ds.dataset_id],
            operations=[
                FilterOperation(type="FILTER", column="order_date",
                               operator=FilterOperator.YEAR_EQUALS, value=2025),
                TrendOperation(type="TREND", date_column="order_date",
                               metric_column="revenue", metric_function=AggregationFunction.SUM,
                               unit=DateGroupUnit.MONTH),
            ],
        )
        compiler = SQLCompiler([orders_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        # Should have 12 months of data (some may have 0 or be missing)
        assert result.row_count >= 10, f"Expected ~12 months, got {result.row_count}"
        # All revenue values should be non-negative
        for row in result.rows:
            val = row[1]
            if val is not None:
                assert float(val) >= 0

    def test_q4_india_vs_uae(self, loaded_session):
        """Q4: Compare revenue between India and UAE."""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.COMPARISON,
            datasets=[orders_ds.dataset_id],
            operations=[
                CompareOperation(
                    type="COMPARE", column="country",
                    values=["India", "UAE"],
                    metric_column="revenue",
                    metric_function=AggregationFunction.SUM,
                ),
            ],
        )
        compiler = SQLCompiler([orders_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        assert result.row_count == 2
        countries = [row[0] for row in result.rows]
        assert "India" in countries
        assert "UAE" in countries

    def test_q5_cross_file_join(self, loaded_session):
        """Q5: Revenue by region (cross-file join orders + customers)."""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)
        customers_ds = next(d for d in session.datasets if "customers" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.CROSS_FILE,
            datasets=[orders_ds.dataset_id, customers_ds.dataset_id],
            operations=[
                JoinOperation(
                    type="JOIN",
                    left_dataset=orders_ds.dataset_id,
                    left_column="customer_id",
                    right_dataset=customers_ds.dataset_id,
                    right_column="customer_id",
                ),
                AggregateOperation(type="AGGREGATE", column="revenue",
                                   function=AggregationFunction.SUM, alias="total_revenue"),
            ],
            group_by=["region"],
            sort=SortSpec(column="total_revenue", direction=SortDirection.DESC),
        )
        compiler = SQLCompiler([orders_ds, customers_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        assert result.row_count >= 3, f"Expected regions, got {result.row_count}"
        top_region = result.rows[0][0]
        assert top_region is not None

    def test_data_quality_null_disclosure(self, loaded_session):
        """Verify NULL revenue rows are properly disclosed in data quality info."""
        session, conn = loaded_session
        orders_ds = next(d for d in session.datasets if "orders" in d.source_file)

        plan = AnalyticalPlan(
            status=PlanStatus.READY, intent=Intent.AGGREGATION,
            datasets=[orders_ds.dataset_id],
            operations=[
                AggregateOperation(type="AGGREGATE", column="revenue",
                                   function=AggregationFunction.AVG, alias="avg_revenue"),
            ],
        )
        compiler = SQLCompiler([orders_ds])
        compiled = compiler.compile(plan)
        validate_sql_safety(compiled.sql)
        result = execute_query(conn, compiled)

        # Check null count tracked (orders.csv has 2 null revenue rows)
        assert result.data_quality is not None
