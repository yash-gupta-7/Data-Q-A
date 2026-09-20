"""Pydantic models for the Analytical DSL — closed-world plan schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_validator


# ────────────────────────────────────────────────────────────────────────────
# DSL Enumerations
# ────────────────────────────────────────────────────────────────────────────

class AggregationFunction(str, Enum):
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    MIN = "MIN"
    MAX = "MAX"
    # Extensible:
    MEDIAN = "MEDIAN"
    STDDEV = "STDDEV"
    VARIANCE = "VARIANCE"


class FilterOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    BETWEEN = "BETWEEN"
    YEAR_EQUALS = "YEAR_EQUALS"
    MONTH_EQUALS = "MONTH_EQUALS"


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class DateGroupUnit(str, Enum):
    YEAR = "YEAR"
    QUARTER = "QUARTER"
    MONTH = "MONTH"
    WEEK = "WEEK"
    DAY = "DAY"


class Intent(str, Enum):
    AGGREGATION = "aggregation"
    GROUPING = "grouping"
    FILTERING = "filtering"
    TREND = "trend"
    COMPARISON = "comparison"
    CROSS_FILE = "cross_file"
    LISTING = "listing"


# ────────────────────────────────────────────────────────────────────────────
# Operations
# ────────────────────────────────────────────────────────────────────────────

class FilterOperation(BaseModel):
    type: Literal["FILTER"] = "FILTER"
    column: str
    operator: FilterOperator
    value: Any = None  # None for IS_NULL / IS_NOT_NULL; list for IN/NOT_IN/BETWEEN
    dataset: str | None = None  # optional: which dataset this column belongs to


class AggregateOperation(BaseModel):
    type: Literal["AGGREGATE"] = "AGGREGATE"
    column: str
    function: AggregationFunction
    alias: str | None = None
    dataset: str | None = None


class SelectOperation(BaseModel):
    type: Literal["SELECT"] = "SELECT"
    columns: list[str]
    dataset: str | None = None


class GroupByOperation(BaseModel):
    type: Literal["GROUP_BY"] = "GROUP_BY"
    columns: list[str]
    dataset: str | None = None


class SortSpec(BaseModel):
    column: str
    direction: SortDirection = SortDirection.DESC


class JoinOperation(BaseModel):
    type: Literal["JOIN"] = "JOIN"
    left_dataset: str
    left_column: str
    right_dataset: str
    right_column: str
    join_type: Literal["INNER", "LEFT"] = "LEFT"


class DateGroupOperation(BaseModel):
    type: Literal["DATE_GROUP"] = "DATE_GROUP"
    column: str
    unit: DateGroupUnit
    alias: str | None = None
    dataset: str | None = None


class CompareOperation(BaseModel):
    type: Literal["COMPARE"] = "COMPARE"
    column: str
    values: list[Any]
    metric_column: str
    metric_function: AggregationFunction = AggregationFunction.SUM
    dataset: str | None = None


class TrendOperation(BaseModel):
    type: Literal["TREND"] = "TREND"
    date_column: str
    metric_column: str
    metric_function: AggregationFunction = AggregationFunction.SUM
    unit: DateGroupUnit = DateGroupUnit.MONTH
    dataset: str | None = None


Operation = Union[
    FilterOperation,
    AggregateOperation,
    SelectOperation,
    GroupByOperation,
    JoinOperation,
    DateGroupOperation,
    CompareOperation,
    TrendOperation,
]


# ────────────────────────────────────────────────────────────────────────────
# Visualization Hint
# ────────────────────────────────────────────────────────────────────────────

class ChartType(str, Enum):
    KPI = "kpi"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    GROUPED_BAR = "grouped_bar"
    HISTOGRAM = "histogram"
    TABLE = "table"


class VisualizationHint(BaseModel):
    type: ChartType
    x: str | None = None
    y: str | None = None
    series: str | None = None
    title: str | None = None


# ────────────────────────────────────────────────────────────────────────────
# Analytical Plan (LLM output, Pydantic-validated)
# ────────────────────────────────────────────────────────────────────────────

class PlanStatus(str, Enum):
    READY = "ready"
    CLARIFICATION = "clarification"
    UNSUPPORTED = "unsupported"


class AnalyticalPlan(BaseModel):
    status: PlanStatus
    intent: Intent | None = None
    datasets: list[str] = Field(default_factory=list)  # dataset_ids
    operations: list[Operation] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    sort: SortSpec | None = None
    limit: int | None = None
    visualization: VisualizationHint | None = None
    assumptions: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    unsupported_reason: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> "AnalyticalPlan":
        if self.status == PlanStatus.CLARIFICATION and not self.clarification_question:
            raise ValueError("clarification_question required when status=clarification")
        if self.status == PlanStatus.UNSUPPORTED and not self.unsupported_reason:
            raise ValueError("unsupported_reason required when status=unsupported")
        if self.status == PlanStatus.READY and not self.datasets:
            raise ValueError("datasets required when status=ready")
        return self
