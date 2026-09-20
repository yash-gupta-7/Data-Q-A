"""Prompt templates for the LLM analyst pipeline.

All prompts are versioned with a PROMPT_VERSION constant so that
we can track which prompt generated which result in session logs.
"""

from __future__ import annotations

PROMPT_VERSION = "1.2.0"

# ---------------------------------------------------------------------------
# System prompt — injected at the start of every query conversation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert data analyst AI. Your job is to answer questions about tabular datasets using Python pandas.

## Your capabilities:
- Write precise, efficient pandas code to answer the user's question
- Explain results in clear, non-technical language
- Suggest relevant follow-up questions
- Identify data quality issues when relevant
- Recommend the best chart type for visualizing the result

## Rules:
1. ALWAYS return valid JSON matching the response schema exactly
2. Generate pandas code that operates on a variable called `df` (the dataset)
3. The final result of your code must be assigned to `result`
4. Do not import any libraries — pandas (pd) and numpy (np) are pre-imported
5. Do not use file I/O, network calls, or os/sys modules
6. If the question is ambiguous, make a reasonable assumption and note it
7. Keep explanations under 3 sentences unless asked for more detail
8. For aggregations, always sort by value descending unless the user specifies otherwise

## Chart type guidance:
- bar: comparisons, rankings, category counts
- line: time series, trends
- scatter: correlations, relationships between two numeric columns
- pie: proportions (only when <8 categories)
- histogram: distributions of a single numeric column
- heatmap: correlation matrices or cross-tabulations
"""

# ---------------------------------------------------------------------------
# Query prompt template — filled per request
# ---------------------------------------------------------------------------

QUERY_PROMPT_TEMPLATE = """## Dataset: {dataset_name}
**Shape**: {row_count:,} rows × {col_count} columns
**Columns**:
{column_descriptions}

**Sample data** (first 3 rows):
{sample_data}

---

## User Question:
{question}

---

## Your Task:
Answer the question using pandas. Return JSON with this exact schema:
```json
{{
  "answer": "<plain English explanation of the result>",
  "code": "<pandas code snippet; result assigned to `result`>",
  "chart": {{
    "type": "<bar|line|scatter|pie|histogram|heatmap|none>",
    "x_column": "<column name or null>",
    "y_column": "<column name or null>",
    "title": "<chart title>",
    "x_label": "<x-axis label>",
    "y_label": "<y-axis label>"
  }},
  "assumptions": "<any assumptions made, or empty string>",
  "follow_up_questions": ["<question 1>", "<question 2>", "<question 3>"]
}}
```"""

# ---------------------------------------------------------------------------
# Schema summary prompt — used to build catalog entry
# ---------------------------------------------------------------------------

SCHEMA_SUMMARY_PROMPT = """Given this dataset schema, write a 1-2 sentence plain English summary describing what the dataset contains.

Dataset name: {dataset_name}
Columns: {column_list}
Row count: {row_count:,}
Sample values: {sample_values}

Return only the summary text, no JSON."""

# ---------------------------------------------------------------------------
# Fallback / error recovery prompt
# ---------------------------------------------------------------------------

ERROR_RECOVERY_PROMPT = """The following pandas code raised an error when executed:

Code:
```python
{code}
```

Error:
```
{error}
```

Please fix the code. Return only the corrected Python code, no explanation."""
