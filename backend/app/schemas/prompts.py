"""
Prompt 配置管理相关的 Pydantic 模型
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PromptItemResponse(BaseModel):
    """单个 Prompt 项响应"""
    id: str = Field(description="Prompt ID")
    name: str = Field(description="Prompt 名称")
    content: str = Field(description="Prompt 内容")
    enabled: bool = Field(default=True, description="是否启用")


class PromptListResponse(BaseModel):
    """Prompt 列表响应"""
    engine: str = Field(description="引擎名称")
    prompts: list[PromptItemResponse] = Field(description="Prompt 列表")


class PromptConfigResponse(BaseModel):
    """完整 Prompt 配置响应"""
    engine: str = Field(description="引擎名称")
    config: Dict[str, Any] = Field(description="完整配置数据")


class PromptCreateRequest(BaseModel):
    """创建 Prompt 请求"""
    id: str = Field(description="Prompt ID", min_length=1, max_length=100)
    name: str = Field(description="Prompt 名称", min_length=1)
    content: str = Field(description="Prompt 内容", min_length=1)
    enabled: bool = Field(default=True, description="是否启用")


class PromptUpdateRequest(BaseModel):
    """更新 Prompt 请求"""
    name: Optional[str] = Field(default=None, description="Prompt 名称")
    content: Optional[str] = Field(default=None, description="Prompt 内容")
    enabled: Optional[bool] = Field(default=None, description="是否启用")
