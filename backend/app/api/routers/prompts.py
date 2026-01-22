"""
Prompt 配置管理路由
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db_session
from app.schemas.prompts import (
    PromptItemResponse,
    PromptListResponse,
    PromptCreateRequest,
    PromptUpdateRequest,
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


def config_to_prompt_list(engine: str, config: dict) -> PromptListResponse:
    """
    将配置字典转换为 PromptListResponse

    Args:
        engine: 引擎名称
        config: 配置字典（包含 prompts 字段）

    Returns:
        仅包含提示词列表的响应（不含供应商信息）
    """
    prompts = []
    for prompt_id, prompt_data in config.get("prompts", {}).items():
        prompts.append(
            PromptItemResponse(
                id=prompt_id,
                name=prompt_data.get("name", prompt_id),
                content=prompt_data.get("content", ""),
                enabled=prompt_data.get("enabled", True),
            )
        )
    return PromptListResponse(engine=engine, prompts=prompts)


@router.get(
    "/v1/config/prompts/{engine}",
    response_model=PromptListResponse,
    summary="获取 Prompt 列表",
    description="获取服务器级 (~/.claude/~/.codex/~/.gemini) 的 Prompt 列表（仅返回提示词，不含敏感信息）。",
)
async def get_prompt_config(
    engine: str,
    session=Depends(get_db_session),
):
    """
    获取 Prompt 列表

    仅返回提示词配置，不包含 API Key、环境变量等敏感信息。
    """
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取 prompts 配置（不包含敏感信息）
    config = service.read_prompt_config(engine, config_scope)

    # 转换为响应格式
    return config_to_prompt_list(engine, config)


@router.post(
    "/v1/config/prompts/{engine}",
    response_model=PromptListResponse,
    summary="创建 Prompt",
    description="在服务器级配置中创建新的 Prompt。",
)
async def create_prompt(
    engine: str,
    request: PromptCreateRequest,
    session=Depends(get_db_session),
):
    """创建 Prompt"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取当前配置
    config = service.read_prompt_config(engine, config_scope)

    # 检查 Prompt ID 是否已存在
    if request.id in config.get("prompts", {}):
        from app.core.errors import APIError
        raise APIError(
            status_code=409,
            code="PROMPT_ALREADY_EXISTS",
            message=f"Prompt ID '{request.id}' 已存在",
            details=request.id,
        )

    # 添加新 Prompt
    if "prompts" not in config:
        config["prompts"] = {}

    config["prompts"][request.id] = {
        "name": request.name,
        "content": request.content,
        "enabled": request.enabled,
    }

    # 写回配置
    service.write_prompt_config(engine, config_scope, config)

    return config_to_prompt_list(engine, config)


@router.put(
    "/v1/config/prompts/{engine}/{prompt_id}",
    response_model=PromptListResponse,
    summary="更新 Prompt",
    description="更新服务器级配置中的 Prompt。",
)
async def update_prompt(
    engine: str,
    prompt_id: str,
    request: PromptUpdateRequest,
    session=Depends(get_db_session),
):
    """更新 Prompt"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取当前配置
    config = service.read_prompt_config(engine, config_scope)

    # 检查 Prompt 是否存在
    if "prompts" not in config or prompt_id not in config["prompts"]:
        from app.core.errors import APIError
        raise APIError(
            status_code=404,
            code="PROMPT_NOT_FOUND",
            message="Prompt 不存在",
            details=prompt_id,
        )

    # 更新 Prompt（仅更新非 None 字段）
    prompt = config["prompts"][prompt_id]
    if request.name is not None:
        prompt["name"] = request.name
    if request.content is not None:
        prompt["content"] = request.content
    if request.enabled is not None:
        prompt["enabled"] = request.enabled

    # 写回配置
    service.write_prompt_config(engine, config_scope, config)

    return config_to_prompt_list(engine, config)


@router.delete(
    "/v1/config/prompts/{engine}/{prompt_id}",
    summary="删除 Prompt",
    description="删除服务器级配置中的 Prompt。",
)
async def delete_prompt(
    engine: str,
    prompt_id: str,
    session=Depends(get_db_session),
):
    """删除 Prompt"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取当前配置
    config = service.read_prompt_config(engine, config_scope)

    # 检查 Prompt 是否存在
    if "prompts" not in config or prompt_id not in config["prompts"]:
        from app.core.errors import APIError
        raise APIError(
            status_code=404,
            code="PROMPT_NOT_FOUND",
            message="Prompt 不存在",
            details=prompt_id,
        )

    # 删除 Prompt
    del config["prompts"][prompt_id]

    # 写回配置
    service.write_prompt_config(engine, config_scope, config)

    return {"success": True}


@router.post(
    "/v1/config/prompts/{engine}/{prompt_id}/enable",
    response_model=PromptListResponse,
    summary="启用 Prompt",
    description="启用服务器级配置中的 Prompt。",
)
async def enable_prompt(
    engine: str,
    prompt_id: str,
    session=Depends(get_db_session),
):
    """启用 Prompt"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取当前配置
    config = service.read_prompt_config(engine, config_scope)

    # 检查 Prompt 是否存在
    if "prompts" not in config or prompt_id not in config["prompts"]:
        from app.core.errors import APIError
        raise APIError(
            status_code=404,
            code="PROMPT_NOT_FOUND",
            message="Prompt 不存在",
            details=prompt_id,
        )

    # 启用 Prompt
    config["prompts"][prompt_id]["enabled"] = True

    # 写回配置
    service.write_prompt_config(engine, config_scope, config)

    return config_to_prompt_list(engine, config)


@router.post(
    "/v1/config/prompts/{engine}/{prompt_id}/disable",
    response_model=PromptListResponse,
    summary="禁用 Prompt",
    description="禁用服务器级配置中的 Prompt。",
)
async def disable_prompt(
    engine: str,
    prompt_id: str,
    session=Depends(get_db_session),
):
    """禁用 Prompt"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )

    # 读取当前配置
    config = service.read_prompt_config(engine, config_scope)

    # 检查 Prompt 是否存在
    if "prompts" not in config or prompt_id not in config["prompts"]:
        from app.core.errors import APIError
        raise APIError(
            status_code=404,
            code="PROMPT_NOT_FOUND",
            message="Prompt 不存在",
            details=prompt_id,
        )

    # 禁用 Prompt
    config["prompts"][prompt_id]["enabled"] = False

    # 写回配置
    service.write_prompt_config(engine, config_scope, config)

    return config_to_prompt_list(engine, config)
