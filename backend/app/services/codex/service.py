"""
Codex 会话服务
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Optional

import structlog

from app.core.errors import SessionNotFoundError
from app.core.sse import SSEEvent, SSEEventType
from app.schemas.codex import CodexExecuteRequest, CodexResumeRequest
from app.services.codex.parser import safe_parse_json_line
from app.services.codex.runner import CodexRunner
from app.services.storage.repositories import StorageRepository

logger = structlog.get_logger()


class CodexSessionState:
    """Codex 会话状态"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self.task: Optional[asyncio.Task[None]] = None


class CodexSessionRegistry:
    """Codex 会话注册表"""

    def __init__(self) -> None:
        self._sessions: Dict[str, CodexSessionState] = {}

    def register(self, session_id: str, state: CodexSessionState) -> None:
        self._sessions[session_id] = state

    def get(self, session_id: str) -> Optional[CodexSessionState]:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


codex_registry = CodexSessionRegistry()


class CodexService:
    """Codex 业务服务"""

    def __init__(
        self,
        repository: StorageRepository,
        runner: CodexRunner,
        registry: CodexSessionRegistry,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._registry = registry

    async def execute(self, payload: CodexExecuteRequest) -> str:
        session_id = payload.sessionId or str(uuid.uuid4())
        exists = await self._repository.session_exists(session_id)
        if not exists:
            await self._repository.create_session(
                session_id=session_id,
                engine="codex",
                project_path=payload.projectPath,
                status="running",
            )
        else:
            await self._repository.update_session_status(session_id, "running")
        await self._start_task(session_id, payload.model_dump())
        return session_id

    async def resume(self, payload: CodexResumeRequest) -> str:
        exists = await self._repository.session_exists(payload.sessionId)
        if not exists:
            raise SessionNotFoundError(payload.sessionId)
        await self._repository.update_session_status(payload.sessionId, "running")
        await self._start_task(payload.sessionId, payload.model_dump())
        return payload.sessionId

    async def cancel(self, session_id: str) -> None:
        state = self._registry.get(session_id)
        if not state:
            raise SessionNotFoundError(session_id)
        if state.task and not state.task.done():
            state.task.cancel()
        await self._repository.update_session_status(session_id, "canceled")
        self._registry.remove(session_id)

    async def stream_events(self, session_id: str) -> AsyncIterator[SSEEvent]:
        state = self._registry.get(session_id)
        if not state:
            raise SessionNotFoundError(session_id)

        yield SSEEvent(
            event_type=SSEEventType.SESSION_INIT,
            session_id=session_id,
            engine="codex",
        )

        while True:
            event = await state.queue.get()
            yield event
            if event.type == SSEEventType.COMPLETE:
                self._registry.remove(session_id)
                break

    async def _start_task(self, session_id: str, payload: Dict[str, object]) -> None:
        state = CodexSessionState(session_id)
        self._registry.register(session_id, state)

        async def run_codex() -> None:
            try:
                async for line in self._runner.stream(payload):
                    parsed, error = safe_parse_json_line(line)
                    if error:
                        await state.queue.put(
                            SSEEvent(
                                event_type=SSEEventType.ERROR,
                                session_id=session_id,
                                engine="codex",
                                payload={"error": error},
                            )
                        )
                        continue
                    await state.queue.put(
                        SSEEvent(
                            event_type=SSEEventType.OUTPUT,
                            session_id=session_id,
                            engine="codex",
                            payload=parsed,
                        )
                    )
                await self._repository.update_session_status(session_id, "completed")
            except asyncio.CancelledError:
                logger.info("codex_session_cancelled", session_id=session_id)
                await state.queue.put(
                    SSEEvent(
                        event_type=SSEEventType.ERROR,
                        session_id=session_id,
                        engine="codex",
                        payload={"error": "session canceled"},
                    )
                )
            except Exception as exc:
                logger.exception("codex_session_error", session_id=session_id)
                await state.queue.put(
                    SSEEvent(
                        event_type=SSEEventType.ERROR,
                        session_id=session_id,
                        engine="codex",
                        payload={"error": str(exc)},
                    )
                )
                await self._repository.update_session_status(session_id, "failed")
            finally:
                await state.queue.put(
                    SSEEvent(
                        event_type=SSEEventType.COMPLETE,
                        session_id=session_id,
                        engine="codex",
                        payload={"exitCode": 0},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )

        state.task = asyncio.create_task(run_codex())
