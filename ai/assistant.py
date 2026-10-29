from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from analytics.customer_segmentation import segment_customers
from analytics.sales_forecasting import build_forecast_summary


def _safe_decimal(df: pd.DataFrame, col: str) -> float:
    return float(df[col].sum()) if col in df.columns and not df.empty else 0.0


def _merge_sales_data(
    items: pd.DataFrame,
    products: pd.DataFrame,
    orders: pd.DataFrame,
    product_columns: tuple[str, ...],
    order_columns: tuple[str, ...],
) -> tuple[pd.DataFrame | None, str | None]:
    required_items = {
        "order_id", "product_id", "quantity", "unit_price", "discount_percent"
    }
    missing_items = sorted(required_items - set(items.columns))
    missing_products = sorted(
        ({"product_id"} | set(product_columns)) - set(products.columns)
    )
    missing_orders = sorted(
        ({"order_id", "order_status"} | set(order_columns)) - set(orders.columns)
    )
    missing = (
        [f"order_items.{column}" for column in missing_items]
        + [f"products.{column}" for column in missing_products]
        + [f"orders.{column}" for column in missing_orders]
    )
    if missing:
        return None, "Required analytics columns are missing: " + ", ".join(missing) + "."

    product_fields = list(dict.fromkeys(["product_id", *product_columns]))
    order_fields = list(dict.fromkeys(["order_id", "order_status", *order_columns]))
    merged = (
        items.merge(
            products[product_fields].drop_duplicates("product_id"),
            on="product_id",
            how="inner",
            validate="many_to_one",
        )
        .merge(
            orders[order_fields].drop_duplicates("order_id"),
            on="order_id",
            how="inner",
            validate="many_to_one",
        )
    )
    for column in ("quantity", "unit_price", "discount_percent"):
        merged[column] = pd.to_numeric(merged[column], errors="coerce")
    valid = (
        merged["quantity"].gt(0)
        & merged["unit_price"].ge(0)
        & merged["discount_percent"].between(0, 100)
    )
    merged = merged.loc[valid].copy()
    merged["net_sales"] = (
        merged["quantity"]
        * merged["unit_price"]
        * (1 - merged["discount_percent"] / 100)
    )
    return merged, None


