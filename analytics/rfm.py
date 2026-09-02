"""RFM analysis — pure pandas, no external dependencies beyond numpy."""

import numpy as np
import pandas as pd


def compute_rfm(
    orders: pd.DataFrame,
    n_segments: int = 4,
    reference_date: str | None = None,
) -> pd.DataFrame:
    """Compute RFM scores and segment labels for all customers.

    Args:
        orders: orders_enriched DataFrame with columns [customer_id, purchase_date, order_value].
        n_segments: Number of quantile bins per RFM dimension. Must be 3-5.
        reference_date: ISO date string for recency anchor. Defaults to dataset max purchase_date.

    Returns:
        DataFrame with columns [customer_id, recency_days, frequency, monetary,
        r_score, f_score, m_score, rfm_score, segment].
    """
    if n_segments not in (3, 4, 5):
        raise ValueError("n_segments must be 3, 4, or 5")

    ref = pd.to_datetime(reference_date) if reference_date else orders["purchase_date"].max()

    # Une ligne par commande : `orders_enriched` est au grain article, et
    # `order_value` est un montant par commande.
    orders_dedup = orders.drop_duplicates("order_id")[
        ["customer_uid", "purchase_date", "order_value"]
    ]

    # Grouper sur `customer_uid`, jamais sur `customer_id` : chez Olist,
    # `customer_id` est réattribué à chaque commande, si bien qu'un groupement
    # dessus fait de chaque commande un client distinct. La fréquence vaudrait
    # alors 1 pour tout le monde et la dimension F de la RFM ne mesurerait rien.
    rfm = (
        orders_dedup.groupby("customer_uid")
        .agg(
            recency_days=("purchase_date", lambda x: (ref - x.max()).days),
            frequency=("purchase_date", "count"),
            monetary=("order_value", "sum"),
        )
        .reset_index()
        .rename(columns={"customer_uid": "customer_id"})
    )

    # Score: recency is inverted (lower days = better = higher score)
    rfm["r_score"] = pd.qcut(rfm["recency_days"], q=n_segments, labels=range(n_segments, 0, -1), duplicates="drop").astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=n_segments, labels=range(1, n_segments + 1), duplicates="drop").astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"], q=n_segments, labels=range(1, n_segments + 1), duplicates="drop").astype(int)

    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    max_score = n_segments * 3
    rfm["segment"] = rfm.apply(
        lambda row: _label_segment(row["rfm_score"], row["r_score"], max_score, n_segments),
        axis=1,
    )

    return rfm


def _label_segment(score: int, r_score: int, max_score: int, n_segments: int) -> str:
    ratio = score / max_score
    # Champions require high recency AND high overall score
    if ratio >= 0.75 and r_score >= n_segments - 1:
        return "Champions"
    elif ratio >= 0.55:
        return "Loyal Customers"
    elif ratio >= 0.35 or r_score >= n_segments - 1:
        return "At Risk"
    else:
        return "Lost"


def format_rfm_summary(rfm: pd.DataFrame) -> str:
    seg_counts = rfm["segment"].value_counts()
    seg_revenue = rfm.groupby("segment")["monetary"].sum().sort_values(ascending=False)
    lines = [f"RFM Analysis — {len(rfm):,} customers total:"]
    for seg in seg_revenue.index:
        pct = seg_counts.get(seg, 0) / len(rfm) * 100
        lines.append(
            f"  {seg}: {seg_counts.get(seg, 0):,} customers ({pct:.1f}%), "
            f"revenue R$ {seg_revenue[seg]:,.0f}"
        )
    avg_recency = rfm["recency_days"].mean()
    lines.append(f"Average recency: {avg_recency:.0f} days since last purchase")
    return "\n".join(lines)
