"""Tool: sql_query — read-only SQL on the CRM dataset via DuckDB."""

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from analytics.plots import auto_bar_chart
from tools.base import BaseTool

SCHEMA_PATH = Path("data/processed/schema.json")
FORBIDDEN_PREFIXES = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE")


class SQLTool(BaseTool):
    name = "sql_query"
    description = (
        "Run a read-only SQL SELECT query on the CRM dataset (DuckDB dialect). "
        "Use for ad-hoc counts, sums, aggregations, and breakdowns not covered by other tools. "
        "Tables available: orders_enriched, customers_enriched."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._conn = duckdb.connect()
        for table_name, df in data.items():
            if isinstance(df, pd.DataFrame):
                self._conn.register(table_name, df)

        schema_text = ""
        if SCHEMA_PATH.exists():
            schema = json.loads(SCHEMA_PATH.read_text())
            lines = ["Available tables and columns:"]
            for tbl, cols in schema.items():
                lines.append(f"\n{tbl}:")
                for col, dtype in cols.items():
                    lines.append(f"  - {col} ({dtype})")
            schema_text = "\n".join(lines)
        self._schema_text = schema_text

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description + (
                    f"\n\nSchema reference:\n{self._schema_text}" if self._schema_text else ""
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A valid DuckDB SELECT statement.",
                        }
                    },
                    "required": ["query"],
                },
            },
        }

    def run(self, query: str) -> tuple[str, Any]:
        normalized = query.strip().upper()
        if any(normalized.startswith(kw) for kw in FORBIDDEN_PREFIXES):
            return "Error: only SELECT queries are allowed.", None

        try:
            result = self._conn.execute(query).df()
        except Exception as exc:
            return f"Error: SQL execution failed — {exc}", None

        if result.empty:
            return "The query returned no results.", None

        row_count = len(result)
        display = result.head(50)
        summary = f"Query returned {row_count} rows.\n\n{display.to_string(index=False)}"

        fig = None
        if 2 <= len(result.columns) <= 3 and row_count <= 30:
            fig = auto_bar_chart(result)

        return summary, fig
