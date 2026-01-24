"""
项目文件相关的 Pydantic 模型
"""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class FileNode(BaseModel):
    """文件树节点"""

    id: str = Field(description="节点唯一 ID（相对路径）")
    name: str = Field(description="文件或目录名")
    path: str = Field(description="相对项目根目录的路径")
    type: Literal["file", "folder"] = Field(description="节点类型")
    children: Optional[List["FileNode"]] = Field(default=None, description="子节点")
    extension: Optional[str] = Field(default=None, description="文件扩展名")
    size: Optional[int] = Field(default=None, description="文件大小（字节）")


class FileTreeResponse(BaseModel):
    """文件树响应"""

    files: List[FileNode] = Field(description="文件树节点列表")


class FileContentResponse(BaseModel):
    """文件内容响应"""

    path: str = Field(description="相对项目根目录的路径")
    content: str = Field(description="文件内容")
    truncated: bool = Field(description="是否被截断")
    size: int = Field(description="文件大小（字节）")
