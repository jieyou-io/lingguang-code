"""
项目管理路由
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from app.schemas.projects import (
    ProjectListResponse,
    ProjectResponse,
    ProjectCompareResponse,
    SessionListResponse,
    SessionResponse,
)
from app.schemas.project_files import FileTreeResponse, FileContentResponse
from app.services.project_manager import ProjectManagerService
from app.services.project_manager.session_scanner import CodexSessionScanner, GeminiSessionScanner
from app.services.project_manager.session_loader import (
    ClaudeSessionLoader,
    CodexSessionLoader,
    GeminiSessionLoader,
)
from app.services.project_files import ProjectFileService

router = APIRouter()


def build_service() -> ProjectManagerService:
    """构建项目管理服务实例"""
    return ProjectManagerService()


def build_file_service() -> ProjectFileService:
    """构建项目文件服务实例"""
    return ProjectFileService()


@router.get(
    "/v1/projects/integrated",
    response_model=ProjectListResponse,
    summary="获取已集成项目",
    description="从 ~/.claude/projects/ 目录扫描所有使用过 Claude CLI 的项目，返回完整的项目信息（包括 id、path、sessions、created_at）。",
)
async def list_integrated_projects():
    """
    获取所有已集成项目
    """
    service = build_service()
    projects = await service.list_integrated_projects()
    return ProjectListResponse(
        projects=[ProjectResponse(**p) for p in projects]
    )


@router.get(
    "/v1/projects/{project_id}/sessions",
    response_model=SessionListResponse,
    summary="获取项目会话列表",
    description="获取指定项目的所有会话详情，包括会话 ID、第一条消息、模型等信息。",
)
async def get_project_sessions(
    project_id: str,
):
    """
    获取项目会话列表
    """
    service = build_service()
    sessions = service.get_project_sessions(project_id)
    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions]
    )


@router.get(
    "/v1/projects/scanned",
    response_model=ProjectListResponse,
    summary="扫描服务器项目",
    description="扫描指定根目录查找所有 Git 项目（包含 .git 目录）。",
)
async def scan_server_projects(
    roots: list[str] = Query(
        ...,
        description="要扫描的根目录列表",
        example=["/Users/king/Documents/projects"],
    ),
    max_depth: int = Query(6, description="最大扫描深度", ge=1, le=10),
):
    """扫描服务器项目"""
    service = build_service()
    root_paths = [Path(root) for root in roots]
    projects = service.scan_projects(root_paths, max_depth=max_depth)
    return ProjectListResponse(projects=projects)


@router.get(
    "/v1/projects/compare",
    response_model=ProjectCompareResponse,
    summary="对比项目差异",
    description="对比已集成项目和扫描项目的差异，识别未集成项目和缺失项目。",
)
async def compare_projects(
    roots: list[str] = Query(
        ...,
        description="要扫描的根目录列表",
        example=["/Users/king/Documents/projects"],
    ),
    max_depth: int = Query(6, description="最大扫描深度", ge=1, le=10),
):
    """对比项目差异"""
    service = build_service()

    # 获取已集成项目
    integrated_projects = await service.list_integrated_projects()
    integrated_paths = [p["path"] for p in integrated_projects]

    # 扫描服务器项目
    root_paths = [Path(root) for root in roots]
    scanned = service.scan_projects(root_paths, max_depth=max_depth)

    # 对比差异
    result = service.compare_projects(integrated_paths, scanned)

    return ProjectCompareResponse(**result)


@router.get(
    "/v1/projects/files/tree",
    response_model=FileTreeResponse,
    summary="获取项目文件树",
    description="按项目路径扫描并返回文件树结构。",
)
async def get_project_file_tree(
    project_path: str = Query(..., description="项目路径"),
    max_depth: int = Query(4, description="最大扫描深度", ge=1, le=12),
    max_files: int = Query(3000, description="最大文件数量", ge=1, le=20000),
    include_hidden: bool = Query(False, description="是否包含隐藏文件"),
):
    service = build_file_service()
    files = service.build_tree(
        project_path=project_path,
        max_depth=max_depth,
        max_files=max_files,
        include_hidden=include_hidden,
    )
    return FileTreeResponse(files=files)


@router.get(
    "/v1/projects/files/content",
    response_model=FileContentResponse,
    summary="读取文件内容",
    description="读取指定项目下某个文件的内容。",
)
async def get_project_file_content(
    project_path: str = Query(..., description="项目路径"),
    file_path: str = Query(..., description="相对项目根目录的文件路径"),
    max_bytes: int = Query(200000, description="最大读取字节数", ge=1, le=1000000),
):
    service = build_file_service()
    result = service.read_file_content(
        project_path=project_path,
        file_path=file_path,
        max_bytes=max_bytes,
    )
    return FileContentResponse(
        path=result.path,
        content=result.content,
        truncated=result.truncated,
        size=result.size,
    )

@router.get(
    "/v1/sessions/codex",
    response_model=SessionListResponse,
    summary="获取所有 Codex 会话",
    description="扫描 ~/.codex/sessions/ 目录，返回所有 Codex 会话列表。前端可根据 projectPath 过滤属于特定项目的会话。",
)
async def list_codex_sessions(
):
    """
    获取所有 Codex 会话

    """
    scanner = CodexSessionScanner()
    sessions = scanner.list_sessions()
    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions]
    )


@router.get(
    "/v1/sessions/gemini",
    response_model=SessionListResponse,
    summary="获取所有 Gemini 会话",
    description="扫描 ~/.gemini/tmp/*/chats/*.json 目录，返回 Gemini 会话列表。可通过 project_path 参数过滤特定项目的会话。",
)
async def list_gemini_sessions(
    project_path: Optional[str] = Query(None, description="项目路径，用于过滤特定项目的会话"),
):
    """获取 Gemini 会话列表"""
    scanner = GeminiSessionScanner()
    sessions = scanner.list_sessions(project_path=project_path)
    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions]
    )


@router.get(
    "/v1/sessions/claude/{project_id}/{session_id}/history",
    summary="获取 Claude 会话历史消息",
    description="加载指定 Claude 会话的完整消息历史（包括子代理消息）。",
)
async def get_claude_session_history(
    project_id: str,
    session_id: str,
):
    """
    获取 Claude 会话历史消息
    """
    loader = ClaudeSessionLoader()
    try:
        messages = loader.load_session_history(session_id, project_id)
        return {"messages": messages}
    except FileNotFoundError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/v1/sessions/codex/{session_id}/history",
    summary="获取 Codex 会话历史消息",
    description="加载指定 Codex 会话的完整消息历史。",
)
async def get_codex_session_history(
    session_id: str,
):
    """获取 Codex 会话历史消息"""
    loader = CodexSessionLoader()
    try:
        messages = loader.load_session_history(session_id)
        return {"messages": messages}
    except FileNotFoundError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/v1/sessions/gemini/{session_id}/history",
    summary="获取 Gemini 会话历史消息",
    description="加载指定 Gemini 会话的完整消息历史。",
)
async def get_gemini_session_history(
    session_id: str,
):
    """获取 Gemini 会话历史消息"""
    loader = GeminiSessionLoader()
    try:
        result = loader.load_session_history(session_id)
        # 🔥 返回消息和项目路径
        return {
            "messages": result.get("messages", []),
            "project_path": result.get("project_path"),
        }
    except FileNotFoundError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))
