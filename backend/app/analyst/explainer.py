"""Explanation LLM — grounded natural-language explanation of verified results."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.analyst.compiler import CompiledQuery
from app.analyst.prompts.explainer_v1 import EXPLAINER_SYSTEM_PROMPT
from app.llm.base import LLMError, LLMProvider
from app.models.result import ExplanationResult, QueryResult, ValidationResult

logger = logging.getLogger(__name__)


def _format_result_for_explainer(result: QueryResult, max_rows: int = 20) -> str:
    """Convert QueryResult to a compact text representation for the LLM."""
    if not result.columns:
        return "Result: empty"

    col_names = [c.name for c in result.columns]
    rows_to_show = result.rows[:max_rows]

    lines = [f"Columns: {', '.join(col_names)}"]
    lines.append(f"Rows ({min(result.row_count, max_rows)} shown):")
    for row in rows_to_show:
        row_parts = []
        for i, val in enumerate(row):
            col = col_names[i] if i < len(col_names) else f"col{i}"
            row_parts.append(f"{col}={val}")
        lines.append("  " + ", ".join(row_parts))

    if result.truncated:
        lines.append(f"... (truncated to {result.row_count} rows)")

    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Extract JSON from model response."""
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class Explainer:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def explain(
        self,
        question: str,
        result: QueryResult,
        validation: ValidationResult,
        compiled: CompiledQuery,
        assumptions: list[str],
    ) -> ExplanationResult:
        """
        Generate a grounded explanation from verified result data.
        The LLM MUST NOT recalculate or invent values.
        """
        result_text = _format_result_for_explainer(result)
        warnings_text = "\n".join(validation.warnings) if validation.warnings else "None"
        assumptions_text = "\n".join(assumptions) if assumptions else "None"

        user_message = f"""Question: {question}

Verified result data:
{result_text}

Data quality warnings:
{warnings_text}

Assumptions made:
{assumptions_text}

Datasets used: {', '.join(compiled.datasets_used)}
Operations: {', '.join(compiled.operations_summary)}

Generate the JSON explanation:"""

        messages = [
            {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            raw = await self.llm.complete_json(messages=messages, temperature=0.1, max_tokens=1024)
            extracted = _extract_json(raw)
            data = json.loads(extracted)
            return ExplanationResult(
                answer=data.get("answer", "The analysis is complete. Please see the results above."),
                key_points=data.get("key_points", []),
                assumptions=data.get("assumptions", assumptions),
                warnings=data.get("warnings", validation.warnings),
            )
        except (LLMError, json.JSONDecodeError, Exception) as e:
            logger.warning("Explainer LLM failed: %s", e)
            # Fallback: generate basic explanation from result data
            return _fallback_explanation(question, result, validation, assumptions)


def _fallback_explanation(
    question: str,
    result: QueryResult,
    validation: ValidationResult,
    assumptions: list[str],
) -> ExplanationResult:
    """Generate a basic explanation without LLM when the model fails."""
    if result.row_count == 0:
        answer = "The query returned no results."
    elif result.row_count == 1 and len(result.columns) == 1:
        val = result.rows[0][0] if result.rows else "N/A"
        answer = f"The result is: {val}"
    else:
        answer = f"The analysis returned {result.row_count} rows across {len(result.columns)} columns."

    key_points = []
    for col_idx, col in enumerate(result.columns[:3]):
        if col.type == "number" and result.rows:
            vals = [row[col_idx] for row in result.rows if col_idx < len(row) and row[col_idx] is not None]
            if vals:
                try:
                    key_points.append(f"{col.name}: max={max(vals)}, min={min(vals)}")
                except Exception:
                    pass

    return ExplanationResult(
        answer=answer,
        key_points=key_points,
        assumptions=assumptions,
        warnings=validation.warnings,
    )
