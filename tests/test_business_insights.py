import pandas as pd

from analytics.business_insights import generate_business_insights
from analytics.customer_segmentation import segment_customers
from database.seed_data import generate_demo_dataframes


def test_business_insights_are_generated():
    orders, items, products, customers = generate_demo_dataframes()
    insights = generate_business_insights(orders, items, products)
    assert len(insights) > 0
    assert 'headline' in insights[0]
    assert 'summary' in insights[0]


def test_rfm_segmentation_includes_recency_and_scored_segments():
    orders, items, products, customers = generate_demo_dataframes()
    segments = segment_customers(orders, items, products, customers)
    assert not segments.empty
    assert {"recency_days", "recency_score", "frequency_score", "monetary_score"} <= set(segments.columns)
    active = segments[segments["segment"] != "No purchases"]
    assert active["recency_days"].ge(0).all()
    assert segments["segment"].notna().all()


def test_rfm_includes_customers_without_completed_purchases():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "order_date": "2024-01-01", "order_status": "Cancelled"},
    ])
    items = pd.DataFrame([
        {"order_id": 1, "product_id": 1, "quantity": 1, "unit_price": 10, "discount_percent": 0},
    ])
    products = pd.DataFrame([{"product_id": 1}])
    customers = pd.DataFrame([
        {"customer_id": 1, "customer_name": "A"},
        {"customer_id": 2, "customer_name": "B"},
    ])
    segments = segment_customers(orders, items, products, customers)
    assert len(segments) == 2
    assert segments["segment"].eq("No purchases").all()
    assert segments["purchase_frequency"].eq(0).all()


def test_assistant_answers_category_sales_and_forecast_questions():
    from ai.assistant import answer_business_question

    orders, items, products, customers = generate_demo_dataframes()
    context = {
        "orders": orders,
        "order_items": items,
        "products": products,
        "customers": customers,
    }
    assert "generated the most net sales" in answer_business_question(
        "Which category generated the most sales?", context
    )
    assert "forecasts total net sales" in answer_business_question(
        "What are the forecasted sales?", context
    )


def test_assistant_uses_transaction_price_when_product_also_has_catalog_price():
    from ai.assistant import answer_business_question

    orders = pd.DataFrame([
        {"order_id": 1, "order_status": "Completed", "order_date": "2024-01-15", "shipping_state": "CA"},
        {"order_id": 2, "order_status": "Completed", "order_date": "2024-02-15", "shipping_state": "CA"},
        {"order_id": 3, "order_status": "Completed", "order_date": "2024-03-15", "shipping_state": "CA"},
    ])
    items = pd.DataFrame([
        {"order_id": i, "product_id": 1, "quantity": 1, "unit_price": 10, "discount_percent": 0}
        for i in (1, 2, 3)
    ])
    products = pd.DataFrame([
        {"product_id": 1, "unit_price": 999, "category": "Books", "unit_cost": 2, "product_name": "Book"}
    ])
    context = {"orders": orders, "order_items": items, "products": products}

    monthly_answer = answer_business_question("What were the monthly sales trends?", context)
    regional_answer = answer_business_question("Which state generated the highest sales?", context)

    assert "₹10.00" in monthly_answer
    assert "₹30.00" in regional_answer
    assert "₹999.00" not in monthly_answer + regional_answer


def test_assistant_handles_empty_and_missing_required_columns():
    from ai.assistant import answer_business_question

    empty_answer = answer_business_question(
        "What were the monthly sales?",
        {"orders": pd.DataFrame(), "order_items": pd.DataFrame(), "products": pd.DataFrame()},
    )
    assert "dataset is empty" in empty_answer

    missing_columns_answer = answer_business_question(
        "What were the monthly sales?",
        {
            "orders": pd.DataFrame([{"order_id": 1, "order_status": "Completed", "order_date": "2024-01-01"}]),
            "order_items": pd.DataFrame([{"order_id": 1, "product_id": 1, "quantity": 1}]),
            "products": pd.DataFrame([{"product_id": 1}]),
        },
    )
    assert "Required analytics columns are missing" in missing_columns_answer
