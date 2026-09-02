"""Tool: get_data_summary — dataset overview."""

from typing import Any

import pandas as pd

from tools.base import BaseTool


class SummaryTool(BaseTool):
    name = "get_data_summary"
    description = (
        "Return a high-level overview of the CRM dataset: row counts, date range, "
        "key metrics, and available columns. Use when the user asks what data is available "
        "or wants a general overview before running an analysis."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._orders = data["orders_enriched"]
        self._customers = data["customers_enriched"]

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }

    def run(self) -> tuple[str, Any]:
        orders = self._orders
        customers = self._customers

        date_min = orders["purchase_date"].min()
        date_max = orders["purchase_date"].max()
        orders_dedup = orders.drop_duplicates("order_id")
        total_revenue = orders_dedup["order_value"].sum()
        avg_order = orders_dedup["order_value"].mean()
        top_states = orders["customer_state"].value_counts().head(5).to_dict()

        lines = [
            f"Dataset: Olist Brazilian E-Commerce",
            f"Period: {date_min.date()} → {date_max.date()}",
            f"Orders: {orders['order_id'].nunique():,}",
            f"Customers: {customers['customer_id'].nunique():,}",
            f"Total revenue: R$ {total_revenue:,.0f}",
            f"Average order value: R$ {avg_order:,.2f}",
            f"Top 5 states by orders: {top_states}",
            f"\norders_enriched columns: {', '.join(orders.columns.tolist())}",
            f"customers_enriched columns: {', '.join(customers.columns.tolist())}",
        ]
        return "\n".join(lines), None
