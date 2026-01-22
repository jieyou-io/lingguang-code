"""
Gemini CLI 执行器
"""
import asyncio
from typing import List, Optional

from app.core.config import settings


class GeminiRunner:
    """Gemini CLI 进程执行器"""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SESSIONS)

    async def start(
        self,
        project_path: str,
        prompt: str,
        model: str,
        approval_mode: str,
        include_directories: List[str],
        debug: bool,
        session_id: Optional[str] = None,
    ) -> asyncio.subprocess.Process:
        """启动 Gemini CLI 进程"""
        await self._semaphore.acquire()

        # 🔥 Gemini CLI 通过 cwd 确定项目路径，不需要 --project 参数
        args: List[str] = [settings.GEMINI_CLI_PATH]

        # 🔥 如果提供了 session_id，直接恢复指定会话
        # 然后通过位置参数传递新的 prompt（不能使用 -i，会冲突）
        if session_id:
            args.extend(["--resume", session_id])

        # 🔥 位置参数传递 prompt（新会话或恢复会话都使用位置参数）
        args.append(prompt)

        # 🔥 必须使用 stream-json 格式才能获取 JSON 输出
        args.extend(["--output-format", "stream-json"])
        args.extend(["--model", model])
        args.extend(["--approval-mode", approval_mode])

        for directory in include_directories:
            args.extend(["--include-directories", directory])

        if debug:
            args.append("--debug")

        # 🔥 设置工作目录为项目路径，不使用 stdin 管道
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_path,  # 通过 cwd 指定项目路径
        )

        return process

    async def release(self) -> None:
        """释放并发令牌"""
        self._semaphore.release()
