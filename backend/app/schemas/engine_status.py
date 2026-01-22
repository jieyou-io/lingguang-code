"""
引擎状态相关的数据模型
"""
from typing import Literal
from pydantic import BaseModel, Field


class EngineStatusResponse(BaseModel):
    """引擎状态响应模型"""

    name: str = Field(..., description="引擎名称（展示名称）")
    engine: Literal["claude", "codex", "gemini"] = Field(..., description="引擎标识符")
    status: Literal["online", "offline", "degraded"] = Field(
        ..., description="引擎状态：online(正常), offline(离线), degraded(延迟)"
    )
    latency: int = Field(..., description="延迟时间（毫秒）", ge=0)
    message: str = Field(default="", description="状态消息（如错误信息）")


class EngineStatusListResponse(BaseModel):
    """引擎状态列表响应模型"""

    engines: list[EngineStatusResponse] = Field(..., description="引擎状态列表")
