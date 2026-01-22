"""
使用统计请求/响应模型

"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ModelUsage(BaseModel):
    """按模型统计"""
    model: str = Field(description="模型名称")
    total_cost: float = Field(description="总成本")
    total_tokens: int = Field(description="总 Token 数")
    input_tokens: int = Field(description="输入 Token 数")
    output_tokens: int = Field(description="输出 Token 数")
    cache_creation_tokens: int = Field(description="缓存创建 Token 数")
    cache_read_tokens: int = Field(description="缓存读取 Token 数")
    session_count: int = Field(description="会话数量")


class DailyUsage(BaseModel):
    """按日期统计"""
    date: str = Field(description="日期 (YYYY-MM-DD)")
    total_cost: float = Field(description="总成本")
    total_tokens: int = Field(description="总 Token 数")
    models_used: List[str] = Field(description="使用的模型列表")


class ProjectUsage(BaseModel):
    """按项目统计"""
    project_path: str = Field(description="项目路径")
    project_name: str = Field(description="项目名称")
    total_cost: float = Field(description="总成本")
    total_tokens: int = Field(description="总 Token 数")
    session_count: int = Field(description="会话数量")
    last_used: str = Field(description="最后使用时间")


class UsageStatsResponse(BaseModel):
    """使用统计响应 - 与原项目格式完全一致"""
    total_cost: float = Field(description="总成本")
    total_tokens: int = Field(description="总 Token 数")
    total_input_tokens: int = Field(description="总输入 Token 数")
    total_output_tokens: int = Field(description="总输出 Token 数")
    total_cache_creation_tokens: int = Field(description="总缓存创建 Token 数")
    total_cache_read_tokens: int = Field(description="总缓存读取 Token 数")
    total_sessions: int = Field(description="总会话数")
    by_model: List[ModelUsage] = Field(description="按模型统计")
    by_date: List[DailyUsage] = Field(description="按日期统计")
    by_project: List[ProjectUsage] = Field(description="按项目统计")
    by_engine: dict = Field(description="按引擎统计 (claude, codex, gemini)", default_factory=dict)
