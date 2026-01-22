"""
快速统计响应模型
"""
from pydantic import BaseModel, Field


class QuickStatsItem(BaseModel):
    """快速统计单项数据"""
    tokens: int = Field(description="Token 数量", ge=0)
    cost: float = Field(description="成本", ge=0.0)
    sessions: int = Field(description="会话数量", ge=0)


class QuickStatsResponse(BaseModel):
    """快速统计响应 - 专为会话页面和项目页面设计"""
    today: QuickStatsItem = Field(description="今日统计")
    week: QuickStatsItem = Field(description="本周统计")
    month: QuickStatsItem = Field(description="本月统计")
