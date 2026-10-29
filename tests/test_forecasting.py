import pandas as pd

from analytics.sales_forecasting import build_forecast_summary
from database.seed_data import generate_demo_dataframes


def test_forecasting_returns_summary_frame():
    orders, items, products, customers = generate_demo_dataframes()
    forecast = build_forecast_summary(orders, items, products)
    assert isinstance(forecast, pd.DataFrame)
    assert 'actual' in forecast.columns
    assert 'predicted' in forecast.columns
    assert forecast["predicted"].notna().sum() >= 3
    assert forecast.tail(3)["actual"].isna().all()
    assert (forecast.tail(3)["predicted"] >= 0).all()
    assert forecast["baseline_model"].eq("Last observed month").all()
    assert forecast["baseline_mae"].notna().all()


def test_forecasting_requires_three_months_of_history():
    orders = pd.DataFrame([
        {"order_id": 1, "order_status": "Completed", "order_date": "2024-01-15"},
        {"order_id": 2, "order_status": "Completed", "order_date": "2024-02-15"},
    ])
    items = pd.DataFrame([
        {"order_id": 1, "product_id": 1, "quantity": 1, "unit_price": 10, "discount_percent": 0},
        {"order_id": 2, "product_id": 1, "quantity": 1, "unit_price": 10, "discount_percent": 0},
    ])
    products = pd.DataFrame([{"product_id": 1}])
    assert build_forecast_summary(orders, items, products).empty
