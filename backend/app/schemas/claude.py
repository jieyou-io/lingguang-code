"""
Claude 请求/响应模型
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ClaudeExecuteRequest(BaseModel):
    projectPath: str = Field(..., description="项目路径")
    prompt: str = Field(..., description="提示词")
    model: str = Field(..., description="模型名称")
    planMode: bool = Field(default=False, description="是否启用计划模式")
    maxThinkingTokens: Optional[int] = Field(default=None, description="最大思考 token 数")
    tabId: Optional[str] = Field(default=None, description="前端 Tab ID")
    sessionId: Optional[str] = Field(default=None, description="历史会话 ID（用于 --resume 恢复指定对话）")


class ClaudeResumeRequest(BaseModel):
    projectPath: str = Field(..., description="项目路径")
    sessionId: str = Field(..., description="会话 ID")
    prompt: str = Field(..., description="提示词")
    model: str = Field(..., description="模型名称")
    planMode: bool = Field(default=False, description="是否启用计划模式")
    maxThinkingTokens: Optional[int] = Field(default=None, description="最大思考 token 数")
    tabId: Optional[str] = Field(default=None, description="前端 Tab ID")


class ClaudeCancelRequest(BaseModel):
    sessionId: str = Field(..., description="会话 ID")


class ClaudeSessionResponse(BaseModel):
    sessionId: str = Field(..., description="会话 ID")
    status: str = Field(..., description="状态")


class ClaudePermissionResponse(BaseModel):
    """权限响应请求"""
    sessionId: str = Field(..., description="会话 ID")
    response: Literal["y", "n"] = Field(..., description="用户响应: y=授权, n=拒绝")
