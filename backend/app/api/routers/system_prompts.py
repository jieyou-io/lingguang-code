"""
系统提示词管理路由

管理 CLAUDE.md, AGENTS.md, GEMINI.md 等系统提示词文件
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.system_prompts import SystemPromptsService

router = APIRouter()


class SystemPromptResponse(BaseModel):
    """系统提示词响应"""
    engine: str
    content: str
    file_path: str
    exists: bool


class SystemPromptUpdateRequest(BaseModel):
    """系统提示词更新请求"""
    content: str


@router.get(
    "/v1/system-prompts/{engine}",
    response_model=SystemPromptResponse,
    summary="获取系统提示词",
    description="获取指定引擎的系统提示词文件内容 (CLAUDE.md, AGENTS.md, GEMINI.md)",
)
async def get_system_prompt(
    engine: str,
):
    """
    获取系统提示词

    - **engine**: 引擎名称 (claude, codex, gemini)

    返回系统提示词文件的内容。如果文件不存在，返回空字符串。
    """
    service = SystemPromptsService()
    content, file_path, exists = await service.get_system_prompt(engine)

    return SystemPromptResponse(
        engine=engine,
        content=content,
        file_path=file_path,
        exists=exists,
    )


@router.put(
    "/v1/system-prompts/{engine}",
    response_model=SystemPromptResponse,
    summary="更新系统提示词",
    description="更新指定引擎的系统提示词文件内容",
)
async def update_system_prompt(
    engine: str,
    request: SystemPromptUpdateRequest,
):
    """
    更新系统提示词

    - **engine**: 引擎名称 (claude, codex, gemini)
    - **content**: 新的提示词内容

    保存系统提示词到对应的文件。
    """
    service = SystemPromptsService()
    file_path = await service.save_system_prompt(engine, request.content)

    return SystemPromptResponse(
        engine=engine,
        content=request.content,
        file_path=file_path,
        exists=True,
    )
