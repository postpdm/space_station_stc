"""
SQL Validator based on Pydantic schemas.

Validates that a SQL query:
- Is a SELECT statement only.
- Uses only tables from a whitelist.
- Uses only fields from a whitelist.
- Does not contain forbidden operations (e.g., UNION, INSERT, DDL, etc.).
- Optionally disallows SELECT *.

Uses sqlglot for robust SQL parsing.
"""

from typing import Set, Optional
import sqlglot
from sqlglot import expressions as exp
from pydantic import BaseModel, Field
import re


class SQLValidatorConfig(BaseModel):
    """
    Configuration for the SQL validator.
    """
    allowed_tables: Set[str] = Field(default_factory=set)
    allowed_fields: Set[str] = Field(default_factory=set)
    forbidden_operations: Set[str] = Field(
        default_factory=lambda: {
            "UNION", "INTERSECT", "EXCEPT",
            "INSERT", "UPDATE", "DELETE",
            "CREATE", "ALTER", "DROP", "TRUNCATE",
            "MERGE", "CALL", "EXECUTE",
            "GRANT", "REVOKE",
            "INTO", "FOR UPDATE", "LOCK IN SHARE MODE"
        }
    )
    allow_star: bool = False
    allowed_functions: Optional[Set[str]] = None  # None = all functions allowed
    forbidden_functions: Set[str] = Field(default_factory=set)
    max_subquery_depth: int = 1  # 0 = no subquery, 1 = one subquery level, etc
    allow_cte: bool = True


class SQLValidationError(Exception):
    """Raised when SQL validation fails."""
    pass