def answer_business_question(question: str, context: Dict[str, Any]) -> str:
    question = (question or "").strip()
    if not question:
        return "Please ask a specific analytics question."

    orders = context.get("orders", pd.DataFrame())
    items = context.get("order_items", pd.DataFrame())
    products = context.get("products", pd.DataFrame())
    customers = context.get("customers", pd.DataFrame())

    if any(
        frame is None or not isinstance(frame, pd.DataFrame) or frame.empty
        for frame in (orders, items, products)
    ):
        return "The analytical dataset is empty. Load the e-commerce data before asking for a business answer."

    if any(keyword in question.lower() for keyword in ["gross profit", "category generated the highest estimated gross profit", "highest estimated gross profit"]):
        merged, error = _merge_sales_data(
            items, products, orders, ("category", "unit_cost"), ()
        )
        if error:
            return error
        merged["cost"] = merged["quantity"] * merged["unit_cost"].fillna(0)
        merged["gross_profit"] = merged["net_sales"] - merged["cost"]
        completed = merged[merged["order_status"] == "Completed"]
        result = completed.groupby("category")["gross_profit"].sum().sort_values(ascending=False)
        if result.empty:
            return "No completed sales data is available for category gross profit analysis."
        top = result.index[0]
        value = float(result.iloc[0])
        return f"{top} generated the highest estimated gross profit at ₹{value:,.2f} from completed sales."

    normalized_question = question.lower()

    if "forecast" in normalized_question:
        try:
            forecast = build_forecast_summary(orders, items, products)
        except (KeyError, TypeError, ValueError) as exc:
            return f"Forecast unavailable because the source data is incomplete: {exc}"
        future = forecast[forecast["actual"].isna()] if not forecast.empty else forecast
        if future.empty:
            return "A forecast is unavailable: at least three months of completed sales history are required."
        total = float(future["predicted"].sum())
        first, last = future["period"].iloc[0], future["period"].iloc[-1]
        return (
            f"The model forecasts total net sales of ₹{total:,.2f} from {first} "
            f"through {last}. This is a linear-regression estimate, not a guarantee."
        )

    if "segment" in normalized_question and any(
        word in normalized_question for word in ("spend", "highest", "customer")
    ):
        if customers.empty:
            return "Customer profile data is unavailable for segmentation."
        segments = segment_customers(orders, items, products, customers)
        active = segments[segments["segment"] != "No purchases"]
        if active.empty:
            return "No completed purchases are available for customer segmentation."
        spend = active.groupby("segment")["total_spend"].sum().sort_values(ascending=False)
        top = spend.index[0]
        return (
            f"{top} customers have the highest combined completed-order spending "
            f"at ₹{float(spend.iloc[0]):,.2f}."
        )

    if any(keyword in normalized_question for keyword in ["monthly sales trends", "monthly sales", "sales trend", "trend"]):
        merged, error = _merge_sales_data(
            items, products, orders, (), ("order_date",)
        )
        if error:
            return error
        merged["order_date"] = pd.to_datetime(merged["order_date"], errors="coerce")
        merged = merged.dropna(subset=["order_date"])
        monthly = merged[merged["order_status"] == "Completed"].groupby(merged["order_date"].dt.to_period("M").astype(str))["net_sales"].sum().reset_index()
        if monthly.empty:
            return "No completed sales trend is available for the selected period."
        latest = monthly.iloc[-1]
        previous = monthly.iloc[-2] if len(monthly) > 1 else latest
        trend = ((latest["net_sales"] - previous["net_sales"]) / previous["net_sales"]) if previous["net_sales"] else 0
        return f"The latest monthly sales were ₹{latest['net_sales']:,.2f}. Trend versus the previous month is {trend * 100:.2f}% ."

    if any(keyword in normalized_question for keyword in ["five products sold the most units", "top 5 products", "most units", "highest-selling products", "highest selling products"]):
        merged, error = _merge_sales_data(
            items, products, orders, ("product_name",), ()
        )
        if error:
            return error
        top = merged[merged["order_status"] == "Completed"].groupby("product_name")["quantity"].sum().sort_values(ascending=False).head(5)
        if top.empty:
            return "No completed product sales data is available."
        parts = [f"{name}: {qty} units" for name, qty in top.items()]
        return "Top products by units sold: " + "; ".join(parts) + "."

    if "category" in normalized_question and any(
        word in normalized_question for word in ("most", "highest", "top", "generated")
    ):
        merged, error = _merge_sales_data(
            items, products, orders, ("category",), ()
        )
        if error:
            return error
        merged = merged.loc[merged["order_status"].eq("Completed")]
        sales = merged.groupby("category")["net_sales"].sum().sort_values(ascending=False)
        if sales.empty:
            return "No completed sales are available for category analysis."
        return f"{sales.index[0]} generated the most net sales at ₹{float(sales.iloc[0]):,.2f}."

    if any(keyword in normalized_question for keyword in ["state generated the highest sales", "highest sales", "highest sales by state", "state"]):
        merged, error = _merge_sales_data(
            items, products, orders, (), ("shipping_state",)
        )
        if error:
            return error
        result = merged[merged["order_status"] == "Completed"].groupby("shipping_state")["net_sales"].sum().sort_values(ascending=False)
        if result.empty:
            return "No completed sales records are available for regional analysis."
        top = result.index[0]
        value = float(result.iloc[0])
        return f"{top} generated the highest sales with ₹{value:,.2f} in completed order value."

    if any(keyword in question.lower() for keyword in ["customers purchased repeatedly", "repeat customers", "repeatedly"]):
        if not {"order_id", "customer_id", "order_status"} <= set(orders.columns):
            return "Required analytics columns are missing: orders.order_id, orders.customer_id, or orders.order_status."
        if not {"order_id"} <= set(items.columns):
            return "Required analytics column is missing: order_items.order_id."
        merged = items.merge(
            orders[["order_id", "customer_id", "order_status"]].drop_duplicates("order_id"),
            on="order_id",
            how="inner",
            validate="many_to_one",
        )
        repeated = merged[merged["order_status"] == "Completed"].groupby("customer_id")["order_id"].nunique().reset_index()
        repeated = repeated[repeated["order_id"] > 1]
        if repeated.empty:
            return "No repeat customers are present in the available completed order history."
        top = repeated.sort_values("order_id", ascending=False).head(5)
        names = []
        for _, row in top.iterrows():
            names.append(f"Customer {int(row['customer_id'])} ({int(row['order_id'])} purchases)")
        return "Repeat customers: " + "; ".join(names) + "."

    if any(keyword in question.lower() for keyword in ["management investigate", "business trends", "should management investigate"]):
        return "Key trends to investigate: category concentration, regional concentration, and cancelled or returned order rates. The dashboard indicates a need to review product quality and conversion bottlenecks in the largest revenue segments."

    return "This question is not covered by the local analytical assistant. Please use one of the supported templates like category gross profit, monthly sales, top products, state sales, repeat customers, or management investigation prompts."
