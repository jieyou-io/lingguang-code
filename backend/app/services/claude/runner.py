"""
Claude CLI 执行器
"""
import asyncio
import os
from typing import Dict, List, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ClaudeRunner:
    """Claude CLI 进程执行器"""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SESSIONS)
        # 🔥 存储进程的 stdin，用于发送权限响应
        self._process_stdin: Dict[str, asyncio.StreamWriter] = {}
        self._skip_permissions: Dict[str, bool] = {}

    async def start(
        self,
        project_path: str,
        prompt: str,
        model: str,
        plan_mode: bool,
        max_thinking_tokens: Optional[int],
        tab_id: Optional[str],
        continue_conversation: bool = False,
        resume_session_id: Optional[str] = None,
        session_id: Optional[str] = None,  # 新增：用于关联 stdin
    ) -> asyncio.subprocess.Process:
        """启动 Claude CLI 进程

        🔥 关键：斜杠命令（如 /mcp, /compact, /help）通过 -p 参数传递
        普通 prompt 通过 stdin 管道传递，避免命令行长度限制

        Args:
            continue_conversation: 使用 -c 标志继续最近的对话
            resume_session_id: 使用 --resume 恢复指定的历史对话
            session_id: 会话 ID，用于关联 stdin（发送权限响应）
        """
        await self._semaphore.acquire()

        # 准备环境变量
        env = os.environ.copy()

        # 构建命令参数
        args: List[str] = [settings.CLAUDE_CLI_PATH]

        # 🔥 恢复指定会话（优先级最高）
        if resume_session_id:
            args.extend(["--resume", resume_session_id])
        # 继续最近对话
        elif continue_conversation:
            args.append("-c")

        # 🔥 添加模型参数
        if model:
            model_alias_map = {
                "claude-sonnet-4-5": "sonnet",
                "claude-sonnet-4-5-thinking": "sonnet",
                "claude-sonnet-4-20250": "sonnet",
                "claude-4-sonnet": "sonnet",
                "claude-opus-4-5": "opus",
                "claude-opus-4-20250": "opus",
                "claude-4-opus": "opus",
            }
            resolved_model = model_alias_map.get(model, model)
            args.extend(["--model", resolved_model])

        # 🔥 检测斜杠命令（如 /mcp, /compact, /help）
        # Claude CLI 只在 -p 参数中解析斜杠命令，stdin 管道不会触发
        is_slash_command = self._is_slash_command(prompt)

        if is_slash_command:
            # 斜杠命令通过 -p 参数传递
            logger.info("Detected slash command, using -p flag", command=prompt.strip())
            args.extend(["-p", prompt])

        args.extend([
            "--output-format", "stream-json",
            "--verbose",
        ])

        # Root/sudo 环境下 Claude CLI 不允许跳过权限检查
        skip_permissions = os.geteuid() != 0
        if skip_permissions:
            args.append("--dangerously-skip-permissions")

        # 打印完整的 CLI 命令
        logger.info(
            "Executing Claude CLI",
            command=" ".join(args),
            cwd=project_path,
            model=model,
            continue_conversation=continue_conversation,
            resume_session_id=resume_session_id,
            prompt_length=len(prompt),
            prompt_preview=prompt[:100] + "..." if len(prompt) > 100 else prompt,
            is_slash_command=is_slash_command,
        )

        # 启动进程
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=project_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        logger.info(
            "CLI process spawned",
            pid=process.pid,
            returncode=process.returncode,
        )

        if session_id and process.stdin:
            self._process_stdin[session_id] = process.stdin
            self._skip_permissions[session_id] = skip_permissions

        # 🔥 普通 prompt 通过 stdin 管道传递，避免命令行长度限制
        # 斜杠命令已通过 -p 参数传递，不需要 stdin
        if not is_slash_command:
            if process.stdin:
                logger.info("Writing prompt to stdin", prompt_length=len(prompt))
                process.stdin.write(prompt.encode('utf-8'))
                process.stdin.write(b'\n')
                await process.stdin.drain()
                if not session_id or skip_permissions:
                    process.stdin.close()
                    await process.stdin.wait_closed()
                    logger.info("Prompt written and stdin closed")
        else:
            # 斜杠命令模式：无 session_id 时关闭 stdin 以信号结束
            if process.stdin and not session_id:
                process.stdin.close()
                await process.stdin.wait_closed()
                logger.info("Stdin closed for slash command")

        return process

    def _is_slash_command(self, prompt: str) -> bool:
        """检测是否是斜杠命令

        斜杠命令特征：
        - 以 / 开头
        - 不包含换行符
        - 长度小于 256 字符

        示例：/mcp, /compact, /help, /clear
        """
        trimmed = prompt.strip()
        return (
            trimmed.startswith('/')
            and '\n' not in trimmed
            and len(trimmed) < 256
        )

    async def send_permission_response(
        self,
        session_id: str,
        response: str,  # "y" 或 "n"
    ) -> bool:
        """发送权限响应到 Claude CLI stdin（使用 stream-json 格式）

        Args:
            session_id: 会话 ID
            response: 用户响应 ("y" 授权, "n" 拒绝)

        Returns:
            是否成功发送
        """
        import json

        stdin = self._process_stdin.get(session_id)
        if not stdin:
            logger.warning("No stdin found for session", session_id=session_id)
            return False

        try:
            # 🔥 使用 stream-json 格式发送用户响应
            response_msg = json.dumps({
                "role": "user",
                "content": response
            })
            stdin.write(response_msg.encode('utf-8'))
            stdin.write(b'\n')
            await stdin.drain()
            logger.info(
                "Permission response sent (stream-json)",
                session_id=session_id,
                response=response,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to send permission response",
                session_id=session_id,
                error=str(e),
            )
            return False

    async def close_stdin(self, session_id: str) -> None:
        """关闭指定会话的 stdin"""
        stdin = self._process_stdin.pop(session_id, None)
        self._skip_permissions.pop(session_id, None)
        if stdin:
            try:
                if stdin.is_closing():
                    return
                stdin.close()
                await stdin.wait_closed()
                logger.info("Stdin closed for session", session_id=session_id)
            except Exception as e:
                logger.warning("Error closing stdin", session_id=session_id, error=str(e))

    def should_skip_permissions(self, session_id: str) -> bool:
        return self._skip_permissions.get(session_id, False)

    async def release(self, session_id: Optional[str] = None) -> None:
        """释放并发令牌并清理 stdin"""
        if session_id:
            await self.close_stdin(session_id)
        self._semaphore.release()
