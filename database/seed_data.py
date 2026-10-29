from __future__ import annotations

import numpy as np
import pandas as pd


def generate_demo_dataframes() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = pd.date_range(start="2023-01-01", end="2024-12-31", freq="D")
    np_rng = np.random.default_rng(42)

    customers = []
    for i in range(1, 501):
        customer_name = f"Customer {i}"
        customers.append(
            {
                "customer_id": i,
                "customer_name": customer_name,
                "email": f"customer{i}@demo.local",
                "city": f"City {i % 25}",
                "state": ["California", "New York", "Texas", "Florida", "Illinois"][i % 5],
                "country": "USA",
                "signup_date": pd.Timestamp("2022-01-01") + pd.Timedelta(days=i * 3),
            }
        )
    customers_df = pd.DataFrame(customers)

    categories = {
        "Electronics": {"unit_cost_base": 120, "unit_price_base": 220},
        "Home": {"unit_cost_base": 70, "unit_price_base": 130},
        "Fashion": {"unit_cost_base": 30, "unit_price_base": 80},
        "Beauty": {"unit_cost_base": 25, "unit_price_base": 60},
        "Sports": {"unit_cost_base": 40, "unit_price_base": 95},
        "Books": {"unit_cost_base": 12, "unit_price_base": 28},
    }
    products = []
    product_id = 1
    for category_index, (category, meta) in enumerate(categories.items()):
        item_count = 17 if category_index < 4 else 16
        for j in range(1, item_count + 1):
            price = meta["unit_price_base"] + (j * 6)
            cost = meta["unit_cost_base"] + (j * 2)
            products.append(
                {
                    "product_id": product_id,
                    "product_name": f"{category} Item {j}",
                    "category": category,
                    "unit_cost": round(cost, 2),
                    "unit_price": round(price, 2),
                    "stock_quantity": 200 + (j * 10),
                }
            )
            product_id += 1
    products_df = pd.DataFrame(products)

    orders = []
    order_id = 1
    order_items = []
    item_id = 1
    for idx in range(1, 2001):
        cust_id = (idx % 500) + 1
        order_date = pd.to_datetime(rng[idx % len(rng)] + pd.Timedelta(days=(idx * 3) % 20))
        status = ["Completed", "Cancelled", "Returned", "Shipped", "Pending"][idx % 5]
        payment = ["Card", "UPI", "Wallet", "Net Banking"][idx % 4]
        city = f"City {idx % 20}"
        state = ["California", "New York", "Texas", "Florida", "Illinois"][(idx // 5) % 5]
        orders.append(
            {
                "order_id": order_id,
                "customer_id": cust_id,
                "order_date": order_date,
                "order_status": status,
                "payment_method": payment,
                "shipping_city": city,
                "shipping_state": state,
            }
        )
        item_count = 1 + (idx % 4)
        for _ in range(item_count):
            product = products_df.iloc[(idx + _) % len(products_df)]
            quantity = 1 + int(np_rng.integers(1, 6))
            discount = float(np_rng.integers(0, 25)) / 100
            unit_price = float(product["unit_price"])
            order_items.append(
                {
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "product_id": int(product["product_id"]),
                    "quantity": quantity,
                    "unit_price": round(unit_price, 2),
                    "discount_percent": round(discount * 100, 2),
                }
            )
            item_id += 1
        order_id += 1

    orders_df = pd.DataFrame(orders)
    order_items_df = pd.DataFrame(order_items)
    return orders_df, order_items_df, products_df, customers_df
