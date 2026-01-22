"""
Codex CLI 执行器
"""
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CodexRunner:
    """Codex CLI 进程执行器"""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SESSIONS)

    async def stream(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        """启动 Codex CLI 进程并流式返回输出行"""
        await self._semaphore.acquire()

        try:
            # 构建命令参数
            # 🔥 关键: --json 必须在 resume 子命令之前!
            # 正确顺序: codex exec --json [options] resume <SESSION_ID> -
            args: List[str] = [settings.CODEX_CLI_PATH, "exec"]

            session_id = payload.get("sessionId")
            prompt = payload.get("prompt", "")

            # 🔥 --json 必须在 resume 之前添加
            args.append("--json")

            # 🔥 跳过 Git 仓库检查（避免 "Not inside a trusted directory" 错误）
            args.append("--skip-git-repo-check")

            # 🔥 自动批准模式（避免交互式提示）
            args.append("--dangerously-bypass-approvals-and-sandbox")

            # 🔥 根据是否有 sessionId 选择命令模式
            if session_id:
                # 恢复会话: codex exec --json resume <SESSION_ID> -
                args.append("resume")

                # 🔥 Codex CLI 期望纯 UUID，需要从 rollout-YYYY-MM-DDTHH-MM-SS-UUID 格式中提取
                # 例如: rollout-2026-01-20T09-44-04-019bd912-c5cd-7240-96ff-977fb0b05b67
                # 提取: 019bd912-c5cd-7240-96ff-977fb0b05b67
                if session_id.startswith("rollout-"):
                    # 格式: rollout-{timestamp}-{uuid}
                    # timestamp 格式: YYYY-MM-DDTHH-MM-SS (19字符)
                    # 完整前缀: rollout-YYYY-MM-DDTHH-MM-SS- (28字符)
                    parts = session_id.split("-")
                    # rollout-2026-01-20T09-44-04-019bd912-c5cd-7240-96ff-977fb0b05b67
                    # parts: ['rollout', '2026', '01', '20T09', '44', '04', '019bd912', 'c5cd', '7240', '96ff', '977fb0b05b67']
                    # UUID 是最后 5 个部分用 - 连接
                    if len(parts) >= 6:
                        uuid_parts = parts[-5:]  # 最后 5 个部分
                        codex_session_id = "-".join(uuid_parts)
                        logger.info("codex_session_id_extracted",
                                   original=session_id,
                                   extracted=codex_session_id)
                    else:
                        codex_session_id = session_id
                else:
                    codex_session_id = session_id

                args.append(codex_session_id)
                # Prompt 通过 stdin 传递，使用 "-" 表示从 stdin 读取
                args.append("-")
            else:
                # 新会话: codex exec --json [--model MODEL] -
                # 模型参数（仅新会话时有效，resume 时会话保留原模型）
                model = payload.get("model")
                unsupported_models = ("gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo")
                if model and model not in unsupported_models:
                    args.extend(["--model", model])
                # Prompt 通过 stdin 传递
                args.append("-")

            # 工作目录
            project_path = payload.get("projectPath")

            # 🔥 记录完整命令用于调试
            logger.info("codex_cli_start", args=args, cwd=project_path)

            # 启动进程（需要 stdin 来传递 prompt）
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_path,
            )

            # 🔥 写入 prompt 到 stdin 并关闭
            if process.stdin and prompt:
                process.stdin.write(prompt.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()
                await process.stdin.wait_closed()
                logger.debug("codex_stdin_written", prompt_len=len(prompt))

            # 🔥 并发读取 stdout 和 stderr
            async def read_stderr():
                if process.stderr:
                    async for line in process.stderr:
                        line_str = line.decode("utf-8", errors="ignore").strip()
                        if line_str:
                            logger.warning("codex_cli_stderr", stderr=line_str)

            stderr_task = asyncio.create_task(read_stderr())

            # 读取 stdout
            if process.stdout:
                async for line in process.stdout:
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    if line_str:
                        yield line_str

            # 等待 stderr 读取完成
            await stderr_task

            # 等待进程结束
            exit_code = await process.wait()
            logger.info("codex_cli_exit", exit_code=exit_code)

        finally:
            self._semaphore.release()

    async def release(self) -> None:
        """释放并发令牌"""
        self._semaphore.release()
