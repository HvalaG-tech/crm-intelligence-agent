"""All Plotly figure builders for CRM analytics."""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PALETTE = px.colors.qualitative.Plotly


def plot_rfm_scatter(rfm: pd.DataFrame) -> go.Figure:
    """Scatter: Recency vs Monetary, size=frequency, color=segment."""
    fig = px.scatter(
        rfm,
        x="recency_days",
        y="monetary",
        size="frequency",
        color="segment",
        hover_data=["customer_id", "rfm_score"],
        title="RFM Customer Segmentation",
        labels={"recency_days": "Recency (days)", "monetary": "Total Revenue (R$)"},
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(legend_title="Segment")
    return fig


def plot_churn_risk(scored: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Horizontal bar chart: top N customers by churn score."""
    top = scored.head(top_n).copy()
    top["label"] = top["customer_id"].astype(str).str[:12] + "…"

    fig = px.bar(
        top,
        x="churn_score",
        y="label",
        orientation="h",
        color="churn_score",
        color_continuous_scale="RdYlGn_r",
        title=f"Top {top_n} Customers by Churn Risk",
        labels={"churn_score": "Churn Probability", "label": "Customer"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    return fig


def plot_segments_scatter(segmented: pd.DataFrame) -> go.Figure:
    """Scatter: total_orders vs total_revenue, color=cluster_label."""
    fig = px.scatter(
        segmented,
        x="total_orders",
        y="total_revenue",
        color="cluster_label",
        hover_data=["customer_id", "avg_order_value"],
        title="Customer Behavioral Segments (KMeans)",
        labels={"total_orders": "Number of Orders", "total_revenue": "Total Revenue (R$)"},
        color_discrete_sequence=PALETTE,
    )
    return fig


def plot_clv_bar(clv_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Horizontal bar: top N customers by estimated CLV."""
    top = clv_df.head(top_n).copy()
    top["label"] = top["customer_id"].astype(str).str[:12] + "…"

    fig = px.bar(
        top,
        x="clv_estimated",
        y="label",
        orientation="h",
        title=f"Top {top_n} Customers by Estimated 12-Month CLV",
        labels={"clv_estimated": "CLV Estimate (R$)", "label": "Customer"},
        color="clv_estimated",
        color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    return fig


def auto_bar_chart(df: pd.DataFrame) -> go.Figure | None:
    """Heuristic: generate a bar chart if the DataFrame has 2 columns (label + value)."""
    if len(df.columns) < 2:
        return None
    try:
        label_col = df.columns[0]
        value_col = df.columns[1]
        fig = px.bar(
            df,
            x=label_col,
            y=value_col,
            title=f"{value_col} by {label_col}",
        )
        fig.update_layout(xaxis_tickangle=-30)
        return fig
    except Exception:
        return None
