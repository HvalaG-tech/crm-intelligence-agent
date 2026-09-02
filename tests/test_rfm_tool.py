"""Integration test: RFMTool returns (str, Figure)."""

from tools.rfm_tool import RFMTool


def test_rfm_tool_returns_summary_and_figure(sample_data):
    tool = RFMTool(sample_data)
    summary, fig = tool.run(n_segments=3)
    assert isinstance(summary, str)
    assert len(summary) <= 2000
    assert fig is not None