class SQLValidator:
    """
    Validates SQL queries according to the provided configuration.
    """

    def __init__(self, config: SQLValidatorConfig):
        self.config = config

    async def validate(self, sql: str) -> None:
        """
        Validate the given SQL string.

        Raises:
            SQLValidationError: If any validation rule is violated.
        """
        try:
            expression = sqlglot.parse_one(sql)
        except Exception as e:
            raise SQLValidationError(f"Failed to parse SQL: {e}")

        # 1. Only SELECT
        if not isinstance(expression, exp.Select):
            raise SQLValidationError("Only SELECT statements are allowed.")

        # 2. Forbidden operations
        await self._check_forbidden_operations(expression)

        # 3. CTE handling
        cte_tables = await self._extract_cte_tables(expression)
        if cte_tables and not self.config.allow_cte:
            raise SQLValidationError("CTE (WITH) is forbidden.")

        # 4. Tables whitelist
        tables = await self._extract_tables(expression, exclude_cte=cte_tables)
        for table in tables:
            if not await self._is_table_allowed(table):
                raise SQLValidationError(f"Table not allowed: {table}")

        # 5. Fields whitelist
        fields = await self._extract_fields(expression)
        for field in fields:
            if field not in self.config.allowed_fields:
                raise SQLValidationError(f"Field not allowed: {field}")

        # 6. Star check
        if not self.config.allow_star and await self._contains_star(expression):
            raise SQLValidationError("SELECT * is not allowed (allow_star=False).")

        # 7. Functions check
        await self._check_functions(expression)

        # 8. Subquery depth
        await self._check_subquery_depth(expression)

    async def _check_forbidden_operations(self, expression: exp.Expression) -> None:
        """Check for forbidden operations (UNION, DML, DDL, etc.)."""
        # Stable AST node types
        for node in expression.walk():
            if isinstance(node, exp.Union):
                raise SQLValidationError("Forbidden operation: UNION")
            if isinstance(node, exp.Intersect):
                raise SQLValidationError("Forbidden operation: INTERSECT")
            if isinstance(node, exp.Except):
                raise SQLValidationError("Forbidden operation: EXCEPT")
            if isinstance(node, exp.Insert):
                raise SQLValidationError("Forbidden operation: INSERT")
            if isinstance(node, exp.Update):
                raise SQLValidationError("Forbidden operation: UPDATE")
            if isinstance(node, exp.Delete):
                raise SQLValidationError("Forbidden operation: DELETE")
            if isinstance(node, exp.Create):
                raise SQLValidationError("Forbidden operation: CREATE")
            if isinstance(node, exp.Drop):
                raise SQLValidationError("Forbidden operation: DROP")
            if isinstance(node, exp.Alter):
                raise SQLValidationError("Forbidden operation: ALTER")

        # SELECT INTO
        if isinstance(expression, exp.Select) and expression.args.get("into"):
            raise SQLValidationError("SELECT INTO is forbidden.")

        # String-based check for other forbidden operations
        sql_upper = expression.sql().upper()
        for op in self.config.forbidden_operations:
            pattern = r'\b' + re.escape(op.upper()) + r'\b'
            if re.search(pattern, sql_upper):
                raise SQLValidationError(f"Forbidden operation: {op}")

    async def _extract_cte_tables(self, expression: exp.Expression) -> Set[str]:
        """Extract CTE names from the AST."""
        cte_names = set()
        for cte in expression.find_all(exp.CTE):
            name = None
            if cte.alias:
                name = cte.alias
            elif cte.name:
                name = cte.name
            elif cte.this and isinstance(cte.this, exp.Table):
                name = cte.this.name
            if name:
                cte_names.add(name)
        return cte_names

    async def _extract_tables(self, expression: exp.Expression, exclude_cte: Optional[Set[str]] = None) -> Set[str]:
        """Extract table names, excluding CTEs."""
        tables = set()
        for table in expression.find_all(exp.Table):
            if exclude_cte and table.name in exclude_cte:
                continue
            parts = []
            if table.catalog:
                parts.append(table.catalog)
            if table.db:
                parts.append(table.db)
            parts.append(table.name)
            full_name = ".".join(parts)
            tables.add(full_name)
        return tables

    async def _extract_fields(self, expression: exp.Expression) -> Set[str]:
        """Extract column names (without qualifiers)."""
        fields = set()
        for column in expression.find_all(exp.Column):
            fields.add(column.name)
        return fields

    async def _contains_star(self, expression: exp.Expression) -> bool:
        """Check for any Star node."""
        return any(isinstance(node, exp.Star) for node in expression.walk())

    async def _is_table_allowed(self, table: str) -> bool:
        """Check if table is allowed (full name or just table name)."""
        if table in self.config.allowed_tables:
            return True
        if "." in table:
            table_name = table.split(".")[-1]
            if table_name in self.config.allowed_tables:
                return True
        return False

    async def _check_functions(self, expression: exp.Expression) -> None:
        """Check function usage."""
        used_functions = set()
        for func in expression.find_all(exp.Func):
            if isinstance(func, exp.Anonymous):
                func_name = func.name.upper() if hasattr(func, 'name') and func.name else ''
            else:
                func_name = func.sql_name().upper() if hasattr(func, 'sql_name') else str(func).upper()
            if func_name:
                used_functions.add(func_name)

        if self.config.forbidden_functions:
            forbidden = {f.upper() for f in self.config.forbidden_functions}
            intersection = used_functions & forbidden
            if intersection:
                raise SQLValidationError(f"Forbidden functions: {', '.join(intersection)}")

        if self.config.allowed_functions is not None:
            allowed = {f.upper() for f in self.config.allowed_functions}
            not_allowed = used_functions - allowed
            if not_allowed:
                raise SQLValidationError(f"Functions not allowed: {', '.join(not_allowed)}")

    async def _check_subquery_depth(self, expression: exp.Expression) -> None:
        """Check nested subquery depth."""
        def max_depth(node: exp.Expression, current_depth: int) -> int:
            if isinstance(node, exp.Select):
                this_depth = current_depth + 1
            else:
                this_depth = current_depth
            max_child = this_depth
            for child in node.iter_expressions():
                if child is not None:
                    child_depth = max_depth(child, this_depth)
                    if child_depth > max_child:
                        max_child = child_depth
            return max_child

        root_depth = max_depth(expression, -1)
        if root_depth > self.config.max_subquery_depth:
            raise SQLValidationError(
                f"Maximum subquery depth exceeded ({root_depth} > {self.config.max_subquery_depth})"
            )


