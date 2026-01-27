"""
模型列表路由

提供各引擎可用模型列表和斜杠命令列表
- 模型列表：从配置文件动态读取
- 斜杠命令：内置命令 + 自定义命令（从 ~/.claude/commands 和项目目录扫描）
"""
import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.claude.slash_commands import (
    list_custom_slash_commands,
    list_codex_custom_slash_commands,
    list_gemini_custom_slash_commands,
    list_agent_slash_commands,
)


router = APIRouter()


# ============================================================================
# 配置读取辅助函数
# ============================================================================

def get_claude_config() -> dict:
    """读取 Claude 配置文件 ~/.claude/settings.json"""
    try:
        config_path = Path.home() / ".claude" / "settings.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_codex_config() -> dict:
    """读取 Codex 配置文件 ~/.codex/config.toml"""
    try:
        config_path = Path.home() / ".codex" / "config.toml"
        if config_path.exists():
            import tomli
            with open(config_path, "rb") as f:
                return tomli.load(f)
    except Exception:
        pass
    return {}


def get_gemini_env() -> dict:
    """读取 Gemini 环境变量（从 .env 或系统环境）"""
    env = {}
    # 尝试从 ~/.gemini/.env 读取
    try:
        env_path = Path.home() / ".gemini" / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line.replace("export ", "", 1).strip()
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        continue
                    if value.startswith(("'", "\"")) and value.endswith(("'", "\"")) and len(value) >= 2:
                        value = value[1:-1]
                    elif " #" in value:
                        value = value.split(" #", 1)[0].strip()
                    env[key] = value
    except Exception:
        pass

    # 合并系统环境变量
    if "GEMINI_MODEL" in os.environ:
        env["GEMINI_MODEL"] = os.environ["GEMINI_MODEL"]

    return env


# ============================================================================
# 数据模型
# ============================================================================

class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str
    context_window: int = 200000
    is_default: bool = False


class SlashCommand(BaseModel):
    """斜杠命令"""
    name: str
    description: str
    category: str
    supports_non_interactive: bool = True


# ============================================================================
# Claude 模型和命令
# ============================================================================

# Claude 模型列表（与原项目 src/components/FloatingPromptInput/constants.tsx 保持一致）
CLAUDE_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="claude-sonnet-4-5",
        name="Claude 4.5 Sonnet",
        description="Faster, efficient for most tasks",
        context_window=200000,
        is_default=True,
    ),
    ModelInfo(
        id="claude-sonnet-4-5-thinking",
        name="Claude 4.5 Sonnet (Thinking)",
        description="Sonnet with extended thinking mode",
        context_window=200000,
        is_default=False,
    ),
    ModelInfo(
        id="claude-opus-4-5",
        name="Claude 4.5 Opus",
        description="Latest model with enhanced coding & reasoning capabilities",
        context_window=200000,
        is_default=False,
    ),
]

CLAUDE_SLASH_COMMANDS: List[SlashCommand] = [
    # Session 管理
    SlashCommand(name="clear", description="清除会话历史", category="session", supports_non_interactive=False),
    SlashCommand(name="compact", description="压缩会话上下文", category="session", supports_non_interactive=True),
    SlashCommand(name="resume", description="恢复之前的会话", category="session", supports_non_interactive=False),
    SlashCommand(name="rename", description="重命名当前会话", category="session", supports_non_interactive=False),
    SlashCommand(name="export", description="导出会话到文件", category="session", supports_non_interactive=False),
    # 上下文和成本
    SlashCommand(name="context", description="查看上下文使用情况", category="context", supports_non_interactive=True),
    SlashCommand(name="cost", description="查看 Token 使用统计", category="context", supports_non_interactive=True),
    SlashCommand(name="usage", description="查看订阅计划用量", category="context", supports_non_interactive=True),
    SlashCommand(name="stats", description="查看使用统计和历史", category="context", supports_non_interactive=True),
    # 系统和配置
    SlashCommand(name="help", description="显示帮助信息", category="system", supports_non_interactive=False),
    SlashCommand(name="config", description="打开设置界面", category="config", supports_non_interactive=False),
    SlashCommand(name="status", description="显示版本和连接状态", category="system", supports_non_interactive=True),
    SlashCommand(name="doctor", description="检查安装健康状态", category="system", supports_non_interactive=True),
    SlashCommand(name="model", description="选择或更换 AI 模型", category="config", supports_non_interactive=False),
    SlashCommand(name="permissions", description="查看或更新权限", category="config", supports_non_interactive=False),
    # 项目和代码
    SlashCommand(name="init", description="初始化项目 CLAUDE.md", category="system", supports_non_interactive=True),
    SlashCommand(name="memory", description="编辑 CLAUDE.md 记忆文件", category="system", supports_non_interactive=False),
    SlashCommand(name="review", description="请求代码审查", category="git", supports_non_interactive=True),
    SlashCommand(name="todos", description="列出当前 TODO 项", category="system", supports_non_interactive=True),
    SlashCommand(name="rewind", description="回退会话或代码", category="git", supports_non_interactive=False),
    # 工具和集成
    SlashCommand(name="mcp", description="管理 MCP 服务器连接", category="system", supports_non_interactive=False),
    SlashCommand(name="hooks", description="管理 Hook 配置", category="config", supports_non_interactive=False),
    SlashCommand(name="plugin", description="管理 Claude Code 插件", category="system", supports_non_interactive=False),
    SlashCommand(name="agents", description="管理自定义 AI 子代理", category="system", supports_non_interactive=False),
    SlashCommand(name="bashes", description="列出后台任务", category="system", supports_non_interactive=True),
]


