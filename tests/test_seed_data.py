import pandas as pd

from database.seed_data import generate_demo_dataframes


def test_generated_demo_data_has_expected_scale_and_is_reproducible():
    first = generate_demo_dataframes()
    second = generate_demo_dataframes()
    orders, items, products, customers = first
    assert len(customers) == 500
    assert len(products) == 100
    assert len(orders) == 2000
    assert 4000 <= len(items) <= 6000
    for left, right in zip(first, second):
        pd.testing.assert_frame_equal(left, right)
