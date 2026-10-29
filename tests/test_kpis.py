import pandas as pd

from analytics.kpi_calculations import compute_kpis
from analytics.sales_analysis import build_regional_sales
from database.seed_data import generate_demo_dataframes


def test_kpis_are_calculated_for_demo_data():
    orders, items, products, customers = generate_demo_dataframes()
    kpis = compute_kpis(orders, items, products)
    assert kpis["gross_merchandise_value"] > 0
    assert kpis["net_merchandise_sales"] > 0
    assert kpis["estimated_product_cost"] > 0
    assert kpis["estimated_gross_profit"] > 0
    assert kpis["completed_orders"] > 0
    assert kpis["units_sold"] > 0
    assert kpis["average_order_value"] > 0

    regional_sales = build_regional_sales(orders, items, products)
    assert regional_sales["state"].nunique() > 1


def test_kpis_exclude_cancelled_sales_and_use_completed_buyers_for_aov():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 10, "order_date": "2024-01-01", "order_status": "Completed"},
        {"order_id": 2, "customer_id": 20, "order_date": "2024-01-02", "order_status": "Cancelled"},
    ])
    items = pd.DataFrame([
        {"order_item_id": 1, "order_id": 1, "product_id": 1, "quantity": 2, "unit_price": 100, "discount_percent": 10},
        {"order_item_id": 2, "order_id": 2, "product_id": 1, "quantity": 2, "unit_price": 100, "discount_percent": 0},
    ])
    products = pd.DataFrame([
        {"product_id": 1, "unit_cost": 30, "category": "Books"},
    ])
    kpis = compute_kpis(orders, items, products)
    assert kpis["gross_merchandise_value"] == 200
    assert kpis["net_merchandise_sales"] == 180
    assert kpis["estimated_product_cost"] == 60
    assert kpis["estimated_gross_profit"] == 120
    assert kpis["completed_orders"] == 1
    assert kpis["average_order_value"] == 180
    assert kpis["repeat_customer_rate"] == 0


def test_kpis_exclude_cancelled_and_returned_orders_from_sales_but_count_status_rates():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 10, "order_date": "2024-01-01", "order_status": "Completed"},
        {"order_id": 2, "customer_id": 20, "order_date": "2024-01-02", "order_status": "Cancelled"},
        {"order_id": 3, "customer_id": 30, "order_date": "2024-01-03", "order_status": "Returned"},
    ])
    items = pd.DataFrame([
        {"order_item_id": 1, "order_id": 1, "product_id": 1, "quantity": 2, "unit_price": 100, "discount_percent": 10},
        {"order_item_id": 2, "order_id": 2, "product_id": 1, "quantity": 3, "unit_price": 100, "discount_percent": 0},
        {"order_item_id": 3, "order_id": 3, "product_id": 1, "quantity": 4, "unit_price": 100, "discount_percent": 0},
    ])
    products = pd.DataFrame([
        {"product_id": 1, "unit_cost": 30, "category": "Books"},
    ])

    kpis = compute_kpis(orders, items, products)

    assert kpis["gross_merchandise_value"] == 200
    assert kpis["net_merchandise_sales"] == 180
    assert kpis["estimated_product_cost"] == 60
    assert kpis["estimated_gross_profit"] == 120
    assert kpis["completed_orders"] == 1
    assert kpis["average_order_value"] == 180
    assert kpis["cancellation_rate"] == 1 / 3
    assert kpis["return_rate"] == 1 / 3


def test_kpis_return_zero_for_empty_frames_and_zero_sales_denominators():
    empty = compute_kpis(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert empty["average_order_value"] == 0
    assert empty["gross_profit_margin"] == 0

    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "order_date": "2024-01-01", "order_status": "Completed"},
    ])
    items = pd.DataFrame([
        {"order_item_id": 1, "order_id": 1, "product_id": 1, "quantity": 1, "unit_price": 0, "discount_percent": 0},
    ])
    products = pd.DataFrame([{"product_id": 1, "unit_cost": 0, "category": "Books"}])
    kpis = compute_kpis(orders, items, products)
    assert kpis["average_order_value"] == 0
    assert kpis["gross_profit_margin"] == 0
