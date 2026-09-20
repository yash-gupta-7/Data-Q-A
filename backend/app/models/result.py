"""Models for query execution results and validation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ColumnMeta(BaseModel):
    name: str
    type: str  # "string", "number", "date", "boolean"


class DataQualityInfo(BaseModel):
    rows_analyzed: int = 0
    total_rows: int = 0
    nulls_excluded: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    columns: list[ColumnMeta] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    total_row_count: int = 0  # before truncation
    truncated: bool = False
    execution_time_ms: float = 0.0
    data_quality: DataQualityInfo = Field(default_factory=DataQualityInfo)


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    VALIDATED_WITH_WARNINGS = "VALIDATED_WITH_WARNINGS"
    BLOCKED = "BLOCKED"


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str | None = None


class ValidationResult(BaseModel):
    status: ValidationStatus
    validation_score: float  # 0.0 - 1.0, diagnostic only
    checks: list[ValidationCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_reason: str | None = None


class ProvenanceInfo(BaseModel):
    datasets_used: list[str] = Field(default_factory=list)  # display names
    columns_used: list[str] = Field(default_factory=list)
    rows_analyzed: int = 0
    operations_summary: list[str] = Field(default_factory=list)
    compiled_sql: str | None = None  # shown in collapsed section


class ExplanationResult(BaseModel):
    answer: str
    key_points: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Full response for a single query."""
    question: str
    plan_status: str  # ready / clarification / unsupported
    clarification_question: str | None = None
    unsupported_reason: str | None = None
    result: QueryResult | None = None
    validation: ValidationResult | None = None
    explanation: ExplanationResult | None = None
    provenance: ProvenanceInfo | None = None
    visualization: dict[str, Any] | None = None  # chart spec
    processing_stages: list[str] = Field(default_factory=list)
