"""Tool: predict_churn — churn risk scoring."""

from pathlib import Path
from typing import Any

import pandas as pd

from analytics.churn import ChurnModel, format_churn_summary
from analytics.plots import plot_churn_risk
from tools.base import BaseTool

MODEL_PATH = Path("models/churn_model.pkl")


class ChurnTool(BaseTool):
    name = "predict_churn"
    description = (
        "Predict churn risk for customers and rank them by probability of leaving. "
        "Use for questions about at-risk customers, inactive clients, or churn prevention. "
        "Returns a ranked list of high-risk customers with their churn score."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._customers = data["customers_enriched"]
        self._model = ChurnModel()

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
                            "description": "Number of highest-risk customers to return. Default 20.",
                            "default": 20,
                        },
                        "inactivity_days": {
                            "type": "integer",
                            "description": "Days without purchase to label as churned (for model training). Default 180.",
                            "default": 180,
                        },
                    },
                    "required": [],
                },
            },
        }

    def run(self, top_n: int = 20, inactivity_days: int = 180) -> tuple[str, Any]:
        scored = self._model.score(self._customers, inactivity_days=inactivity_days)
        fig = plot_churn_risk(scored, top_n=top_n)
        summary = format_churn_summary(scored, top_n=top_n)
        return summary, fig
