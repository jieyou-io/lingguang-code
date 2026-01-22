"""
健康检查路由
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    summary="健康检查",
    description="返回服务状态、版本与时间戳。",
)
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "appName": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
