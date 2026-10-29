import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from database import connection


class FailingEngine:
    def connect(self):
        raise SQLAlchemyError("connection refused")

    def dispose(self):
        pass


def test_mysql_load_failure_does_not_substitute_demo_data(monkeypatch):
    monkeypatch.setattr(connection, "get_mysql_engine", lambda: FailingEngine())
    monkeypatch.setitem(connection.DB_CONFIG, "password", "test-secret")

    orders, items, products, customers, message = connection.load_analytics_data()

    assert orders.empty and items.empty and products.empty and customers.empty
    assert "connection refused" in message
    assert "test-secret" not in message
    assert "demo data" not in message


def test_explicit_demo_mode_is_labeled(monkeypatch):
    monkeypatch.setattr(connection, "get_mysql_engine", lambda: None)
    monkeypatch.setitem(connection.DB_CONFIG, "use_mysql", False)

    orders, _, _, _, message = connection.load_analytics_data()

    assert len(orders) == 2000
    assert "explicitly disabled" in message
