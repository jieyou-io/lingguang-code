"""
Provider 配置管理相关的 Pydantic 模型
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ProviderConfigResponse(BaseModel):
    """Provider 配置响应"""
    engine: str = Field(description="引擎名称")
    config: Dict[str, Any] = Field(description="配置数据")


class ProviderConfigUpdateRequest(BaseModel):
    """Provider 配置更新请求"""
    apiKey: Optional[str] = Field(default=None, description="API Key")
    baseUrl: Optional[str] = Field(default=None, description="API Base URL")
    enabled: Optional[bool] = Field(default=None, description="是否启用")
    model: Optional[str] = Field(default=None, description="默认模型")
    temperature: Optional[float] = Field(default=None, description="温度参数")


class ProviderPresetResponse(BaseModel):
    """Provider 预设响应"""
    id: str = Field(description="预设 ID")
    name: str = Field(description="预设名称")
    description: Optional[str] = Field(default=None, description="预设描述")
    config: Dict[str, Any] = Field(description="完整配置数据")


class ProviderPresetCreateRequest(BaseModel):
    """Provider 预设创建/更新请求"""
    id: str = Field(description="预设 ID")
    name: str = Field(description="预设名称")
    description: Optional[str] = Field(default=None, description="预设描述")
    config: Dict[str, Any] = Field(description="完整配置数据")
