# ==============================================================================
# PyTest Guardrail Unit Tests
# Path: tests/test_guardrails.py
# Purpose: Automated CI/CD regression unit tests ensuring that:
#          1. Clean SELECT statements receive proper Cmp_No tenant parameter injection.
#          2. Merging tenant conditions with existing user WHERE clauses succeeds without syntax errors.
#          3. Mutation statements (DELETE, UPDATE, DROP) are strictly blocked.
#          4. Unauthorized sensitive tables (users, sec_users) are strictly rejected.
#          5. Multi-statement semicolon stacking attacks are neutralized.
# ==============================================================================

# PyTest testing framework
import pytest

# AST Guardrails validator and security exception
from app.modules.text_to_sql.guardrails import validate_and_sanitize_sql, SQLSecurityException


def test_valid_select_query_injection():
    """
    Test 1: Ensures clean SELECT statements have tenant condition and LIMIT 100 injected.
    """
    raw = "SELECT invoice_number, total_amount FROM v_sales_invoices"
    sql, params = validate_and_sanitize_sql(raw, cmp_no=605)

    assert "Cmp_No = :cmp_no" in sql
    assert params["cmp_no"] == 605
    assert "LIMIT 100" in sql


def test_valid_select_with_existing_where():
    """
    Test 2: Ensures that pre-existing WHERE clauses are safely merged with tenant conditions via AND.
    """
    raw = "SELECT * FROM v_sales_invoices WHERE total_amount > 1000"
    sql, params = validate_and_sanitize_sql(raw, cmp_no=605, brn_no=1)

    assert "Cmp_No = :cmp_no" in sql
    assert "Brn_No = :brn_no" in sql
    assert "total_amount > 1000" in sql
    assert params["cmp_no"] == 605
    assert params["brn_no"] == 1


def test_block_mutation_statements():
    """
    Test 3: Ensures mutation statements (DELETE, UPDATE, DROP) raise SQLSecurityException.
    """
    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("DELETE FROM v_sales_invoices", cmp_no=605)

    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("UPDATE v_sales_invoices SET total_amount = 0", cmp_no=605)

    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("DROP TABLE maincompany", cmp_no=605)


def test_block_unauthorized_tables():
    """
    Test 4: Ensures attempts to query unauthorized or sensitive system tables are blocked.
    """
    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("SELECT * FROM users", cmp_no=605)

    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("SELECT * FROM sec_users", cmp_no=605)


def test_block_multi_statement():
    """
    Test 5: Ensures semicolon-stacked multi-statement queries are blocked.
    """
    with pytest.raises(SQLSecurityException):
        validate_and_sanitize_sql("SELECT * FROM v_sales_invoices; DROP TABLE v_sales_invoices", cmp_no=605)
