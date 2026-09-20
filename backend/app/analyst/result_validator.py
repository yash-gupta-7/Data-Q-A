"""Result validator — deterministic post-execution checks."""

from __future__ import annotations

import math
from typing import Any

from app.models.plan import AggregateOperation, AggregationFunction, AnalyticalPlan
from app.models.result import (
    QueryResult,
    ValidationCheck,
    ValidationResult,
    ValidationStatus,
)


def _is_numeric(val: Any) -> bool:
    if val is None:
        return False
    try:
        f = float(val)
        return not math.isnan(f) and not math.isinf(f)
    except (TypeError, ValueError):
        return False


def validate_result(
    result: QueryResult,
    plan: AnalyticalPlan,
) -> ValidationResult:
    """
    Perform deterministic post-execution checks on the query result.
    Returns VALIDATED, VALIDATED_WITH_WARNINGS, or BLOCKED.
    """
    checks: list[ValidationCheck] = []
    warnings: list[str] = []

    # 1. Structural validity — has columns
    has_cols = len(result.columns) > 0
    checks.append(ValidationCheck(
        name="has_columns",
        passed=has_cols,
        message=None if has_cols else "Result has no columns.",
    ))

    # 2. Non-empty where expected (aggregation should always return at least 1 row)
    from app.models.plan import PlanStatus
    is_agg = any(isinstance(op, AggregateOperation) for op in plan.operations)
    if is_agg and result.row_count == 0:
        checks.append(ValidationCheck(
            name="non_empty_aggregation",
            passed=False,
            message="Aggregation returned 0 rows — the filter may be too restrictive.",
        ))
    else:
        checks.append(ValidationCheck(
            name="non_empty_aggregation",
            passed=True,
        ))

    # 3. Numeric validity — numeric columns should not be all NaN
    for col in result.columns:
        if col.type == "number":
            col_idx = result.columns.index(col)
            values = [row[col_idx] for row in result.rows if col_idx < len(row)]
            non_null = [v for v in values if v is not None]
            if values and not non_null:
                checks.append(ValidationCheck(
                    name=f"numeric_not_all_null:{col.name}",
                    passed=False,
                    message=f"Column '{col.name}' has all NULL values.",
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"numeric_not_all_null:{col.name}",
                    passed=True,
                ))

    # 4. Grouped totals consistency (if GROUP BY + SUM, verify grand total makes sense)
    agg_ops = [op for op in plan.operations if isinstance(op, AggregateOperation)]
    if agg_ops and len(plan.group_by) > 0 and result.row_count > 1:
        for agg_op in agg_ops:
            if agg_op.function in (AggregationFunction.SUM, AggregationFunction.COUNT):
                alias = agg_op.alias or f"{agg_op.function.value.lower()}_{agg_op.column}"
                # Find column index
                col_idx = next(
                    (i for i, c in enumerate(result.columns) if c.name == alias),
                    None,
                )
                if col_idx is not None:
                    vals = [row[col_idx] for row in result.rows if col_idx < len(row)]
                    numeric_vals = [v for v in vals if _is_numeric(v)]
                    if len(numeric_vals) == len(vals) and numeric_vals:
                        total = sum(float(v) for v in numeric_vals)
                        # Check no individual value exceeds the total
                        max_val = max(float(v) for v in numeric_vals)
                        consistent = max_val <= total + 1e-6
                        checks.append(ValidationCheck(
                            name=f"grouped_total_consistency:{alias}",
                            passed=consistent,
                            message=None if consistent else
                            f"Grouped totals inconsistency detected in '{alias}'.",
                        ))

    # 5. Data quality warnings
    if result.data_quality.nulls_excluded:
        for col_name, null_count in result.data_quality.nulls_excluded.items():
            if null_count > 0:
                warnings.append(
                    f"{null_count} records with missing '{col_name}' were excluded from the calculation."
                )

    if result.truncated:
        warnings.append(
            f"Result was truncated to {result.row_count} rows. The full result may be larger."
        )

    # Compute final status
    hard_failures = [c for c in checks if not c.passed]
    if hard_failures:
        return ValidationResult(
            status=ValidationStatus.BLOCKED,
            validation_score=0.0,
            checks=checks,
            warnings=warnings,
            blocking_reason="; ".join(c.message for c in hard_failures if c.message),
        )

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    score = passed / max(total, 1)

    status = ValidationStatus.VALIDATED_WITH_WARNINGS if warnings else ValidationStatus.VALIDATED

    return ValidationResult(
        status=status,
        validation_score=round(score, 3),
        checks=checks,
        warnings=warnings,
    )
