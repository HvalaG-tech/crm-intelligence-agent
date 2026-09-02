"""Tool: compute_clv — Customer Lifetime Value estimation."""

from typing import Any

import pandas as pd

from analytics.clv import compute_clv, format_clv_summary
from analytics.plots import plot_clv_bar
from tools.base import BaseTool


class CLVTool(BaseTool):
    name = "compute_clv"
    description = (
        "Estimate Customer Lifetime Value (CLV) and rank customers by long-term revenue potential. "
        "Use for questions about best ROI customers, who to invest in, or long-term value ranking."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._customers = data["customers_enriched"]

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "top_n": {
                            "type": "integer",
                            "description": "Number of top-value customers to display. Default 15.",
                            "default": 15,
                        }
                    },
                    "required": [],
                },
            },
        }

    def run(self, top_n: int = 15) -> tuple[str, Any]:
        clv_df = compute_clv(self._customers)
        fig = plot_clv_bar(clv_df, top_n=top_n)
        summary = format_clv_summary(clv_df, top_n=top_n)
        return summary, fig
