from __future__ import annotations

from typing import Dict

import pandas as pd


def _prepare_frames(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame):
    orders_copy = orders.copy() if orders is not None else pd.DataFrame()
    items_copy = order_items.copy() if order_items is not None else pd.DataFrame()
    products_copy = products.copy() if products is not None else pd.DataFrame()
    if not orders_copy.empty:
        orders_copy["order_date"] = pd.to_datetime(orders_copy["order_date"], errors="coerce")
    if not items_copy.empty:
        for column in ("quantity", "discount_percent", "unit_price"):
            if column in items_copy:
                items_copy[column] = pd.to_numeric(
                    items_copy[column], errors="coerce"
                ).fillna(0)
    if not products_copy.empty:
        for column in ("unit_cost", "unit_price"):
            if column in products_copy:
                products_copy[column] = pd.to_numeric(
                    products_copy[column], errors="coerce"
                ).fillna(0)
    return orders_copy, items_copy, products_copy


def compute_kpis(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> Dict[str, float]:
    orders_df, items_df, products_df = _prepare_frames(orders, order_items, products)
    if orders_df.empty or items_df.empty or products_df.empty:
        return {
            "gross_merchandise_value": 0.0,
            "net_merchandise_sales": 0.0,
            "estimated_product_cost": 0.0,
            "estimated_gross_profit": 0.0,
            "completed_orders": 0,
            "units_sold": 0,
            "average_order_value": 0.0,
            "month_over_month_growth": 0.0,
            "repeat_customer_rate": 0.0,
            "cancellation_rate": 0.0,
            "return_rate": 0.0,
            "average_discount": 0.0,
            "total_customers": 0,
            "gross_profit_margin": 0.0,
            "category_sales_contribution": {},
            "regional_sales_contribution": {},
        }

    merged = items_df.merge(products_df[["product_id", "unit_cost", "category"]], on="product_id", how="left")
    merged = merged.merge(orders_df[["order_id", "order_status", "customer_id", "order_date"]], on="order_id", how="left")
    merged["gmv"] = merged["quantity"] * merged["unit_price"]
    merged["net_sales"] = merged["gmv"] * (1 - merged["discount_percent"] / 100)
    merged["product_cost"] = merged["quantity"] * merged["unit_cost"]
    merged["gross_profit"] = merged["net_sales"] - merged["product_cost"]

    completed_mask = merged["order_status"] == "Completed"
    completed_sales = merged[completed_mask]
    total_gmv = float(completed_sales["gmv"].sum())
    net_sales = float(completed_sales["net_sales"].sum())
    estimated_cost = float(completed_sales["product_cost"].sum())
    gross_profit = float(completed_sales["gross_profit"].sum())
    completed_orders = int(completed_sales["order_id"].nunique())
    units_sold = int(completed_sales["quantity"].sum())

    dated_sales = completed_sales.dropna(subset=["order_date"])
    month_groups = dated_sales.assign(
        order_month=dated_sales["order_date"].dt.to_period("M")
    ).groupby("order_month")["net_sales"].sum()
    if not month_groups.empty:
        month_groups = month_groups.reindex(
            pd.period_range(month_groups.index.min(), month_groups.index.max(), freq="M"),
            fill_value=0,
        )
    if len(month_groups) >= 2:
        current = month_groups.iloc[-1]
        previous = month_groups.iloc[-2]
        growth = ((current - previous) / previous) if previous else 0.0
    else:
        growth = 0.0

    repeat_customers = completed_sales.groupby("customer_id")["order_id"].nunique()
    total_customers = int(repeat_customers.index.nunique())
    repeat_customer_count = int((repeat_customers > 1).sum())
    repeat_customer_rate = repeat_customer_count / total_customers if total_customers else 0.0

    cancellation_rate = float((orders_df["order_status"] == "Cancelled").mean()) if not orders_df.empty else 0.0
    return_rate = float((orders_df["order_status"] == "Returned").mean()) if not orders_df.empty else 0.0
    average_discount = (
        float(completed_sales["discount_percent"].mean() / 100)
        if not completed_sales.empty
        else 0.0
    )
    avg_order_value = net_sales / completed_orders if completed_orders else 0.0
    gross_profit_margin = gross_profit / net_sales if net_sales else 0.0

    category_sales = completed_sales.groupby("category")["net_sales"].sum().to_dict() if "category" in completed_sales.columns else {}
    region_sales = completed_sales.groupby("shipping_state")["net_sales"].sum().to_dict() if "shipping_state" in completed_sales.columns else {}

    return {
        "gross_merchandise_value": float(total_gmv),
        "net_merchandise_sales": float(net_sales),
        "estimated_product_cost": float(estimated_cost),
        "estimated_gross_profit": float(gross_profit),
        "completed_orders": completed_orders,
        "units_sold": units_sold,
        "average_order_value": float(avg_order_value),
        "month_over_month_growth": float(growth),
        "repeat_customer_rate": float(repeat_customer_rate),
        "cancellation_rate": float(cancellation_rate),
        "return_rate": float(return_rate),
        "average_discount": float(average_discount),
        "total_customers": total_customers,
        "gross_profit_margin": float(gross_profit_margin),
        "category_sales_contribution": category_sales,
        "regional_sales_contribution": region_sales,
    }
