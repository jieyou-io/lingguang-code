"""
API 依赖注入模块
"""
from typing import AsyncIterator, Optional


async def get_db_session() -> AsyncIterator[Optional[object]]:
    """获取数据库会话（已禁用持久化）"""
    yield None
