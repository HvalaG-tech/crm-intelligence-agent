"""KMeans customer segmentation."""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


FEATURES = ["total_orders", "total_revenue", "avg_order_value"]


def kmeans_segments(customers: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    """Cluster customers using KMeans on purchase features.

    Args:
        customers: customers_enriched DataFrame.
        n_clusters: Number of clusters. Clamped to [2, 8].

    Returns:
        DataFrame with additional columns: cluster (int), cluster_label (str).
    """
    n_clusters = max(2, min(8, n_clusters))
    df = customers.copy()
    X = df[FEATURES].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X_scaled)

    # Label clusters by average revenue (descending)
    cluster_revenue = df.groupby("cluster")["total_revenue"].mean().rank(ascending=False).astype(int)
    df["cluster_label"] = df["cluster"].map(
        lambda c: f"Segment {cluster_revenue[c]}"
    )

    return df


def format_segment_summary(segmented: pd.DataFrame) -> str:
    summary = (
        segmented.groupby("cluster_label")
        .agg(
            customers=("customer_id", "count"),
            avg_revenue=("total_revenue", "mean"),
            avg_orders=("total_orders", "mean"),
            avg_order_value=("avg_order_value", "mean"),
        )
        .sort_values("avg_revenue", ascending=False)
    )
    lines = [f"KMeans Segmentation — {len(segmented):,} customers, {summary.shape[0]} clusters:"]
    for seg, row in summary.iterrows():
        lines.append(
            f"  {seg}: {row['customers']:,} customers | "
            f"avg revenue R$ {row['avg_revenue']:,.0f} | "
            f"avg orders {row['avg_orders']:.1f} | "
            f"avg basket R$ {row['avg_order_value']:,.0f}"
        )
    return "\n".join(lines)
