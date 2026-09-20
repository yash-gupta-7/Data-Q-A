"""Pydantic models for datasets and schema catalog."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SemanticType(str, Enum):
    METRIC = "METRIC"
    DIMENSION = "DIMENSION"
    IDENTIFIER = "IDENTIFIER"
    DATE = "DATE"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"


class ColumnQuality(BaseModel):
    null_count: int = 0
    null_pct: float = 0.0
    unique_count: int = 0
    unique_ratio: float = 0.0
    has_formula_injection: bool = False
    pii_detected: list[str] = Field(default_factory=list)


class ColumnInfo(BaseModel):
    name: str
    physical_type: str  # e.g. "INTEGER", "FLOAT", "VARCHAR", "DATE"
    semantic_type: SemanticType
    nullable: bool = True
    unique_ratio: float = 0.0
    sample_values: list[Any] = Field(default_factory=list)
    min_value: Any = None
    max_value: Any = None
    quality: ColumnQuality = Field(default_factory=ColumnQuality)


class DatasetStatus(str, Enum):
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    REMOVED = "removed"


class Dataset(BaseModel):
    dataset_id: str  # e.g. "ds_001"
    internal_table_name: str  # e.g. "dataset_001" — safe SQL identifier
    display_name: str  # human-friendly, e.g. "Sales (Sheet1)"
    source_file: str  # original filename for display only
    source_file_id: str  # UUID internal file id
    sheet_name: str | None = None  # for XLSX sheets
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnInfo] = Field(default_factory=list)
    status: DatasetStatus = DatasetStatus.PROCESSING
    warnings: list[str] = Field(default_factory=list)
    skipped_sheets: list[str] = Field(default_factory=list)


class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class RelationshipStatus(str, Enum):
    HIGH_CONFIDENCE = "high_confidence"   # >= AUTO_JOIN_THRESHOLD → auto-use
    SUGGESTED = "suggested"               # >= SUGGEST_THRESHOLD → ask user
    LOW_CONFIDENCE = "low_confidence"     # below threshold → do not use


class RelationshipEvidence(BaseModel):
    name_similarity: float = 0.0
    name_match: bool = False
    type_match: bool = False
    semantic_match: bool = False
    overlap_ratio: float = 0.0
    left_uniqueness: float = 0.0
    right_uniqueness: float = 0.0
    evidence_score: float = 0.0


class Relationship(BaseModel):
    relationship_id: str
    left_dataset: str  # dataset_id
    left_column: str
    right_dataset: str  # dataset_id
    right_column: str
    relationship_type: RelationshipType
    status: RelationshipStatus
    evidence: RelationshipEvidence
    user_confirmed: bool = False
