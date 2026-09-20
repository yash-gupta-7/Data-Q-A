"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_timeout_seconds: int = 30

    # File limits
    max_file_size_mb: int = 25
    max_files_per_session: int = 10
    max_session_size_mb: int = 100

    # Query limits
    max_result_rows: int = 1000
    query_timeout_seconds: int = 10

    # Relationship detection thresholds
    relationship_auto_join_threshold: float = 0.90
    relationship_suggest_threshold: float = 0.70

    # Analytical plan
    max_plan_retries: int = 1
    max_join_depth: int = 3

    # App — stored as str, parsed by .cors_origins property
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"

    # Session storage base dir
    session_base_dir: str = "/tmp/ai-analyst-sessions"

    # Prompt versioning (increment when prompts change to invalidate caches)
    prompt_version: str = "v1"

    @property
    def cors_origins(self) -> list[str]:
        """Parse BACKEND_CORS_ORIGINS — accepts comma-separated or JSON array."""
        v = self.backend_cors_origins.strip()
        if v.startswith("["):
            import json as _json
            return _json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_session_size_bytes(self) -> int:
        return self.max_session_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
