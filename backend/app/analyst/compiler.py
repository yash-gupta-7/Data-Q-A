"""SQL Compiler — translates AnalyticalPlan (closed-world DSL) into parameterized DuckDB SQL."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.models.dataset import Dataset
from app.models.plan import (
    AggregateOperation,
    AggregationFunction,
    AnalyticalPlan,
    CompareOperation,
    DateGroupOperation,
    DateGroupUnit,
    FilterOperation,
    FilterOperator,
    GroupByOperation,
    JoinOperation,
    SelectOperation,
    SortDirection,
    TrendOperation,
)

logger = logging.getLogger(__name__)


@dataclass
class CompiledQuery:
    sql: str
    parameters: list[Any] = field(default_factory=list)
    datasets_used: list[str] = field(default_factory=list)
    columns_used: list[str] = field(default_factory=list)
    operations_summary: list[str] = field(default_factory=list)


class SQLCompileError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# DuckDB date truncation mapping
_DATE_TRUNC_MAP = {
    DateGroupUnit.YEAR: "year",
    DateGroupUnit.QUARTER: "quarter",
    DateGroupUnit.MONTH: "month",
    DateGroupUnit.WEEK: "week",
    DateGroupUnit.DAY: "day",
}

# Aggregation function SQL mapping
_AGG_SQL = {
    AggregationFunction.SUM: "SUM",
    AggregationFunction.AVG: "AVG",
    AggregationFunction.COUNT: "COUNT",
    AggregationFunction.COUNT_DISTINCT: "COUNT(DISTINCT {col})",
    AggregationFunction.MIN: "MIN",
    AggregationFunction.MAX: "MAX",
    AggregationFunction.MEDIAN: "MEDIAN",
    AggregationFunction.STDDEV: "STDDEV",
    AggregationFunction.VARIANCE: "VARIANCE",
}


def _quote_identifier(name: str) -> str:
    """DuckDB-safe double-quoted identifier."""
    return f'"{name}"'


def _agg_expr(func: AggregationFunction, col: str) -> str:
    template = _AGG_SQL.get(func, "SUM")
    if "{col}" in template:
        return template.format(col=_quote_identifier(col))
    return f"{template}({_quote_identifier(col)})"


class SQLCompiler:
    """
    Translates a validated AnalyticalPlan into parameterized DuckDB SQL.
    The LLM never controls executable SQL directly.
    """

    def __init__(self, datasets: list[Dataset], relationships: list[Any] | None = None):
        self._ds_map = {d.dataset_id: d for d in datasets}
        self._relationships = relationships or []

    def _table(self, dataset_id: str) -> str:
        ds = self._ds_map.get(dataset_id)
        if not ds:
            raise SQLCompileError(f"Dataset '{dataset_id}' not found in compiler.")
        return _quote_identifier(ds.internal_table_name)

    def _resolve_column(self, col_name: str, dataset_id: str | None, plan_datasets: list[str]) -> str:
        """Return qualified column ref, optionally table-prefixed."""
        if dataset_id:
            ds = self._ds_map.get(dataset_id)
            if ds and any(c.name == col_name for c in ds.columns):
                return f"{_quote_identifier(ds.internal_table_name)}.{_quote_identifier(col_name)}"
        # Single dataset — no prefix needed
        if len(plan_datasets) == 1:
            return _quote_identifier(col_name)
        # Multi-dataset — try to qualify
        for ds_id in plan_datasets:
            ds = self._ds_map.get(ds_id)
            if ds and any(c.name == col_name for c in ds.columns):
                return f"{_quote_identifier(ds.internal_table_name)}.{_quote_identifier(col_name)}"
        return _quote_identifier(col_name)

    def _build_filter_clause(
        self,
        op: FilterOperation,
        params: list[Any],
        plan_datasets: list[str],
        alias_map: dict[str, str],
    ) -> str:
        col = self._resolve_column(op.column, op.dataset, plan_datasets)
        oper = op.operator

        if oper == FilterOperator.IS_NULL:
            return f"{col} IS NULL"
        if oper == FilterOperator.IS_NOT_NULL:
            return f"{col} IS NOT NULL"

        val = op.value

        if oper == FilterOperator.EQUALS:
            params.append(val)
            return f"{col} = ?"
        if oper == FilterOperator.NOT_EQUALS:
            params.append(val)
            return f"{col} != ?"
        if oper == FilterOperator.GREATER_THAN:
            params.append(val)
            return f"{col} > ?"
        if oper == FilterOperator.GREATER_THAN_OR_EQUAL:
            params.append(val)
            return f"{col} >= ?"
        if oper == FilterOperator.LESS_THAN:
            params.append(val)
            return f"{col} < ?"
        if oper == FilterOperator.LESS_THAN_OR_EQUAL:
            params.append(val)
            return f"{col} <= ?"
        if oper == FilterOperator.IN:
            placeholders = ", ".join("?" * len(val))
            params.extend(val)
            return f"{col} IN ({placeholders})"
        if oper == FilterOperator.NOT_IN:
            placeholders = ", ".join("?" * len(val))
            params.extend(val)
            return f"{col} NOT IN ({placeholders})"
        if oper == FilterOperator.CONTAINS:
            params.append(f"%{val}%")
            return f"{col} LIKE ?"
        if oper == FilterOperator.STARTS_WITH:
            params.append(f"{val}%")
            return f"{col} LIKE ?"
        if oper == FilterOperator.ENDS_WITH:
            params.append(f"%{val}")
            return f"{col} LIKE ?"
        if oper == FilterOperator.BEFORE:
            params.append(val)
            return f"{col} < ?"
        if oper == FilterOperator.AFTER:
            params.append(val)
            return f"{col} > ?"
        if oper == FilterOperator.BETWEEN:
            params.append(val[0])
            params.append(val[1])
            return f"{col} BETWEEN ? AND ?"
        if oper == FilterOperator.YEAR_EQUALS:
            params.append(int(val))
            return f"YEAR({col}) = ?"
        if oper == FilterOperator.MONTH_EQUALS:
            params.append(int(val))
            return f"MONTH({col}) = ?"

        raise SQLCompileError(f"Unsupported filter operator: {oper}")

    def compile(self, plan: AnalyticalPlan) -> CompiledQuery:
        """Main compilation entry point."""
        params: list[Any] = []
        datasets_used: list[str] = []
        columns_used: list[str] = []
        ops_summary: list[str] = []

        # Separate operations by type
        filters: list[FilterOperation] = []
        aggregates: list[AggregateOperation] = []
        selects: list[SelectOperation] = []
        group_by_ops: list[GroupByOperation] = []
        joins: list[JoinOperation] = []
        date_groups: list[DateGroupOperation] = []
        compare_op: CompareOperation | None = None
        trend_op: TrendOperation | None = None

        for op in plan.operations:
            if isinstance(op, FilterOperation):
                filters.append(op)
            elif isinstance(op, AggregateOperation):
                aggregates.append(op)
            elif isinstance(op, SelectOperation):
                selects.append(op)
            elif isinstance(op, GroupByOperation):
                group_by_ops.append(op)
            elif isinstance(op, JoinOperation):
                joins.append(op)
            elif isinstance(op, DateGroupOperation):
                date_groups.append(op)
            elif isinstance(op, CompareOperation):
                compare_op = op
            elif isinstance(op, TrendOperation):
                trend_op = op

        # ── TREND shortcut ──────────────────────────────────────────────
        if trend_op:
            return self._compile_trend(trend_op, filters, plan, params, ops_summary)

        # ── COMPARE shortcut ────────────────────────────────────────────
        if compare_op:
            return self._compile_compare(compare_op, filters, plan, params, ops_summary)

        # ── General query ───────────────────────────────────────────────
        select_parts: list[str] = []
        group_by_cols: list[str] = []
        alias_map: dict[str, str] = {}

        # Determine primary table(s)
        primary_ds = plan.datasets[0] if plan.datasets else None
        if not primary_ds:
            raise SQLCompileError("No datasets in plan.")

        # FROM clause
        if not joins and len(plan.datasets) > 1 and self._relationships:
            auto_joins = []
            seen_ds = {plan.datasets[0]}
            for ds_id in plan.datasets[1:]:
                for rel in self._relationships:
                    if rel.left_dataset in seen_ds and rel.right_dataset == ds_id:
                        auto_joins.append(JoinOperation(
                            left_dataset=rel.left_dataset,
                            left_column=rel.left_column,
                            right_dataset=rel.right_dataset,
                            right_column=rel.right_column,
                            join_type="LEFT",
                        ))
                        seen_ds.add(ds_id)
                        break
                    elif rel.right_dataset in seen_ds and rel.left_dataset == ds_id:
                        auto_joins.append(JoinOperation(
                            left_dataset=rel.right_dataset,
                            left_column=rel.right_column,
                            right_dataset=rel.left_dataset,
                            right_column=rel.left_column,
                            join_type="LEFT",
                        ))
                        seen_ds.add(ds_id)
                        break
            if auto_joins:
                joins = auto_joins

        if joins:
            from_clause, join_clauses = self._build_joins(joins, plan.datasets, ops_summary)
        else:
            from_clause = self._table(primary_ds)
            join_clauses = ""
            datasets_used.append(primary_ds)

        # Collect aggregate aliases and metric columns
        agg_aliases: set[str] = set()
        for agg in aggregates:
            alias = agg.alias or f"{agg.function.value.lower()}_{agg.column}"
            agg_aliases.add(alias)

        selected_cols: set[str] = set()

        # DATE_GROUP columns → added to SELECT and GROUP BY
        for dg in date_groups:
            trunc = _DATE_TRUNC_MAP.get(dg.unit, "month")
            col = self._resolve_column(dg.column, dg.dataset, plan.datasets)
            alias = dg.alias or f"{dg.column}_{dg.unit.value.lower()}"
            expr = f"DATE_TRUNC('{trunc}', {col}::TIMESTAMP) AS {_quote_identifier(alias)}"
            select_parts.append(expr)
            group_by_cols.append(_quote_identifier(alias))
            columns_used.append(dg.column)
            ops_summary.append(f"DATE_TRUNC({dg.unit.value}, {dg.column})")
            alias_map[alias] = alias
            selected_cols.add(alias)
            selected_cols.add(dg.column)

        # GROUP_BY from operations (deduplicated)
        all_group_by = list(plan.group_by)
        for gbo in group_by_ops:
            all_group_by.extend(gbo.columns)

        seen_gb: set[str] = set()
        for col_name in all_group_by:
            if col_name in seen_gb:
                continue
            seen_gb.add(col_name)
            col = self._resolve_column(col_name, None, plan.datasets)
            select_parts.append(f"{col} AS {_quote_identifier(col_name)}")
            group_by_cols.append(col)
            columns_used.append(col_name)
            selected_cols.add(col_name)

        # SELECT columns
        for sel in selects:
            for col_name in sel.columns:
                if col_name in agg_aliases or col_name in selected_cols:
                    continue
                if aggregates and col_name not in seen_gb:
                    continue
                col = self._resolve_column(col_name, sel.dataset, plan.datasets)
                select_parts.append(f"{col} AS {_quote_identifier(col_name)}")
                columns_used.append(col_name)
                selected_cols.add(col_name)

        # AGGREGATE expressions
        for agg in aggregates:
            col_name = agg.column
            col = self._resolve_column(col_name, agg.dataset, plan.datasets)
            alias = agg.alias or f"{agg.function.value.lower()}_{col_name}"
            # Build agg expression with resolved col
            if agg.function == AggregationFunction.COUNT_DISTINCT:
                expr = f"COUNT(DISTINCT {col}) AS {_quote_identifier(alias)}"
            else:
                expr = f"{agg.function.value}({col}) AS {_quote_identifier(alias)}"
            select_parts.append(expr)
            columns_used.append(col_name)
            ops_summary.append(f"{agg.function.value}({col_name})")
            selected_cols.add(alias)

        # If no select at all, do SELECT *
        if not select_parts:
            if selects:
                pass
            else:
                select_parts = ["*"]

        # WHERE clause
        where_parts: list[str] = []
        for flt in filters:
            clause = self._build_filter_clause(flt, params, plan.datasets, alias_map)
            where_parts.append(clause)
            columns_used.append(flt.column)
            ops_summary.append(f"FILTER {flt.column} {flt.operator.value}")

        # Assemble SQL
        sql_parts = [f"SELECT {', '.join(select_parts)}"]
        sql_parts.append(f"FROM {from_clause}")
        if join_clauses:
            sql_parts.append(join_clauses)
        if where_parts:
            sql_parts.append(f"WHERE {' AND '.join(where_parts)}")
        if group_by_cols:
            sql_parts.append(f"GROUP BY {', '.join(group_by_cols)}")
        if plan.sort:
            sort_col = _quote_identifier(plan.sort.column)
            direction = plan.sort.direction.value
            sql_parts.append(f"ORDER BY {sort_col} {direction}")
        if plan.limit:
            sql_parts.append(f"LIMIT {int(plan.limit)}")

        sql = "\n".join(sql_parts)

        # datasets_used
        for ds_id in plan.datasets:
            ds = self._ds_map.get(ds_id)
            if ds:
                datasets_used.append(ds.display_name)

        return CompiledQuery(
            sql=sql,
            parameters=params,
            datasets_used=list(set(datasets_used)),
            columns_used=list(set(columns_used)),
            operations_summary=ops_summary,
        )

    def _build_joins(
        self,
        joins: list[JoinOperation],
        plan_datasets: list[str],
        ops_summary: list[str],
    ) -> tuple[str, str]:
        """Build FROM + JOIN clauses. Returns (from_clause, join_sql)."""
        if not joins:
            return "", ""

        first = joins[0]
        from_clause = self._table(first.left_dataset)
        join_lines = []

        seen_datasets = {first.left_dataset}
        for join in joins:
            right_table = self._table(join.right_dataset)
            left_col = self._resolve_column(join.left_column, join.left_dataset, plan_datasets)
            right_col = self._resolve_column(join.right_column, join.right_dataset, plan_datasets)

            if join.right_dataset not in seen_datasets:
                jtype = join.join_type
                join_lines.append(f"{jtype} JOIN {right_table} ON {left_col} = {right_col}")
                seen_datasets.add(join.right_dataset)
                ops_summary.append(f"JOIN {join.left_dataset}.{join.left_column} -> {join.right_dataset}.{join.right_column}")

        return from_clause, "\n".join(join_lines)

    def _compile_trend(
        self,
        trend: TrendOperation,
        filters: list[FilterOperation],
        plan: AnalyticalPlan,
        params: list[Any],
        ops_summary: list[str],
    ) -> CompiledQuery:
        trunc = _DATE_TRUNC_MAP.get(trend.unit, "month")
        date_col = self._resolve_column(trend.date_column, trend.dataset, plan.datasets)
        metric_col = self._resolve_column(trend.metric_column, trend.dataset, plan.datasets)
        agg_func = trend.metric_function.value
        alias_map: dict[str, str] = {}

        where_parts = []
        for flt in filters:
            clause = self._build_filter_clause(flt, params, plan.datasets, alias_map)
            where_parts.append(clause)

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        primary_table = self._table(plan.datasets[0])

        if trend.metric_function == AggregationFunction.COUNT_DISTINCT:
            agg_expr = f"COUNT(DISTINCT {metric_col})"
        else:
            agg_expr = f"{agg_func}({metric_col})"

        sql = f"""SELECT
  DATE_TRUNC('{trunc}', {date_col}::TIMESTAMP) AS "period",
  {agg_expr} AS "value"
