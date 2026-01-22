"""
自定义斜杠命令服务

扫描并加载用户和项目级别的自定义斜杠命令
- 用户级别: ~/.claude/commands/*.md
- 项目级别: {projectPath}/.claude/commands/*.md
"""
import os
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

import structlog

logger = structlog.get_logger()


class CustomSlashCommand(BaseModel):
    """自定义斜杠命令"""
    name: str
    path: str
    scope: str  # "user" | "project"
    description: Optional[str] = None
    arg_hint: Optional[str] = None
    content: str


def get_claude_dir() -> Path:
    """获取 Claude 配置目录"""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~"
    return Path(home).expanduser() / ".claude"


def get_codex_dir() -> Path:
    """获取 Codex 配置目录"""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~"
    return Path(home).expanduser() / ".codex"


def get_gemini_dir() -> Path:
    """获取 Gemini 配置目录"""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~"
    return Path(home).expanduser() / ".gemini"


def parse_command_file(file_path: Path) -> tuple[Optional[str], Optional[str]]:
    """解析命令文件，提取描述和参数提示

    支持的格式:
    ---
    description: 命令描述
    arg_hint: <参数提示>
    ---

    或者使用第一行注释作为描述
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read command file", path=str(file_path), error=str(e))
        return None, None

    description = None
    arg_hint = None

    # 尝试解析 YAML front matter
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx > 0:
            front_matter = content[3:end_idx].strip()
            for line in front_matter.split("\n"):
                line = line.strip()
                if line.startswith("description:"):
                    description = line[12:].strip().strip('"\'')
                elif line.startswith("arg_hint:"):
                    arg_hint = line[9:].strip().strip('"\'')
                elif line.startswith("argument-hint:"):
                    arg_hint = line[14:].strip().strip('"\'')

    # 如果没有 front matter，使用第一行作为描述
    if not description:
        first_line = content.split("\n")[0].strip()
        # 移除 markdown 标题符号
        if first_line.startswith("#"):
            description = first_line.lstrip("#").strip()
        elif first_line:
            description = first_line[:100]  # 限制长度

    return description, arg_hint


def scan_commands_directory(
    commands_dir: Path,
    scope: str,
) -> List[CustomSlashCommand]:
    """扫描命令目录，返回命令列表（支持子目录）"""
    commands = []

    if not commands_dir.exists() or not commands_dir.is_dir():
        return commands

    # 递归扫描 .md 文件，兼容 nested/index.md 形式
    for file_path in commands_dir.rglob("*.md"):
        if not file_path.is_file():
            continue

        try:
            relative_path = file_path.relative_to(commands_dir)
        except ValueError:
            continue

        parts = relative_path.parts
        if len(parts) == 1:
            command_id = relative_path.stem
        elif len(parts) == 2:
            parent_name = parts[0]
            file_name = Path(parts[1]).stem
            if (
                file_name == "index"
                or file_name.startswith("$")
                or file_name == parent_name
                or file_name.lower() == "readme"
            ):
                command_id = parent_name
            else:
                command_id = f"{parent_name}:{file_name}"
        else:
            continue

        if not command_id or command_id.startswith("."):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read command file", path=str(file_path), error=str(e))
            continue

        description, arg_hint = parse_command_file(file_path)

        commands.append(CustomSlashCommand(
            name=command_id,
            path=str(file_path),
            scope=scope,
            description=description,
            arg_hint=arg_hint,
            content=content,
        ))

    logger.info(
        "Scanned commands directory",
        directory=str(commands_dir),
        scope=scope,
        count=len(commands),
    )

    return commands


def parse_gemini_command_toml(file_path: Path) -> tuple[Optional[str], Optional[str]]:
    """解析 Gemini 命令 TOML 文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read gemini command file", path=str(file_path), error=str(e))
        return None, None

    try:
        import tomli
        value = tomli.loads(content)
        description = value.get("description")
        if description is not None:
            description = str(description).strip()
        arg_hint = value.get("argument-hint") or value.get("argHint")
        if arg_hint is not None:
            arg_hint = str(arg_hint).strip()
        return description or None, arg_hint or None
    except Exception:
        pass

    first_line = content.split("\n")[0].strip()
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip(), None

    return None, None


def scan_gemini_commands_directory(
    commands_dir: Path,
    scope: str,
) -> List[CustomSlashCommand]:
    """扫描 Gemini 命令目录（.toml，支持命名空间）"""
    commands = []

    if not commands_dir.exists() or not commands_dir.is_dir():
        return commands

    for file_path in commands_dir.rglob("*.toml"):
        if not file_path.is_file():
            continue

        try:
            relative_path = file_path.relative_to(commands_dir)
        except ValueError:
            continue

        parts = relative_path.parts
        if len(parts) == 1:
            command_id = relative_path.stem
        elif len(parts) == 2:
            command_id = f"{parts[0]}:{Path(parts[1]).stem}"
        else:
            continue

        if not command_id or command_id.startswith("."):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read gemini command file", path=str(file_path), error=str(e))
            continue

        description, arg_hint = parse_gemini_command_toml(file_path)

        commands.append(CustomSlashCommand(
            name=command_id,
            path=str(file_path),
            scope=scope,
            description=description,
            arg_hint=arg_hint,
            content=content,
        ))

    logger.info(
        "Scanned gemini commands directory",
        directory=str(commands_dir),
        scope=scope,
        count=len(commands),
    )

    return commands


