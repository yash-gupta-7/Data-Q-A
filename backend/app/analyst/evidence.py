"""Evidence scorer — deterministic evidence score, NOT an LLM probability."""

from __future__ import annotations

from app.analyst.compiler import CompiledQuery
from app.models.plan import AnalyticalPlan, PlanStatus
from app.models.result import QueryResult, ValidationCheck, ValidationResult, ValidationStatus


def compute_evidence_score(
    plan: AnalyticalPlan,
    compiled: CompiledQuery | None,
    result: QueryResult | None,
    plan_validation: ValidationResult,
    result_validation: ValidationResult | None,
    sql_safe: bool,
) -> ValidationResult:
    """
    Compute a holistic evidence score from all deterministic checks.

    The score is a diagnostic/evidentiary indicator — NOT a probability.
    BLOCKED status overrides everything.
    """
    checks: list[ValidationCheck] = []
    warnings: list[str] = []

    # ── Check 1: Plan status ──────────────────────────────────────────────
    plan_ready = plan.status == PlanStatus.READY
    checks.append(ValidationCheck(
        name="plan_status_ready",
        passed=plan_ready,
        message=None if plan_ready else f"Plan status is '{plan.status.value}', not 'ready'.",
    ))

    # ── Check 2: Plan validation passed ──────────────────────────────────
    pv_passed = plan_validation.status != ValidationStatus.BLOCKED
    checks.append(ValidationCheck(
        name="plan_validation_passed",
        passed=pv_passed,
        message=None if pv_passed else f"Plan validation blocked: {plan_validation.blocking_reason}",
    ))

    # ── Check 3: SQL compiled ─────────────────────────────────────────────
    sql_compiled = compiled is not None
    checks.append(ValidationCheck(
        name="sql_compiled",
        passed=sql_compiled,
        message=None if sql_compiled else "SQL compilation failed.",
    ))

    # ── Check 4: SQL safety passed ────────────────────────────────────────
    checks.append(ValidationCheck(
        name="sql_safety_passed",
        passed=sql_safe,
        message=None if sql_safe else "SQL safety validation failed.",
    ))

    # ── Check 5: Execution succeeded ─────────────────────────────────────
    execution_ok = result is not None
    checks.append(ValidationCheck(
        name="execution_succeeded",
        passed=execution_ok,
        message=None if execution_ok else "DuckDB execution failed.",
    ))

    # ── Check 6: Result validation passed ────────────────────────────────
    if result_validation:
        rv_passed = result_validation.status != ValidationStatus.BLOCKED
        checks.append(ValidationCheck(
            name="result_validation_passed",
            passed=rv_passed,
            message=None if rv_passed else result_validation.blocking_reason,
        ))
        warnings.extend(result_validation.warnings)
    else:
        checks.append(ValidationCheck(
            name="result_validation_passed",
            passed=False,
            message="Result validation did not run.",
        ))

    # ── Check 7: Has datasets ─────────────────────────────────────────────
    has_datasets = bool(plan.datasets)
    checks.append(ValidationCheck(
        name="has_datasets",
        passed=has_datasets,
        message=None if has_datasets else "No datasets in plan.",
    ))

    # ── Compute score ─────────────────────────────────────────────────────
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    score = passed / max(total, 1)

    hard_failures = [c for c in checks if not c.passed]

    if hard_failures:
        # Inherit highest priority from plan_validation or result_validation
        if not pv_passed or not sql_safe:
            status = ValidationStatus.BLOCKED
            blocking = "; ".join(c.message for c in hard_failures if c.message)
        elif not execution_ok:
            status = ValidationStatus.BLOCKED
            blocking = "Query execution failed."
        elif result_validation and result_validation.status == ValidationStatus.BLOCKED:
            status = ValidationStatus.BLOCKED
            blocking = result_validation.blocking_reason
        else:
            status = ValidationStatus.VALIDATED_WITH_WARNINGS
            blocking = None
    elif warnings:
        status = ValidationStatus.VALIDATED_WITH_WARNINGS
        blocking = None
    else:
        status = ValidationStatus.VALIDATED
        blocking = None

    return ValidationResult(
        status=status,
        validation_score=round(score, 3),
        checks=checks,
        warnings=warnings,
        blocking_reason=blocking,
    )
