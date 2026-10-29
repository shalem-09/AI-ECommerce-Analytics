from __future__ import annotations

import pandas as pd


def generate_business_insights(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> list[dict]:
    insights = []
    if orders.empty or order_items.empty or products.empty:
        return [{"headline": "Data not available", "summary": "No order data is available to assess business performance."}]

    order_items_copy = order_items.copy()
    order_items_copy = order_items_copy.rename(columns={"unit_price": "order_item_unit_price"})
    merged = order_items_copy.merge(products[["product_id", "product_name", "category", "unit_price"]], on="product_id", how="left")
    merged = merged.merge(orders[["order_id", "order_status", "shipping_state"]], on="order_id", how="left")
    merged["net_sales"] = merged["quantity"] * merged["order_item_unit_price"] * (1 - merged["discount_percent"] / 100)
    completed = merged[merged["order_status"] == "Completed"]
    if completed.empty:
        return [{"headline": "No completed sales", "summary": "There are no completed orders to generate sales insights."}]
    category_sales = completed.groupby("category")["net_sales"].sum()
    regional_sales = completed.groupby("shipping_state")["net_sales"].sum()
    if category_sales.empty or regional_sales.empty:
        return [{"headline": "Incomplete sales data", "summary": "Category or shipping-region fields are missing from completed order lines."}]
    top_category = category_sales.idxmax()
    top_state = regional_sales.idxmax()
    insights.append({
        "headline": "Category momentum",
        "summary": f"{top_category} is delivering the strongest sales contribution, making it the best category to prioritize for inventory planning.",
    })
    insights.append({
        "headline": "Regional concentration",
        "summary": f"{top_state} is the largest region by completed sales, which indicates a strong growth opportunity for local campaigns and targeted promotions.",
    })
    insights.append({
        "headline": "Fulfillment watchlist",
        "summary": f"Cancelled and returned orders together account for {((orders['order_status'].isin(['Cancelled','Returned']).mean()) * 100):.1f}% of all orders and should be reviewed for conversion and product quality issues.",
    })
    return insights
