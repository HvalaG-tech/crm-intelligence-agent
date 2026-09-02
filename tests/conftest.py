"""Shared test fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_orders() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": [f"ord_{i}" for i in range(100)],
        "customer_id": [f"cust_{i % 20}" for i in range(100)],
        "purchase_date": pd.date_range("2023-01-01", periods=100, freq="3D"),
        "order_value": [50.0 + i * 10 for i in range(100)],
        "order_status": ["delivered"] * 100,
        "customer_state": (["SP", "RJ", "MG"] * 34)[:100],
        "product_category_name": (["electronics", "fashion", "home"] * 34)[:100],
    })


@pytest.fixture
def sample_customers(sample_orders) -> pd.DataFrame:
    return (
        sample_orders.groupby("customer_id")
        .agg(
            total_orders=("order_id", "count"),
            total_revenue=("order_value", "sum"),
            avg_order_value=("order_value", "mean"),
            first_purchase=("purchase_date", "min"),
            last_purchase=("purchase_date", "max"),
            customer_state=("customer_state", "first"),
        )
        .reset_index()
    )


@pytest.fixture
def sample_data(sample_orders, sample_customers) -> dict:
    return {"orders_enriched": sample_orders, "customers_enriched": sample_customers}
