"""
Claude Skills 管理路由
"""
from fastapi import APIRouter

from app.schemas.skills import (
    SkillResponse,
    SkillListResponse,
    SkillCreateRequest,
    SkillUpdateRequest,
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
    "/v1/claude/skills",
    response_model=SkillListResponse,
    summary="列出所有 Skills",
    description="获取服务器级 (~/.claude/skills) 的 Claude Skills 列表。",
)
async def list_skills(
):
    """列出所有 Skills"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    skills = service.list_skills(config_scope)
    return SkillListResponse(skills=[SkillResponse(**skill) for skill in skills])


@router.get(
    "/v1/claude/skills/{skill_id:path}",
    response_model=SkillResponse,
    summary="获取单个 Skill",
    description="获取服务器级 Claude Skill 详情。",
)
async def get_skill(
    skill_id: str,
):
    """获取单个 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    skill = service.get_skill(config_scope, skill_id)
    return SkillResponse(**skill)


@router.post(
    "/v1/claude/skills",
    response_model=SkillResponse,
    summary="创建 Skill",
    description="在服务器级 (~/.claude/skills) 创建新的 Claude Skill。",
)
async def create_skill(
    request: SkillCreateRequest,
):
    """创建 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.upsert_skill(config_scope, request.id, request.metadata, request.content)
    skill = service.get_skill(config_scope, request.id)
    return SkillResponse(**skill)


@router.put(
    "/v1/claude/skills/{skill_id:path}",
    response_model=SkillResponse,
    summary="更新 Skill",
    description="更新服务器级 Claude Skill。",
)
async def update_skill(
    skill_id: str,
    request: SkillUpdateRequest,
):
    """更新 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.upsert_skill(config_scope, skill_id, request.metadata, request.content)
    skill = service.get_skill(config_scope, skill_id)
    return SkillResponse(**skill)


@router.delete(
    "/v1/claude/skills/{skill_id:path}",
    summary="删除 Skill",
    description="删除指定 ID 的 Claude Skill。",
)
async def delete_skill(
    skill_id: str,
):
    """删除 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    service.delete_skill(config_scope, skill_id)
    return {"success": True}


@router.post(
    "/v1/claude/skills/{skill_id:path}/enable",
    response_model=SkillResponse,
    summary="启用 Skill",
    description="启用服务器级 Claude Skill。",
)
async def enable_skill(
    skill_id: str,
):
    """启用 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    skill = service.toggle_skill(config_scope, skill_id, enabled=True)
    return SkillResponse(**skill)


@router.post(
    "/v1/claude/skills/{skill_id:path}/disable",
    response_model=SkillResponse,
    summary="禁用 Skill",
    description="禁用服务器级 Claude Skill。",
)
async def disable_skill(
    skill_id: str,
):
    """禁用 Skill"""
    service = build_service()
    config_scope = ConfigScope(
        scope="user",
        project_root=None,
    )
    skill = service.toggle_skill(config_scope, skill_id, enabled=False)
    return SkillResponse(**skill)
