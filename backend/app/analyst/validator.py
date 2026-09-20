"""Plan validator — validates AnalyticalPlan against the session catalog."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.models.dataset import Dataset, Relationship, RelationshipStatus, SemanticType
from app.models.plan import (
    AggregateOperation,
    AnalyticalPlan,
    CompareOperation,
    DateGroupOperation,
    FilterOperation,
    GroupByOperation,
    JoinOperation,
    SelectOperation,
    TrendOperation,
)
from app.models.result import ValidationCheck, ValidationResult, ValidationStatus

logger = logging.getLogger(__name__)


class PlanValidator:
    def __init__(
        self,
        datasets: list[Dataset],
        relationships: list[Relationship],
    ):
        self._datasets = {d.dataset_id: d for d in datasets}
        self._tables = {d.internal_table_name: d for d in datasets}
        self._relationships = relationships
        self._settings = get_settings()

    def _get_column(self, dataset_id: str, col_name: str):
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return next((c for c in ds.columns if c.name == col_name), None)

    def _check_datasets_exist(self, plan: AnalyticalPlan) -> list[ValidationCheck]:
        checks = []
        for ds_id in plan.datasets:
            exists = ds_id in self._datasets and self._datasets[ds_id].status.value == "ready"
            checks.append(ValidationCheck(
                name=f"dataset_exists:{ds_id}",
                passed=exists,
                message=None if exists else f"Dataset '{ds_id}' not found or not ready.",
            ))
        return checks

    def _check_operations(self, plan: AnalyticalPlan) -> list[ValidationCheck]:
        checks = []
        join_count = 0

        for i, op in enumerate(plan.operations):
            op_name = f"operation[{i}]:{op.type}"

            if isinstance(op, (FilterOperation, AggregateOperation, DateGroupOperation)):
                # Validate column exists in at least one listed dataset
                col_name = op.column
                ds_id = getattr(op, "dataset", None)
                if ds_id:
                    col = self._get_column(ds_id, col_name)
                    passed = col is not None
                    checks.append(ValidationCheck(
                        name=f"{op_name}:column_exists",
                        passed=passed,
                        message=None if passed else f"Column '{col_name}' not found in dataset '{ds_id}'.",
                    ))
                else:
                    # Check at least one dataset has this column
                    found = any(
                        self._get_column(ds_id2, col_name) is not None
                        for ds_id2 in plan.datasets
                    )
                    checks.append(ValidationCheck(
                        name=f"{op_name}:column_exists",
                        passed=found,
                        message=None if found else f"Column '{col_name}' not found in any listed dataset.",
                    ))

            elif isinstance(op, GroupByOperation):
                for col_name in op.columns:
                    ds_id = getattr(op, "dataset", None)
                    if ds_id:
                        col = self._get_column(ds_id, col_name)
                        found = col is not None
                    else:
                        found = any(
                            self._get_column(ds_id2, col_name) is not None
                            for ds_id2 in plan.datasets
                        )
                    checks.append(ValidationCheck(
                        name=f"{op_name}:group_column:{col_name}",
                        passed=found,
                        message=None if found else f"Group-by column '{col_name}' not found.",
                    ))

            elif isinstance(op, SelectOperation):
                agg_aliases = {
                    getattr(o, "alias", None) or f"{getattr(o, 'function', '').value.lower()}_{getattr(o, 'column', '')}"
                    for o in plan.operations if isinstance(o, AggregateOperation)
                }
                for col_name in op.columns:
                    if col_name in agg_aliases:
                        continue
                    ds_id = getattr(op, "dataset", None)
                    if ds_id:
                        col = self._get_column(ds_id, col_name)
                        found = col is not None
                    else:
                        found = any(
                            self._get_column(ds_id2, col_name) is not None
                            for ds_id2 in plan.datasets
                        )
                    checks.append(ValidationCheck(
                        name=f"{op_name}:select_column:{col_name}",
                        passed=found,
                        message=None if found else f"Select column '{col_name}' not found.",
                    ))

            elif isinstance(op, JoinOperation):
                join_count += 1
                # Check join depth
                if join_count > self._settings.max_join_depth:
                    checks.append(ValidationCheck(
                        name=f"{op_name}:join_depth",
                        passed=False,
                        message=f"Join depth {join_count} exceeds MAX_JOIN_DEPTH={self._settings.max_join_depth}.",
                    ))

                # Both datasets must exist
                for ds_id, col_name in [
                    (op.left_dataset, op.left_column),
                    (op.right_dataset, op.right_column),
                ]:
                    ds_exists = ds_id in self._datasets
                    checks.append(ValidationCheck(
                        name=f"{op_name}:join_dataset:{ds_id}",
                        passed=ds_exists,
                        message=None if ds_exists else f"Join dataset '{ds_id}' not found.",
                    ))
                    if ds_exists:
                        col = self._get_column(ds_id, col_name)
                        checks.append(ValidationCheck(
                            name=f"{op_name}:join_column:{ds_id}.{col_name}",
                            passed=col is not None,
                            message=None if col else f"Join column '{col_name}' not found in '{ds_id}'.",
                        ))

            elif isinstance(op, (CompareOperation, TrendOperation)):
                col_name = op.metric_column if hasattr(op, "metric_column") else ""
                if col_name:
                    found = any(
                        self._get_column(ds_id2, col_name) is not None
                        for ds_id2 in plan.datasets
                    )
                    checks.append(ValidationCheck(
                        name=f"{op_name}:metric_column",
                        passed=found,
                        message=None if found else f"Metric column '{col_name}' not found.",
                    ))

        return checks

    def _check_group_by_columns(self, plan: AnalyticalPlan) -> list[ValidationCheck]:
        checks = []
        for col_name in plan.group_by:
            found = any(
                self._get_column(ds_id, col_name) is not None
                for ds_id in plan.datasets
            )
            checks.append(ValidationCheck(
                name=f"group_by:{col_name}",
                passed=found,
                message=None if found else f"Group-by column '{col_name}' not found in any dataset.",
            ))
        return checks

    def validate(self, plan: AnalyticalPlan) -> ValidationResult:
        """Full plan validation. Returns BLOCKED on hard failures."""
        all_checks: list[ValidationCheck] = []

        # Check datasets exist
        all_checks.extend(self._check_datasets_exist(plan))

        # Check operations
        all_checks.extend(self._check_operations(plan))

        # Check group_by columns
        all_checks.extend(self._check_group_by_columns(plan))

        # Compute score and status
        total = len(all_checks)
        passed = sum(1 for c in all_checks if c.passed)
        score = passed / max(total, 1)

        hard_failures = [c for c in all_checks if not c.passed]

        if hard_failures:
            status = ValidationStatus.BLOCKED
            blocking = "; ".join(c.message for c in hard_failures if c.message)
        else:
            status = ValidationStatus.VALIDATED
            blocking = None

        return ValidationResult(
            status=status,
            validation_score=round(score, 3),
            checks=all_checks,
            blocking_reason=blocking,
        )
