"""
上下文管理服务
"""
from typing import Optional

from app.services.storage.repositories import StorageRepository


class ContextManagerService:
    """上下文管理业务服务"""

    def __init__(self, repository: StorageRepository) -> None:
        self._repository = repository

    def get_config(self) -> dict:
        return {
            "enabled": True,
            "maxContextTokens": 120000,
            "compactionThreshold": 0.85,
            "minCompactionInterval": 300,
            "compactionStrategy": "Smart",
            "preserveRecentMessages": True,
            "preserveMessageCount": 10,
            "customInstructions": None,
        }

    async def compact(self, session_id: str) -> Optional[str]:
        await self._repository.upsert_context_compaction(
            session_id=session_id,
            token_count=0,
            message_count=0,
            summary=None,
        )
        return None
