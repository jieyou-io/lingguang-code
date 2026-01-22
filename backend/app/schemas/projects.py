"""
项目管理相关的 Pydantic 模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    """项目响应模型"""
    id: str = Field(description="项目 ID（目录名）")
    path: str = Field(description="项目路径")
    sessions: List[str] = Field(description="会话 ID 列表")
    created_at: int = Field(description="最后活跃时间 (Unix 时间戳)")


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    projects: List[ProjectResponse] = Field(description="项目列表")


class ProjectCompareResponse(BaseModel):
    """项目对比响应"""
    integrated: List[str] = Field(description="所有已集成项目")
    scanned: List[str] = Field(description="所有扫描到的项目")
    unintegrated: List[str] = Field(description="扫描到但未集成的项目")
    missingOnDisk: List[str] = Field(description="已集成但磁盘上不存在的项目")


class SessionResponse(BaseModel):
    """会话响应模型"""
    id: str = Field(description="会话 ID (UUID)")
    project_id: Optional[str] = Field(default=None, description="项目 ID（仅 Claude）")
    project_path: Optional[str] = Field(default=None, description="项目路径")
    projectPath: Optional[str] = Field(default=None, description="项目路径（Codex/Gemini 格式）")
    todo_data: Optional[Dict[str, Any]] = Field(default=None, description="Todo 数据")
    created_at: int = Field(description="创建时间 (Unix 时间戳)")
    first_message: Optional[str] = Field(default=None, description="第一条用户消息")
    message_timestamp: Optional[str] = Field(default=None, description="消息时间戳")
    last_message_timestamp: Optional[str] = Field(default=None, description="最后消息时间戳 (ISO 字符串)")
    model: Optional[str] = Field(default=None, description="使用的模型")
    engine: Optional[str] = Field(default=None, description="执行引擎: claude | codex | gemini")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionResponse] = Field(description="会话列表")
