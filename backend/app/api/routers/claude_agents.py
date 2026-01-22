"""
Claude Subagents 管理路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.agents import (
    AgentResponse,
    AgentListResponse,
    AgentCreateRequest,
    AgentUpdateRequest,
)
from app.services.config_manager import (
    ConfigHubService,
    ConfigScope,
    FileLockProvider,
    BackupManager,
    ConfigParsers,
)

router = APIRouter()


def build_service() -> ConfigHubService:
    """构建配置管理服务实例"""
    return ConfigHubService(
        lock_provider=FileLockProvider(),
        backup_manager=BackupManager(),
        parsers=ConfigParsers(),
    )


@router.get(
    "/v1/claude/agents",
    response_model=AgentListResponse,
    summary="列出所有 Subagents",
    description="获取服务器级 (~/.claude/agents) 的 Claude Subagents 列表。",
)
async def list_agents(
    session=Depends(get_db_session),
):
    """列出所有 Subagents"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    agents = service.list_agents(config_scope)
    return AgentListResponse(agents=[AgentResponse(**agent) for agent in agents])


@router.get(
    "/v1/claude/agents/{agent_id:path}",
    response_model=AgentResponse,
    summary="获取单个 Subagent",
    description="获取服务器级 Claude Subagent 详情。",
)
async def get_agent(
    agent_id: str,
    session=Depends(get_db_session),
):
    """获取单个 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    agent = service.get_agent(config_scope, agent_id)
    return AgentResponse(**agent)


@router.post(
    "/v1/claude/agents",
    response_model=AgentResponse,
    summary="创建 Subagent",
    description="在服务器级 (~/.claude/agents) 创建新的 Claude Subagent。",
)
async def create_agent(
    request: AgentCreateRequest,
    session=Depends(get_db_session),
):
    """创建 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.upsert_agent(config_scope, request.id, request.metadata, request.content)
    agent = service.get_agent(config_scope, request.id)
    return AgentResponse(**agent)


@router.put(
    "/v1/claude/agents/{agent_id:path}",
    response_model=AgentResponse,
    summary="更新 Subagent",
    description="更新服务器级 Claude Subagent。",
)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    session=Depends(get_db_session),
):
    """更新 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.upsert_agent(config_scope, agent_id, request.metadata, request.content)
    agent = service.get_agent(config_scope, agent_id)
    return AgentResponse(**agent)


@router.delete(
    "/v1/claude/agents/{agent_id:path}",
    summary="删除 Subagent",
    description="删除指定 ID 的 Claude Subagent。",
)
async def delete_agent(
    agent_id: str,
    session=Depends(get_db_session),
):
    """删除 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.delete_agent(config_scope, agent_id)
    return {"success": True}


@router.post(
    "/v1/claude/agents/{agent_id:path}/enable",
    response_model=AgentResponse,
    summary="启用 Subagent",
    description="启用服务器级 Claude Subagent。",
)
async def enable_agent(
    agent_id: str,
    session=Depends(get_db_session),
):
    """启用 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    agent = service.toggle_agent(config_scope, agent_id, enabled=True)
    return AgentResponse(**agent)


@router.post(
    "/v1/claude/agents/{agent_id:path}/disable",
    response_model=AgentResponse,
    summary="禁用 Subagent",
    description="禁用服务器级 Claude Subagent。",
)
async def disable_agent(
    agent_id: str,
    session=Depends(get_db_session),
):
    """禁用 Subagent"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    agent = service.toggle_agent(config_scope, agent_id, enabled=False)
    return AgentResponse(**agent)
