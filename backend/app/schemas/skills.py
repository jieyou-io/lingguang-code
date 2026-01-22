"""
Skills 管理相关的 Pydantic 模型
"""
from typing import Any, Dict
from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    """Skill 响应模型"""
    id: str = Field(description="Skill ID")
    path: str = Field(description="Skill 文件路径")
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")
    enabled: bool = Field(description="是否启用")


class SkillListResponse(BaseModel):
    """Skill 列表响应"""
    skills: list[SkillResponse] = Field(description="Skill 列表")


class SkillCreateRequest(BaseModel):
    """创建 Skill 请求"""
    id: str = Field(description="Skill ID", min_length=1, max_length=100)
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")


class SkillUpdateRequest(BaseModel):
    """更新 Skill 请求"""
    metadata: Dict[str, Any] = Field(description="YAML 元数据")
    content: str = Field(description="Markdown 正文内容")
