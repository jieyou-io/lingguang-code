"""
Claude 路由
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.config import settings
from app.core.sse import merge_with_keepalive, sse_manager
from app.schemas.claude import (
    ClaudeExecuteRequest,
    ClaudeResumeRequest,
    ClaudeCancelRequest,
    ClaudeSessionResponse,
    ClaudePermissionResponse,
)
from app.services.claude.runner import ClaudeRunner
from app.services.claude.service import ClaudeService, claude_registry
from app.services.claude.slash_commands import (
    list_custom_slash_commands,
    get_command_content,
    CustomSlashCommand,
)
from app.services.storage.repositories import StorageRepository

router = APIRouter()


def build_service() -> ClaudeService:
    """创建 Claude 服务实例"""
    repository = StorageRepository()
    runner = ClaudeRunner()
    return ClaudeService(repository, runner, claude_registry)


@router.post(
    "/v1/claude/execute",
    response_model=ClaudeSessionResponse,
    summary="执行 Claude 会话",
    description="启动新会话并返回 sessionId。",
)
async def execute_claude(
    payload: ClaudeExecuteRequest,
):
    service = build_service()
    session_id = await service.execute(payload)
    return ClaudeSessionResponse(sessionId=session_id, status="started")


@router.post(
    "/v1/claude/continue",
    response_model=ClaudeSessionResponse,
    summary="继续 Claude 会话",
    description="恢复指定的历史对话，使用 --resume session_id 标志。",
)
async def continue_claude(
    payload: ClaudeExecuteRequest,
):
    service = build_service()
    # 🔥 关键：使用 --resume 恢复指定的历史对话
    session_id = await service.execute(payload, resume_session_id=payload.sessionId)
    return ClaudeSessionResponse(sessionId=session_id, status="started")


@router.post(
    "/v1/claude/resume",
    response_model=ClaudeSessionResponse,
    summary="恢复 Claude 会话",
    description="恢复已存在的会话并返回 sessionId。",
)
async def resume_claude(
    payload: ClaudeResumeRequest,
):
    service = build_service()
    session_id = await service.resume(payload)
    return ClaudeSessionResponse(sessionId=session_id, status="resumed")


@router.post(
    "/v1/claude/cancel",
    response_model=ClaudeSessionResponse,
    summary="取消 Claude 会话",
    description="取消指定会话并返回状态。",
)
async def cancel_claude(
    payload: ClaudeCancelRequest,
):
    service = build_service()
    await service.cancel(payload.sessionId)
    return ClaudeSessionResponse(sessionId=payload.sessionId, status="canceled")


@router.get(
    "/v1/claude/stream",
    summary="Claude 流式输出",
    description="SSE 流式返回会话消息，使用 query 参数 sessionId。",
)
async def stream_claude(
    sessionId: str,
):
    service = build_service()

    async def event_source():
        sse_manager.register_connection(sessionId)
        try:
            async for event in service.stream_events(sessionId):
                # 🔥 关键修复：显式序列化为 JSON 字符串
                yield ServerSentEvent(
                    data=json.dumps(event.to_dict(), ensure_ascii=False),
                    event=event.type.value,
                )
                # 如果是 complete 事件，结束流
                if event.type.value == "complete":
                    break
        finally:
            sse_manager.unregister_connection(sessionId)

    return EventSourceResponse(event_source(), media_type="text/event-stream")


@router.post(
    "/v1/claude/permission",
    response_model=ClaudeSessionResponse,
    summary="发送权限响应",
    description="发送用户的权限授权响应到 Claude CLI。",
)
async def send_permission_response(
    payload: ClaudePermissionResponse,
):
    """发送权限响应到 Claude CLI stdin"""
    service = build_service()
    success = await service.send_permission_response(
        session_id=payload.sessionId,
        response=payload.response,
    )
    status = "sent" if success else "failed"
    return ClaudeSessionResponse(sessionId=payload.sessionId, status=status)


# ============================================================================
# 🔥 自定义斜杠命令 API
# ============================================================================

@router.get(
    "/v1/claude/commands",
    response_model=List[dict],
    summary="获取自定义斜杠命令",
    description="列出用户和项目级别的自定义斜杠命令。",
)
async def get_custom_commands(
    project_path: Optional[str] = Query(None, description="项目路径"),
):
    """获取自定义斜杠命令列表

    扫描以下目录:
    - ~/.claude/commands/*.md (用户级别)
    - {projectPath}/.claude/commands/*.md (项目级别)
    """
    commands = list_custom_slash_commands(project_path)
    return [
        {
            "name": cmd.name,
            "path": cmd.path,
            "scope": cmd.scope,
            "description": cmd.description,
            "argHint": cmd.arg_hint,
            "content": cmd.content,
        }
        for cmd in commands
    ]


@router.get(
    "/v1/claude/commands/{command_name}",
    summary="获取命令内容",
    description="获取指定斜杠命令的内容。",
)
async def get_command(
    command_name: str,
    project_path: Optional[str] = Query(None, description="项目路径"),
):
    """获取指定命令的内容"""
    content = get_command_content(command_name, project_path)
    if content is None:
        return {"error": f"Command '{command_name}' not found"}
    return {"name": command_name, "content": content}
