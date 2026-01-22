"""
系统提示词管理服务

管理 CLAUDE.md, AGENTS.md, GEMINI.md 等系统提示词文件
"""
from pathlib import Path
from typing import Tuple

import structlog

from app.core.errors import APIError

logger = structlog.get_logger()


class SystemPromptsService:
    """系统提示词服务"""

    def _get_prompt_file_path(self, engine: str) -> Tuple[Path, str]:
        """
        获取系统提示词文件路径

        Args:
            engine: 引擎名称 (claude, codex, gemini)

        Returns:
            (文件路径, 文件名) 元组

        Raises:
            APIError: 不支持的引擎类型
        """
        engine = engine.lower().strip()

        if engine == "claude":
            # Claude 系统提示词: ~/.claude/CLAUDE.md
            return Path("~/.claude/CLAUDE.md").expanduser(), "CLAUDE.md"
        elif engine == "codex":
            # Codex 系统提示词: ~/.codex/AGENTS.md
            return Path("~/.codex/AGENTS.md").expanduser(), "AGENTS.md"
        elif engine == "gemini":
            # Gemini 系统提示词: ~/.gemini/GEMINI.md
            return Path("~/.gemini/GEMINI.md").expanduser(), "GEMINI.md"
        else:
            raise APIError(
                status_code=400,
                code="INVALID_ENGINE",
                message=f"不支持的引擎: {engine}",
                details=f"支持的引擎: claude, codex, gemini",
            )

    async def get_system_prompt(self, engine: str) -> Tuple[str, str, bool]:
        """
        获取系统提示词内容

        Args:
            engine: 引擎名称

        Returns:
            (内容, 文件路径, 是否存在) 元组
        """
        file_path, file_name = self._get_prompt_file_path(engine)

        logger.info(
            "system_prompt_read",
            engine=engine,
            file_path=str(file_path),
        )

        if not file_path.exists():
            logger.warning(
                "system_prompt_not_found",
                engine=engine,
                file_path=str(file_path),
            )
            return "", str(file_path), False

        try:
            content = file_path.read_text(encoding="utf-8")
            logger.info(
                "system_prompt_read_success",
                engine=engine,
                size=len(content),
            )
            return content, str(file_path), True
        except OSError as exc:
            logger.error(
                "system_prompt_read_failed",
                engine=engine,
                file_path=str(file_path),
                error=str(exc),
            )
            raise APIError(
                status_code=500,
                code="READ_FAILED",
                message=f"读取系统提示词失败: {exc}",
                details=str(file_path),
            )

    async def save_system_prompt(self, engine: str, content: str) -> str:
        """
        保存系统提示词内容

        Args:
            engine: 引擎名称
            content: 提示词内容

        Returns:
            保存的文件路径

        Raises:
            APIError: 保存失败时抛出
        """
        file_path, file_name = self._get_prompt_file_path(engine)

        logger.info(
            "system_prompt_save",
            engine=engine,
            file_path=str(file_path),
            size=len(content),
        )

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_text(content, encoding="utf-8")
            logger.info(
                "system_prompt_save_success",
                engine=engine,
                file_path=str(file_path),
            )
            return str(file_path)
        except OSError as exc:
            logger.error(
                "system_prompt_save_failed",
                engine=engine,
                file_path=str(file_path),
                error=str(exc),
            )
            raise APIError(
                status_code=500,
                code="WRITE_FAILED",
                message=f"保存系统提示词失败: {exc}",
                details=str(file_path),
            )
