"""
引擎状态路由
"""
from fastapi import APIRouter

from app.schemas.engine_status import EngineStatusListResponse
from app.services.engine_status import EngineStatusService

router = APIRouter()


@router.get(
    "/v1/engines/status",
    response_model=EngineStatusListResponse,
    summary="获取所有引擎状态",
    description="并行检查 Claude Code CLI、Codex API、Gemini CLI 的可用性和延迟。",
)
async def get_engines_status():
    """获取所有引擎的状态"""
    service = EngineStatusService()
    engines = await service.check_all_engines()
    return EngineStatusListResponse(engines=engines)
