"""
Subagents 管理相关的 Pydantic 模型
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Agent 元数据"""
    enabled: bool = Field(default=True, description="是否启用")
    name: Optional[str] = Field(default=None, description="Agent 名称")
    tools: Optional[list] = Field(default=None, description="可用工具列表")


class AgentResponse(BaseModel):
    """Agent 响应模型"""
    id: str = Field(description="Agent ID")
    path: str = Field(description="Agent 文件路径")
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")
    enabled: bool = Field(description="是否启用")


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    agents: list[AgentResponse] = Field(description="Agent 列表")


class AgentCreateRequest(BaseModel):
    """创建 Agent 请求"""
    id: str = Field(description="Agent ID", min_length=1, max_length=100)
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")


class AgentUpdateRequest(BaseModel):
    """更新 Agent 请求"""
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")
