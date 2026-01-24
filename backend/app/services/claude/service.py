"""
Claude 会话服务

架构说明：
- execute() 只创建会话配置，不启动进程
- stream_events() 在前端连接 SSE 后才启动 CLI 进程
- 这样确保前端不会错过任何 output 事件
"""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Optional

import structlog

from app.core.config import settings
from app.core.errors import SessionNotFoundError
from app.core.sse import SSEEvent, SSEEventType
from app.schemas.claude import ClaudeExecuteRequest, ClaudeResumeRequest
from app.services.claude.parser import safe_parse_jsonl_line
from app.services.claude.runner import ClaudeRunner
from app.services.storage.repositories import StorageRepository

logger = structlog.get_logger()


# 🔥 全局共享的 Runner 实例（单例模式）
# 这样所有 service 实例共享同一个 runner，权限响应可以找到正确的 stdin
_shared_runner = ClaudeRunner()


@dataclass
class SessionConfig:
    """会话配置（用于延迟启动进程）"""
    project_path: str
    prompt: str
    model: str
    plan_mode: bool
    max_thinking_tokens: Optional[int]
    tab_id: Optional[str]
    continue_conversation: bool = False
    resume_session_id: Optional[str] = None


class ClaudeSessionRegistry:
    """Claude 会话注册表（存储配置和进程）"""

    def __init__(self) -> None:
        self._configs: Dict[str, SessionConfig] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    def register_config(self, session_id: str, config: SessionConfig) -> None:
        """注册会话配置（execute 阶段）"""
        self._configs[session_id] = config

    def get_config(self, session_id: str) -> Optional[SessionConfig]:
        """获取会话配置"""
        return self._configs.get(session_id)

    def register_process(self, session_id: str, process: asyncio.subprocess.Process) -> None:
        """注册进程（stream 阶段）"""
        self._processes[session_id] = process

    def get_process(self, session_id: str) -> Optional[asyncio.subprocess.Process]:
        """获取进程"""
        return self._processes.get(session_id)

    def remove(self, session_id: str) -> None:
        """移除会话"""
        self._configs.pop(session_id, None)
        self._processes.pop(session_id, None)

    # 向后兼容
    def register(self, session_id: str, process: asyncio.subprocess.Process) -> None:
        self.register_process(session_id, process)

    def get(self, session_id: str) -> Optional[asyncio.subprocess.Process]:
        return self.get_process(session_id)


claude_registry = ClaudeSessionRegistry()


