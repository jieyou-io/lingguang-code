"""
引擎状态检查服务
"""
import asyncio
import time
from typing import Literal

import structlog

from app.core.config import settings
from app.schemas.engine_status import EngineStatusResponse

logger = structlog.get_logger()


class EngineStatusService:
    """引擎状态检查服务"""

    def __init__(self):
        self.timeout_seconds = 5.0  # 健康检查超时时间

    async def check_all_engines(self) -> list[EngineStatusResponse]:
        """
        并行检查所有引擎的状态

        Returns:
            所有引擎的状态列表
        """
        tasks = [
            self.check_claude_status(),
            self.check_codex_status(),
            self.check_gemini_status(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            result if not isinstance(result, Exception) else self._error_status(str(result))
            for result in results
        ]

    async def check_claude_status(self) -> EngineStatusResponse:
        """
        检查 Claude CLI 状态

        Returns:
            Claude 引擎状态
        """
        start_time = time.time()

        try:
            # 执行 claude --version 命令
            process = await asyncio.create_subprocess_exec(
                settings.CLAUDE_CLI_PATH,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            latency = int((time.time() - start_time) * 1000)

            if process.returncode == 0:
                status: Literal["online", "degraded"] = "degraded" if latency > 500 else "online"
                return EngineStatusResponse(
                    name="Claude Code",
                    engine="claude",
                    status=status,
                    latency=latency,
                    message="",
                )
            else:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                logger.warning("claude_cli_check_failed", error=error_msg)
                return EngineStatusResponse(
                    name="Claude Code",
                    engine="claude",
                    status="offline",
                    latency=latency,
                    message=f"CLI error: {error_msg}",
                )

        except FileNotFoundError:
            logger.error("claude_cli_not_found", path=settings.CLAUDE_CLI_PATH)
            return EngineStatusResponse(
                name="Claude Code",
                engine="claude",
                status="offline",
                latency=0,
                message=f"CLI not found: {settings.CLAUDE_CLI_PATH}",
            )
        except asyncio.TimeoutError:
            latency = int(self.timeout_seconds * 1000)
            logger.warning("claude_cli_timeout", timeout=self.timeout_seconds)
            return EngineStatusResponse(
                name="Claude Code",
                engine="claude",
                status="offline",
                latency=latency,
                message=f"Timeout after {self.timeout_seconds}s",
            )
        except Exception as e:
            logger.error("claude_cli_check_error", error=str(e))
            return EngineStatusResponse(
                name="Claude Code",
                engine="claude",
                status="offline",
                latency=0,
                message=f"Error: {str(e)}",
            )

    async def check_codex_status(self) -> EngineStatusResponse:
        """
        检查 Codex CLI 状态

        Returns:
            Codex 引擎状态
        """
        start_time = time.time()

        try:
            # 执行 codex --version 命令
            process = await asyncio.create_subprocess_exec(
                settings.CODEX_CLI_PATH,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            latency = int((time.time() - start_time) * 1000)

            if process.returncode == 0:
                status: Literal["online", "degraded"] = "degraded" if latency > 500 else "online"
                return EngineStatusResponse(
                    name="Codex",
                    engine="codex",
                    status=status,
                    latency=latency,
                    message="",
                )
            else:
                error_msg = stderr.decode().strip()
                return EngineStatusResponse(
                    name="Codex",
                    engine="codex",
                    status="offline",
                    latency=latency,
                    message=f"CLI error: {error_msg}",
                )

        except FileNotFoundError:
            logger.error("codex_cli_not_found", path=settings.CODEX_CLI_PATH)
            return EngineStatusResponse(
                name="Codex",
                engine="codex",
                status="offline",
                latency=0,
                message=f"CLI not found: {settings.CODEX_CLI_PATH}",
            )
        except asyncio.TimeoutError:
            latency = int(self.timeout_seconds * 1000)
            logger.warning("codex_cli_timeout", timeout=self.timeout_seconds)
            return EngineStatusResponse(
                name="Codex",
                engine="codex",
                status="offline",
                latency=latency,
                message=f"Timeout after {self.timeout_seconds}s",
            )
        except Exception as e:
            logger.error("codex_cli_check_error", error=str(e))
            return EngineStatusResponse(
                name="Codex",
                engine="codex",
                status="offline",
                latency=0,
                message=f"Error: {str(e)}",
            )

    async def check_gemini_status(self) -> EngineStatusResponse:
        """
        检查 Gemini CLI 状态

        Returns:
            Gemini 引擎状态
        """
        start_time = time.time()

        try:
            # 执行 gemini --version 命令
            process = await asyncio.create_subprocess_exec(
                settings.GEMINI_CLI_PATH,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            latency = int((time.time() - start_time) * 1000)

            if process.returncode == 0:
                status: Literal["online", "degraded"] = "degraded" if latency > 500 else "online"
                return EngineStatusResponse(
                    name="Gemini CLI",
                    engine="gemini",
                    status=status,
                    latency=latency,
                    message="",
                )
            else:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                logger.warning("gemini_cli_check_failed", error=error_msg)
                return EngineStatusResponse(
                    name="Gemini CLI",
                    engine="gemini",
                    status="offline",
                    latency=latency,
                    message=f"CLI error: {error_msg}",
                )

        except FileNotFoundError:
            logger.error("gemini_cli_not_found", path=settings.GEMINI_CLI_PATH)
            return EngineStatusResponse(
                name="Gemini CLI",
                engine="gemini",
                status="offline",
                latency=0,
                message=f"CLI not found: {settings.GEMINI_CLI_PATH}",
            )
        except asyncio.TimeoutError:
            latency = int(self.timeout_seconds * 1000)
            logger.warning("gemini_cli_timeout", timeout=self.timeout_seconds)
            return EngineStatusResponse(
                name="Gemini CLI",
                engine="gemini",
                status="offline",
                latency=latency,
                message=f"Timeout after {self.timeout_seconds}s",
            )
        except Exception as e:
            logger.error("gemini_cli_check_error", error=str(e))
            return EngineStatusResponse(
                name="Gemini CLI",
                engine="gemini",
                status="offline",
                latency=0,
                message=f"Error: {str(e)}",
            )

    def _error_status(self, error: str) -> EngineStatusResponse:
        """生成错误状态"""
        return EngineStatusResponse(
            name="Unknown",
            engine="claude",
            status="offline",
            latency=0,
            message=error,
        )
