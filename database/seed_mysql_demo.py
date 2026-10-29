from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from config import DB_CONFIG, BASE_DIR
from database.seed_data import generate_demo_dataframes


TABLE_COLUMNS = {
    "customers": (
        "customer_id", "customer_name", "email", "city", "state", "country", "signup_date",
    ),
    "products": (
        "product_id", "product_name", "category", "unit_cost", "unit_price", "stock_quantity",
    ),
    "orders": (
        "order_id", "customer_id", "order_date", "order_status", "payment_method",
        "shipping_city", "shipping_state",
    ),
    "order_items": (
        "order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount_percent",
    ),
}


def _engine(database: str | None = None) -> Engine:
    return create_engine(
        URL.create(
            "mysql+pymysql",
            username=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=database,
        ),
        pool_pre_ping=True,
    )


def _create_demo_schema(database: str) -> None:
    admin = _engine()
    schema_engine = _engine(database)
    try:
        with admin.begin() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))
        schema_path = BASE_DIR / "database" / "schema.sql"
        statements = schema_path.read_text(encoding="utf-8").split(";")
        for statement in statements:
            sql = statement.strip()
            if not sql or sql.upper().startswith(("CREATE DATABASE", "USE ")):
                continue
            with schema_engine.begin() as connection:
                connection.exec_driver_sql(sql)
    finally:
        admin.dispose()
        schema_engine.dispose()


def _records(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[dict]:
    records = []
    for row in frame.loc[:, columns].to_dict(orient="records"):
        records.append({
            key: value.to_pydatetime() if isinstance(value, pd.Timestamp)
            else value.item() if hasattr(value, "item")
            else value
            for key, value in row.items()
        })
    return records


def seed_demo_database(database: str) -> dict[str, int]:
    if not re.fullmatch(r"[A-Za-z0-9_]+_demo", database):
        raise ValueError("The target database name must end in '_demo'.")

    _create_demo_schema(database)
    engine = _engine(database)
    try:
        with engine.connect() as connection:
            counts = {
                table: int(connection.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
                for table in TABLE_COLUMNS
            }
            if all(count == 0 for count in counts.values()):
                pass
            elif (
                counts == {"customers": 500, "products": 100, "orders": 2000, "order_items": 5000}
                and connection.execute(
                    text("SELECT COUNT(*) FROM customers WHERE email LIKE '%@demo.local'")
                ).scalar_one() == 500
            ):
                return counts
            else:
                raise RuntimeError(
                    "Seeding stopped: the target database contains records that are not "
                    "the complete recognized demo dataset. No records were changed."
                )

        orders, items, products, customers = generate_demo_dataframes()
        frames = {
            "customers": customers,
            "products": products,
            "orders": orders,
            "order_items": items,
        }
        with engine.begin() as connection:
            for table, columns in TABLE_COLUMNS.items():
                column_sql = ", ".join(f"`{column}`" for column in columns)
                placeholders = ", ".join(f":{column}" for column in columns)
                connection.execute(
                    text(f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})"),
                    _records(frames[table], columns),
                )

        with engine.connect() as connection:
            actual_counts = {
                table: int(connection.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
                for table in TABLE_COLUMNS
            }
        return actual_counts
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load deterministic sample data into an isolated MySQL *_demo database."
    )
    parser.add_argument("--database", required=True, help="Explicit target database name ending in _demo")
    parser.add_argument(
        "--confirm-demo-data",
        action="store_true",
        help="Confirm that this isolated target is intended for synthetic demo records.",
    )
    args = parser.parse_args()
    if not args.confirm_demo_data:
        parser.error("Pass --confirm-demo-data to authorize synthetic sample-data insertion.")

    try:
        counts = seed_demo_database(args.database)
    except (SQLAlchemyError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Demo data was not loaded: {exc}") from exc
    for table, count in counts.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
