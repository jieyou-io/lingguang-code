"""
MCP 进程管理器
"""
import asyncio
import os
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()


class MCPProcessManager:
    """MCP 服务器进程管理器"""

    def __init__(self) -> None:
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, server_config: dict) -> Optional[asyncio.subprocess.Process]:
        """
        启动 MCP 服务器进程

        Args:
            server_config: 服务器配置字典

        Returns:
            进程对象（stdio 传输）或 None（SSE 传输）
        """
        server_id = server_config["id"]

        # 检查进程是否已运行
        if server_id in self._processes:
            process = self._processes[server_id]
            if process.returncode is None:
                logger.info("mcp_server_already_running", server_id=server_id)
                return process

        # 根据传输协议启动进程
        if server_config["transport"] == "stdio":
            command = server_config.get("command")
            if not command:
                raise ValueError(f"stdio 传输需要 command 参数: {server_id}")

            args = server_config.get("args", [])
            env = {**os.environ, **server_config.get("env", {})}

            try:
                process = await asyncio.create_subprocess_exec(
                    command,
                    *args,
                    env=env,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self._processes[server_id] = process
                logger.info(
                    "mcp_server_started",
                    server_id=server_id,
                    pid=process.pid,
                    transport="stdio",
                )
                return process
            except Exception as exc:
                logger.error(
                    "mcp_server_start_failed",
                    server_id=server_id,
                    error=str(exc),
                )
                raise

        elif server_config["transport"] == "sse":
            # SSE 传输不需要进程管理
            logger.info(
                "mcp_server_sse_mode",
                server_id=server_id,
                url=server_config.get("url"),
            )
            return None

        else:
            raise ValueError(f"不支持的传输协议: {server_config['transport']}")

    async def stop(self, server_id: str) -> None:
        """
        停止 MCP 服务器进程

        Args:
            server_id: 服务器 ID
        """
        process = self._processes.pop(server_id, None)
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
                logger.info("mcp_server_stopped", server_id=server_id)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.warning("mcp_server_killed", server_id=server_id)
            except Exception as exc:
                logger.error(
                    "mcp_server_stop_failed",
                    server_id=server_id,
                    error=str(exc),
                )
        else:
            logger.warning("mcp_server_not_found", server_id=server_id)

    def get_process(self, server_id: str) -> Optional[asyncio.subprocess.Process]:
        """
        获取服务器进程

        Args:
            server_id: 服务器 ID

        Returns:
            进程对象或 None
        """
        return self._processes.get(server_id)

    def is_running(self, server_id: str) -> bool:
        """
        检查服务器是否正在运行

        Args:
            server_id: 服务器 ID

        Returns:
            是否正在运行
        """
        process = self._processes.get(server_id)
        return process is not None and process.returncode is None

    async def cleanup(self) -> None:
        """清理所有进程"""
        for server_id in list(self._processes.keys()):
            await self.stop(server_id)
