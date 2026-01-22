"""
MCP 路由
"""
from fastapi import APIRouter

from app.schemas.mcp import (
    MCPListResponse,
    MCPTestResponse,
    MCPCreateRequest,
    MCPUpdateRequest,
    MCPServerItem,
    MCPStartResponse,
    MCPStopResponse,
)
from app.services.mcp.registry import mcp_registry
from app.services.mcp.service import MCPService

router = APIRouter()


def build_service() -> MCPService:
    return MCPService(mcp_registry)


@router.get(
    "/v1/mcp/engines/{engine}/servers",
    response_model=MCPListResponse,
    summary="列出 MCP 服务器",
    description="按引擎获取当前已配置的 MCP 服务器列表。",
)
async def list_servers(
    engine: str,
):
    service = build_service()
    servers = await service.list_servers(engine)
    return MCPListResponse(servers=servers)


@router.post(
    "/v1/mcp/engines/{engine}/servers/{id}/test",
    response_model=MCPTestResponse,
    summary="测试 MCP 服务器",
    description="对 MCP 服务器执行连通性测试并返回结果。",
)
async def test_server(
    engine: str,
    id: str,
):
    service = build_service()
    result = await service.test_server(id)
    return MCPTestResponse(id=id, status=result["status"], detail=result["detail"])


@router.post(
    "/v1/mcp/engines/{engine}/servers",
    response_model=MCPServerItem,
    summary="创建 MCP 服务器",
    description="创建新的 MCP 服务器配置。",
)
async def create_server(
    engine: str,
    request: MCPCreateRequest,
):
    """创建 MCP 服务器"""
    service = build_service()
    server = await service.create_server(engine, request.model_dump())
    return MCPServerItem(**server, status={"running": False, "error": None, "lastChecked": None})


@router.put(
    "/v1/mcp/engines/{engine}/servers/{id}",
    response_model=MCPServerItem,
    summary="更新 MCP 服务器",
    description="更新指定 MCP 服务器的配置。",
)
async def update_server(
    engine: str,
    id: str,
    request: MCPUpdateRequest,
):
    """更新 MCP 服务器"""
    service = build_service()
    server = await service.update_server(engine, id, request.model_dump(exclude_none=True))
    return MCPServerItem(**server, status={"running": False, "error": None, "lastChecked": None})


@router.delete(
    "/v1/mcp/engines/{engine}/servers/{id}",
    summary="删除 MCP 服务器",
    description="删除指定的 MCP 服务器配置。",
)
async def delete_server(
    engine: str,
    id: str,
):
    """删除 MCP 服务器"""
    service = build_service()
    await service.delete_server(engine, id)
    return {"success": True}


@router.post(
    "/v1/mcp/engines/{engine}/servers/{id}/start",
    response_model=MCPStartResponse,
    summary="启动 MCP 服务器",
    description="启动指定的 MCP 服务器进程。",
)
async def start_server(
    engine: str,
    id: str,
):
    """启动 MCP 服务器"""
    service = build_service()
    result = await service.start_server(engine, id)
    return MCPStartResponse(**result)


@router.post(
    "/v1/mcp/engines/{engine}/servers/{id}/stop",
    response_model=MCPStopResponse,
    summary="停止 MCP 服务器",
    description="停止指定的 MCP 服务器进程。",
)
async def stop_server(
    engine: str,
    id: str,
):
    """停止 MCP 服务器"""
    service = build_service()
    result = await service.stop_server(id)
    return MCPStopResponse(**result)
