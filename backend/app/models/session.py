"""Session model and conversation state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.dataset import Dataset, Relationship
from app.models.result import QueryResponse


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_response: QueryResponse | None = None  # for assistant messages


class ConversationState(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    # Last N messages for LLM context (configurable)
    max_context_messages: int = 6

    def get_context_messages(self) -> list[ConversationMessage]:
        return self.messages[-self.max_context_messages :]

    def add_user_message(self, content: str) -> None:
        self.messages.append(ConversationMessage(role="user", content=content))

    def add_assistant_message(self, content: str, response: QueryResponse | None = None) -> None:
        self.messages.append(
            ConversationMessage(role="assistant", content=content, query_response=response)
        )


class UploadedFile(BaseModel):
    file_id: str  # UUID
    original_filename: str  # display only
    internal_path: str  # UUID-based safe path
    size_bytes: int
    mime_type: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    dataset_ids: list[str] = Field(default_factory=list)  # datasets extracted from this file


class DataReadinessSummary(BaseModel):
    files_processed: int = 0
    datasets_detected: int = 0
    total_rows: int = 0
    total_columns: int = 0
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_sheets: list[str] = Field(default_factory=list)


class Session(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    temp_dir: str
    duckdb_path: str
    files: list[UploadedFile] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    conversation: ConversationState = Field(default_factory=ConversationState)
    readiness: DataReadinessSummary = Field(default_factory=DataReadinessSummary)
    # Caches (not serialized to client)
    _planner_cache: dict[str, Any] = {}
    _result_cache: dict[str, Any] = {}

    model_config = {"arbitrary_types_allowed": True}

    def get_dataset_by_id(self, dataset_id: str) -> Dataset | None:
        return next((d for d in self.datasets if d.dataset_id == dataset_id), None)

    def get_dataset_by_table(self, table_name: str) -> Dataset | None:
        return next((d for d in self.datasets if d.internal_table_name == table_name), None)

    def get_active_datasets(self) -> list[Dataset]:
        from app.models.dataset import DatasetStatus
        return [d for d in self.datasets if d.status == DatasetStatus.READY]
