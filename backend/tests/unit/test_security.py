"""Unit tests — SQL safety validator."""

from __future__ import annotations

import pytest
from app.security.sql import SQLSafetyError, validate_sql_safety


class TestSQLSafety:
    def test_valid_select(self):
        validate_sql_safety('SELECT region, SUM(revenue) FROM "dataset_001" GROUP BY region')

    def test_select_with_filter(self):
        validate_sql_safety('SELECT * FROM "dataset_001" WHERE country = ?')

    def test_select_with_join(self):
        validate_sql_safety(
            'SELECT a.region, SUM(b.revenue) FROM "dataset_001" a '
            'LEFT JOIN "dataset_002" b ON a.customer_id = b.customer_id GROUP BY a.region'
        )

    def test_insert_blocked(self):
        with pytest.raises(SQLSafetyError) as exc:
            validate_sql_safety("INSERT INTO users VALUES (1, 'admin')")
        assert exc.value.code == "UNSAFE_SQL"

    def test_update_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("UPDATE dataset_001 SET revenue = 0")

    def test_delete_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("DELETE FROM dataset_001")

    def test_drop_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("DROP TABLE dataset_001")

    def test_alter_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("ALTER TABLE dataset_001 ADD COLUMN evil VARCHAR")

    def test_create_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("CREATE TABLE evil AS SELECT * FROM dataset_001")

    def test_empty_blocked(self):
        with pytest.raises(SQLSafetyError):
            validate_sql_safety("")

    def test_select_with_date_trunc(self):
        validate_sql_safety(
            "SELECT DATE_TRUNC('month', order_date::TIMESTAMP) AS period, SUM(revenue) AS value "
            'FROM "dataset_001" GROUP BY period ORDER BY period ASC'
        )


class TestFileSecurity:
    def test_path_traversal_blocked(self):
        from app.security.files import validate_filename
        # validate_filename strips path traversal by extracting basename
        # "../../etc/passwd" -> "passwd" (traversal components removed)
        result = validate_filename("../../etc/passwd")
        # The dangerous path is neutralized — no traversal chars remain
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_clean_filename_passes(self):
        from app.security.files import validate_filename
        result = validate_filename("my_data.csv")
        assert result == "my_data.csv"

    def test_invalid_extension_blocked(self):
        from app.security.files import FileSecurityError, validate_extension
        with pytest.raises(FileSecurityError) as exc:
            validate_extension("malware.exe")
        assert exc.value.code == "UNSUPPORTED_FORMAT"

    def test_csv_extension_passes(self):
        from app.security.files import validate_extension
        assert validate_extension("data.csv") == ".csv"

    def test_xlsx_extension_passes(self):
        from app.security.files import validate_extension
        assert validate_extension("data.xlsx") == ".xlsx"

    def test_oversized_file_blocked(self):
        from app.security.files import FileSecurityError, validate_file_size
        with pytest.raises(FileSecurityError) as exc:
            validate_file_size(30 * 1024 * 1024, "huge.csv")  # 30MB > 25MB default
        assert exc.value.code == "FILE_TOO_LARGE"


class TestPIIDetection:
    def test_email_detected(self):
        from app.security.pii import detect_pii_in_values
        result = detect_pii_in_values(["test@example.com", "alice@corp.org"])
        assert "email" in result

    def test_no_pii(self):
        from app.security.pii import detect_pii_in_values
        result = detect_pii_in_values(["India", "UAE", "Germany"])
        assert result == []

    def test_ssn_detected(self):
        from app.security.pii import detect_pii_in_values
        result = detect_pii_in_values(["123-45-6789"])
        assert "ssn" in result

    def test_column_name_pii_hint(self):
        from app.security.pii import detect_pii_in_column_name
        result = detect_pii_in_column_name("customer_email")
        assert "email" in result
