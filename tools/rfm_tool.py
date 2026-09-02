"""Tool: compute_rfm — RFM segmentation."""

from typing import Any

import pandas as pd

from analytics.plots import plot_rfm_scatter
from analytics.rfm import compute_rfm, format_rfm_summary
from tools.base import BaseTool


class RFMTool(BaseTool):
    name = "compute_rfm"
    description = (
        "Compute RFM (Recency, Frequency, Monetary) scores and segment customers. "
        "Use for questions about best customers, customer value tiers, or segmentation by purchase behaviour. "
        "Do NOT use for product analysis or revenue breakdowns."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._orders = data["orders_enriched"]

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
                        "n_segments": {
                            "type": "integer",
                            "description": "Number of RFM quantile bins (3, 4, or 5). Default 4.",
                            "default": 4,
                        },
                        "reference_date": {
                            "type": "string",
                            "description": "ISO date string for recency anchor. Defaults to dataset max date.",
                        },
                    },
                    "required": [],
                },
            },
        }

    def run(self, n_segments: int = 4, reference_date: str | None = None) -> tuple[str, Any]:
        rfm = compute_rfm(self._orders, n_segments=n_segments, reference_date=reference_date)
        fig = plot_rfm_scatter(rfm)
        summary = format_rfm_summary(rfm)
        return summary, fig
