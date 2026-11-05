# ==============================================================================
# Multi-Tenant AST Security Guardrails
# Path: app/modules/text_to_sql/guardrails.py
# Related Architecture Document: PROJECT_NOTES_FOR_KHALED.md (Section 6)
# Purpose: Protects the database from unauthorized access, SQL injections,
#          and cross-tenant data leakage using Abstract Syntax Tree (AST) parsing via sqlglot:
#          1. Enforces SELECT-only operations.
#          2. Blocks destructive or dangerous keywords (DROP, DELETE, UPDATE, UNION, EXEC, ...).
#          3. Validates that queries strictly reference allowed semantic views.
#          4. Injects alias-qualified tenant isolation filters (e.g. `alias.Cmp_No = :cmp_no`).
#          5. Enforces a maximum result LIMIT (default: 100) to protect database memory.
# ==============================================================================

# Regular expressions for string cleansing
import re

# Logging module
import logging

# Typing utilities
from typing import Tuple, Dict, Any, List, Optional

# sqlglot: SQL parser, transpiler, and AST optimizer
# exp: Expression classes representing AST nodes (Select, Table, Column, Where, And, ...)
import sqlglot
from sqlglot import exp

# Application configuration instance
from app.config import settings

# Allowed semantic views whitelist
from app.modules.text_to_sql.semantic_layer import ALLOWED_VIEWS

logger = logging.getLogger(__name__)

# Dangerous keywords prohibited in any generated SQL statement
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "replace", "declare", "lock",
    "exec", "execute", "union", "sleep", "benchmark"
]

# Views that do not contain a branch identifier column (global catalog views)
VIEWS_WITHOUT_BRANCH = {"v_inventory_stock"}


class SQLSecurityException(Exception):
    """
    Custom exception raised whenever a security violation or unauthorized query is detected.
    """
    pass


def extract_raw_sql(text: str) -> str:
    """
    Cleans and extracts pure SQL queries from LLM outputs, stripping
    markdown code fences (```sql ... ```) and conversational prose.
    """
    cleaned = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


