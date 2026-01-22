"""
Storage repository (no-op).

Database persistence is disabled; all methods are safe no-ops.
"""
from typing import Optional


class StorageRepository:
    """No-op storage repository (kept for interface compatibility)."""

    def __init__(self, session: Optional[object] = None) -> None:
        self._session = session

    async def create_session(self, session_id: str, engine: str, project_path: str, status: str) -> None:
        return

    async def update_session_status(self, session_id: str, status: str) -> None:
        return

    async def insert_message(
        self,
        session_id: str,
        role: str,
        content: str,
        delta: bool,
        raw_json: Optional[dict],
    ) -> None:
        return

    async def insert_usage(
        self,
        session_id: str,
        engine: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost: float,
    ) -> None:
        return

    async def session_exists(self, session_id: str) -> bool:
        return True

    async def get_translation_cache(self, source_hash: str) -> Optional[object]:
        return None

    async def save_translation_cache(
        self,
        source_hash: str,
        source_lang: str,
        target_lang: str,
        translated_text: str,
    ) -> None:
        return

    async def upsert_context_compaction(
        self,
        session_id: str,
        token_count: int,
        message_count: int,
        summary: Optional[str],
    ) -> None:
        return

    async def get_usage_totals(self) -> dict:
        return {"totalTokens": 0, "totalCost": 0}

    async def get_usage_by_engine(self) -> dict:
        return {
            "claude": {"tokens": 0, "cost": 0},
            "codex": {"tokens": 0, "cost": 0},
            "gemini": {"tokens": 0, "cost": 0},
        }

    async def get_usage_by_model(self) -> list[dict]:
        return []
