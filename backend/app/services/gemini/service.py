"""
Gemini 会话服务
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Optional

import structlog

from app.core.config import settings
from app.core.errors import SessionNotFoundError
from app.core.sse import SSEEvent, SSEEventType
from app.schemas.gemini import GeminiExecuteRequest
from app.services.gemini.parser import safe_parse_jsonl_line
from app.services.gemini.runner import GeminiRunner
from app.services.storage.repositories import StorageRepository

logger = structlog.get_logger()


class GeminiSessionRegistry:
    """Gemini 会话进程注册表"""

    def __init__(self) -> None:
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    def register(self, session_id: str, process: asyncio.subprocess.Process) -> None:
        self._processes[session_id] = process

    def get(self, session_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(session_id)

    def remove(self, session_id: str) -> None:
        self._processes.pop(session_id, None)

    def list_sessions(self) -> Dict[str, asyncio.subprocess.Process]:
        return dict(self._processes)


gemini_registry = GeminiSessionRegistry()


class GeminiService:
    """Gemini 业务服务"""

    def __init__(
        self,
        repository: StorageRepository,
        runner: GeminiRunner,
        registry: GeminiSessionRegistry,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._registry = registry

    async def execute(self, payload: GeminiExecuteRequest) -> str:
        session_id = payload.sessionId or str(uuid.uuid4())
        exists = await self._repository.session_exists(session_id)
        if not exists:
            await self._repository.create_session(
                session_id=session_id,
                engine="gemini",
                project_path=payload.projectPath,
                status="running",
            )
        else:
            await self._repository.update_session_status(session_id, "running")

        process = await self._runner.start(
            project_path=payload.projectPath,
            prompt=payload.prompt,
            model=payload.model,
            approval_mode=payload.approvalMode,
            include_directories=payload.includeDirectories,
            debug=payload.debug,
        )
        self._registry.register(session_id, process)
        return session_id

    async def cancel(self, session_id: str) -> None:
        process = self._registry.get(session_id)
        if not process:
            raise SessionNotFoundError(session_id)
        process.terminate()
        await self._repository.update_session_status(session_id, "canceled")
        self._registry.remove(session_id)
        await self._runner.release()

    async def cancel_all(self) -> None:
        for session_id, process in self._registry.list_sessions().items():
            process.terminate()
            await self._repository.update_session_status(session_id, "canceled")
            self._registry.remove(session_id)
            await self._runner.release()

    async def stream_events(self, session_id: str) -> AsyncIterator[SSEEvent]:
        process = self._registry.get(session_id)
        if not process:
            raise SessionNotFoundError(session_id)

        yield SSEEvent(
            event_type=SSEEventType.SESSION_INIT,
            session_id=session_id,
            engine="gemini",
        )

        queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async def read_stdout():
            assert process.stdout is not None
            async for line in process.stdout:
                parsed, error = safe_parse_jsonl_line(line)
                if error:
                    # 🔥 静默跳过非 JSON 行（Gemini CLI 的日志信息）
                    # 只记录到日志，不发送给前端
                    text = line.decode("utf-8", errors="ignore").strip()
                    logger.debug("gemini_non_json_output", text=text[:100])
                    continue
                await queue.put(
                    SSEEvent(
                        event_type=SSEEventType.OUTPUT,
                        session_id=session_id,
                        engine="gemini",
                        payload=parsed,
                    )
                )

        async def read_stderr():
            assert process.stderr is not None
            async for line in process.stderr:
                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue

                # 🔥 过滤 Gemini CLI 的正常日志信息（这些不是错误）
                ignored_patterns = [
                    "Loaded cached credentials",
                    "supports tool updates",
                    "Listening for changes",
                    "Tool execution for",
                    "denied by policy",
                    "Tool \"run_shell_command\" not found",
                ]

                # 检查是否是需要忽略的日志
                should_ignore = any(pattern in text for pattern in ignored_patterns)
                if should_ignore:
                    logger.debug("gemini_stderr_ignored", text=text[:100])
                    continue

                # 只发送真正的错误信息
                await queue.put(
                    SSEEvent(
                        event_type=SSEEventType.ERROR,
                        session_id=session_id,
                        engine="gemini",
                        payload={"error": text},
                    )
                )

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
                            engine="gemini",
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
            await self._runner.release()
            yield SSEEvent(
                event_type=SSEEventType.COMPLETE,
                session_id=session_id,
                engine="gemini",
                payload={"exitCode": process.returncode},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
