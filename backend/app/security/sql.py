"""SQL safety validation using sqlglot AST parsing."""

from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp


class SQLSafetyError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# Forbidden statement class names — checked by type name string for sqlglot version compatibility
_FORBIDDEN_STATEMENT_NAMES = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "COPY", "COMMAND", "TRANSACTION", "COMMIT", "ROLLBACK",
    "GRANT", "REVOKE", "USE", "SET", "KILL", "TRUNCATE",
}

# Forbidden function names (case-insensitive)
_FORBIDDEN_FUNCTIONS = {
    "read_csv_auto",
    "read_json",
    "read_parquet",
    "copy",
    "export_database",
    "import_database",
    "install",
    "load",
    "httpfs",
    "shell",
    "system",
    "getenv",
}


def validate_sql_safety(sql: str) -> None:
    """
    Parse SQL with sqlglot (DuckDB dialect) and reject any non-analytical statements.
    Raises SQLSafetyError if unsafe.
    Uses class name string matching for sqlglot version compatibility.
    """
    if not sql or not sql.strip():
        raise SQLSafetyError("EMPTY_SQL", "SQL statement is empty.")

    try:
        statements = sqlglot.parse(sql, dialect="duckdb", error_level=sqlglot.ErrorLevel.RAISE)
    except sqlglot.errors.ParseError as e:
        raise SQLSafetyError("SQL_PARSE_ERROR", f"SQL could not be parsed: {e}") from e

    if not statements:
        raise SQLSafetyError("EMPTY_SQL", "SQL statement is empty.")

    for stmt in statements:
        if stmt is None:
            continue

        stmt_class_name = type(stmt).__name__.upper()

        # Check forbidden statement types by class name (version-safe approach)
        if stmt_class_name in _FORBIDDEN_STATEMENT_NAMES:
            raise SQLSafetyError(
                "UNSAFE_SQL",
                f"Statement type '{type(stmt).__name__}' is not permitted. "
                "Only analytical SELECT queries are allowed.",
            )

        # Must be a SELECT statement
        if not isinstance(stmt, exp.Select):
            raise SQLSafetyError(
                "UNSAFE_SQL",
                f"Only SELECT statements are permitted. Got: {type(stmt).__name__}",
            )

        # Walk AST and check for forbidden functions
        for node in stmt.walk():
            if isinstance(node, exp.Anonymous):
                fname = node.name.lower() if node.name else ""
                if fname in _FORBIDDEN_FUNCTIONS:
                    raise SQLSafetyError(
                        "UNSAFE_FUNCTION",
                        f"Function '{node.name}' is not permitted in analytical queries.",
                    )
            elif isinstance(node, exp.Func):
                fname = type(node).__name__.lower()
                if fname in _FORBIDDEN_FUNCTIONS:
                    raise SQLSafetyError(
                        "UNSAFE_FUNCTION",
                        f"Function '{fname}' is not permitted in analytical queries.",
                    )


def is_safe_sql(sql: str) -> tuple[bool, str | None]:
    """Return (is_safe, error_message)."""
    try:
        validate_sql_safety(sql)
        return True, None
    except SQLSafetyError as e:
        return False, e.message
