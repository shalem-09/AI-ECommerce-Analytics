import os

import pytest
from sqlalchemy import text

from database.connection import get_mysql_engine


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MYSQL_INTEGRATION_TESTS") != "1",
    reason="Set RUN_MYSQL_INTEGRATION_TESTS=1 to run read-only MySQL integration checks.",
)


def test_mysql_connectivity_and_analytics_tables_are_readable():
    engine = get_mysql_engine()
    assert engine is not None, "MySQL is disabled or not configured."
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            for table in ("customers", "products", "orders", "order_items"):
                count = connection.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
                assert count >= 0
    finally:
        engine.dispose()
