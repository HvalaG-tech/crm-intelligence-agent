"""Tool factory — returns all tools initialised with the data registry."""

import pandas as pd

from tools.rfm_tool import RFMTool
from tools.churn_tool import ChurnTool
from tools.segmentation_tool import SegmentationTool
from tools.sql_tool import SQLTool
from tools.summary_tool import SummaryTool
from tools.clv_tool import CLVTool
from tools.capabilities_tool import CapabilitiesTool


def get_all_tools(data: dict[str, pd.DataFrame]) -> list:
    return [
        RFMTool(data),
        ChurnTool(data),
        SegmentationTool(data),
        SQLTool(data),
        SummaryTool(data),
        CLVTool(data),
        CapabilitiesTool(),
    ]
