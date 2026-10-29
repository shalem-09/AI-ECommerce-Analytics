from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics.kpi_calculations import compute_kpis
from database.seed_data import generate_demo_dataframes


def validate():
    orders, items, products, customers = generate_demo_dataframes()
    result = compute_kpis(orders, items, products)
    required = [
        'gross_merchandise_value',
        'net_merchandise_sales',
        'estimated_product_cost',
        'estimated_gross_profit',
        'completed_orders',
        'units_sold',
        'average_order_value',
        'month_over_month_growth',
        'repeat_customer_rate',
        'cancellation_rate',
        'return_rate',
    ]
    missing = [name for name in required if name not in result]
    if missing:
        raise RuntimeError(f'Missing KPI keys: {missing}')
    print('Validation OK')


if __name__ == '__main__':
    validate()
    sys.exit(0)
