"""BaseTool ABC — all tools must implement this interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str
    description: str

    @property
    @abstractmethod
    def schema(self) -> dict:
        """Return the OpenAI function-calling schema dict."""
        ...

    @abstractmethod
    def run(self, **kwargs) -> tuple[str, Any]:
        """Execute the tool. Returns (summary_string_under_2000_chars, plotly_figure_or_None)."""
        ...
