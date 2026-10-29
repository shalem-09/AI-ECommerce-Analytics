from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd


VALID_STATUSES = {"Completed", "Cancelled", "Returned", "Shipped", "Pending"}
VALID_CATEGORIES = {"Electronics", "Home", "Fashion", "Beauty", "Sports", "Books"}


def _empty_report() -> Dict[str, int]:
    return {
        "missing_values": 0,
        "duplicate_records": 0,
        "invalid_records": 0,
        "corrected_records": 0,
        "requires_investigation": 0,
    }


def normalize_category(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    text = str(value).strip()
    mapping = {
        "elec": "Electronics",
        "electronics": "Electronics",
        "home & living": "Home",
        "home": "Home",
        "fashion": "Fashion",
        "beauty": "Beauty",
        "sports": "Sports",
        "books": "Books",
    }
    return mapping.get(text.lower(), text.title())


def _integer_values(values: pd.Series) -> Tuple[pd.Series, pd.Series]:
    numeric = pd.to_numeric(values, errors="coerce")
    invalid = numeric.isna() | numeric.le(0) | numeric.mod(1).ne(0)
    return numeric, invalid


def build_data_quality_report(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
) -> Dict[str, object]:
    report: Dict[str, object] = {
        "missing_values": 0,
        "duplicate_records": 0,
        "invalid_records": 0,
        "corrected_records": 0,
        "requires_investigation": 0,
        "warnings": [],
    }
    frames = (orders, order_items, products)
    report["missing_values"] = sum(
        int(frame.isna().sum().sum())
        for frame in frames
        if frame is not None and not frame.empty
    )
    report["duplicate_records"] = sum(
        int(frame.duplicated().sum())
        for frame in frames
        if frame is not None and not frame.empty
    )

    invalid_counts = []
    if orders is not None and not orders.empty and "order_status" in orders:
        invalid_counts.append(int((~orders["order_status"].isin(VALID_STATUSES)).sum()))
    if order_items is not None and not order_items.empty:
        invalid = pd.Series(False, index=order_items.index)
        for column, condition in (
            ("quantity", lambda values: (values <= 0) | values.mod(1).ne(0)),
            ("unit_price", lambda values: values < 0),
            ("discount_percent", lambda values: (values < 0) | (values > 100)),
        ):
            if column in order_items:
                numeric = pd.to_numeric(order_items[column], errors="coerce")
                invalid |= numeric.isna() | condition(numeric)
        invalid_counts.append(int(invalid.sum()))
    if products is not None and not products.empty:
        invalid = pd.Series(False, index=products.index)
        for column in ("unit_cost", "unit_price", "stock_quantity"):
            if column in products:
                numeric = pd.to_numeric(products[column], errors="coerce")
                invalid |= numeric.isna() | (numeric < 0)
        if "category" in products:
            normalized = products["category"].apply(normalize_category)
            invalid |= ~normalized.isin(VALID_CATEGORIES)
        invalid_counts.append(int(invalid.sum()))

    report["invalid_records"] = sum(invalid_counts)
    report["requires_investigation"] = int(report["invalid_records"])
    warnings = report["warnings"]
    if report["missing_values"]:
        warnings.append(f"Found {report['missing_values']} missing field values.")
    if report["duplicate_records"]:
        warnings.append(f"Found {report['duplicate_records']} duplicate records.")
    if report["invalid_records"]:
        warnings.append(f"Found {report['invalid_records']} invalid records.")
    return report


def clean_orders(orders: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if orders is None or orders.empty:
        return pd.DataFrame() if orders is None else orders.copy(), _empty_report()

    clean = orders.copy()
    missing_values = int(clean.isna().sum().sum())
    invalid_ids = pd.Series(False, index=clean.index)
    for column in ("order_id", "customer_id"):
        if column in clean:
            clean[column], invalid = _integer_values(clean[column])
            invalid_ids |= invalid
    original_status = clean["order_status"]
    clean["order_date"] = pd.to_datetime(clean["order_date"], errors="coerce")
    clean["order_status"] = original_status.fillna("Pending").astype(str).str.strip().str.title()
    invalid_status = ~clean["order_status"].isin(VALID_STATUSES)
    clean.loc[invalid_status, "order_status"] = "Pending"
    invalid_dates = clean["order_date"].isna()
    invalid_records = int((invalid_status | invalid_dates | invalid_ids).sum())
    duplicate_records = int(
        clean.duplicated(subset=["order_id"]).sum()
        if "order_id" in clean
        else clean.duplicated().sum()
    )
    if "order_id" in clean:
        clean = clean.drop_duplicates(subset=["order_id"])
    clean = clean.loc[~(invalid_dates | invalid_ids)].copy()
    for column in ("order_id", "customer_id"):
        if column in clean:
            clean[column] = clean[column].astype("int64")
    for column in ("shipping_city", "shipping_state"):
        if column in clean:
            clean[column] = clean[column].fillna("Unknown").astype(str).str.strip()
    return clean, {
        "missing_values": missing_values,
        "duplicate_records": duplicate_records,
        "invalid_records": invalid_records,
        "corrected_records": int(invalid_status.sum()),
        "requires_investigation": int((invalid_dates | invalid_ids).sum()),
    }


def clean_order_items(order_items: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if order_items is None or order_items.empty:
        return pd.DataFrame() if order_items is None else order_items.copy(), _empty_report()

    clean = order_items.copy()
    missing_values = int(clean.isna().sum().sum())
    numeric_columns = ("quantity", "discount_percent", "unit_price")
    raw_numeric = {
        column: pd.to_numeric(clean[column], errors="coerce")
        for column in numeric_columns
    }
    invalid = pd.Series(False, index=clean.index)
    for column in ("order_item_id", "order_id", "product_id"):
        if column in clean:
            clean[column], invalid_ids = _integer_values(clean[column])
            invalid |= invalid_ids
    invalid |= (
        raw_numeric["quantity"].isna()
        | (raw_numeric["quantity"] <= 0)
        | raw_numeric["quantity"].mod(1).ne(0)
    )
    invalid |= raw_numeric["discount_percent"].isna() | (
        (raw_numeric["discount_percent"] < 0)
        | (raw_numeric["discount_percent"] > 100)
    )
    invalid |= raw_numeric["unit_price"].isna() | (raw_numeric["unit_price"] < 0)
    duplicate_records = int(
        clean.duplicated(subset=["order_item_id"]).sum()
        if "order_item_id" in clean
        else clean.duplicated().sum()
    )
    clean["quantity"] = raw_numeric["quantity"]
    clean["discount_percent"] = raw_numeric["discount_percent"]
    clean["unit_price"] = raw_numeric["unit_price"]
    clean = clean.loc[~invalid].copy()
    if "order_item_id" in clean:
        clean = clean.drop_duplicates(subset=["order_item_id"])
    for column in ("order_item_id", "order_id", "product_id"):
        if column in clean:
            clean[column] = clean[column].astype("int64")
    return clean, {
        "missing_values": missing_values,
        "duplicate_records": duplicate_records,
        "invalid_records": int(invalid.sum()),
        "corrected_records": 0,
        "requires_investigation": int(invalid.sum()),
    }


def clean_products(products: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if products is None or products.empty:
        return pd.DataFrame() if products is None else products.copy(), _empty_report()

    clean = products.copy()
    missing_values = int(clean.isna().sum().sum())
    invalid_ids = pd.Series(False, index=clean.index)
    if "product_id" in clean:
        clean["product_id"], invalid_ids = _integer_values(clean["product_id"])
    raw_category = clean["category"]
    clean["category"] = raw_category.apply(normalize_category)
    numeric_columns = ("unit_cost", "unit_price", "stock_quantity")
    numeric_values = {
        column: pd.to_numeric(clean[column], errors="coerce")
        for column in numeric_columns
    }
    invalid = pd.Series(False, index=clean.index)
    for column, values in numeric_values.items():
        invalid |= values.isna() | (values < 0)
    if "stock_quantity" in numeric_values:
        invalid |= numeric_values["stock_quantity"].mod(1).ne(0)
    invalid |= ~clean["category"].isin(VALID_CATEGORIES)
    discard = (
        invalid_ids
        | numeric_values["unit_cost"].isna()
        | (numeric_values["unit_cost"] < 0)
        | numeric_values["unit_price"].isna()
        | (numeric_values["unit_price"] < 0)
        | numeric_values["stock_quantity"].isna()
        | (numeric_values["stock_quantity"] < 0)
        | numeric_values["stock_quantity"].mod(1).ne(0)
    )
    duplicate_records = int(
        clean.duplicated(subset=["product_id"]).sum()
        if "product_id" in clean
        else clean.duplicated().sum()
    )
    for column, values in numeric_values.items():
        clean[column] = values.fillna(0).clip(lower=0)
    clean = clean.loc[~discard].copy()
    if "product_id" in clean:
        clean = clean.drop_duplicates(subset=["product_id"])
        clean["product_id"] = clean["product_id"].astype("int64")
    return clean, {
        "missing_values": missing_values,
        "duplicate_records": duplicate_records,
        "invalid_records": int(invalid.sum()),
        "corrected_records": int(
            ((raw_category.notna()) & (raw_category.astype(str) != clean["category"].reindex(raw_category.index))).sum()
        ),
        "requires_investigation": int((invalid | invalid_ids).sum()),
    }


def clean_customers(customers: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if customers is None or customers.empty:
        return (
            pd.DataFrame() if customers is None else customers.copy(),
            _empty_report(),
        )

    clean = customers.copy()
    missing_values = int(clean.isna().sum().sum())
    if "customer_id" not in clean:
        return clean.iloc[0:0].copy(), {
            **_empty_report(),
            "invalid_records": len(clean),
            "requires_investigation": len(clean),
        }

    invalid_dates = pd.Series(False, index=clean.index)
    if "signup_date" in clean:
        clean["signup_date"] = pd.to_datetime(clean["signup_date"], errors="coerce")
        invalid_dates = clean["signup_date"].isna()
    customer_ids = pd.to_numeric(clean["customer_id"], errors="coerce")
    invalid_ids = customer_ids.isna() | customer_ids.le(0) | customer_ids.mod(1).ne(0)
    clean["customer_id"] = customer_ids
    clean = clean.loc[~invalid_ids].copy()
    clean["customer_id"] = clean["customer_id"].astype("int64")
    duplicate_records = int(clean.duplicated(subset=["customer_id"]).sum())
    clean = clean.drop_duplicates(subset=["customer_id"])

    corrected = 0
    for column in ("customer_name", "email", "city", "state", "country"):
        if column in clean:
            missing_text = clean[column].isna() | clean[column].astype(str).str.strip().eq("")
            corrected += int(missing_text.sum())
            clean.loc[missing_text, column] = "Unknown"
            clean[column] = clean[column].astype(str).str.strip()

    invalid_records = int(invalid_ids.sum()) + int(invalid_dates.sum())
    return clean, {
        "missing_values": missing_values,
        "duplicate_records": duplicate_records,
        "invalid_records": invalid_records,
        "corrected_records": corrected,
        "requires_investigation": int(invalid_ids.sum()) + int(invalid_dates.sum()),
    }


def clean_dataframes(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, object]]:
    cleaned_orders, order_report = clean_orders(orders)
    cleaned_items, item_report = clean_order_items(order_items)
    cleaned_products, product_report = clean_products(products)
    reports = (order_report, item_report, product_report)
    return cleaned_orders, cleaned_items, cleaned_products, {
        "missing_values": sum(report["missing_values"] for report in reports),
        "duplicate_records": sum(report["duplicate_records"] for report in reports),
        "invalid_records": sum(report["invalid_records"] for report in reports),
        "corrected_records": sum(report["corrected_records"] for report in reports),
        "requires_investigation": sum(report["requires_investigation"] for report in reports),
        "warnings": [
            f"{label}: {report['invalid_records']} invalid rows."
            for label, report in zip(("Orders", "Order items", "Products"), reports)
            if report["invalid_records"] or report["requires_investigation"]
        ],
    }
