"""
SSE (Server-Sent Events) 流式传输模块

提供 SSE 事件生成和连接管理
"""
import asyncio
import json
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional
from enum import Enum

import structlog

logger = structlog.get_logger()


class SSEEventType(str, Enum):
    """SSE 事件类型"""
    SESSION_INIT = "session_init"
    OUTPUT = "output"
    ERROR = "error"
    COMPLETE = "complete"
    KEEPALIVE = "keepalive"
    PERMISSION_REQUEST = "permission_request"  # 🔥 新增：权限请求事件


class SSEEvent:
    """SSE 事件"""

    def __init__(
        self,
        event_type: SSEEventType,
        session_id: str,
        engine: str,
        payload: Optional[Any] = None,
        timestamp: Optional[str] = None,
    ):
        self.type = event_type
        self.session_id = session_id
        self.engine = engine
        self.payload = payload
        self.timestamp = timestamp or datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "sessionId": self.session_id,
            "engine": self.engine,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_sse_format(self) -> str:
        """
        转换为 SSE 格式

        格式:
        event: <event_type>
        data: <json_data>

        """
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {self.type.value}\ndata: {data}\n\n"


async def sse_keepalive_generator(interval_seconds: int = 15) -> AsyncIterator[str]:
    """
    SSE 心跳生成器

    定期发送 keepalive 事件，防止连接超时
    """
    while True:
        await asyncio.sleep(interval_seconds)
        # 发送注释作为心跳（SSE 标准）
        yield ": keepalive\n\n"


async def merge_with_keepalive(
    event_generator: AsyncIterator[SSEEvent],
    keepalive_interval: int = 15
) -> AsyncIterator[str]:
    """
    合并事件流和心跳

    Args:
        event_generator: 事件生成器
        keepalive_interval: 心跳间隔（秒）

    Yields:
        SSE 格式的字符串
    """
    keepalive_task = None

    try:
        # 创建心跳任务
        keepalive_gen = sse_keepalive_generator(keepalive_interval)
        keepalive_task = asyncio.create_task(keepalive_gen.__anext__())

        # 处理事件流
        async for event in event_generator:
            # 如果心跳已触发，发送心跳
            if keepalive_task.done():
                try:
                    keepalive_msg = await keepalive_task
                    yield keepalive_msg
                except StopAsyncIteration:
                    pass
                # 重新创建心跳任务
                keepalive_task = asyncio.create_task(keepalive_gen.__anext__())

            # 发送实际事件
            yield event.to_sse_format()

            # 如果是 complete 事件，结束流
            if event.type == SSEEventType.COMPLETE:
                logger.info("sse_stream_complete", session_id=event.session_id)
                break

    finally:
        # 清理心跳任务
        if keepalive_task and not keepalive_task.done():
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass


class SSEManager:
    """SSE 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, int] = {}

    def register_connection(self, session_id: str):
        """注册连接"""
        if session_id not in self.active_connections:
            self.active_connections[session_id] = 0
        self.active_connections[session_id] += 1
        logger.info(
            "sse_connection_registered",
            session_id=session_id,
            connection_count=self.active_connections[session_id],
        )

    def unregister_connection(self, session_id: str):
        """注销连接"""
        if session_id in self.active_connections:
            self.active_connections[session_id] -= 1
            if self.active_connections[session_id] <= 0:
                del self.active_connections[session_id]
            logger.info(
                "sse_connection_unregistered",
                session_id=session_id,
                connection_count=self.active_connections.get(session_id, 0),
            )

    def get_connection_count(self, session_id: str) -> int:
        """获取连接数"""
        return self.active_connections.get(session_id, 0)


# 全局 SSE 管理器实例
sse_manager = SSEManager()
