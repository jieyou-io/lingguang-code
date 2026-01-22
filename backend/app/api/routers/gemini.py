"""
Gemini 路由
"""
import json
import uuid

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import get_db_session
from app.core.config import settings
from app.core.sse import sse_manager
from app.schemas.gemini import GeminiExecuteRequest, GeminiCancelRequest, GeminiSessionResponse
from app.services.gemini.runner import GeminiRunner
from app.services.gemini.service import GeminiService, gemini_registry
from app.services.storage.repositories import StorageRepository

router = APIRouter()


def build_service(session) -> GeminiService:
    """创建 Gemini 服务实例"""
    repository = StorageRepository(session)
    runner = GeminiRunner()
    return GeminiService(repository, runner, gemini_registry)


@router.post(
    "/v1/gemini/execute",
    response_model=GeminiSessionResponse,
    summary="执行 Gemini 会话",
    description="启动新会话并返回 sessionId。",
)
async def execute_gemini(
    payload: GeminiExecuteRequest,
    session=Depends(get_db_session),
):
    service = build_service(session)
    session_id = await service.execute(payload)
    return GeminiSessionResponse(sessionId=session_id, status="started")


@router.post(
    "/v1/gemini/continue",
    response_model=GeminiSessionResponse,
    summary="继续 Gemini 会话",
    description="恢复指定的历史对话。",
)
async def continue_gemini(
    payload: GeminiExecuteRequest,
    session=Depends(get_db_session),
):
    # 🔥 跳过数据库依赖，直接启动 Gemini CLI
    # Gemini CLI 会自动从 ~/.gemini/tmp/ 恢复会话
    runner = GeminiRunner()

    process = await runner.start(
        project_path=payload.projectPath,
        prompt=payload.prompt,
        model=payload.model,
        approval_mode=payload.approvalMode,
        include_directories=payload.includeDirectories,
        debug=payload.debug,
        session_id=payload.sessionId,  # 🔥 传递 session_id 以启用会话恢复
    )

    # 使用传入的 sessionId 或生成新的
    session_id = payload.sessionId or str(uuid.uuid4())
    gemini_registry.register(session_id, process)

    return GeminiSessionResponse(sessionId=session_id, status="resumed")


@router.post(
    "/v1/gemini/cancel",
    response_model=GeminiSessionResponse,
    summary="取消 Gemini 会话",
    description="取消指定会话；未提供 sessionId 时取消所有会话。",
)
async def cancel_gemini(
    payload: GeminiCancelRequest,
    session=Depends(get_db_session),
):
    service = build_service(session)
    if payload.sessionId:
        await service.cancel(payload.sessionId)
        return GeminiSessionResponse(sessionId=payload.sessionId, status="canceled")
    await service.cancel_all()
    return GeminiSessionResponse(sessionId=None, status="canceled")


@router.get(
    "/v1/gemini/stream",
    summary="Gemini 流式输出",
    description="SSE 流式返回会话消息，使用 query 参数 sessionId。",
)
async def stream_gemini(
    sessionId: str,
    session=Depends(get_db_session),
):
    service = build_service(session)

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
