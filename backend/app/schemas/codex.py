"""
Codex 请求/响应模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class CodexExecuteRequest(BaseModel):
    projectPath: str = Field(..., description="项目路径")
    prompt: str = Field(..., description="提示词")
    mode: str = Field(default="read-only", description="执行模式")
    model: Optional[str] = Field(default=None, description="模型名称")
    json: bool = Field(default=True, description="是否输出 JSON")
    outputSchema: Optional[str] = Field(default=None, description="输出 Schema")
    outputFile: Optional[str] = Field(default=None, description="输出文件路径")
    skipGitRepoCheck: bool = Field(default=False, description="跳过 Git 仓库检查")
    apiKey: Optional[str] = Field(default=None, description="API Key")
    sessionId: Optional[str] = Field(default=None, description="会话 ID")
    resumeLast: bool = Field(default=False, description="恢复上一次会话")


class CodexResumeRequest(BaseModel):
    sessionId: str = Field(..., description="会话 ID")
    projectPath: str = Field(..., description="项目路径")
    prompt: str = Field(..., description="提示词")
    mode: str = Field(default="read-only", description="执行模式")
    model: Optional[str] = Field(default=None, description="模型名称")
    json: bool = Field(default=True, description="是否输出 JSON")
    outputSchema: Optional[str] = Field(default=None, description="输出 Schema")
    outputFile: Optional[str] = Field(default=None, description="输出文件路径")
    skipGitRepoCheck: bool = Field(default=False, description="跳过 Git 仓库检查")
    apiKey: Optional[str] = Field(default=None, description="API Key")
    resumeLast: bool = Field(default=False, description="恢复上一次会话")


class CodexCancelRequest(BaseModel):
    sessionId: str = Field(..., description="会话 ID")


class CodexSessionResponse(BaseModel):
    sessionId: str = Field(..., description="会话 ID")
    status: str = Field(..., description="状态")