def list_custom_slash_commands(
    project_path: Optional[str] = None,
) -> List[CustomSlashCommand]:
    """列出所有自定义斜杠命令

    Args:
        project_path: 项目路径（可选），用于加载项目级别命令

    Returns:
        自定义命令列表（用户级别 + 项目级别）
    """
    commands: List[CustomSlashCommand] = []

    # 1. 加载用户级别命令 (~/.claude/commands/*.md)
    user_commands_dir = get_claude_dir() / "commands"
    commands.extend(scan_commands_directory(user_commands_dir, "user"))

    # 2. 加载项目级别命令 ({projectPath}/.claude/commands/*.md)
    if project_path:
        project_commands_dir = Path(project_path) / ".claude" / "commands"
        commands.extend(scan_commands_directory(project_commands_dir, "project"))

    logger.info(
        "Listed custom slash commands",
        total=len(commands),
        user_count=len([c for c in commands if c.scope == "user"]),
        project_count=len([c for c in commands if c.scope == "project"]),
    )

    return commands


def list_codex_custom_slash_commands(
    project_path: Optional[str] = None,
) -> List[CustomSlashCommand]:
    """列出 Codex 自定义斜杠命令（.codex/commands）"""
    commands: List[CustomSlashCommand] = []

    user_commands_dir = get_codex_dir() / "commands"
    commands.extend(scan_commands_directory(user_commands_dir, "user"))

    if project_path:
        project_commands_dir = Path(project_path) / ".codex" / "commands"
        commands.extend(scan_commands_directory(project_commands_dir, "project"))

    logger.info(
        "Listed codex custom slash commands",
        total=len(commands),
        user_count=len([c for c in commands if c.scope == "user"]),
        project_count=len([c for c in commands if c.scope == "project"]),
    )

    return commands


def list_gemini_custom_slash_commands(
    project_path: Optional[str] = None,
) -> List[CustomSlashCommand]:
    """列出 Gemini 自定义斜杠命令（.gemini/commands）"""
    commands: List[CustomSlashCommand] = []

    user_commands_dir = get_gemini_dir() / "commands"
    commands.extend(scan_gemini_commands_directory(user_commands_dir, "user"))

    if project_path:
        project_commands_dir = Path(project_path) / ".gemini" / "commands"
        commands.extend(scan_gemini_commands_directory(project_commands_dir, "project"))

    logger.info(
        "Listed gemini custom slash commands",
        total=len(commands),
        user_count=len([c for c in commands if c.scope == "user"]),
        project_count=len([c for c in commands if c.scope == "project"]),
    )

    return commands


def scan_agents_directory(
    agents_dir: Path,
    scope: str,
) -> List[CustomSlashCommand]:
    """扫描 Claude agents 目录，将子代理映射为斜杠命令"""
    commands: List[CustomSlashCommand] = []

    if not agents_dir.exists() or not agents_dir.is_dir():
        return commands

    group_names = set()

    for file_path in agents_dir.rglob("*.md"):
        if not file_path.is_file():
            continue

        try:
            relative_path = file_path.relative_to(agents_dir)
        except ValueError:
            continue

        parts = relative_path.parts
        if len(parts) == 1:
            command_id = relative_path.stem
        elif len(parts) == 2:
            parent_name = parts[0]
            file_name = Path(parts[1]).stem
            group_names.add(parent_name)
            if (
                file_name == "index"
                or file_name.startswith("$")
                or file_name == parent_name
                or file_name.lower() == "readme"
            ):
                command_id = parent_name
            else:
                command_id = f"{parent_name}:{file_name}"
        else:
            continue

        if not command_id or command_id.startswith("."):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read agent file", path=str(file_path), error=str(e))
            continue

        description, arg_hint = parse_command_file(file_path)
        commands.append(
            CustomSlashCommand(
                name=command_id,
                path=str(file_path),
                scope=scope,
                description=description,
                arg_hint=arg_hint,
                content=content,
            )
        )

    # Create a synthetic group command (e.g. /ccg) if only subcommands exist
    existing = {cmd.name for cmd in commands}
    for group in group_names:
        if group not in existing and group and not group.startswith("."):
            commands.append(
                CustomSlashCommand(
                    name=group,
                    path=str(agents_dir / group),
                    scope=scope,
                    description=f"Subagent group: {group}",
                    arg_hint=None,
                    content="",
                )
            )

    logger.info(
        "Scanned agents directory",
        directory=str(agents_dir),
        scope=scope,
        count=len(commands),
    )

    return commands


def list_agent_slash_commands(
    project_path: Optional[str] = None,
) -> List[CustomSlashCommand]:
    """列出 Claude agents 的斜杠命令（.claude/agents）"""
    commands: List[CustomSlashCommand] = []

    user_agents_dir = get_claude_dir() / "agents"
    commands.extend(scan_agents_directory(user_agents_dir, "user"))

    if project_path:
        project_agents_dir = Path(project_path) / ".claude" / "agents"
        commands.extend(scan_agents_directory(project_agents_dir, "project"))

    logger.info(
        "Listed agent slash commands",
        total=len(commands),
        user_count=len([c for c in commands if c.scope == "user"]),
        project_count=len([c for c in commands if c.scope == "project"]),
    )

    return commands


def get_command_content(command_name: str, project_path: Optional[str] = None) -> Optional[str]:
    """获取指定命令的内容

    Args:
        command_name: 命令名称（不含 /）
        project_path: 项目路径

    Returns:
        命令内容，如果不存在返回 None
    """
    commands = list_custom_slash_commands(project_path)

    for cmd in commands:
        if cmd.name == command_name:
            return cmd.content

    return None
