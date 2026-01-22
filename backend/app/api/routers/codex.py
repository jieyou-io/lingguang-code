"""
Codex 路由
"""
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.config import settings
from app.core.sse import sse_manager
from app.schemas.codex import (
    CodexExecuteRequest,
    CodexResumeRequest,
    CodexCancelRequest,
    CodexSessionResponse,
)
from app.services.codex.runner import CodexRunner
from app.services.codex.service import CodexService, codex_registry
from app.services.storage.repositories import StorageRepository

router = APIRouter()


def build_service() -> CodexService:
    """创建 Codex 服务实例"""
    repository = StorageRepository()
    runner = CodexRunner()
    return CodexService(repository, runner, codex_registry)


@router.post(
    "/v1/codex/execute",
    response_model=CodexSessionResponse,
    summary="执行 Codex 会话",
    description="启动新会话并返回 sessionId。",
)
async def execute_codex(
    payload: CodexExecuteRequest,
):
    service = build_service()
    session_id = await service.execute(payload)
    return CodexSessionResponse(sessionId=session_id, status="started")


@router.post(
    "/v1/codex/continue",
    response_model=CodexSessionResponse,
    summary="继续 Codex 会话",
    description="恢复指定的历史对话。",
)
async def continue_codex(
    payload: CodexResumeRequest,
):
    # 🔥 使用 service.execute 方法，与 execute_codex 保持一致
    # Codex 是通过 HTTP API 调用的，不是 CLI 进程
    service = build_service()

    # 将 CodexResumeRequest 转换为 CodexExecuteRequest 格式
    from app.schemas.codex import CodexExecuteRequest
    execute_payload = CodexExecuteRequest(
        projectPath=payload.projectPath,
        prompt=payload.prompt,
        sessionId=payload.sessionId,  # 传递 sessionId 用于恢复会话
        model=payload.model,
        mode=payload.mode,
    )

    session_id = await service.execute(execute_payload)
    return CodexSessionResponse(sessionId=session_id, status="resumed")


@router.post(
    "/v1/codex/resume",
    response_model=CodexSessionResponse,
    summary="恢复 Codex 会话",
    description="恢复已存在的会话并返回 sessionId。",
)
async def resume_codex(
    payload: CodexResumeRequest,
):
    service = build_service()
    session_id = await service.resume(payload)
    return CodexSessionResponse(sessionId=session_id, status="resumed")


@router.post(
    "/v1/codex/cancel",
    response_model=CodexSessionResponse,
    summary="取消 Codex 会话",
    description="取消指定会话并返回状态。",
)
async def cancel_codex(
    payload: CodexCancelRequest,
):
    service = build_service()
    await service.cancel(payload.sessionId)
    return CodexSessionResponse(sessionId=payload.sessionId, status="canceled")


@router.get(
    "/v1/codex/stream",
    summary="Codex 流式输出",
    description="SSE 流式返回会话消息，使用 query 参数 sessionId。",
)
async def stream_codex(
    sessionId: str,
):
    service = build_service()

    async def event_source():
        sse_manager.register_connection(sessionId)
        try:
            async for event in service.stream_events(sessionId):
                yield ServerSentEvent(
                    data=json.dumps(event.to_dict(), ensure_ascii=False),
                    event=event.type.value,
                )
                if event.type.value == "complete":
                    break
        finally:
            sse_manager.unregister_connection(sessionId)

    return EventSourceResponse(event_source(), media_type="text/event-stream")
