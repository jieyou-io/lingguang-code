"""
上下文管理路由
"""
from fastapi import APIRouter

from app.schemas.context_manager import (
    ContextConfigResponse,
    ContextCompactRequest,
    ContextCompactResponse,
)
from app.services.context_manager.service import ContextManagerService
from app.services.storage.repositories import StorageRepository

router = APIRouter()


def build_service() -> ContextManagerService:
    repository = StorageRepository()
    return ContextManagerService(repository)


@router.get(
    "/v1/context/config",
    response_model=ContextConfigResponse,
    summary="获取上下文配置",
    description="返回当前上下文压缩配置。",
)
async def get_config(
):
    service = build_service()
    return ContextConfigResponse(**service.get_config())


@router.post(
    "/v1/context/compact",
    response_model=ContextCompactResponse,
    summary="执行上下文压缩",
    description="对指定会话进行上下文压缩并返回摘要。",
)
async def compact(
    payload: ContextCompactRequest,
):
    service = build_service()
    summary = await service.compact(payload.sessionId)
    return ContextCompactResponse(sessionId=payload.sessionId, status="completed", summary=summary)