# ============================================================================
# Codex 模型和命令
# ============================================================================

# Codex 模型列表（与原项目 src/components/FloatingPromptInput/CodexModelSelector.tsx 保持一致）
CODEX_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="gpt-5.2-codex",
        name="GPT-5.2 Codex",
        description="最新代码模型（2025年12月18日发布）",
        context_window=128000,
        is_default=True,
    ),
    ModelInfo(
        id="gpt-5.2",
        name="GPT-5.2",
        description="最新旗舰模型（2025年12月）",
        context_window=128000,
        is_default=False,
    ),
    ModelInfo(
        id="gpt-5.1-codex-max",
        name="GPT-5.1 Codex Max",
        description="代码编写优化，速度与质量平衡",
        context_window=128000,
        is_default=False,
    ),
    ModelInfo(
        id="gpt-5.1-codex",
        name="GPT-5.1 Codex",
        description="专注代码生成的基础版本",
        context_window=128000,
        is_default=False,
    ),
    ModelInfo(
        id="gpt-5.1",
        name="GPT-5.1",
        description="通用大语言模型",
        context_window=128000,
        is_default=False,
    ),
]

CODEX_SLASH_COMMANDS: List[SlashCommand] = [
    # 会话管理
    SlashCommand(name="clear", description="清除会话历史", category="session", supports_non_interactive=False),
    SlashCommand(name="compact", description="压缩会话上下文", category="session", supports_non_interactive=True),
    # 统计和信息
    SlashCommand(name="stats", description="显示 Token 使用统计", category="context", supports_non_interactive=True),
    SlashCommand(name="context", description="查看当前上下文使用", category="context", supports_non_interactive=True),
    # 配置
    SlashCommand(name="help", description="显示帮助信息", category="system", supports_non_interactive=False),
    SlashCommand(name="model", description="选择或更换 AI 模型", category="config", supports_non_interactive=False),
    SlashCommand(name="config", description="查看配置信息", category="config", supports_non_interactive=True),
    # 项目
    SlashCommand(name="init", description="初始化项目配置", category="system", supports_non_interactive=True),
    SlashCommand(name="review", description="代码审查", category="git", supports_non_interactive=True),
]


# ============================================================================
# Gemini 模型和命令
# ============================================================================

# Gemini 模型列表
GEMINI_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="gemini-3-flash",
        name="Gemini 3 Flash",
        description="Latest and fastest model (December 17, 2025)",
        context_window=1000000,
        is_default=True,
    ),
    ModelInfo(
        id="gemini-3-pro",
        name="Gemini 3 Pro",
        description="Most capable reasoning and coding model",
        context_window=1000000,
        is_default=False,
    ),
    ModelInfo(
        id="gemini-3-pro-preview",
        name="Gemini 3 Pro (Preview)",
        description="Experimental preview version",
        context_window=1000000,
        is_default=False,
    ),
    ModelInfo(
        id="gemini-3-flash-thinking",
        name="Gemini 3 Flash Thinking",
        description="Flash model with chain-of-thought reasoning",
        context_window=1000000,
        is_default=False,
    ),
]

