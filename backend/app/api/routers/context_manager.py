"""
上下文管理路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.context_manager import (
    ContextConfigResponse,
    ContextCompactRequest,
    ContextCompactResponse,
)
from app.services.context_manager.service import ContextManagerService
from app.services.storage.repositories import StorageRepository

router = APIRouter()


def build_service(session) -> ContextManagerService:
    repository = StorageRepository(session)
    return ContextManagerService(repository)


@router.get(
    "/v1/context/config",
    response_model=ContextConfigResponse,
    summary="获取上下文配置",
    description="返回当前上下文压缩配置。",
)
async def get_config(
    session=Depends(get_db_session),
):
    service = build_service(session)
    return ContextConfigResponse(**service.get_config())


@router.post(
    "/v1/context/compact",
    response_model=ContextCompactResponse,
    summary="执行上下文压缩",
    description="对指定会话进行上下文压缩并返回摘要。",
)
async def compact(
    payload: ContextCompactRequest,
    session=Depends(get_db_session),
):
    service = build_service(session)
    summary = await service.compact(payload.sessionId)
    return ContextCompactResponse(sessionId=payload.sessionId, status="completed", summary=summary)
