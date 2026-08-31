import pytest
# Import classes from the package
from space_station_stc.forbidden_scripts.forbidden_sql import *

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

config_user_orders = SQLValidatorConfig(
    allowed_tables={"users", "orders", "public.users"},
    allowed_fields={"id", "name", "email", "total", "user_id", "cnt"},
    allow_star=False,
    allowed_functions={"DATE","COUNT", "SUM", "MAX", "MIN"},
    forbidden_functions={"SLEEP", "BENCHMARK"},
    max_subquery_depth=1,
    allow_cte=True,
)

def test_abracadabra():
    """test corrupted queries."""

    validator = SQLValidator(config_user_orders)

    # should raise SQLValidationError
    with pytest.raises(SQLValidationError):
        validator.validate( 'hublyz123vv' )

def test_drop_database():
    """test drop database queries."""

    validator = SQLValidator(config_user_orders)

    # should raise SQLValidationError
    with pytest.raises(SQLValidationError):
        validator.validate( 'drop database' )

def test_forbidden_table():
    """test query for forbidden table."""

    validator = SQLValidator(config_user_orders)

    with pytest.raises(SQLValidationError):
        validator.validate( 'select id from admins' )

def test_valid_queries():
    """test valid queries."""

    validator = SQLValidator(config_user_orders)

    # should not raise nothing
    for q in valid_queries:
        validator.validate(q)

def test_invalid_queries():
    """test invalid queries."""

    validator = SQLValidator(config_user_orders)

    # should raise SQLValidationError
    for q in invalid_queries:
        with pytest.raises(SQLValidationError):
            validator.validate(q)
