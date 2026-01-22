"""
Gemini 请求/响应模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class GeminiExecuteRequest(BaseModel):
    projectPath: str = Field(..., description="项目路径")
    prompt: str = Field(..., description="提示词")
    model: str = Field(default="gemini-3-flash", description="模型名称")
    approvalMode: str = Field(default="auto_edit", description="审批模式")
    includeDirectories: List[str] = Field(default_factory=list, description="包含目录")
    sessionId: Optional[str] = Field(default=None, description="会话 ID")
    debug: bool = Field(default=False, description="调试模式")


class GeminiCancelRequest(BaseModel):
    sessionId: Optional[str] = Field(default=None, description="会话 ID")


class GeminiSessionResponse(BaseModel):
    sessionId: Optional[str] = Field(default=None, description="会话 ID")
    status: str = Field(..., description="状态")
