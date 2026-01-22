"""
统一配置管理服务（ConfigHub）

提供对 Claude/Codex/Gemini CLI 配置文件的统一 CRUD 和启用/禁用操作。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from app.core.errors import APIError
from app.services.claude.plugin_runner import PluginCLIRunner
from app.services.config_manager.backups import BackupManager
from app.services.config_manager.locks import FileLockProvider
from app.services.config_manager.parsers import ConfigParsers

logger = structlog.get_logger()


@dataclass(frozen=True)
class ConfigScope:
    """配置文件解析范围"""

    scope: str  # "user" | "project" | "auto"
    project_root: Optional[Path] = None


class ConfigHubService:
    """
    ConfigHub 统一配置管理服务

    提供对 Claude/Codex/Gemini 三个引擎的配置文件统一管理接口，
    支持 CRUD 操作、启用/禁用功能、自动备份和文件锁机制。
    """

    def __init__(
        self,
        lock_provider: FileLockProvider,
        backup_manager: BackupManager,
        parsers: ConfigParsers,
        plugin_runner: Optional[PluginCLIRunner] = None,
    ) -> None:
        """
        初始化 ConfigHub 服务

        Args:
            lock_provider: 文件锁提供者
            backup_manager: 备份管理器
            parsers: 配置文件解析器
            plugin_runner: 插件 CLI 运行器（可选，默认创建新实例）
        """
        self._locks = lock_provider
        self._backups = backup_manager
        self._parsers = parsers
        self._plugin_runner = plugin_runner or PluginCLIRunner()

    # ==================== 提示词配置管理 ====================

    def read_prompt_config(self, engine: str, scope: ConfigScope) -> Dict[str, Any]:
        """
        读取指定引擎的 Prompts 专用配置

        与主配置分离，仅返回提示词数据，避免泄露供应商信息（API Key 等）

        Args:
            engine: 引擎名称 ("claude" | "codex" | "gemini")
            scope: 配置范围

        Returns:
            Prompts 配置字典，结构：
            {
                "schemaVersion": "1.0",
                "prompts": {
                    "prompt-id": {
                        "name": "Prompt Name",
                        "content": "Prompt content...",
                        "enabled": true
                    }
                }
            }

        Raises:
            APIError: 读取失败时抛出（文件不存在时返回默认值）
        """
        path = self._resolve_prompts_config(engine, scope)

        # 文件不存在时，尝试从主配置文件读取（向后兼容）
        if not path.exists():
            logger.info(
                "prompts_config_not_found_trying_legacy",
                engine=engine,
                path=str(path),
            )
            # 尝试从主配置文件读取
            try:
                main_config_path = self._resolve_engine_config(engine, scope)
                if main_config_path.exists():
                    main_config = self._read_config(main_config_path)
                    if "prompts" in main_config:
                        logger.info(
                            "prompts_loaded_from_legacy_config",
                            engine=engine,
                            count=len(main_config.get("prompts", {})),
                        )
                        return {
                            "schemaVersion": "1.0",
                            "prompts": main_config["prompts"],
                        }
            except Exception as exc:
                logger.warning(
                    "prompts_legacy_read_failed",
                    engine=engine,
                    error=str(exc),
                )

            # 返回默认空配置
            return {
                "schemaVersion": "1.0",
                "prompts": {},
            }

        try:
            config = self._read_config(path)
            # 确保配置包含必需字段
            if "prompts" not in config:
                config["prompts"] = {}
            if "schemaVersion" not in config:
                config["schemaVersion"] = "1.0"
            return config
        except APIError as exc:
            # 文件损坏或解析失败时返回默认值
            logger.warning(
                "prompts_config_read_failed",
                engine=engine,
                path=str(path),
                error=str(exc),
            )
            return {
                "schemaVersion": "1.0",
                "prompts": {},
            }

    def write_prompt_config(
        self, engine: str, scope: ConfigScope, data: Dict[str, Any]
    ) -> None:
        """
        写入指定引擎的 Prompts 专用配置

        Args:
            engine: 引擎名称
            scope: 配置范围
            data: 配置数据（应包含 schemaVersion 和 prompts 字段）

        Raises:
            APIError: 写入失败时抛出
        """
        # 确保数据结构完整
        if "schemaVersion" not in data:
            data["schemaVersion"] = "1.0"
        if "prompts" not in data:
            data["prompts"] = {}

        path = self._resolve_prompts_config(engine, scope)
        self._write_config(path, data)

    def read_engine_config(self, engine: str, scope: ConfigScope) -> Dict[str, Any]:
        """
        读取指定引擎的完整配置

        返回完整的 settings.json 内容。

        Args:
            engine: 引擎名称 ("claude" | "codex" | "gemini")
            scope: 配置范围

        Returns:
            完整配置字典（包含所有字段：env、mcpServers、prompts 等）

        Raises:
            APIError: 读取失败时抛出
        """
        path = self._resolve_engine_config(engine, scope)

        if not path.exists():
            logger.warning("engine_config_not_found", engine=engine, path=str(path))
            return {}

        return self._read_config(path)

    # ==================== Provider 配置管理 ====================

    def read_provider_config(self, engine: str) -> Dict[str, Any]:
        """
        读取指定引擎的 Provider 配置（API Key、Base URL 等）

        对于 Claude: 读取 ~/.claude/settings.json 的 env 字段
        对于 Codex: 读取 ~/.codex/auth.json 和 ~/.codex/config.toml
        对于 Gemini: 读取 ~/.gemini/.env 和 ~/.gemini/settings.json

        Args:
            engine: 引擎名称 ("claude" | "codex" | "gemini")

        Returns:
            配置字典

        Raises:
            APIError: 读取失败时抛出
        """
        engine_lower = engine.lower().strip()

        if engine_lower == "claude":
            # Claude 读取 ~/.claude/settings.json
            settings_path = Path("~/.claude/settings.json").expanduser()
            if not settings_path.exists():
                return {}
            config = self._read_config(settings_path)
            # 返回完整的 settings.json 内容（包含 env 和 apiKeyHelper）
            return config
        elif engine_lower == "codex":
            # Codex 读取 ~/.codex/auth.json 和 ~/.codex/config.toml
            codex_dir = Path("~/.codex").expanduser()
            auth_path = codex_dir / "auth.json"
            config_path = codex_dir / "config.toml"

            result = {}

            # 读取 auth.json
            if auth_path.exists():
                result["auth"] = self._read_config(auth_path)
            else:
                result["auth"] = {}

            # 读取 config.toml
            if config_path.exists():
                result["config"] = self._read_config(config_path)
            else:
                result["config"] = {}

            return result
        elif engine_lower == "gemini":
            # Gemini 读取 ~/.gemini/.env 和 ~/.gemini/settings.json
            gemini_dir = Path("~/.gemini").expanduser()
            env_path = gemini_dir / ".env"
            settings_path = gemini_dir / "settings.json"

            result = {}

            # 读取 .env 文件
            if env_path.exists():
                env_content = env_path.read_text(encoding="utf-8")
                env_dict = {}
                for line in env_content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # 移除引号
                            value = value.strip().strip('"').strip("'")
                            env_dict[key.strip()] = value
                result["env"] = env_dict
            else:
                result["env"] = {}

            # 读取 settings.json
            if settings_path.exists():
                result["settings"] = self._read_config(settings_path)
            else:
                result["settings"] = {}

            return result
        else:
            return {}

    def read_provider_presets(self, engine: str) -> List[Dict[str, Any]]:
        """
        读取指定引擎的 Provider 预设列表（用户保存的配置）

        对于 Claude: 读取 ~/.claude/providers.json
        对于 Codex: 读取 ~/.codex/providers.json
        对于 Gemini: 读取 ~/.anycode/gemini_providers.json

        注意：这里只返回用户保存的配置，不包含内置预设
        内置预设应该在前端代码中定义

        Args:
            engine: 引擎名称 ("claude" | "codex" | "gemini")

        Returns:
            预设列表

        Raises:
            APIError: 读取失败时抛出
        """
        engine_lower = engine.lower().strip()

        if engine_lower == "claude":
            presets_path = Path("~/.claude/providers.json").expanduser()
        elif engine_lower == "codex":
            presets_path = Path("~/.codex/providers.json").expanduser()
        elif engine_lower == "gemini":
            presets_path = Path("~/.anycode/gemini_providers.json").expanduser()
        else:
            return []

        if not presets_path.exists():
            return []

        try:
            presets = self._read_config(presets_path)
            if isinstance(presets, list):
                return presets
            return []
        except Exception:
            return []

    def create_provider_preset(self, engine: str, preset: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建 Provider 预设

        Args:
            engine: 引擎名称
            preset: 预设配置

        Returns:
            创建的预设

        Raises:
            APIError: 创建失败时抛出
        """
        presets = self.read_provider_presets(engine)

        # 检查 ID 是否已存在
        preset_id = preset.get("id")
        if any(p.get("id") == preset_id for p in presets):
            raise APIError(
                status_code=400,
                code="PRESET_EXISTS",
                message=f"Preset with ID '{preset_id}' already exists",
            )

        presets.append(preset)
        self._write_provider_presets(engine, presets)

        return preset

    def update_provider_preset(
        self, engine: str, preset_id: str, preset: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新 Provider 预设

        Args:
            engine: 引擎名称
            preset_id: 预设 ID
            preset: 预设配置

        Returns:
            更新后的预设

        Raises:
            APIError: 更新失败时抛出
        """
        presets = self.read_provider_presets(engine)

        # 查找预设
        index = next((i for i, p in enumerate(presets) if p.get("id") == preset_id), None)
        if index is None:
            raise APIError(
                status_code=404,
                code="PRESET_NOT_FOUND",
                message=f"Preset with ID '{preset_id}' not found",
            )

        presets[index] = preset
        self._write_provider_presets(engine, presets)

        return preset

    def delete_provider_preset(self, engine: str, preset_id: str) -> None:
        """
        删除 Provider 预设

        Args:
            engine: 引擎名称
            preset_id: 预设 ID

        Raises:
            APIError: 删除失败时抛出
        """
        presets = self.read_provider_presets(engine)

        # 查找并删除预设
        initial_len = len(presets)
        presets = [p for p in presets if p.get("id") != preset_id]

        if len(presets) == initial_len:
            raise APIError(
                status_code=404,
                code="PRESET_NOT_FOUND",
                message=f"Preset with ID '{preset_id}' not found",
            )

        self._write_provider_presets(engine, presets)

    def switch_provider(self, engine: str, preset_id: str) -> Dict[str, Any]:
        """
        切换到指定的 Provider 预设

        Args:
            engine: 引擎名称
            preset_id: 预设 ID

        Returns:
            切换后的配置

        Raises:
            APIError: 切换失败时抛出
        """
        presets = self.read_provider_presets(engine)

        # 查找预设
        preset = next((p for p in presets if p.get("id") == preset_id), None)
        if preset is None:
            raise APIError(
                status_code=404,
                code="PRESET_NOT_FOUND",
                message=f"Preset with ID '{preset_id}' not found",
            )

        # 根据引擎类型应用配置
        engine_lower = engine.lower().strip()

        if engine_lower == "claude":
            # Claude: 写入 ~/.claude/settings.json
            self._switch_claude_provider(preset)
        elif engine_lower == "codex":
            # Codex: 写入 ~/.codex/auth.json 和 ~/.codex/config.toml
            self._switch_codex_provider(preset)
        elif engine_lower == "gemini":
            # Gemini: 写入 ~/.gemini/.env 和 ~/.gemini/settings.json
            self._switch_gemini_provider(preset)

        # 返回当前配置
        return self.read_provider_config(engine)

    def _write_provider_presets(self, engine: str, presets: List[Dict[str, Any]]) -> None:
        """写入 Provider 预设列表"""
        engine_lower = engine.lower().strip()

        if engine_lower == "claude":
            presets_path = Path("~/.claude/providers.json").expanduser()
        elif engine_lower == "codex":
            presets_path = Path("~/.codex/providers.json").expanduser()
        elif engine_lower == "gemini":
            presets_path = Path("~/.anycode/gemini_providers.json").expanduser()
        else:
            raise APIError(
                status_code=400,
                code="INVALID_ENGINE",
                message="不支持的引擎类型",
            )

        self._write_config(presets_path, presets)

    def _switch_claude_provider(self, preset: Dict[str, Any]) -> None:
        """切换 Claude Provider"""
        settings_path = Path("~/.claude/settings.json").expanduser()

        # 读取现有配置
        if settings_path.exists():
            settings = self._read_config(settings_path)
        else:
            settings = {}

        # 更新 env 字段
        if "env" in preset:
            settings["env"] = preset["env"]

        # 更新 apiKeyHelper 字段
        if "apiKeyHelper" in preset:
            settings["apiKeyHelper"] = preset["apiKeyHelper"]

        self._write_config(settings_path, settings)

    def _switch_codex_provider(self, preset: Dict[str, Any]) -> None:
        """切换 Codex Provider"""
        codex_dir = Path("~/.codex").expanduser()
        auth_path = codex_dir / "auth.json"
        config_path = codex_dir / "config.toml"

        # 写入 auth.json
        if "auth" in preset:
            self._write_config(auth_path, preset["auth"])

        # 写入 config.toml
        if "config" in preset:
            # config 可能是字符串或字典
            config_data = preset["config"]
            if isinstance(config_data, str):
                # 如果是字符串，直接写入
                config_path.write_text(config_data, encoding="utf-8")
            else:
                # 如果是字典，序列化为 TOML
                self._write_config(config_path, config_data)

    def _switch_gemini_provider(self, preset: Dict[str, Any]) -> None:
        """切换 Gemini Provider"""
        gemini_dir = Path("~/.gemini").expanduser()
        env_path = gemini_dir / ".env"
        settings_path = gemini_dir / "settings.json"

        # 写入 .env 文件
        if "env" in preset:
            env_dict = preset["env"]
            env_content = "# Gemini CLI Configuration\n# Generated by AnyCode\n\n"
            for key, value in env_dict.items():
                if ' ' in value or '"' in value:
                    env_content += f'{key}="{value.replace(chr(34), chr(92) + chr(34))}"\n'
                else:
                    env_content += f"{key}={value}\n"
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(env_content, encoding="utf-8")

        # 写入 settings.json
        if "settings" in preset:
            self._write_config(settings_path, preset["settings"])

    def update_provider_config(self, engine: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新指定引擎的 Provider 配置（浅合并）

        对于 Claude: 更新 ~/.claude/settings.json
        对于 Codex/Gemini: 更新主配置文件

        Args:
            engine: 引擎名称
            patch: 要更新的字段

        Returns:
            更新后的完整配置

        Raises:
            APIError: 更新失败时抛出
        """
        engine_lower = engine.lower().strip()

        if engine_lower == "claude":
            # Claude 更新 ~/.claude/settings.json
            settings_path = Path("~/.claude/settings.json").expanduser()
            if not settings_path.exists():
                data = {}
            else:
                data = self._read_config(settings_path)
            data.update(patch)
            self._write_config(settings_path, data)
            return data
        else:
            # Codex/Gemini 更新主配置文件
            path = self._resolve_engine_config(engine, ConfigScope(scope="user"))
            if not path.exists():
                data = {}
            else:
                data = self._read_config(path)
            data.update(patch)
            self._write_config(path, data)
            return data

    # ==================== Subagents 管理 ====================

    def list_agents(self, scope: ConfigScope) -> List[Dict[str, Any]]:
        """
        列出所有 Claude Subagents

        Args:
            scope: 配置范围

        Returns:
            Subagent 列表，每个元素包含 id、path、metadata、content、enabled 字段
        """
        agent_dir = self._resolve_agents_dir(scope)
        if not agent_dir.exists():
            return []

        agents = []
        agent_root = agent_dir.resolve()
        for path in agent_dir.rglob("*.md"):
            try:
                resolved_path = path.resolve()

                # 跳过非文件（如符号链接到目录）
                if not resolved_path.is_file():
                    continue

                try:
                    relative_path = resolved_path.relative_to(agent_root)
                except ValueError:
                    logger.warning(
                        "agent_path_outside_root",
                        path=str(path),
                        root=str(agent_root),
                    )
                    continue
                meta, content = self._parsers.read_markdown_frontmatter(resolved_path)
                relative_id = relative_path.with_suffix("").as_posix()
                agents.append(
                    {
                        "id": relative_id,
                        "path": str(resolved_path),
                        "metadata": meta,
                        "content": content,
                        "enabled": bool(meta.get("enabled", True)),
                    }
                )
            except APIError as exc:
                logger.warning("agent_load_failed", path=str(path), error=str(exc))

        return agents

    def get_agent(self, scope: ConfigScope, agent_id: str) -> Dict[str, Any]:
        """
        获取单个 Claude Subagent 的详情

        Args:
            scope: 配置范围
            agent_id: Subagent ID

        Returns:
            Subagent 详情字典

        Raises:
            APIError: Agent 不存在或读取失败时抛出
        """
        path = self._resolve_agent_path(scope, agent_id)
        meta, content = self._parsers.read_markdown_frontmatter(path)
        return {
            "id": agent_id,
            "path": str(path),
            "metadata": meta,
            "content": content,
            "enabled": bool(meta.get("enabled", True)),
        }

    def upsert_agent(
        self, scope: ConfigScope, agent_id: str, metadata: Dict[str, Any], content: str
    ) -> None:
        """
        创建或更新 Claude Subagent

        Args:
            scope: 配置范围
            agent_id: Subagent ID
            metadata: YAML 元数据
            content: Markdown 正文

        Raises:
            APIError: 操作失败时抛出
        """
        path = self._resolve_agent_path(scope, agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._locks.lock(path):
            self._backups.backup(path)
            self._parsers.write_markdown_frontmatter(path, metadata, content)

    def delete_agent(self, scope: ConfigScope, agent_id: str) -> None:
        """
        删除 Claude Subagent

        Args:
            scope: 配置范围
            agent_id: Subagent ID

        Raises:
            APIError: Agent 不存在或删除失败时抛出
        """
        path = self._resolve_agent_path(scope, agent_id)
        if not path.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="Subagent 不存在",
                details=agent_id,
            )

        with self._locks.lock(path):
            self._backups.backup(path)
            path.unlink()

    def toggle_agent(self, scope: ConfigScope, agent_id: str, enabled: bool) -> Dict[str, Any]:
        """
        启用或禁用 Claude Subagent

        Args:
            scope: 配置范围
            agent_id: Subagent ID
            enabled: True 为启用，False 为禁用

        Returns:
            更新后的 Subagent 详情

        Raises:
            APIError: 操作失败时抛出
        """
        agent = self.get_agent(scope, agent_id)
        metadata = dict(agent["metadata"])
        metadata["enabled"] = enabled
        self.upsert_agent(scope, agent_id, metadata, agent["content"])

        agent["enabled"] = enabled
        agent["metadata"] = metadata
        return agent

    # ==================== Skills 管理 ====================

    def list_skills(self, scope: ConfigScope) -> List[Dict[str, Any]]:
        """
        列出所有 Claude Skills

        Args:
            scope: 配置范围

        Returns:
            Skill 列表
        """
        skill_dir = self._resolve_skills_dir(scope)
        if not skill_dir.exists():
            return []

        skills = []
        skill_root = skill_dir.resolve()

        # 递归查找所有 SKILL.md 文件
        for skill_path in skill_dir.rglob("SKILL.md"):
            try:
                resolved_path = skill_path.resolve()

                # 跳过非文件
                if not resolved_path.is_file():
                    continue

                # 安全检查：确保路径在 skill_dir 内
                try:
                    relative_path = resolved_path.relative_to(skill_root)
                except ValueError:
                    logger.warning(
                        "skill_path_outside_root",
                        path=str(skill_path),
                        root=str(skill_root),
                    )
                    continue

                # 生成相对路径 ID（去掉 /SKILL.md 后缀）
                relative_id = relative_path.parent.as_posix()
                # ccg/sub/SKILL.md → ccg/sub

                meta, content = self._parsers.read_markdown_frontmatter(resolved_path)
                skills.append(
                    {
                        "id": relative_id,
                        "path": str(resolved_path),
                        "metadata": meta,
                        "content": content,
                        "enabled": bool(meta.get("enabled", True)),
                    }
                )
            except APIError as exc:
                logger.warning("skill_load_failed", path=str(skill_path), error=str(exc))

        return skills

    def get_skill(self, scope: ConfigScope, skill_id: str) -> Dict[str, Any]:
        """
        获取单个 Claude Skill 的详情

        Args:
            scope: 配置范围
            skill_id: Skill ID

        Returns:
            Skill 详情字典

        Raises:
            APIError: Skill 不存在或读取失败时抛出
        """
        skill_path = self._resolve_skill_path(scope, skill_id)
        meta, content = self._parsers.read_markdown_frontmatter(skill_path)
        return {
            "id": skill_id,
            "path": str(skill_path),
            "metadata": meta,
            "content": content,
            "enabled": bool(meta.get("enabled", True)),
        }

    def upsert_skill(
        self, scope: ConfigScope, skill_id: str, metadata: Dict[str, Any], content: str
    ) -> None:
        """
        创建或更新 Claude Skill

        Args:
            scope: 配置范围
            skill_id: Skill ID
            metadata: YAML 元数据
            content: Markdown 正文

        Raises:
            APIError: 操作失败时抛出
        """
        skill_path = self._resolve_skill_path(scope, skill_id)
        skill_path.parent.mkdir(parents=True, exist_ok=True)

        with self._locks.lock(skill_path):
            self._backups.backup(skill_path)
            self._parsers.write_markdown_frontmatter(skill_path, metadata, content)

    def delete_skill(self, scope: ConfigScope, skill_id: str) -> None:
        """
        删除 Claude Skill

        Args:
            scope: 配置范围
            skill_id: Skill ID

        Raises:
            APIError: Skill 不存在或删除失败时抛出
        """
        skill_path = self._resolve_skill_path(scope, skill_id)
        if not skill_path.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="Skill 不存在",
                details=skill_id,
            )

        with self._locks.lock(skill_path):
            self._backups.backup(skill_path)
            skill_path.unlink()

        # 尝试删除空的父目录
        try:
            skill_path.parent.rmdir()
        except OSError:
            pass

    def toggle_skill(self, scope: ConfigScope, skill_id: str, enabled: bool) -> Dict[str, Any]:
        """
        启用或禁用 Claude Skill

        Args:
            scope: 配置范围
            skill_id: Skill ID
            enabled: True 为启用，False 为禁用

        Returns:
            更新后的 Skill 详情

        Raises:
            APIError: 操作失败时抛出
        """
        skill = self.get_skill(scope, skill_id)
        metadata = dict(skill["metadata"])
        metadata["enabled"] = enabled
        self.upsert_skill(scope, skill_id, metadata, skill["content"])

        skill["enabled"] = enabled
        skill["metadata"] = metadata
        return skill

    # ==================== Plugins 管理 ====================

    async def list_plugins(self, scope: ConfigScope) -> List[Dict[str, Any]]:
        """
        列出 Claude Plugins（服务器级）

        优先通过 Claude CLI 获取插件列表（与官方插件系统一致），
        CLI 失败时回退到目录扫描作为兼容性保障。

        Args:
            scope: 配置范围

        Returns:
            Plugin 列表，每个插件包含 id、path、enabled 等字段
        """
        # 优先尝试通过 CLI 获取插件列表
        try:
            cli_plugins = await self._plugin_runner.list_plugins()
            # 如果 CLI 返回空列表，可能是不支持或失败，回退到目录扫描
            if cli_plugins:
                logger.info(
                    "claude_plugin_list_from_cli",
                    count=len(cli_plugins),
                )
                # 补充 path 和 enabled 字段（CLI 可能不返回）
                # 只返回 id, path, enabled 三个字段，过滤掉其他字段
                plugin_dir = self._resolve_plugins_dir(scope)
                filtered_plugins = []
                for plugin in cli_plugins:
                    plugin_id = plugin.get("id", "")
                    plugin_path = plugin.get("path", str(plugin_dir / plugin_id))
                    plugin_enabled = plugin.get("enabled", True)

                    filtered_plugins.append({
                        "id": plugin_id,
                        "path": plugin_path,
                        "enabled": plugin_enabled,
                    })
                return filtered_plugins
            else:
                logger.info(
                    "claude_plugin_list_cli_empty",
                    fallback="directory_scan",
                )
        except Exception as exc:
            logger.warning(
                "claude_plugin_list_cli_failed",
                error=str(exc),
                fallback="directory_scan",
            )

        # 回退到目录扫描
        plugin_dir = self._resolve_plugins_dir(scope)
        if not plugin_dir.exists():
            return []

        # 读取 installed_plugins.json 文件（如果存在）
        installed_plugins_file = plugin_dir / "installed_plugins.json"
        if installed_plugins_file.exists():
            try:
                import json
                with installed_plugins_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    installed_plugins = data.get("plugins", {})

                    # 如果有已安装的插件，返回它们
                    if installed_plugins:
                        plugins = []
                        for plugin_id, plugin_info in installed_plugins.items():
                            plugin_path = plugin_dir / plugin_id
                            disabled = (plugin_path / ".disabled").exists()
                            plugins.append({
                                "id": plugin_id,
                                "path": str(plugin_path),
                                "enabled": not disabled,
                            })
                        logger.info(
                            "claude_plugin_list_from_installed_json",
                            count=len(plugins),
                        )
                        return plugins
            except Exception as exc:
                logger.warning(
                    "claude_plugin_installed_json_read_failed",
                    error=str(exc),
                )

        # 如果 installed_plugins.json 不存在或为空，扫描目录
        # 只扫描一级子目录，不递归
        plugins = []
        plugin_root = plugin_dir.resolve()

        try:
            for entry in plugin_dir.iterdir():
                # 跳过文件和特殊目录
                if not entry.is_dir():
                    continue

                # 跳过 marketplaces 等特殊目录
                if entry.name in {"marketplaces", ".git", "__pycache__"}:
                    continue

                try:
                    resolved_path = entry.resolve()

                    # 安全检查：确保路径在 plugin_dir 内
                    try:
                        relative_path = resolved_path.relative_to(plugin_root)
                    except ValueError:
                        logger.warning(
                            "plugin_path_outside_root",
                            path=str(entry),
                            root=str(plugin_root),
                        )
                        continue

                    # 使用目录名作为 ID
                    plugin_id = entry.name

                    # 检查是否禁用
                    disabled = (resolved_path / ".disabled").exists()

                    plugins.append(
                        {
                            "id": plugin_id,
                            "path": str(resolved_path),
                            "enabled": not disabled,
                        }
                    )
                except Exception as exc:
                    logger.warning("plugin_load_failed", path=str(entry), error=str(exc))

        except OSError as exc:
            logger.error("plugin_dir_scan_failed", error=str(exc))
            return []

        logger.info(
            "claude_plugin_list_from_directory_scan",
            count=len(plugins),
        )
        return plugins

    async def toggle_plugin(
        self, scope: ConfigScope, plugin_id: str, enabled: bool
    ) -> Dict[str, Any]:
        """
        启用或禁用 Claude Plugin

        优先通过 Claude CLI 执行操作（与官方插件系统一致），
        CLI 失败时回退到文件标记方式作为兼容性保障。

        Args:
            scope: 配置范围
            plugin_id: Plugin ID
            enabled: True 为启用，False 为禁用

        Returns:
            更新后的 Plugin 详情

        Raises:
            APIError: Plugin 不存在或操作失败时抛出
        """
        # 验证 plugin_id 以防止路径遍历攻击
        self._validate_identifier(plugin_id)

        # 优先尝试通过 CLI 操作
        try:
            if enabled:
                result = await self._plugin_runner.enable_plugin(plugin_id)
            else:
                result = await self._plugin_runner.disable_plugin(plugin_id)

            # 补充 path 字段
            plugin_dir = self._resolve_plugins_dir(scope) / plugin_id
            result["path"] = str(plugin_dir)

            logger.info(
                "claude_plugin_toggled_via_cli",
                plugin_id=plugin_id,
                enabled=enabled,
            )
            return result
        except Exception as exc:
            logger.warning(
                "claude_plugin_toggle_cli_failed",
                plugin_id=plugin_id,
                error=str(exc),
                fallback="file_marker",
            )

        # 回退到文件标记方式
        plugin_dir = self._resolve_plugins_dir(scope) / plugin_id
        if not plugin_dir.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="Plugin 不存在",
                details=plugin_id,
            )

        marker = plugin_dir / ".disabled"

        with self._locks.lock(marker):
            if enabled and marker.exists():
                marker.unlink()
            elif not enabled and not marker.exists():
                marker.write_text("disabled", encoding="utf-8")

        return {"id": plugin_id, "path": str(plugin_dir), "enabled": enabled}

    async def install_plugin(self, plugin_ref: str) -> Dict[str, Any]:
        """
        安装新插件

        通过 Claude CLI 安装插件（与官方插件系统一致）。

        Args:
            plugin_ref: 插件引用（可以是名称、URL 等）

        Returns:
            安装结果，包含 id 和 installed 字段

        Raises:
            APIError: 安装失败时抛出
        """
        try:
            result = await self._plugin_runner.install_plugin(plugin_ref)
            logger.info(
                "claude_plugin_installed",
                plugin_ref=plugin_ref,
            )
            return result
        except APIError:
            raise
        except Exception as exc:
            logger.error(
                "claude_plugin_install_failed",
                plugin_ref=plugin_ref,
                error=str(exc),
            )
            raise APIError(
                status_code=500,
                code="PLUGIN_INSTALL_FAILED",
                message=f"Failed to install plugin '{plugin_ref}'",
                details=str(exc),
            ) from exc

    # ==================== 私有工具方法 ====================

    def _read_config(self, path: Path) -> Dict[str, Any]:
        """读取配置文件（自动检测格式）"""
        with self._locks.lock(path):
            if path.suffix == ".toml":
                return self._parsers.read_toml(path)
            return self._parsers.read_json(path)

    def _write_config(self, path: Path, data: Dict[str, Any]) -> None:
        """写入配置文件（自动检测格式，带备份）"""
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._locks.lock(path):
            self._backups.backup(path)

            if path.suffix == ".toml":
                self._parsers.write_toml(path, data)
            else:
                self._parsers.write_json(path, data)

    def _resolve_engine_config(self, engine: str, scope: ConfigScope) -> Path:
        """解析引擎配置文件路径"""
        engine = engine.lower().strip()

        if engine == "claude":
            # Claude 主配置在 ~/.claude.json (包含 mcpServers 和 prompts)
            # ~/.claude/settings.json 只包含 env 和 includeCoAuthoredBy
            return Path("~/.claude.json").expanduser()
        elif engine == "codex":
            # Codex 配置在 ~/.codex/config.toml
            return Path("~/.codex/config.toml").expanduser()
        elif engine == "gemini":
            return Path("~/.gemini/settings.json").expanduser()
        else:
            raise APIError(
                status_code=400,
                code="INVALID_ENGINE",
                message="不支持的引擎类型",
                details=f"engine={engine}",
            )

    def _resolve_prompts_config(self, engine: str, scope: ConfigScope) -> Path:
        """
        解析引擎的 Prompts 专用配置文件路径

        与主配置文件分离，避免泄露供应商信息（API Key 等）

        Args:
            engine: 引擎名称 ("claude" | "codex" | "gemini")
            scope: 配置范围

        Returns:
            Prompts 配置文件的完整路径

        Raises:
            APIError: 引擎类型不支持时抛出
        """
        engine = engine.lower().strip()

        if engine == "claude":
            root = self._resolve_claude_root(scope)
            return root / "prompts.json"
        elif engine == "codex":
            return Path("~/.codex/prompts.toml").expanduser()
        elif engine == "gemini":
            return Path("~/.gemini/prompts.json").expanduser()
        else:
            raise APIError(
                status_code=400,
                code="INVALID_ENGINE",
                message="不支持的引擎类型",
                details=f"engine={engine}",
            )

    def _resolve_claude_root(self, scope: ConfigScope) -> Path:
        """解析 Claude 配置根目录（支持项目级和用户级）"""
        if scope.scope == "project":
            if not scope.project_root:
                raise APIError(
                    status_code=400,
                    code="INVALID_PARAMETER",
                    message="project 范围需要提供 project_root",
                )
            return (scope.project_root / ".claude").resolve()

        if scope.scope == "auto" and scope.project_root:
            project_path = (scope.project_root / ".claude").resolve()
            if project_path.exists():
                return project_path

        return Path("~/.claude").expanduser()

    def _resolve_agents_dir(self, scope: ConfigScope) -> Path:
        """解析 Subagents 目录"""
        root = self._resolve_claude_root(scope)
        return root / "agents"

    def _resolve_agent_path(self, scope: ConfigScope, agent_id: str) -> Path:
        """解析单个 Subagent 文件路径"""
        self._validate_identifier(agent_id)
        agent_dir = self._resolve_agents_dir(scope)
        agent_root = agent_dir.resolve()
        candidate = (agent_dir / f"{agent_id}.md").resolve()
        try:
            candidate.relative_to(agent_root)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符",
                details=f"identifier={agent_id}",
            )
        return candidate

    def _resolve_skills_dir(self, scope: ConfigScope) -> Path:
        """解析 Skills 目录"""
        root = self._resolve_claude_root(scope)
        return root / "skills"

    def _resolve_skill_path(self, scope: ConfigScope, skill_id: str) -> Path:
        """解析单个 Skill 文件路径"""
        self._validate_identifier(skill_id)
        skill_dir = self._resolve_skills_dir(scope)
        skill_root = skill_dir.resolve()
        candidate = (skill_dir / skill_id / "SKILL.md").resolve()
        try:
            candidate.relative_to(skill_root)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符",
                details=f"identifier={skill_id}",
            )
        return candidate

    def _resolve_plugins_dir(self, scope: ConfigScope) -> Path:
        """解析 Plugins 目录（服务器级）"""
        root = self._resolve_claude_root(scope)
        return (root / "plugins").resolve()

    def _validate_identifier(self, value: str) -> None:
        """验证 ID 的合法性（防止路径遍历攻击）"""
        if not value or "\\" in value or value.startswith("."):
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符",
                details=f"identifier={value}",
            )
        if Path(value).is_absolute():
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符",
                details=f"identifier={value}",
            )
        # 检查路径遍历和空路径段
        parts = value.split("/")
        if any(part == ".." for part in parts):
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符",
                details=f"identifier={value}",
            )
        if any(part == "" for part in parts):
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="无效的标识符（包含空路径段）",
                details=f"identifier={value}",
            )