def validate_and_sanitize_sql(
    raw_sql: str,
    cmp_no: Optional[int] = None,
    brn_no: Optional[int] = None,
    max_limit: int = 100
) -> Tuple[str, Dict[str, Any]]:
    """
    Core security validation and tenant injection pipeline.
    
    Parameters:
    - raw_sql: Raw SQL query text produced by the LLM
    - cmp_no: Current tenant company ID (Cmp_No), or None/0 for lab/global queries
    - brn_no: Optional tenant branch ID (Brn_No)
    - max_limit: Maximum permissible row limit (default: 100)
    
    Returns:
    - Tuple containing (sanitized_sql_string, parameterized_bindings_dict)
    
    Raises:
    - SQLSecurityException if any validation check fails.
    """
    # 1. Strip markdown fences and whitespace
    cleaned_sql = extract_raw_sql(raw_sql)

    # 2. Block multi-statement stacking attacks (semicolons)
    if ";" in cleaned_sql.rstrip(";"):
        raise SQLSecurityException("محاولة استعلام غير مصرح بها: تم اكتشاف محاولة تنفيذ استعلامات متعددة (SQL Stacking Attack). يُسمح بتنفيذ استعلام قراءة تحليلي واحد فقط.")

    cleaned_sql = cleaned_sql.rstrip(";")

    # Check if the model returned conversational refusal or plain text instead of SQL
    refusal_patterns = [r"^i'm sorry", r"^sorry", r"^i cannot", r"^i can't", r"^as an ai", r"^عذراً", r"^لا يمكن", r"^لا أستطيع"]
    for pat in refusal_patterns:
        if re.search(pat, cleaned_sql, re.IGNORECASE):
            raise SQLSecurityException("محاولة استعلام غير مصرح بها: تم رفض الطلب لأنه يحاول سحب أو تصدير قاعدة البيانات بالكامل (Bulk Data Exfiltration) أو يفتقر لتحديد نطاق عمل محدد. لحماية أداء وسرية النظام، يرجى توجيه سؤال محدد مثل: 'أعلى الأصناف مبيعاً' أو 'أرصدة العملاء الأكثر مديونية'.")

    # 3. Early lexical check for forbidden operations
    lower_sql = cleaned_sql.lower()
    if not re.search(r"\bselect\b", lower_sql):
        raise SQLSecurityException("محاولة استعلام غير مصرح بها: الرد المُولّد لا يحتوي على أمر استخراج بيانات صالح ومصرح به (SELECT). يرجى إعادة صياغة السؤال بمصطلحات محاسبية أو إدارية واضحة.")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lower_sql) and kw not in ["select", "from", "where", "group", "by", "order"]:
            raise SQLSecurityException(f"محاولة استعلام غير مصرح بها: تم اكتشاف عملية محظورة أمنياً ('{kw}'). النظام مخصص للاستعلامات التحليلية للقراءة فقط (Read-Only) ويمنع أي تعديل أو استنزاف للخادم.")

    # 4. Parse statement into an Abstract Syntax Tree (AST)
    try:
        expression = sqlglot.parse_one(cleaned_sql, read="mysql")
    except Exception as e:
        raise SQLSecurityException(f"محاولة استعلام غير مصرح بها: صياغة استعلام الـ SQL غير صالحة أو تحتوي على تراكيب غير مسموح بها أمنياً ({str(e)}).")

    # Ensure root statement is strictly a SELECT
    if not isinstance(expression, exp.Select):
        raise SQLSecurityException("محاولة استعلام غير مصرح بها: يُسمح فقط باستعلامات القراءة (SELECT) ومحظور تماماً تنفيذ أي أوامر أخرى.")

    # 5. Verify all queried tables/views against whitelist
    tables = list(expression.find_all(exp.Table))
    if not tables:
        raise SQLSecurityException("محاولة استعلام غير مصرح بها: الاستعلام لا يحدد أي جداول أو تقارير صالحة للاستخراج.")

    for table in tables:
        table_name = table.name.lower()
        if table_name not in ALLOWED_VIEWS:
            raise SQLSecurityException(
                f"محاولة استعلام غير مصرح بها: محاولة الوصول إلى جدول أو كائن غير مصرح به ('{table_name}'). الوصول مقتصر حصرياً على الـ Semantic Views المعتمدة لضمان سرية وعزل بيانات الشركات."
            )

    # 6. Build alias-qualified tenant isolation filters
    # Avoids 'ambiguous column name' errors during multi-table JOINs
    params: Dict[str, Any] = {}
    if cmp_no is not None and cmp_no > 0:
        params["cmp_no"] = cmp_no
    if brn_no is not None and brn_no > 0:
        params["brn_no"] = brn_no

    tenant_filters: List[exp.Expression] = []
    seen_aliases = set()

    for table in tables:
        # Determine table alias or fallback to table name
        alias = table.alias_or_name
        if alias in seen_aliases:
            continue
        seen_aliases.add(alias)

        # Build column node: <alias>.Cmp_No = :cmp_no if tenant is active
        if "cmp_no" in params:
            col_cmp = exp.Column(this=exp.to_identifier("Cmp_No"), table=exp.to_identifier(alias))
            tenant_filters.append(
                exp.EQ(this=col_cmp, expression=exp.Placeholder(this="cmp_no"))
            )

        # Inject branch filter if branch is specified and view supports branches
        if "brn_no" in params and table.name.lower() not in VIEWS_WITHOUT_BRANCH:
            col_brn = exp.Column(this=exp.to_identifier("Brn_No"), table=exp.to_identifier(alias))
            tenant_filters.append(
                exp.EQ(this=col_brn, expression=exp.Placeholder(this="brn_no"))
            )

    # Combine all tenant conditions with logical AND if filters exist
    if tenant_filters:
        combined_filter = tenant_filters[0]
        for flt in tenant_filters[1:]:
            combined_filter = exp.And(this=combined_filter, expression=flt)

        # Merge tenant filter into existing WHERE clause or append new WHERE clause
        if expression.args.get("where"):
            expression.args["where"].set("this", exp.And(
                this=expression.args["where"].this,
                expression=combined_filter
            ))
        else:
            expression.set("where", exp.Where(this=combined_filter))

    # 7. Enforce result set LIMIT guardrail
    current_limit = expression.args.get("limit")
    if not current_limit:
        # Auto-inject default limit
        expression.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
    else:
        # Clamp user-specified limit to max_limit
        try:
            limit_val = int(current_limit.expression.this)
            if limit_val > max_limit:
                expression.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
        except Exception:
            expression.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))

    # 8. Transpile to active database dialect (SQLite for local demo, MySQL for production)
    active_dialect = "sqlite" if settings.database_url.startswith("sqlite") else "mysql"
    final_sql = expression.sql(dialect=active_dialect)
    
    return final_sql, params
