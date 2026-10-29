from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from config import DB_CONFIG, get_db_url
from database.seed_data import generate_demo_dataframes


def _empty_analytics_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame(columns=["order_id", "customer_id", "order_date", "order_status", "shipping_state"]),
        pd.DataFrame(columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount_percent"]),
        pd.DataFrame(columns=["product_id", "product_name", "category", "unit_cost", "unit_price"]),
        pd.DataFrame(columns=["customer_id", "customer_name", "email"]),
    )


def get_mysql_engine() -> Optional[Engine]:
    url = get_db_url()
    if not url:
        return None
    return create_engine(url, future=True, pool_pre_ping=True)


def _safe_database_error(exc: SQLAlchemyError) -> str:
    detail = str(getattr(exc, "orig", exc))
    password = DB_CONFIG["password"]
    return detail.replace(password, "[redacted]") if password else detail


def test_mysql_connection() -> tuple[bool, str]:
    engine = get_mysql_engine()
    if engine is None:
        return False, "MySQL connection disabled. Set USE_MYSQL=true and configure DB credentials in `.env`."
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return True, "MySQL connection successful."
        return False, "MySQL connection returned no valid result."
    except SQLAlchemyError as exc:
        return False, f"MySQL connectivity failed: {_safe_database_error(exc)}"
    finally:
        engine.dispose()


def load_analytics_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    engine = get_mysql_engine()
    if engine is None:
        if not DB_CONFIG["use_mysql"]:
            return (*generate_demo_dataframes(), "MySQL is explicitly disabled; using generated demo data.")
        return (*_empty_analytics_frames(), "MySQL is not configured; no data was loaded.")

    queries = {
        "orders": "SELECT * FROM orders",
        "order_items": "SELECT * FROM order_items",
        "products": "SELECT * FROM products",
        "customers": "SELECT * FROM customers",
    }
    try:
        with engine.connect() as connection:
            frames = {
                name: pd.read_sql(text(query), connection)
                for name, query in queries.items()
            }
        return (
            frames["orders"],
            frames["order_items"],
            frames["products"],
            frames["customers"],
            "Connected to MySQL; loaded live database data.",
        )
    except SQLAlchemyError as exc:
        return (
            *_empty_analytics_frames(),
            f"MySQL data could not be loaded: {_safe_database_error(exc)}",
        )
    finally:
        engine.dispose()
