from __future__ import annotations

import numpy as np
import pandas as pd


RFM_COLUMNS = [
    "customer_id",
    "customer_name",
    "recency_days",
    "purchase_frequency",
    "total_spend",
    "recency_score",
    "frequency_score",
    "monetary_score",
    "segment",
]


def _empty_result(customers: pd.DataFrame) -> pd.DataFrame:
    if customers is None or customers.empty or "customer_id" not in customers:
        return pd.DataFrame(columns=RFM_COLUMNS)
    result = customers[["customer_id"]].drop_duplicates().copy()
    result["customer_name"] = (
        customers.drop_duplicates("customer_id").set_index("customer_id")
        .get("customer_name", pd.Series(dtype="object"))
        .reindex(result["customer_id"]).to_numpy()
        if "customer_name" in customers
        else "Unknown"
    )
    result["recency_days"] = np.nan
    result["purchase_frequency"] = 0
    result["total_spend"] = 0.0
    result["recency_score"] = 0
    result["frequency_score"] = 0
    result["monetary_score"] = 0
    result["segment"] = "No purchases"
    return result[RFM_COLUMNS]


def segment_customers(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Score active buyers by within-dataset quintiles; lower recency is better."""
    required = (
        orders, order_items, products, customers
    )
    if any(frame is None or frame.empty for frame in required):
        return _empty_result(customers)
    if not {"order_id", "customer_id", "order_date", "order_status"} <= set(orders):
        return _empty_result(customers)
    if not {"order_id", "product_id", "quantity", "unit_price", "discount_percent"} <= set(order_items):
        return _empty_result(customers)
    if "product_id" not in products or "customer_id" not in customers:
        return _empty_result(customers)

    items = order_items.copy()
    for column in ("quantity", "unit_price", "discount_percent"):
        items[column] = pd.to_numeric(items[column], errors="coerce")
    valid_items = (
        items["quantity"].gt(0)
        & items["unit_price"].ge(0)
        & items["discount_percent"].between(0, 100)
    )
    items = items.loc[valid_items]
    orders_copy = orders[["order_id", "customer_id", "order_date", "order_status"]].copy()
    orders_copy["order_date"] = pd.to_datetime(orders_copy["order_date"], errors="coerce")
    completed = orders_copy.loc[
        orders_copy["order_status"].eq("Completed") & orders_copy["order_date"].notna()
    ]
    merged = (
        items.merge(products[["product_id"]].drop_duplicates(), on="product_id", how="inner")
        .merge(completed, on="order_id", how="inner")
    )
    if merged.empty:
        return _empty_result(customers)

    merged["net_sales"] = (
        merged["quantity"] * merged["unit_price"]
        * (1 - merged["discount_percent"] / 100)
    )
    orders_summary = merged.groupby(
        ["customer_id", "order_id", "order_date"], as_index=False
    )["net_sales"].sum()
    snapshot_date = orders_summary["order_date"].max()
    active = orders_summary.groupby("customer_id").agg(
        total_spend=("net_sales", "sum"),
        purchase_frequency=("order_id", "nunique"),
        last_purchase_date=("order_date", "max"),
    ).reset_index()
    active["recency_days"] = (
        snapshot_date - active["last_purchase_date"]
    ).dt.days

    active["recency_score"] = (
        (1 - active["recency_days"].rank(pct=True, method="average")) * 5
    ).apply(lambda score: min(5, max(1, int(score) + 1)))
    for source, target in (
        ("purchase_frequency", "frequency_score"),
        ("total_spend", "monetary_score"),
    ):
        active[target] = (
            active[source].rank(pct=True, method="average") * 5
        ).apply(lambda score: min(5, max(1, int(score) + 1)))

    r, f, m = active["recency_score"], active["frequency_score"], active["monetary_score"]
    active["segment"] = np.select(
        [
            (r >= 4) & (f >= 4) & (m >= 4),
            (f >= 4) & (m >= 3),
            (r >= 4) & (f <= 2),
            (r <= 2) & (f >= 2),
            (r >= 3) & (f >= 2) & (m >= 3),
        ],
        ["Champions", "Loyal", "New Customers", "At Risk", "Promising"],
        default="Regular",
    )

    customer_names = (
        customers[["customer_id", "customer_name"]]
        if "customer_name" in customers
        else customers[["customer_id"]].assign(customer_name="Unknown")
    )
    result = customers[["customer_id"]].drop_duplicates().merge(
        customer_names.drop_duplicates("customer_id"), on="customer_id", how="left"
    ).merge(
        active[RFM_COLUMNS[:1] + RFM_COLUMNS[2:]], on="customer_id", how="left"
    )
    result["purchase_frequency"] = result["purchase_frequency"].fillna(0).astype(int)
    result["total_spend"] = result["total_spend"].fillna(0.0)
    for score in ("recency_score", "frequency_score", "monetary_score"):
        result[score] = result[score].fillna(0).astype(int)
    result["segment"] = result["segment"].fillna("No purchases")
    return result[RFM_COLUMNS].sort_values(
        ["total_spend", "customer_id"], ascending=[False, True]
    ).reset_index(drop=True)
