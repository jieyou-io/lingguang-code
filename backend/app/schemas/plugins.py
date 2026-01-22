"""
Plugins 管理相关的 Pydantic 模型
"""
from pydantic import BaseModel, Field


class PluginResponse(BaseModel):
    """Plugin 响应模型"""
    id: str = Field(description="Plugin ID")
    path: str = Field(description="Plugin 目录路径")
    enabled: bool = Field(description="是否启用")


class PluginListResponse(BaseModel):
    """Plugin 列表响应"""
    plugins: list[PluginResponse] = Field(description="Plugin 列表")


class PluginInstallRequest(BaseModel):
    """安装 Plugin 请求"""
    plugin_ref: str = Field(description="插件引用（名称、URL 等）", min_length=1)


class PluginInstallResponse(BaseModel):
    """安装 Plugin 响应"""
    id: str = Field(description="插件 ID")
    installed: bool = Field(description="是否安装成功")
