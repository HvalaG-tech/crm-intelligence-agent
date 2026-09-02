"""Tool: run_kmeans — behavioral customer clustering."""

from typing import Any

import pandas as pd

from analytics.segmentation import kmeans_segments, format_segment_summary
from analytics.plots import plot_segments_scatter
from tools.base import BaseTool


class SegmentationTool(BaseTool):
    name = "run_kmeans"
    description = (
        "Cluster customers into behavioral groups using KMeans on purchase features. "
        "Use for questions about customer profiles, behavioral groups, or persona discovery. "
        "Do NOT use when the user explicitly asks for RFM segmentation."
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
                        "n_clusters": {
                            "type": "integer",
                            "description": "Number of clusters. Default 4. Max 8.",
                            "default": 4,
                        },
                    },
                    "required": [],
                },
            },
        }

    def run(self, n_clusters: int = 4) -> tuple[str, Any]:
        segmented = kmeans_segments(self._customers, n_clusters=n_clusters)
        fig = plot_segments_scatter(segmented)
        summary = format_segment_summary(segmented)
        return summary, fig
