"""Unit tests — SQL compiler."""

from __future__ import annotations

import pytest
from app.analyst.compiler import SQLCompiler
from app.models.dataset import ColumnInfo, Dataset, DatasetStatus, SemanticType
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
)


def _make_dataset(ds_id: str, table: str, cols: list[str]) -> Dataset:
    return Dataset(
        dataset_id=ds_id,
        internal_table_name=table,
        display_name=ds_id,
        source_file="test.csv",
        source_file_id="abc",
        columns=[
            ColumnInfo(
                name=c,
                physical_type="VARCHAR" if c not in ("revenue", "quantity", "customer_id", "product_id") else "BIGINT",
                semantic_type=SemanticType.METRIC if "revenue" in c or "quantity" in c else SemanticType.DIMENSION,
                unique_ratio=0.9 if "id" in c else 0.3,
            )
            for c in cols
        ],
        status=DatasetStatus.READY,
    )


class TestSQLCompiler:
    def setup_method(self):
        self.orders_ds = _make_dataset(
            "ds_001", "dataset_001",
            ["order_id", "customer_id", "product_id", "order_date", "revenue", "country", "quantity"]
        )
        self.customers_ds = _make_dataset(
            "ds_002", "dataset_002",
            ["customer_id", "name", "region", "tier"]
        )
        self.compiler = SQLCompiler([self.orders_ds, self.customers_ds])

    def test_simple_aggregate(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.AGGREGATION,
            datasets=["ds_001"],
            operations=[
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM, alias="total_revenue"),
            ],
        )
        compiled = self.compiler.compile(plan)
        assert "SUM" in compiled.sql
        assert "revenue" in compiled.sql
        assert compiled.parameters == []

    def test_filter_equals(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.FILTERING,
            datasets=["ds_001"],
            operations=[
                FilterOperation(type="FILTER", column="country", operator=FilterOperator.EQUALS, value="India"),
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM),
            ],
        )
        compiled = self.compiler.compile(plan)
        assert "WHERE" in compiled.sql
        assert "?" in compiled.sql
        assert "India" in compiled.parameters

    def test_group_by_with_sort(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.GROUPING,
            datasets=["ds_001"],
            operations=[
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM, alias="total_revenue"),
            ],
            group_by=["country"],
            sort=SortSpec(column="total_revenue", direction=SortDirection.DESC),
        )
        compiled = self.compiler.compile(plan)
        assert "GROUP BY" in compiled.sql
        assert "ORDER BY" in compiled.sql
        assert "DESC" in compiled.sql

    def test_join_query(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.CROSS_FILE,
            datasets=["ds_001", "ds_002"],
            operations=[
                JoinOperation(
                    type="JOIN",
                    left_dataset="ds_001",
                    left_column="customer_id",
                    right_dataset="ds_002",
                    right_column="customer_id",
                ),
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM, alias="total_revenue"),
            ],
            group_by=["region"],
        )
        compiled = self.compiler.compile(plan)
        assert "JOIN" in compiled.sql
        assert "dataset_001" in compiled.sql
        assert "dataset_002" in compiled.sql

    def test_trend_query(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.TREND,
            datasets=["ds_001"],
            operations=[
                TrendOperation(
                    type="TREND",
                    date_column="order_date",
                    metric_column="revenue",
                    metric_function=AggregationFunction.SUM,
                    unit=DateGroupUnit.MONTH,
                ),
            ],
        )
        compiled = self.compiler.compile(plan)
        assert "DATE_TRUNC" in compiled.sql
        assert "month" in compiled.sql
        assert "period" in compiled.sql

    def test_filter_in_operator(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.FILTERING,
            datasets=["ds_001"],
            operations=[
                FilterOperation(
                    type="FILTER",
                    column="country",
                    operator=FilterOperator.IN,
                    value=["India", "UAE"],
                ),
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM),
            ],
        )
        compiled = self.compiler.compile(plan)
        assert "IN" in compiled.sql
        assert "India" in compiled.parameters
        assert "UAE" in compiled.parameters

    def test_year_equals_filter(self):
        plan = AnalyticalPlan(
            status=PlanStatus.READY,
            intent=Intent.FILTERING,
            datasets=["ds_001"],
            operations=[
                FilterOperation(
                    type="FILTER",
                    column="order_date",
                    operator=FilterOperator.YEAR_EQUALS,
                    value=2025,
                ),
                AggregateOperation(type="AGGREGATE", column="revenue", function=AggregationFunction.SUM),
            ],
        )
        compiled = self.compiler.compile(plan)
        assert "YEAR(" in compiled.sql
        assert 2025 in compiled.parameters
