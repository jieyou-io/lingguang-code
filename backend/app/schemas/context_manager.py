"""
上下文管理请求/响应模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class ContextConfigResponse(BaseModel):
    enabled: bool
    maxContextTokens: int
    compactionThreshold: float
    minCompactionInterval: int
    compactionStrategy: str
    preserveRecentMessages: bool
    preserveMessageCount: int
    customInstructions: Optional[str]


class ContextCompactRequest(BaseModel):
    sessionId: str = Field(..., description="会话 ID")


class ContextCompactResponse(BaseModel):
    sessionId: str
    status: str
    summary: Optional[str]
