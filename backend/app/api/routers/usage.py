"""
使用统计路由

"""
from fastapi import APIRouter, Query
from app.schemas.usage import UsageStatsResponse
from app.schemas.quick_stats import QuickStatsResponse
from app.services.usage.service import UsageService

router = APIRouter()


@router.get(
    "/v1/usage/stats",
    response_model=UsageStatsResponse,
    summary="获取使用统计",
    description="获取使用统计数据,支持按天数过滤。",
)
async def get_usage_stats(
    days: int = Query(None, description="统计最近 N 天的数据,不传则统计全部"),
):
    """
    获取使用统计
    """
    service = UsageService()
    stats = await service.get_stats(days=days)
    return UsageStatsResponse(**stats)


@router.get(
    "/v1/stats/sessions",
    response_model=list,
    summary="[已废弃] 获取会话统计",
    description="⚠️ 已废弃：此接口功能与 /v1/usage/stats 的 by_project 字段重复，请改用 /v1/usage/stats 接口。",
    deprecated=True,
)
async def get_session_stats(
    since: str = Query(None, description="开始日期 (YYYYMMDD)"),
    until: str = Query(None, description="结束日期 (YYYYMMDD)"),
    order: str = Query("desc", description="排序方式 (asc/desc)"),
):
    """
    获取会话统计

    ⚠️ 已废弃接口

    功能与 /v1/usage/stats 的 by_project 字段重复。
    建议使用 /v1/usage/stats 接口替代。
    """
    service = UsageService()
    stats = await service.get_session_stats(since=since, until=until, order=order)
    return stats


@router.get(
    "/v1/usage/quick-stats",
    response_model=QuickStatsResponse,
    summary="获取快速统计",
    description="获取今日/本周/本月的快速统计数据，支持按项目过滤。专为会话页面和项目页面设计。",
)
async def get_quick_stats(
    project_path: str = Query(None, description="项目路径，不传则统计所有项目"),
):
    """
    获取快速统计

    会话页面传入 project_path 获取当前项目统计
    项目页面不传 project_path 获取全局统计
    """
    service = UsageService()
    stats = await service.get_quick_stats(project_path=project_path)
    return QuickStatsResponse(**stats)
