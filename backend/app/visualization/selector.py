"""Deterministic chart type selector."""

from __future__ import annotations

from app.models.plan import AnalyticalPlan, ChartType, Intent, VisualizationHint
from app.models.result import QueryResult


def select_chart(
    plan: AnalyticalPlan,
    result: QueryResult,
    llm_hint: VisualizationHint | None = None,
) -> dict:
    """
    Deterministically select chart type from result shape.
    LLM hint may be considered but deterministic rules are authoritative.
    Returns a chart spec dict.
    """
    if not result.columns or result.row_count == 0:
        return {"type": ChartType.TABLE.value, "title": "Results"}

    col_count = len(result.columns)
    row_count = result.row_count
    col_types = [c.type for c in result.columns]
    col_names = [c.name for c in result.columns]

    intent = plan.intent

    # Single numeric value → KPI
    if col_count == 1 and col_types[0] == "number":
        val = result.rows[0][0] if result.rows else None
        return {
            "type": ChartType.KPI.value,
            "value": val,
            "label": col_names[0],
            "title": col_names[0].replace("_", " ").title(),
        }

    # Date column + metric → line chart (trend)
    if col_count == 2 and intent == Intent.TREND:
        date_cols = [i for i, t in enumerate(col_types) if t == "date" or col_names[i] == "period"]
        num_cols = [i for i, t in enumerate(col_types) if t == "number"]
        if date_cols and num_cols:
            return {
                "type": ChartType.LINE.value,
                "x": col_names[date_cols[0]],
                "y": col_names[num_cols[0]],
                "title": f"{col_names[num_cols[0]].replace('_', ' ').title()} Over Time",
            }
        # Also handle "period" column from trend compilation
        if "period" in col_names and "value" in col_names:
            return {
                "type": ChartType.LINE.value,
                "x": "period",
                "y": "value",
                "title": "Trend Over Time",
            }

    # category + metric → bar chart
    if col_count == 2:
        str_cols = [i for i, t in enumerate(col_types) if t == "string"]
        num_cols = [i for i, t in enumerate(col_types) if t == "number"]
        if str_cols and num_cols:
            # Pie if small number of categories (≤ 6)
            if row_count <= 6 and intent == Intent.COMPARISON:
                return {
                    "type": ChartType.PIE.value,
                    "x": col_names[str_cols[0]],
                    "y": col_names[num_cols[0]],
                    "title": f"{col_names[num_cols[0]].replace('_', ' ').title()} by {col_names[str_cols[0]].replace('_', ' ').title()}",
                }
            return {
                "type": ChartType.BAR.value,
                "x": col_names[str_cols[0]],
                "y": col_names[num_cols[0]],
                "title": f"{col_names[num_cols[0]].replace('_', ' ').title()} by {col_names[str_cols[0]].replace('_', ' ').title()}",
            }

        # Date + metric (not tagged as TREND)
        date_like = [i for i, n in enumerate(col_names) if "date" in n or "period" in n or "month" in n or "year" in n]
        if date_like and num_cols:
            return {
                "type": ChartType.LINE.value,
                "x": col_names[date_like[0]],
                "y": col_names[num_cols[0]],
                "title": "Trend Over Time",
            }

    # Two string columns + one numeric → grouped bar
    if col_count == 3:
        str_cols = [i for i, t in enumerate(col_types) if t == "string"]
        num_cols = [i for i, t in enumerate(col_types) if t == "number"]
        if len(str_cols) == 2 and len(num_cols) == 1:
            return {
                "type": ChartType.GROUPED_BAR.value,
                "x": col_names[str_cols[0]],
                "y": col_names[num_cols[0]],
                "series": col_names[str_cols[1]],
                "title": "Grouped Analysis",
            }

    # Default: table
    return {"type": ChartType.TABLE.value, "title": "Results"}


def get_compatible_chart_types(chart_spec: dict) -> list[str]:
    """Return chart types compatible with the current result for user switching."""
    current_type = chart_spec.get("type", "table")
    compatible = ["table"]

    if current_type == ChartType.BAR.value:
        compatible = ["bar", "pie", "table"]
    elif current_type == ChartType.PIE.value:
        compatible = ["pie", "bar", "table"]
    elif current_type == ChartType.LINE.value:
        compatible = ["line", "bar", "table"]
    elif current_type == ChartType.KPI.value:
        compatible = ["kpi", "table"]
    elif current_type == ChartType.GROUPED_BAR.value:
        compatible = ["grouped_bar", "bar", "table"]

    return compatible