class ClaudeService:
    """Claude 业务服务"""

    def __init__(
        self,
        repository: StorageRepository,
        runner: ClaudeRunner,
        registry: ClaudeSessionRegistry,
    ) -> None:
        self._repository = repository
        # 🔥 使用全局共享的 runner，而不是传入的 runner
        self._runner = _shared_runner
        self._registry = registry

    async def send_permission_response(self, session_id: str, response: str) -> bool:
        """发送权限响应到 Claude CLI stdin"""
        return await self._runner.send_permission_response(session_id, response)

    def _is_permission_request(self, parsed: dict) -> bool:
        """检测是否是需要用户授权的权限请求

        Claude CLI 在需要用户授权时会输出特定格式的消息：
        1. assistant 类型消息，包含 tool_use 内容块，工具名为 Write/Edit 等
        2. 消息中包含 "permission" 相关字段
        """
        if not parsed:
            return False

        msg_type = parsed.get("type")

        # 检测 assistant 消息中的 tool_use
        if msg_type == "assistant":
            message = parsed.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "")
                        # 需要授权的工具：Write, Edit, Bash, NotebookEdit 等
                        permission_tools = {"Write", "Edit", "Bash", "NotebookEdit", "KillShell"}
                        if tool_name in permission_tools:
                            return True

        # 检测直接的权限请求消息（如果 Claude CLI 有这种格式）
        if parsed.get("type") == "permission_request":
            return True

        return False

    def _get_tool_name(self, parsed: dict) -> str:
        """从消息中提取工具名称"""
        if not parsed:
            return "unknown"

        if parsed.get("type") == "assistant":
            message = parsed.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        return item.get("name", "unknown")

        return "unknown"

    async def execute(
        self,
        payload: ClaudeExecuteRequest,
        continue_conversation: bool = False,
        resume_session_id: Optional[str] = None,
    ) -> str:
        """创建会话配置（不启动进程，等待 stream 连接后启动）

        Args:
            payload: 执行请求参数
            continue_conversation: 使用 -c 标志继续最近的对话
            resume_session_id: 使用 --resume 恢复指定的历史对话
        """
        session_id = str(uuid.uuid4())
        logger.info(
            "Creating session config (process will start on stream connect)",
            session_id=session_id,
            project_path=payload.projectPath,
            model=payload.model,
            continue_conversation=continue_conversation,
            resume_session_id=resume_session_id,
        )

        # 创建会话配置（延迟启动）
        config = SessionConfig(
            project_path=payload.projectPath,
            prompt=payload.prompt,
            model=payload.model,
            plan_mode=payload.planMode,
            max_thinking_tokens=payload.maxThinkingTokens,
            tab_id=payload.tabId,
            continue_conversation=continue_conversation,
            resume_session_id=resume_session_id,
        )
        self._registry.register_config(session_id, config)

        # 尝试创建数据库记录（失败不影响对话）
        try:
            await self._repository.create_session(
                session_id=session_id,
                engine="claude",
                project_path=payload.projectPath,
                status="pending",  # 状态改为 pending，等待 stream 连接
            )
        except Exception as e:
            logger.warning(
                "Failed to save session to database, continuing without persistence",
                session_id=session_id,
                error=str(e),
            )

        logger.info(
            "Session config registered, waiting for stream connection",
            session_id=session_id,
        )
        return session_id

    async def resume(self, payload: ClaudeResumeRequest) -> str:
        exists = await self._repository.session_exists(payload.sessionId)
        if not exists:
            raise SessionNotFoundError(payload.sessionId)

        config = SessionConfig(
            project_path=payload.projectPath,
            prompt=payload.prompt,
            model=payload.model,
            plan_mode=payload.planMode,
            max_thinking_tokens=payload.maxThinkingTokens,
            tab_id=payload.tabId,
            continue_conversation=False,
            resume_session_id=payload.sessionId,
        )
        self._registry.register_config(payload.sessionId, config)

        await self._repository.update_session_status(payload.sessionId, "pending")
        return payload.sessionId

    async def cancel(self, session_id: str) -> None:
        process = self._registry.get_process(session_id)
        if not process:
            raise SessionNotFoundError(session_id)
        process.terminate()
        try:
            await self._repository.update_session_status(session_id, "canceled")
        except Exception:
            pass
        self._registry.remove(session_id)
        await self._runner.release(session_id)

    async def stream_events(self, session_id: str) -> AsyncIterator[SSEEvent]:
        """流式返回 CLI 输出（在此处启动进程，确保前端不会错过事件）"""

        # 获取会话配置（带重试，防止竞态条件）
        config = None
        for attempt in range(5):
            config = self._registry.get_config(session_id)
            if config:
                break
            logger.warning(
                "Session config not found, retrying",
                session_id=session_id,
                attempt=attempt + 1,
            )
            await asyncio.sleep(0.1 * (attempt + 1))

        if not config:
            logger.error("Session config not found after retries", session_id=session_id)
            raise SessionNotFoundError(session_id)

        logger.info(
            "Stream connected, starting CLI process now",
            session_id=session_id,
            project_path=config.project_path,
            model=config.model,
        )

        # 发送 session_init 事件（在启动进程之前，让前端知道连接成功）
        yield SSEEvent(
            event_type=SSEEventType.SESSION_INIT,
            session_id=session_id,
            engine="claude",
        )

        # 🔥 关键：在前端连接后才启动 CLI 进程
        try:
            process = await self._runner.start(
                project_path=config.project_path,
                prompt=config.prompt,
                model=config.model,
                plan_mode=config.plan_mode,
                max_thinking_tokens=config.max_thinking_tokens,
                tab_id=config.tab_id,
                continue_conversation=config.continue_conversation,
                resume_session_id=config.resume_session_id,
                session_id=session_id,  # 🔥 传递 session_id 用于权限响应
            )
            self._registry.register_process(session_id, process)
            logger.info(
                "CLI process started successfully",
                session_id=session_id,
                pid=process.pid,
            )
        except Exception as e:
            logger.error("Failed to start CLI process", session_id=session_id, error=str(e))
            yield SSEEvent(
                event_type=SSEEventType.ERROR,
                session_id=session_id,
                engine="claude",
                payload={"error": f"Failed to start CLI: {e}"},
            )
            self._registry.remove(session_id)
            return

        # 更新数据库状态
        try:
            await self._repository.update_session_status(session_id, "running")
        except Exception:
            pass

        queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async def read_stdout():
            assert process.stdout is not None
            logger.info("Starting stdout reader", session_id=session_id)
            line_count = 0
            async for line in process.stdout:
                line_count += 1
                line_str = line.decode("utf-8", errors="ignore") if isinstance(line, bytes) else str(line)
                logger.info(
                    "stdout line received",
                    session_id=session_id,
                    line_count=line_count,
                    line_preview=line_str[:500] if len(line_str) > 500 else line_str,
                )
                parsed, error = safe_parse_jsonl_line(line)
                if error:
                    logger.warning(
                        "Failed to parse JSONL line",
                        session_id=session_id,
                        error=error,
                    )
                    await queue.put(
                        SSEEvent(
                            event_type=SSEEventType.ERROR,
                            session_id=session_id,
                            engine="claude",
                            payload={"error": error},
                        )
                    )
                    continue

                # 🔥 检测需要用户交互的消息类型
                event_type = SSEEventType.OUTPUT
                if parsed:
                    # 检测权限请求（tool_use 类型，需要用户授权的工具）
                    if self._is_permission_request(parsed):
                        event_type = SSEEventType.PERMISSION_REQUEST
                        logger.info(
                            "Permission request detected",
                            session_id=session_id,
                            tool_name=self._get_tool_name(parsed),
                        )
                        if isinstance(parsed, dict):
                            parsed = {
                                **parsed,
                                "meta": {
                                    **(parsed.get("meta") or {}),
                                    "skip_permissions": self._runner.should_skip_permissions(session_id),
                                },
                            }

                logger.info(
                    "Sending SSE event to queue",
                    session_id=session_id,
                    line_count=line_count,
                    event_type=event_type.value,
                )
                await queue.put(
                    SSEEvent(
                        event_type=event_type,
                        session_id=session_id,
                        engine="claude",
                        payload=parsed,
                    )
                )
            logger.info(
                "stdout reader finished",
                session_id=session_id,
                total_lines=line_count,
            )

        async def read_stderr():
            assert process.stderr is not None
            logger.info("Starting stderr reader", session_id=session_id)
            async for line in process.stderr:
                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue
                logger.warning(
                    "stderr output",
                    session_id=session_id,
                    text=text,
                )
            logger.info("stderr reader finished", session_id=session_id)

        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())
        timeout_task = asyncio.create_task(asyncio.sleep(settings.SESSION_TIMEOUT_SECONDS))

        try:
            while True:
                if timeout_task.done():
                    process.terminate()
                    await queue.put(
                        SSEEvent(
                            event_type=SSEEventType.ERROR,
                            session_id=session_id,
                            engine="claude",
                            payload={"error": "session timeout"},
                        )
                    )
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    if process.returncode is not None and queue.empty():
                        break

            await process.wait()
            await self._repository.update_session_status(session_id, "completed")
        finally:
            stdout_task.cancel()
            stderr_task.cancel()
            timeout_task.cancel()
            self._registry.remove(session_id)
            await self._runner.release(session_id)
            yield SSEEvent(
                event_type=SSEEventType.COMPLETE,
                session_id=session_id,
                engine="claude",
                payload={"exitCode": process.returncode},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