FROM {primary_table}
{where_sql}
GROUP BY DATE_TRUNC('{trunc}', {date_col}::TIMESTAMP)
ORDER BY "period" ASC"""

        ds = self._ds_map.get(plan.datasets[0])
        datasets_used = [ds.display_name if ds else plan.datasets[0]]
        ops_summary.append(f"TREND {agg_func}({trend.metric_column}) BY {trend.unit.value}")

        return CompiledQuery(
            sql=sql.strip(),
            parameters=params,
            datasets_used=datasets_used,
            columns_used=[trend.date_column, trend.metric_column],
            operations_summary=ops_summary,
        )

    def _compile_compare(
        self,
        compare: CompareOperation,
        filters: list[FilterOperation],
        plan: AnalyticalPlan,
        params: list[Any],
        ops_summary: list[str],
    ) -> CompiledQuery:
        col = self._resolve_column(compare.column, compare.dataset, plan.datasets)
        metric_col = self._resolve_column(compare.metric_column, compare.dataset, plan.datasets)
        primary_table = self._table(plan.datasets[0])
        alias_map: dict[str, str] = {}

        # Filter to specified values
        placeholders = ", ".join("?" * len(compare.values))
        params.extend(compare.values)

        agg_func = compare.metric_function.value
        if compare.metric_function == AggregationFunction.COUNT_DISTINCT:
            agg_expr = f"COUNT(DISTINCT {metric_col})"
        else:
            agg_expr = f"{agg_func}({metric_col})"

        extra_where = []
        for flt in filters:
            extra_where.append(self._build_filter_clause(flt, params, plan.datasets, alias_map))

        where_parts = [f"{col} IN ({placeholders})"]
        where_parts.extend(extra_where)

        sql = f"""SELECT {col} AS "category", {agg_expr} AS "value"
FROM {primary_table}
WHERE {' AND '.join(where_parts)}
GROUP BY {col}
ORDER BY "value" DESC"""

        ds = self._ds_map.get(plan.datasets[0])
        ops_summary.append(f"COMPARE {agg_func}({compare.metric_column}) across {compare.values}")

        return CompiledQuery(
            sql=sql.strip(),
            parameters=params,
            datasets_used=[ds.display_name if ds else plan.datasets[0]],
            columns_used=[compare.column, compare.metric_column],
            operations_summary=ops_summary,
        )
