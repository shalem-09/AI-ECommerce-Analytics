from __future__ import annotations

import pandas as pd


def _attach_product_metrics(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    if orders.empty or order_items.empty or products.empty:
        return pd.DataFrame()
    merged = order_items.merge(products[["product_id", "product_name", "category", "unit_cost"]], on="product_id", how="left")
    merged = merged.merge(orders[["order_id", "order_status", "shipping_state", "shipping_city", "order_date"]], on="order_id", how="left")
    merged["gmv"] = merged["quantity"] * merged["unit_price"]
    merged["net_sales"] = merged["gmv"] * (1 - merged["discount_percent"] / 100)
    merged["estimated_product_cost"] = merged["quantity"] * merged["unit_cost"]
    merged["estimated_gross_profit"] = merged["net_sales"] - merged["estimated_product_cost"]
    return merged


def build_monthly_sales(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    merged = _attach_product_metrics(orders, order_items, products)
    if merged.empty:
        return pd.DataFrame(columns=["order_month", "net_sales", "estimated_gross_profit"])
    completed = merged[merged["order_status"] == "Completed"].copy()
    completed["order_month"] = pd.to_datetime(completed["order_date"], errors="coerce").dt.to_period("M").astype(str)
    return completed.groupby("order_month", as_index=False).agg(
        net_sales=("net_sales", "sum"),
        estimated_gross_profit=("estimated_gross_profit", "sum"),
    )


def build_sales_by_category(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    merged = _attach_product_metrics(orders, order_items, products)
    if merged.empty:
        return pd.DataFrame(columns=["category", "net_sales", "estimated_gross_profit", "average_discount_percent"])
    summary = merged[merged["order_status"] == "Completed"].groupby("category").agg(
        net_sales=("net_sales", "sum"),
        estimated_gross_profit=("estimated_gross_profit", "sum"),
        average_discount_percent=("discount_percent", "mean"),
    ).reset_index()
    return summary


def build_regional_sales(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    merged = _attach_product_metrics(orders, order_items, products)
    if merged.empty:
        return pd.DataFrame(columns=["state", "net_sales", "order_count"])
    summary = merged[merged["order_status"] == "Completed"].groupby("shipping_state").agg(net_sales=("net_sales", "sum"), order_count=("order_id", "nunique")).reset_index()
    return summary.rename(columns={"shipping_state": "state"})


def build_top_products(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    merged = _attach_product_metrics(orders, order_items, products)
    if merged.empty:
        return pd.DataFrame(columns=["product_id", "product_name", "units_sold", "net_sales", "estimated_gross_profit", "average_discount_percent"])
    summary = merged[merged["order_status"] == "Completed"].groupby(
        ["product_id", "product_name"]
    ).agg(
        units_sold=("quantity", "sum"),
        net_sales=("net_sales", "sum"),
        estimated_gross_profit=("estimated_gross_profit", "sum"),
        average_discount_percent=("discount_percent", "mean"),
    ).reset_index()
    return summary.sort_values("net_sales", ascending=False).head(limit)


def get_order_status_breakdown(orders: pd.DataFrame) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(columns=["order_status", "order_count"])
    summary = orders.groupby("order_status").size().reset_index(name="order_count")
    summary.columns = ["order_status", "order_count"]
    return summary
