"""Customer Lifetime Value estimation (simplified historical CLV)."""

import pandas as pd


def compute_clv(customers: pd.DataFrame) -> pd.DataFrame:
    """Estimate CLV using a simple historical model: avg_order_value × frequency × tenure_factor.

    Args:
        customers: customers_enriched DataFrame.

    Returns:
        DataFrame with additional column: clv_estimated.
    """
    df = customers.copy()

    # Tenure in months (min 1 to avoid division by zero)
    tenure_months = ((df["last_purchase"] - df["first_purchase"]).dt.days / 30).clip(lower=1)

    # Monthly purchase rate
    monthly_rate = df["total_orders"] / tenure_months

    # Projected 12-month CLV
    df["clv_estimated"] = monthly_rate * df["avg_order_value"] * 12

    return df.sort_values("clv_estimated", ascending=False)


def format_clv_summary(clv_df: pd.DataFrame, top_n: int = 15) -> str:
    total_clv = clv_df["clv_estimated"].sum()
    top = clv_df.head(top_n)[["customer_id", "clv_estimated", "total_revenue", "total_orders"]]
    top_pct = top["clv_estimated"].sum() / total_clv * 100

    lines = [
        f"CLV Analysis — {len(clv_df):,} customers:",
        f"  Total projected 12-month CLV: R$ {total_clv:,.0f}",
        f"  Top {top_n} customers represent {top_pct:.1f}% of total CLV",
        f"\nTop {top_n} customers by CLV:",
        top.to_string(index=False, float_format=lambda x: f"{x:,.0f}"),
    ]
    return "\n".join(lines)
