import pytest
# Import classes from the package
from forbidden_scripts.forbidden_sql import *


def test_length_conversion():
    """Test standard length conversions."""
    

    config = SQLValidatorConfig(
        allowed_tables={"users", "orders", "public.users"},
        allowed_fields={"id", "name", "email", "total", "user_id", "cnt"},
        allow_star=False,
        allowed_functions={"COUNT", "SUM", "MAX", "MIN"},
        forbidden_functions={"SLEEP", "BENCHMARK"},
        max_subquery_depth=1,
        allow_cte=True,
    )
    validator = SQLValidator(config)

    valid_queries = [
        "SELECT id, name FROM users",
        "SELECT u.id, o.total FROM users u JOIN orders o ON u.id = o.user_id",
        "SELECT COUNT(id) AS cnt FROM users",
        "WITH recent AS (SELECT id FROM users WHERE id > 10) SELECT id FROM recent",
        "SELECT id FROM (SELECT id FROM users) t",  # один уровень подзапроса — разрешён
    ]

    invalid_queries = [
        "SELECT * FROM users",
        "SELECT password FROM users",
        "SELECT SLEEP(5) FROM users",
        "DELETE FROM users WHERE id=1",
        "SELECT id FROM users UNION SELECT id FROM orders",
        "SELECT id FROM products",
        "SELECT id FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > (SELECT MAX(total) FROM orders))",
    ]

    print("=== Valid queries ===")
    for q in valid_queries:
        try:
            validator.validate(q)
            print(f"OK: {q}")
        except SQLValidationError as e:
            print(f"FAIL: {q} -> {e}")

    print("\n=== Invalid queries ===")
    for q in invalid_queries:
        try:
            validator.validate(q)
            print(f"OK (unexpected): {q}")
        except SQLValidationError as e:
            print(f"FAIL (expected): {q} -> {e}")