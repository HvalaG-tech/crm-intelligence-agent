"""KPI cards displayed at the top of the page."""

import pandas as pd
import streamlit as st


def render_kpi_cards(data: dict[str, pd.DataFrame]) -> None:
    """Render 4 high-level KPI cards."""
    orders = data["orders_enriched"]
    customers = data["customers_enriched"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Customers", f"{customers['customer_id'].nunique():,}")
    with col2:
        st.metric("Total Orders", f"{orders['order_id'].nunique():,}")
    with col3:
        total_rev = orders.drop_duplicates("order_id")["order_value"].sum()
        st.metric("Total Revenue", f"R$ {total_rev:,.0f}")
    with col4:
        avg_order = orders.drop_duplicates("order_id")["order_value"].mean()
        st.metric("Avg Order Value", f"R$ {avg_order:,.2f}")
