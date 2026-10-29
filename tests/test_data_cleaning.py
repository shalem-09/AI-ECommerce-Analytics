import pandas as pd

from analytics.data_cleaning import clean_customers, clean_dataframes


def test_clean_dataframes_handles_invalid_rows():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "order_date": "2024-01-01", "order_status": "Completed", "payment_method": "Card", "shipping_city": "A", "shipping_state": "TX"},
        {"order_id": 2, "customer_id": 2, "order_date": "bad-date", "order_status": "Cancelled", "payment_method": "UPI", "shipping_city": "B", "shipping_state": "CA"},
    ])
    items = pd.DataFrame([
        {"order_item_id": 1, "order_id": 1, "product_id": 1, "quantity": 3, "unit_price": 100, "discount_percent": 10},
        {"order_item_id": 2, "order_id": 2, "product_id": 2, "quantity": 0, "unit_price": -5, "discount_percent": -10},
    ])
    products = pd.DataFrame([
        {"product_id": 1, "product_name": "Laptop", "category": "Electronics", "unit_cost": 90, "unit_price": 120, "stock_quantity": 10},
        {"product_id": 2, "product_name": "Phone", "category": "electronics", "unit_cost": 30, "unit_price": 50, "stock_quantity": 5},
    ])
    cleaned_orders, cleaned_items, cleaned_products, report = clean_dataframes(orders, items, products)
    assert isinstance(cleaned_orders, pd.DataFrame)
    assert cleaned_items["quantity"].min() >= 0
    assert report["missing_values"] >= 0
    assert report["invalid_records"] > 0
    assert cleaned_orders["order_date"].notna().all()
    assert cleaned_items["quantity"].min() > 0
    assert cleaned_products.loc[cleaned_products["product_id"] == 2, "category"].iloc[0] == "Electronics"


def test_invalid_price_rows_are_reported_and_excluded_without_zero_filling():
    orders = pd.DataFrame([
        {"order_id": 1, "order_date": "2024-01-01", "order_status": "Completed"},
    ])
    items = pd.DataFrame([
        {"order_item_id": 1, "order_id": 1, "product_id": 1, "quantity": 1, "unit_price": -2, "discount_percent": 0},
        {"order_item_id": 2, "order_id": 1, "product_id": 1, "quantity": 0, "unit_price": 5, "discount_percent": 0},
    ])
    products = pd.DataFrame([
        {"product_id": 1, "category": "Books", "unit_cost": 2, "unit_price": 5, "stock_quantity": 1},
    ])
    _, cleaned_items, _, report = clean_dataframes(orders, items, products)
    assert cleaned_items.empty
    assert report["invalid_records"] >= 2
    assert report["requires_investigation"] >= 2


def test_customer_quality_cleans_missing_text_and_drops_bad_or_duplicate_ids():
    customers = pd.DataFrame([
        {"customer_id": 1, "customer_name": "", "email": "a@example.test", "signup_date": "2024-01-01"},
        {"customer_id": 1, "customer_name": "Duplicate", "email": "b@example.test", "signup_date": "2024-01-02"},
        {"customer_id": "bad", "customer_name": "Invalid", "email": "c@example.test", "signup_date": "bad-date"},
    ])
    cleaned, report = clean_customers(customers)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["customer_name"] == "Unknown"
    assert report["duplicate_records"] == 1
    assert report["invalid_records"] == 2
    assert report["corrected_records"] == 1