GEMINI_SLASH_COMMANDS: List[SlashCommand] = [
    # 会话管理
    SlashCommand(name="clear", description="清除当前会话历史", category="session", supports_non_interactive=False),
    SlashCommand(name="compact", description="压缩会话上下文", category="session", supports_non_interactive=True),
    SlashCommand(name="save", description="保存当前会话到文件", category="session", supports_non_interactive=False),
    SlashCommand(name="load", description="加载已保存的会话", category="session", supports_non_interactive=False),
    # 统计和信息
    SlashCommand(name="stats", description="显示 Token 使用统计", category="context", supports_non_interactive=True),
    SlashCommand(name="context", description="查看当前上下文使用", category="context", supports_non_interactive=True),
    # 配置
    SlashCommand(name="help", description="显示帮助信息", category="system", supports_non_interactive=False),
    SlashCommand(name="settings", description="打开设置界面", category="config", supports_non_interactive=False),
    SlashCommand(name="model", description="选择或更换 AI 模型", category="config", supports_non_interactive=False),
    SlashCommand(name="tools", description="管理可用工具列表", category="config", supports_non_interactive=False),
    # 扩展管理
    SlashCommand(name="extensions", description="管理 Gemini CLI 扩展", category="system", supports_non_interactive=False),
    SlashCommand(name="mcp", description="管理 MCP 服务器连接", category="system", supports_non_interactive=False),
    # 项目
    SlashCommand(name="init", description="初始化项目 GEMINI.md", category="system", supports_non_interactive=True),
    SlashCommand(name="memory", description="编辑 GEMINI.md 记忆文件", category="system", supports_non_interactive=False),
    # 其他
    SlashCommand(name="quit", description="退出 Gemini CLI", category="session", supports_non_interactive=False),
    SlashCommand(name="version", description="显示版本信息", category="system", supports_non_interactive=True),
]


# ============================================================================
# 路由端点
# ============================================================================

@router.get(
    "/v1/claude/models",
    response_model=List[ModelInfo],
    summary="获取 Claude 可用模型列表",
)
async def get_claude_models() -> List[ModelInfo]:
    """从 ~/.claude/config.json 的 env 字段读取模型配置"""
    config = get_claude_config()
    env = config.get("env", {})

    models = []

    # 读取配置的模型
    sonnet = env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or env.get("ANTHROPIC_MODEL")
    opus = env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
    haiku = env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
    reasoning = env.get("ANTHROPIC_REASONING_MODEL")

    # 添加 Sonnet 模型
    if sonnet:
        models.append(ModelInfo(
            id=sonnet,
            name=f"Sonnet ({sonnet})",
            description=sonnet,
            context_window=200000,
            is_default=True,
        ))

    # 添加 Opus 模型
    if opus:
        models.append(ModelInfo(
            id=opus,
            name=f"Opus ({opus})",
            description=opus,
            context_window=200000,
            is_default=False,
        ))

    # 添加 Haiku 模型
    if haiku:
        models.append(ModelInfo(
            id=haiku,
            name=f"Haiku ({haiku})",
            description=haiku,
            context_window=200000,
            is_default=False,
        ))

    # 添加 Reasoning 模型
    if reasoning and reasoning not in [sonnet, opus, haiku]:
        models.append(ModelInfo(
            id=reasoning,
            name=f"Reasoning ({reasoning})",
            description=reasoning,
            context_window=200000,
            is_default=False,
        ))

    # 如果没有配置或只有一个默认模型，返回硬编码列表
    if not models or len(models) == 1:
        return CLAUDE_MODELS

    return models


@router.get(
    "/v1/codex/models",
    response_model=List[ModelInfo],
    summary="获取 Codex 可用模型列表",
)
async def get_codex_models() -> List[ModelInfo]:
    """从 ~/.codex/config.toml 读取 model 配置"""
    config = get_codex_config()
    model = config.get("model")

    if model:
        return [
            ModelInfo(
                id=model,
                name=model,
                description=f"Configured model: {model}",
                context_window=128000,
                is_default=True,
            )
        ]

    # 默认返回
    return CODEX_MODELS


@router.get(
    "/v1/gemini/models",
    response_model=List[ModelInfo],
    summary="获取 Gemini 可用模型列表",
)
async def get_gemini_models() -> List[ModelInfo]:
    """从 ~/.gemini/.env 或环境变量读取 GEMINI_MODEL"""
    env = get_gemini_env()
    model = env.get("GEMINI_MODEL")

    if model:
        return [
            ModelInfo(
                id=model,
                name=model,
                description=f"Configured model: {model}",
                context_window=1000000,
                is_default=True,
            )
        ]

    # 默认返回
    return GEMINI_MODELS


