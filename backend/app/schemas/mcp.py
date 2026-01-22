"""
MCP 请求/响应模型
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MCPServerStatus(BaseModel):
    running: bool
    error: Optional[str]
    lastChecked: Optional[int]


class MCPServerItem(BaseModel):
    id: str
    name: str
    transport: str
    command: Optional[str]
    args: List[str]
    env: Dict[str, str]
    url: Optional[str]
    scope: str
    isActive: bool
    status: MCPServerStatus


class MCPListResponse(BaseModel):
    servers: List[MCPServerItem]


class MCPTestResponse(BaseModel):
    id: str
    status: str
    detail: Optional[str]


class MCPCreateRequest(BaseModel):
    """创建 MCP 服务器请求"""
    name: str = Field(description="服务器名称", min_length=1)
    transport: str = Field(description="传输协议 (stdio|sse)")
    command: Optional[str] = Field(default=None, description="命令（stdio 必需）")
    args: List[str] = Field(default_factory=list, description="命令参数")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    url: Optional[str] = Field(default=None, description="URL（sse 必需）")
    scope: str = Field(default="local", description="作用域")
    isActive: bool = Field(default=True, description="是否激活")


class MCPUpdateRequest(BaseModel):
    """更新 MCP 服务器请求"""
    name: Optional[str] = Field(default=None, description="服务器名称")
    transport: Optional[str] = Field(default=None, description="传输协议")
    command: Optional[str] = Field(default=None, description="命令")
    args: Optional[List[str]] = Field(default=None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(default=None, description="环境变量")
    url: Optional[str] = Field(default=None, description="URL")
    isActive: Optional[bool] = Field(default=None, description="是否激活")


class MCPStartResponse(BaseModel):
    """启动 MCP 服务器响应"""
    id: str = Field(description="服务器 ID")
    status: str = Field(description="状态 (started|already_running)")
    pid: Optional[int] = Field(default=None, description="进程 ID")


class MCPStopResponse(BaseModel):
    """停止 MCP 服务器响应"""
    id: str = Field(description="服务器 ID")
    status: str = Field(description="状态 (stopped|not_running)")
