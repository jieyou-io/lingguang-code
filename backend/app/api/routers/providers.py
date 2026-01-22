"""
Provider 配置管理路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.providers import (
    ProviderConfigResponse,
    ProviderConfigUpdateRequest,
    ProviderPresetResponse,
    ProviderPresetCreateRequest,
)
from app.services.config_manager import (
    ConfigHubService,
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
    "/v1/providers/{engine}",
    response_model=ProviderConfigResponse,
    summary="获取当前 Provider 配置",
    description="获取指定引擎当前使用的 Provider 配置（API Key、Base URL 等）。",
)
async def get_provider_config(
    engine: str,
    session=Depends(get_db_session),
):
    """
    获取当前 Provider 配置

    """
    service = build_service()
    full_config = service.read_provider_config(engine)

    return ProviderConfigResponse(engine=engine, config=full_config)


@router.get(
    "/v1/providers/{engine}/presets",
    response_model=list[ProviderPresetResponse],
    summary="获取 Provider 预设列表",
    description="获取指定引擎的所有代理商预设配置。",
)
async def get_provider_presets(
    engine: str,
    session=Depends(get_db_session),
):
    """
    获取 Provider 预设列表


    """
    service = build_service()
    presets = service.read_provider_presets(engine)

    return [
        ProviderPresetResponse(
            id=preset.get("id", ""),
            name=preset.get("name", ""),
            description=preset.get("description"),
            config=preset,
        )
        for preset in presets
    ]


@router.post(
    "/v1/providers/{engine}/presets",
    response_model=ProviderPresetResponse,
    summary="添加 Provider 预设",
    description="添加新的代理商预设配置。",
)
async def create_provider_preset(
    engine: str,
    request: ProviderPresetCreateRequest,
    session=Depends(get_db_session),
):
    """添加 Provider 预设"""
    service = build_service()
    preset = service.create_provider_preset(engine, request.model_dump())

    return ProviderPresetResponse(
        id=preset.get("id", ""),
        name=preset.get("name", ""),
        description=preset.get("description"),
        config=preset,
    )


@router.put(
    "/v1/providers/{engine}/presets/{preset_id}",
    response_model=ProviderPresetResponse,
    summary="更新 Provider 预设",
    description="更新指定的代理商预设配置。",
)
async def update_provider_preset(
    engine: str,
    preset_id: str,
    request: ProviderPresetCreateRequest,
    session=Depends(get_db_session),
):
    """更新 Provider 预设"""
    service = build_service()
    preset = service.update_provider_preset(engine, preset_id, request.model_dump())

    return ProviderPresetResponse(
        id=preset.get("id", ""),
        name=preset.get("name", ""),
        description=preset.get("description"),
        config=preset,
    )


@router.delete(
    "/v1/providers/{engine}/presets/{preset_id}",
    summary="删除 Provider 预设",
    description="删除指定的代理商预设配置。",
)
async def delete_provider_preset(
    engine: str,
    preset_id: str,
    session=Depends(get_db_session),
):
    """删除 Provider 预设"""
    service = build_service()
    service.delete_provider_preset(engine, preset_id)

    return {"message": f"Successfully deleted preset: {preset_id}"}


@router.post(
    "/v1/providers/{engine}/switch",
    response_model=ProviderConfigResponse,
    summary="切换 Provider",
    description="切换到指定的代理商预设配置。",
)
async def switch_provider(
    engine: str,
    preset_id: str,
    session=Depends(get_db_session),
):
    """
    切换 Provider


    """
    service = build_service()
    config = service.switch_provider(engine, preset_id)

    return ProviderConfigResponse(engine=engine, config=config)


@router.put(
    "/v1/providers/{engine}",
    response_model=ProviderConfigResponse,
    summary="更新 Provider 配置",
    description="更新指定引擎的 Provider 配置（浅合并）。",
)
async def update_provider_config(
    engine: str,
    request: ProviderConfigUpdateRequest,
    session=Depends(get_db_session),
):
    """更新 Provider 配置"""
    service = build_service()

    # 过滤掉 None 值
    patch = {k: v for k, v in request.model_dump().items() if v is not None}

    config = service.update_provider_config(engine, patch)
    return ProviderConfigResponse(engine=engine, config=config)


@router.post(
    "/v1/providers/{engine}/enable",
    response_model=ProviderConfigResponse,
    summary="启用 Provider",
    description="启用指定引擎的 Provider。",
)
async def enable_provider(
    engine: str,
    session=Depends(get_db_session),
):
    """启用 Provider"""
    service = build_service()
    config = service.update_provider_config(engine, {"enabled": True})
    return ProviderConfigResponse(engine=engine, config=config)


@router.post(
    "/v1/providers/{engine}/disable",
    response_model=ProviderConfigResponse,
    summary="禁用 Provider",
    description="禁用指定引擎的 Provider。",
)
async def disable_provider(
    engine: str,
    session=Depends(get_db_session),
):
    """禁用 Provider"""
    service = build_service()
    config = service.update_provider_config(engine, {"enabled": False})
    return ProviderConfigResponse(engine=engine, config=config)