async def _build_slash_commands(
    engine_lower: str,
    project_path: Optional[str] = None,
) -> List[SlashCommand]:
    if engine_lower == "claude":
        built_in = CLAUDE_SLASH_COMMANDS
    elif engine_lower == "codex":
        built_in = CODEX_SLASH_COMMANDS
    elif engine_lower == "gemini":
        built_in = GEMINI_SLASH_COMMANDS
    else:
        built_in = []

    custom_commands: List[SlashCommand] = []
    try:
        if engine_lower == "claude":
            custom_list = list_custom_slash_commands(project_path)
            custom_list.extend(list_agent_slash_commands(project_path))
        elif engine_lower == "gemini":
            custom_list = list_gemini_custom_slash_commands(project_path)
        elif engine_lower == "codex":
            custom_list = list_codex_custom_slash_commands(project_path)
        else:
            custom_list = []

        seen = set()
        for cmd in custom_list:
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            custom_commands.append(
                SlashCommand(
                    name=cmd.name,
                    description=cmd.description or f"自定义命令: {cmd.name}",
                    category="custom" if cmd.scope == "user" else "project",
                    supports_non_interactive=True,
                )
            )
    except Exception:
        pass

    return built_in + custom_commands


@router.get(
    "/v1/claude/slash-commands",
    response_model=List[SlashCommand],
    summary="获取 Claude 斜杠命令列表",
)
async def get_claude_slash_commands(
    project_path: Optional[str] = Query(None, description="项目路径，用于加载项目级自定义命令"),
) -> List[SlashCommand]:
    return await _build_slash_commands("claude", project_path)


@router.get(
    "/v1/codex/slash-commands",
    response_model=List[SlashCommand],
    summary="获取 Codex 斜杠命令列表",
)
async def get_codex_slash_commands(
    project_path: Optional[str] = Query(None, description="项目路径，用于加载项目级自定义命令"),
) -> List[SlashCommand]:
    return await _build_slash_commands("codex", project_path)


@router.get(
    "/v1/gemini/slash-commands",
    response_model=List[SlashCommand],
    summary="获取 Gemini 斜杠命令列表",
)
async def get_gemini_slash_commands(
    project_path: Optional[str] = Query(None, description="项目路径，用于加载项目级自定义命令"),
) -> List[SlashCommand]:
    return await _build_slash_commands("gemini", project_path)


@router.get(
    "/v1/{engine}/models",
    response_model=List[ModelInfo],
    summary="获取指定引擎的可用模型列表",
)
async def get_engine_models(engine: str) -> List[ModelInfo]:
    """统一接口：根据引擎名获取模型列表（从配置文件动态读取）"""
    engine_lower = engine.lower()
    if engine_lower == "claude":
        return await get_claude_models()
    elif engine_lower == "codex":
        return await get_codex_models()
    elif engine_lower == "gemini":
        return await get_gemini_models()
    else:
        return []


@router.get(
    "/v1/{engine}/slash-commands",
    response_model=List[SlashCommand],
    summary="获取指定引擎的斜杠命令列表",
)
async def get_engine_slash_commands(
    engine: str,
    project_path: Optional[str] = Query(None, description="项目路径，用于加载项目级自定义命令"),
) -> List[SlashCommand]:
    """统一接口：根据引擎名获取斜杠命令列表（内置 + 自定义）"""
    engine_lower = engine.lower()

    return await _build_slash_commands(engine_lower, project_path)


@router.get(
    "/v1/{engine}/custom-commands",
    summary="获取自定义斜杠命令列表",
)
async def get_custom_slash_commands(
    engine: str,
    project_path: Optional[str] = Query(None, description="项目路径"),
):
    """获取用户和项目级别的自定义斜杠命令"""
    engine_lower = engine.lower()

    try:
        if engine_lower == "claude":
            commands = list_custom_slash_commands(project_path)
        elif engine_lower == "gemini":
            commands = list_gemini_custom_slash_commands(project_path)
        elif engine_lower == "codex":
            commands = list_codex_custom_slash_commands(project_path)
        else:
            return []
        return [
            {
                "name": cmd.name,
                "description": cmd.description,
                "scope": cmd.scope,
                "path": cmd.path,
                "arg_hint": cmd.arg_hint,
            }
            for cmd in commands
        ]
    except Exception as e:
        return {"error": str(e), "commands": []}
