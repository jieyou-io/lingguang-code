"""
Claude Plugins 管理路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.plugins import (
    PluginResponse,
    PluginListResponse,
    PluginInstallRequest,
    PluginInstallResponse,
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
    "/v1/claude/plugins",
    response_model=PluginListResponse,
    summary="列出所有 Plugins",
    description="获取服务器级 (~/.claude/plugins) 的 Claude Plugins 列表。",
)
async def list_plugins(
    session=Depends(get_db_session),
):
    """列出所有 Plugins"""
    service = build_service()
    config_scope = ConfigScope(scope="user", project_root=None)
    plugins = await service.list_plugins(config_scope)
    return PluginListResponse(plugins=[PluginResponse(**plugin) for plugin in plugins])


@router.post(
    "/v1/claude/plugins",
    response_model=PluginInstallResponse,
    summary="安装 Plugin",
    description="通过 Claude CLI 安装新的 Plugin。",
)
async def install_plugin(
    request: PluginInstallRequest,
    session=Depends(get_db_session),
):
    """安装 Plugin"""
    service = build_service()
    result = await service.install_plugin(request.plugin_ref)
    return PluginInstallResponse(**result)


@router.post(
    "/v1/claude/plugins/{plugin_id:path}/enable",
    response_model=PluginResponse,
    summary="启用 Plugin",
    description="启用服务器级 Claude Plugin。",
)
async def enable_plugin(
    plugin_id: str,
    session=Depends(get_db_session),
):
    """启用 Plugin"""
    service = build_service()
    config_scope = ConfigScope(scope="user", project_root=None)
    plugin = await service.toggle_plugin(config_scope, plugin_id, enabled=True)
    return PluginResponse(**plugin)


@router.post(
    "/v1/claude/plugins/{plugin_id:path}/disable",
    response_model=PluginResponse,
    summary="禁用 Plugin",
    description="禁用服务器级 Claude Plugin。",
)
async def disable_plugin(
    plugin_id: str,
    session=Depends(get_db_session),
):
    """禁用 Plugin"""
    service = build_service()
    config_scope = ConfigScope(scope="user", project_root=None)
    plugin = await service.toggle_plugin(config_scope, plugin_id, enabled=False)
    return PluginResponse(**plugin)
