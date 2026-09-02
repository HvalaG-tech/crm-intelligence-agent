"""Tests for tools/sql_tool.py."""

from tools.sql_tool import SQLTool


def test_sql_select(sample_data):
    tool = SQLTool(sample_data)
    result, fig = tool.run("SELECT COUNT(*) AS n FROM orders_enriched")
    assert "100" in result


def test_sql_blocks_insert(sample_data):
    tool = SQLTool(sample_data)
    result, fig = tool.run("INSERT INTO orders_enriched VALUES (1)")
    assert result.startswith("Error:")


def test_sql_invalid_query(sample_data):
    tool = SQLTool(sample_data)
    result, fig = tool.run("SELECT nonexistent_column FROM orders_enriched")
    assert result.startswith("Error:")
