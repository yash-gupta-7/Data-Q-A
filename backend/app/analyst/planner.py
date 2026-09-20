"""Context builder and LLM planner — converts question to AnalyticalPlan."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.analyst.prompts.planner_v1 import PLANNER_SYSTEM_PROMPT
from app.config import get_settings
from app.llm.base import LLMError, LLMProvider
from app.models.dataset import Dataset, Relationship, RelationshipStatus, SemanticType
from app.models.plan import AnalyticalPlan, PlanStatus
from app.models.session import ConversationMessage

logger = logging.getLogger(__name__)


def _build_schema_context(datasets: list[Dataset]) -> str:
    """Build compact schema description for LLM context."""
    lines = []
    for ds in datasets:
        lines.append(f"Dataset: {ds.dataset_id} | Table: {ds.internal_table_name} | Name: {ds.display_name}")
        lines.append(f"  Rows: {ds.row_count:,} | Columns: {ds.column_count}")
        for col in ds.columns:
            pii_flag = " [PII DETECTED - do not use raw values]" if col.quality.pii_detected else ""
            samples = ""
            if col.sample_values and col.semantic_type not in (SemanticType.IDENTIFIER,):
                # Limit to 3 samples to avoid sending too much data
                s = col.sample_values[:3]
                samples = f" | samples: {s}"
            lines.append(
                f"  - {col.name}: {col.physical_type} ({col.semantic_type.value})"
                f" | nullable: {col.nullable} | unique_ratio: {col.unique_ratio:.2f}"
                f"{samples}{pii_flag}"
            )
        lines.append("")
    return "\n".join(lines)


def _build_relationships_context(
    relationships: list[Relationship],
    datasets: list[Dataset],
) -> str:
    """Build relationship description for LLM context."""
    if not relationships:
        return "No detected relationships between datasets."

    ds_map = {d.dataset_id: d.display_name for d in datasets}
    lines = ["Detected relationships:"]
    for rel in relationships:
        if rel.status == RelationshipStatus.HIGH_CONFIDENCE:
            status_label = "AUTO (high-confidence)"
        elif rel.status == RelationshipStatus.SUGGESTED:
            status_label = "SUGGESTED (requires user confirmation)"
        else:
            continue

        left_name = ds_map.get(rel.left_dataset, rel.left_dataset)
        right_name = ds_map.get(rel.right_dataset, rel.right_dataset)
        lines.append(
            f"  {left_name}.{rel.left_column} -> {right_name}.{rel.right_column} "
            f"[{rel.relationship_type.value}] [{status_label}]"
            f" | left_id={rel.left_dataset} right_id={rel.right_dataset}"
        )
    return "\n".join(lines)


def _build_conversation_context(messages: list[ConversationMessage]) -> str:
    """Build recent conversation for follow-up context."""
    if not messages:
        return ""
    lines = ["Recent conversation:"]
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        # For assistant messages, include only the answer text, not full response
        content = msg.content[:500]
        lines.append(f"  {role}: {content}")
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Extract JSON from model response (handles markdown code blocks)."""
    # Try to find JSON block
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Find first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


class Planner:
    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.settings = get_settings()

    def _build_user_message(
        self,
        question: str,
        schema_context: str,
        relationships_context: str,
        conversation_context: str,
    ) -> str:
        parts = [
            f"Schema:\n{schema_context}",
            f"\n{relationships_context}",
        ]
        if conversation_context:
            parts.append(f"\n{conversation_context}")
        parts.append(f"\nQuestion: {question}")
        parts.append("\nReturn the JSON Analytical Plan:")
        return "\n".join(parts)

    def _parse_plan(self, raw_json: str) -> AnalyticalPlan:
        """Parse and validate the LLM response as an AnalyticalPlan."""
        extracted = _extract_json(raw_json)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw_json[:500]}") from e

        return AnalyticalPlan.model_validate(data)

    async def plan(
        self,
        question: str,
        datasets: list[Dataset],
        relationships: list[Relationship],
        recent_messages: list[ConversationMessage],
    ) -> AnalyticalPlan:
        """
        Build context and call LLM to produce an AnalyticalPlan.
        Retries once on parse/validation failure.
        """
        schema_context = _build_schema_context(datasets)
        relationships_context = _build_relationships_context(relationships, datasets)
        conversation_context = _build_conversation_context(recent_messages)

        user_message = self._build_user_message(
            question, schema_context, relationships_context, conversation_context
        )

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        retries = self.settings.max_plan_retries
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                raw = await self.llm.complete_json(messages=messages, temperature=0.0)
                plan = self._parse_plan(raw)
                logger.info(
                    "Plan produced: status=%s intent=%s datasets=%s (attempt %d)",
                    plan.status,
                    plan.intent,
                    plan.datasets,
                    attempt + 1,
                )
                return plan

            except (ValueError, ValidationError) as e:
                last_error = e
                logger.warning("Plan parse/validation failed (attempt %d): %s", attempt + 1, e)
                if attempt < retries:
                    # Add repair instruction
                    messages.append({"role": "assistant", "content": raw if "raw" in dir() else ""})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Your response had a validation error: {e}\n"
                            "Please return a corrected JSON Analytical Plan."
                        ),
                    })
                continue

            except LLMError as e:
                logger.error("LLM error during planning: %s", e)
                raise

        # All retries exhausted — return clarification plan
        return AnalyticalPlan(
            status=PlanStatus.CLARIFICATION,
            clarification_question=(
                "I had trouble understanding your question. Could you rephrase it? "
                f"(Technical: {last_error})"
            ),
        )
