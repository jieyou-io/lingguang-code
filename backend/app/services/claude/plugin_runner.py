"""
Claude CLI Plugin Runner

通过 Claude CLI 命令管理插件，与官方插件系统保持一致。
根据官方文档 (https://docs.claude.com/en/docs/claude-code/plugins)，
插件应通过 CLI 命令而非目录扫描管理。
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.core.errors import APIError

logger = structlog.get_logger()


class PluginCLIRunner:
    """
    Claude CLI 插件管理器

    通过 Claude CLI 提供的 plugin 命令管理插件生命周期，
    包括列表查询、启用/禁用、安装等操作。

    Examples:
        >>> runner = PluginCLIRunner()
        >>> plugins = await runner.list_plugins()
        >>> await runner.enable_plugin("my-plugin")
    """

    def __init__(
        self,
        cli_path: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        """
        初始化插件 CLI 运行器

        Args:
            cli_path: Claude CLI 可执行文件路径，默认使用配置中的值
            timeout_seconds: 命令执行超时时间（秒）
        """
        self._cli_path = cli_path or settings.CLAUDE_CLI_PATH
        self._timeout_seconds = timeout_seconds

    async def list_plugins(self) -> List[Dict[str, Any]]:
        """
        列出所有已安装的插件

        优先尝试 JSON 输出格式以获得结构化数据，
        失败时回退到文本格式并尝试解析。

        Returns:
            插件列表，每个插件包含 id、name、description、enabled 等字段

        Raises:
            APIError: CLI 执行失败或响应格式无效时抛出
        """
        # 优先尝试 JSON 格式
        try:
            payload = await self._run_json_command(
                ["code", "plugin", "list", "--json"]
            )
            return self._normalize_plugins(payload)
        except APIError as exc:
            logger.warning(
                "claude_plugin_list_json_failed",
                error=str(exc),
                error_code=exc.code if hasattr(exc, 'code') else None,
                fallback="text",
            )

        # 回退到文本格式
        try:
            output = await self._run_text_command(["code", "plugin", "list"])
            return self._parse_plugin_list_text(output)
        except APIError as exc:
            logger.error(
                "claude_plugin_list_text_failed",
                error=str(exc),
                error_code=exc.code if hasattr(exc, 'code') else None,
            )
            # CLI 不支持或失败，返回空列表让上层回退到目录扫描
            # 不抛出异常，让调用方可以继续使用目录扫描
            return []

    async def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        启用指定插件

        Args:
            plugin_id: 插件 ID

        Returns:
            操作结果，包含 id 和 enabled 字段

        Raises:
            APIError: CLI 执行失败时抛出
        """
        try:
            await self._run_text_command(["code", "plugin", "enable", plugin_id])
            logger.info("claude_plugin_enabled", plugin_id=plugin_id)
            return {"id": plugin_id, "enabled": True}
        except APIError as exc:
            logger.error(
                "claude_plugin_enable_failed",
                plugin_id=plugin_id,
                error=str(exc),
            )
            raise

    async def disable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        禁用指定插件

        Args:
            plugin_id: 插件 ID

        Returns:
            操作结果，包含 id 和 enabled 字段

        Raises:
            APIError: CLI 执行失败时抛出
        """
        try:
            await self._run_text_command(["code", "plugin", "disable", plugin_id])
            logger.info("claude_plugin_disabled", plugin_id=plugin_id)
            return {"id": plugin_id, "enabled": False}
        except APIError as exc:
            logger.error(
                "claude_plugin_disable_failed",
                plugin_id=plugin_id,
                error=str(exc),
            )
            raise

    async def install_plugin(self, plugin_ref: str) -> Dict[str, Any]:
        """
        安装新插件

        Args:
            plugin_ref: 插件引用（可以是名称、URL 等，具体格式取决于 CLI 实现）

        Returns:
            操作结果，包含 id 和 installed 字段

        Raises:
            APIError: CLI 执行失败时抛出
        """
        try:
            await self._run_text_command(["code", "plugin", "install", plugin_ref])
            logger.info("claude_plugin_installed", plugin_ref=plugin_ref)
            return {"id": plugin_ref, "installed": True}
        except APIError as exc:
            logger.error(
                "claude_plugin_install_failed",
                plugin_ref=plugin_ref,
                error=str(exc),
            )
            raise

    # ==================== 私有方法 ====================

    async def _run_text_command(self, args: List[str]) -> str:
        """
        执行 CLI 命令并返回文本输出

        Args:
            args: 命令参数列表

        Returns:
            命令输出的文本内容

        Raises:
            APIError: 命令执行失败时抛出
        """
        return await self._run_command(args)

    async def _run_json_command(self, args: List[str]) -> Any:
        """
        执行 CLI 命令并解析 JSON 输出

        Args:
            args: 命令参数列表

        Returns:
            解析后的 JSON 数据

        Raises:
            APIError: 命令执行失败或 JSON 解析失败时抛出
        """
        output = await self._run_command(args)
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise APIError(
                status_code=500,
                code="CLAUDE_CLI_INVALID_JSON",
                message="Claude CLI returned invalid JSON",
                details=str(exc),
            ) from exc

    async def _run_command(self, args: List[str]) -> str:
        """
        执行 Claude CLI 命令核心逻辑

        Args:
            args: 命令参数列表（不含可执行文件路径）

        Returns:
            命令的标准输出内容

        Raises:
            APIError: 命令执行失败时抛出（包括 CLI 不存在、超时、非零退出码）
        """
        # 启动子进程
        try:
            process = await asyncio.create_subprocess_exec(
                self._cli_path,
                *args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise APIError(
                status_code=500,
                code="CLAUDE_CLI_NOT_FOUND",
                message=f"Claude CLI not found at: {self._cli_path}",
                details=str(exc),
            ) from exc

        # 执行命令并等待结果（带超时）
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise APIError(
                status_code=504,
                code="CLAUDE_CLI_TIMEOUT",
                message=f"Claude CLI command timed out after {self._timeout_seconds}s",
                details=" ".join([self._cli_path] + args),
            ) from exc

        # 解码输出
        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        # 检查退出码
        if process.returncode != 0:
            error_message = stderr_text or stdout_text or "unknown error"
            raise APIError(
                status_code=500,
                code="CLAUDE_CLI_FAILED",
                message=f"Claude CLI command failed with exit code {process.returncode}",
                details=error_message,
            )

        return stdout_text

    def _normalize_plugins(self, payload: Any) -> List[Dict[str, Any]]:
        """
        标准化 JSON 格式的插件列表数据

        支持多种可能的 JSON 格式：
        - {"plugins": [...]}
        - [...]
        - 列表元素可以是 dict、str 或其他类型

        Args:
            payload: JSON 解析后的数据

        Returns:
            标准化后的插件列表

        Raises:
            APIError: 数据格式不符合预期时抛出
        """
        # 提取插件列表
        if isinstance(payload, dict) and "plugins" in payload:
            items = payload["plugins"]
        else:
            items = payload

        if not isinstance(items, list):
            raise APIError(
                status_code=500,
                code="CLAUDE_CLI_INVALID_RESPONSE",
                message="Unexpected plugin list response format",
                details=f"Expected list, got {type(items).__name__}",
            )

        # 标准化每个插件条目
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                # 已经是字典，直接使用（CLI 返回了结构化数据）
                normalized.append(item)
            elif isinstance(item, str):
                # 仅有插件 ID 的简单格式
                normalized.append({"id": item})
            else:
                # 其他类型，转换为字符串作为 ID
                normalized.append({"id": str(item)})

        return normalized

    def _parse_plugin_list_text(self, output: str) -> List[Dict[str, Any]]:
        """
        解析文本格式的插件列表输出

        尝试从文本中提取插件信息，支持常见格式：
        - "plugin-id - Description"
        - "plugin-id"
        - "plugin-id (enabled/disabled)"

        Args:
            output: CLI 文本输出

        Returns:
            解析后的插件列表
        """
        plugins: List[Dict[str, Any]] = []

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # 解析 "id - description" 格式
            plugin_id, _, description = line.partition(" - ")
            plugin_id = plugin_id.strip()

            if not plugin_id:
                continue

            plugin_data: Dict[str, Any] = {
                "id": plugin_id,
                "raw": line,
            }

            # 添加描述（如果有）
            if description:
                plugin_data["description"] = description.strip()

            # 尝试推断启用状态
            enabled_status = self._infer_enabled_status(line)
            if enabled_status is not None:
                plugin_data["enabled"] = enabled_status

            plugins.append(plugin_data)

        return plugins

    def _infer_enabled_status(self, line: str) -> Optional[bool]:
        """
        从文本行推断插件启用状态

        通过关键词匹配尝试判断插件是否启用。

        Args:
            line: 文本行

        Returns:
            True (启用) / False (禁用) / None (无法判断)
        """
        lowered = line.lower()

        # 明确的禁用标记
        if any(
            keyword in lowered
            for keyword in ["disabled", "inactive", "not enabled"]
        ):
            return False

        # 明确的启用标记
        if any(keyword in lowered for keyword in ["enabled", "active"]):
            return True

        # 无法判断
        return None
